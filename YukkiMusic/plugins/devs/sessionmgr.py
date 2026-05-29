#
# Session manager: /genstring (interactive phone+OTP) and /setstring (paste).
# Owner-only. Stores STRING_SESSION{n} in .env + MongoDB and triggers a clean restart.
#

import asyncio
import os
import re
import sys
import time

from pyrogram import Client, filters
from pyrogram.errors import (
    AuthKeyUnregistered,
    BadRequest,
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberBanned,
    PhoneNumberInvalid,
    SessionPasswordNeeded,
)
from pyrogram.types import Message

import config
from YukkiMusic import LOGGER, app
from YukkiMusic.utils.env_writer import (
    find_next_free_slot,
    save_session,
    update_env,
)

# In-memory wizard state: {user_id: {...}}
STATE: dict = {}
STATE_TIMEOUT_SEC = 600  # 10 min


def _is_owner(user_id: int) -> bool:
    try:
        return int(user_id) in config.OWNER_ID
    except Exception:
        return False


def _now() -> int:
    return int(time.time())


def _state(user_id: int) -> dict:
    s = STATE.get(user_id)
    if s and _now() - s.get("ts", 0) > STATE_TIMEOUT_SEC:
        STATE.pop(user_id, None)
        return None
    return s


def _set_state(user_id: int, **kw) -> dict:
    cur = STATE.get(user_id, {})
    cur.update(kw)
    cur["ts"] = _now()
    STATE[user_id] = cur
    return cur


def _clear_state(user_id: int):
    STATE.pop(user_id, None)


# ---------- /genstring : interactive ----------

@app.on_message(filters.command(["genstring", "newsession"]) & filters.private)
async def genstring_start(client, message: Message):
    if not _is_owner(message.from_user.id):
        return await message.reply_text(
            "⛔ Bu komut yalnızca bot sahibi (`OWNER_ID`) tarafından kullanılabilir."
        )
    slot = find_next_free_slot()
    if slot is None:
        return await message.reply_text(
            "⚠️ Tüm 5 string-session slotu dolu. "
            "Bir slotu boşaltmak için `/clearsession <slot>` kullanın."
        )
    _set_state(
        message.from_user.id,
        step="phone",
        slot=slot,
    )
    await message.reply_text(
        f"🔐 **String Session Üretici** (Slot #{slot})\n\n"
        "1️⃣ Telefon numaranızı uluslararası formatta gönderin.\n"
        "Örnek: `+905551234567`\n\n"
        "İptal: /cancel"
    )


@app.on_message(filters.command(["cancel"]) & filters.private)
async def genstring_cancel(client, message: Message):
    if _state(message.from_user.id):
        _clear_state(message.from_user.id)
        await message.reply_text("❌ İşlem iptal edildi.")
    else:
        await message.reply_text("Aktif işlem yok.")


@app.on_message(
    filters.private
    & ~filters.command(
        [
            "genstring", "newsession", "cancel", "setstring",
            "clearsession", "restart", "sessions", "start", "help",
        ]
    ),
    group=-1,  # run before generic handlers
)
async def genstring_step(client, message: Message):
    user_id = message.from_user.id
    s = _state(user_id)
    if not s:
        return  # not in a wizard

    if not _is_owner(user_id):
        return

    text = (message.text or "").strip()

    # ===== Step 1: phone number =====
    if s["step"] == "phone":
        m = re.match(r"^\+?\d{6,18}$", text.replace(" ", "").replace("-", ""))
        if not m:
            return await message.reply_text(
                "❌ Geçersiz telefon numarası. Tekrar deneyin: `+905551234567`"
            )
        phone = text.replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = "+" + phone

        wait = await message.reply_text("📡 Telegram'a bağlanılıyor…")
        try:
            tc = Client(
                name=f":memory:gs_{user_id}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                in_memory=True,
            )
            await tc.connect()
            sent = await tc.send_code(phone)
        except PhoneNumberInvalid:
            _clear_state(user_id)
            return await wait.edit_text("❌ Telefon numarası geçersiz.")
        except PhoneNumberBanned:
            _clear_state(user_id)
            return await wait.edit_text("❌ Bu numara Telegram tarafından yasaklı.")
        except FloodWait as e:
            _clear_state(user_id)
            return await wait.edit_text(
                f"⏳ FloodWait: {e.value} saniye sonra tekrar deneyin."
            )
        except Exception as e:
            _clear_state(user_id)
            return await wait.edit_text(f"❌ Hata: `{type(e).__name__}: {e}`")

        _set_state(
            user_id,
            step="code",
            phone=phone,
            code_hash=sent.phone_code_hash,
            tc=tc,
        )
        await wait.edit_text(
            "2️⃣ Telegram'dan gelen OTP kodunu girin.\n\n"
            "⚠️ **Güvenlik:** Kodu rakamlar arasına boşluk koyarak gönderin "
            "(örn: `1 2 3 4 5`). Aksi takdirde Telegram otomatik iptal eder.\n\n"
            "İptal: /cancel"
        )
        return

    # ===== Step 2: OTP code =====
    if s["step"] == "code":
        digits = re.sub(r"\D", "", text)
        if not digits or len(digits) < 4:
            return await message.reply_text(
                "❌ Geçersiz kod. Rakamları boşlukla ayırarak gönderin: `1 2 3 4 5`"
            )
        tc: Client = s["tc"]
        wait = await message.reply_text("🔑 Doğrulanıyor…")
        try:
            await tc.sign_in(
                phone_number=s["phone"],
                phone_code_hash=s["code_hash"],
                phone_code=digits,
            )
        except PhoneCodeInvalid:
            return await wait.edit_text("❌ Kod yanlış. Tekrar gönderin.")
        except PhoneCodeExpired:
            _clear_state(user_id)
            try:
                await tc.disconnect()
            except Exception:
                pass
            return await wait.edit_text(
                "❌ Kod süresi doldu. /genstring ile baştan başlayın."
            )
        except SessionPasswordNeeded:
            _set_state(user_id, step="2fa", tc=tc)
            return await wait.edit_text(
                "3️⃣ Hesabınızda **2FA şifresi** etkin. Cloud password'unuzu gönderin.\n\n"
                "⚠️ Mesajı **gönderdikten hemen sonra silin**.\n"
                "İptal: /cancel"
            )
        except Exception as e:
            _clear_state(user_id)
            try:
                await tc.disconnect()
            except Exception:
                pass
            return await wait.edit_text(f"❌ Hata: `{type(e).__name__}: {e}`")

        return await _finish(tc, user_id, message, wait)

    # ===== Step 3: 2FA password =====
    if s["step"] == "2fa":
        password = text
        tc: Client = s["tc"]
        wait = await message.reply_text("🔑 2FA doğrulanıyor…")
        try:
            await tc.check_password(password)
        except PasswordHashInvalid:
            return await wait.edit_text("❌ 2FA şifresi yanlış. Tekrar gönderin.")
        except Exception as e:
            _clear_state(user_id)
            try:
                await tc.disconnect()
            except Exception:
                pass
            return await wait.edit_text(f"❌ Hata: `{type(e).__name__}: {e}`")

        # Try to delete the password message for security
        try:
            await message.delete()
        except Exception:
            pass

        return await _finish(tc, user_id, message, wait)


async def _finish(tc: Client, user_id: int, message: Message, wait: Message):
    """Common path after successful sign_in / check_password."""
    s = _state(user_id) or {}
    slot = s.get("slot", 1)
    try:
        session_string = await tc.export_session_string()
        me = await tc.get_me()
    except Exception as e:
        return await wait.edit_text(f"❌ Session export hatası: `{type(e).__name__}: {e}`")
    finally:
        try:
            await tc.disconnect()
        except Exception:
            pass

    try:
        await save_session(slot, session_string)
    except Exception as e:
        return await wait.edit_text(f"❌ Kayıt hatası: `{type(e).__name__}: {e}`")

    _clear_state(user_id)
    await wait.edit_text(
        f"✅ **Session created & saved!**\n\n"
        f"👤 Account: `{me.first_name}` (@{me.username or '—'})\n"
        f"🆔 ID: `{me.id}`\n"
        f"📦 Slot: `STRING_SESSION{slot if slot > 1 else ''}`\n\n"
        f"⚠️ The session string will be sent in the next message — "
        f"**save it somewhere safe** (do not share!).\n"
        f"♻️ Bot will restart in 8 seconds…"
    )
    # Send session string as separate message for easy copy-paste
    try:
        await message.reply_text(
            f"`{session_string}`",
            quote=False,
        )
        await message.reply_text(
            "⬆️ This is your **STRING_SESSION** — tap to copy. "
            "It is already saved automatically to .env and MongoDB; this message is for your backup."
        )
    except Exception:
        pass
    await asyncio.sleep(8)
    await _restart_self()


# ---------- /setstring : direct paste ----------

@app.on_message(filters.command(["setstring"]) & filters.private)
async def setstring_cmd(client, message: Message):
    if not _is_owner(message.from_user.id):
        return await message.reply_text("⛔ Sadece bot sahibi kullanabilir.")
    parts = message.text.split(None, 2)
    if len(parts) < 2:
        return await message.reply_text(
            "Kullanım:\n"
            "  • `/setstring <session_string>` — boş ilk slota yaz\n"
            "  • `/setstring <slot> <session_string>` — belirli slot (1-5)"
        )
    if len(parts) == 2:
        slot = find_next_free_slot()
        if slot is None:
            return await message.reply_text("⚠️ Boş slot yok. Bir slot belirtin (1-5).")
        session_string = parts[1].strip()
    else:
        try:
            slot = int(parts[1])
        except ValueError:
            return await message.reply_text("❌ Slot 1-5 arası bir sayı olmalı.")
        if slot < 1 or slot > 5:
            return await message.reply_text("❌ Slot 1-5 arası olmalı.")
        session_string = parts[2].strip()

    if len(session_string) < 100:
        return await message.reply_text("❌ Bu bir string-session'a benzemiyor (çok kısa).")

    wait = await message.reply_text("🔍 Session doğrulanıyor…")
    try:
        tc = Client(
            name=f":memory:check_{message.from_user.id}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_string,
            in_memory=True,
            no_updates=True,
        )
        await tc.connect()
        me = await tc.get_me()
        await tc.disconnect()
    except AuthKeyUnregistered:
        return await wait.edit_text("❌ Bu session geçersiz / iptal edilmiş.")
    except Exception as e:
        return await wait.edit_text(f"❌ Doğrulama hatası: `{type(e).__name__}: {e}`")

    try:
        await save_session(slot, session_string)
    except Exception as e:
        return await wait.edit_text(f"❌ Kayıt hatası: `{type(e).__name__}: {e}`")

    # Delete the message containing the session for security
    try:
        await message.delete()
    except Exception:
        pass

    await wait.edit_text(
        f"✅ **Session saved!**\n\n"
        f"👤 Account: `{me.first_name}` (@{me.username or '—'})\n"
        f"📦 Slot: `STRING_SESSION{slot if slot > 1 else ''}`\n\n"
        f"♻️ Bot will restart in 5 seconds…"
    )
    await asyncio.sleep(5)
    await _restart_self()


# ---------- /sessions : list status ----------

@app.on_message(filters.command(["sessions", "sessionstatus"]) & filters.private)
async def sessions_status(client, message: Message):
    if not _is_owner(message.from_user.id):
        return await message.reply_text("⛔ Sadece bot sahibi kullanabilir.")

    slots = [config.STRING1, config.STRING2, config.STRING3, config.STRING4, config.STRING5]
    lines = ["📦 **Session Slot Durumu**\n"]
    for i, s in enumerate(slots, start=1):
        ok = bool(s and s != "None")
        lines.append(f"  • Slot #{i}: {'✅ dolu' if ok else '⬜ boş'}")
    lines.append("")
    lines.append("Komutlar:")
    lines.append("  • /genstring – yeni session üret")
    lines.append("  • /setstring <session> – yapıştır")
    lines.append("  • /clearsession <slot> – slotu sil")
    lines.append("  • /restart – botu yeniden başlat")
    await message.reply_text("\n".join(lines))


# ---------- /clearsession <slot> ----------

@app.on_message(filters.command(["clearsession", "delsession"]) & filters.private)
async def clear_session_cmd(client, message: Message):
    if not _is_owner(message.from_user.id):
        return await message.reply_text("⛔ Sadece bot sahibi kullanabilir.")
    if len(message.command) < 2:
        return await message.reply_text("Kullanım: `/clearsession <slot 1-5>`")
    try:
        slot = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ Slot 1-5 arası bir sayı olmalı.")
    if slot < 1 or slot > 5:
        return await message.reply_text("❌ Slot 1-5 arası olmalı.")
    key = "STRING_SESSION" if slot == 1 else f"STRING_SESSION{slot}"
    update_env(key, "")
    try:
        from YukkiMusic.utils.env_writer import _mongo
        await _mongo().delete_one({"_id": f"slot_{slot}"})
    except Exception:
        pass
    await message.reply_text(
        f"🗑️ Slot #{slot} temizlendi. /restart ile etkinleştirin."
    )


# ---------- /restart ----------

@app.on_message(filters.command(["restart", "reboot"]) & filters.private)
async def restart_cmd(client, message: Message):
    if not _is_owner(message.from_user.id):
        return await message.reply_text("⛔ Sadece bot sahibi kullanabilir.")
    await message.reply_text("♻️ Bot yeniden başlatılıyor…")
    await asyncio.sleep(2)
    await _restart_self()


async def _restart_self():
    """Replace the current process with a fresh `python -m YukkiMusic` invocation.
    Supervisor / Docker will also auto-restart if exec replacement fails.
    """
    LOGGER("YukkiMusic").info("⟳ Restart triggered by owner.")
    try:
        await app.stop()
    except Exception:
        pass
    try:
        os.execv(sys.executable, [sys.executable, "-m", "YukkiMusic"])
    except Exception:
        # Last resort – exit and let supervisor restart us.
        os._exit(0)
