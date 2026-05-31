#
# Owner-only ad commands.
#

import os
import tempfile

from pyrogram import filters
from pyrogram.types import Message

from YukkiMusic import app
from YukkiMusic.misc import SUDOERS
from YukkiMusic.utils.database import (
    get_ad_config,
    set_ad_text,
    set_ad_audio,
    clear_ad,
    set_ad_enabled,
)


def _is_sudo(_, __, m: Message):
    if not m.from_user:
        return False
    return m.from_user.id in SUDOERS


sudo_filter = filters.create(_is_sudo)


# ---------------------------------------------------------------------------
# /setad <metin> — TTS reklam
# ---------------------------------------------------------------------------
@app.on_message(filters.command(["setad"]) & sudo_filter)
async def cmd_setad(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Kullanım**\n"
            "`/setad <reklam metni>` — TTS ile sesli reklam ayarlar.\n"
            "Opsiyonel: `/setad [voice=tr-TR-EmelNeural] <metin>` (ses seçimi)\n\n"
            "Örnek: `/setad Melih Music botu kullandığınız için teşekkürler! "
            "Daha fazlası için @GoogleBilgi kanalımıza katılın.`"
        )
    text = message.text.split(None, 1)[1].strip()
    voice = "tr-TR-AhmetNeural"
    if text.startswith("[voice="):
        try:
            voice = text.split("[voice=", 1)[1].split("]", 1)[0]
            text = text.split("]", 1)[1].strip()
        except Exception:
            pass
    if not text:
        return await message.reply_text("Reklam metni boş olamaz.")
    await set_ad_text(text, voice, message.from_user.id)
    await message.reply_text(
        f"✅ **Reklam (TTS) kaydedildi.**\n"
        f"• Ses: `{voice}`\n"
        f"• Metin: {text[:300]}{'…' if len(text) > 300 else ''}\n\n"
        f"Reklam **açık**. Kapatmak için /adoff."
    )


# ---------------------------------------------------------------------------
# /setadfile  (reply to audio/voice) — audio dosyası reklam
# ---------------------------------------------------------------------------
@app.on_message(filters.command(["setadfile", "setadaudio"]) & sudo_filter)
async def cmd_setadfile(client, message: Message):
    reply = message.reply_to_message
    if not reply or not (
        reply.audio or reply.voice or
        (reply.document and (reply.document.mime_type or "").startswith("audio"))
    ):
        return await message.reply_text(
            "**Kullanım**\n"
            "Bir ses dosyası ya da voice mesajına **reply** atarak "
            "`/setadfile` yazın. Bot dosyayı kaydedip reklam olarak kullanır."
        )
    media = reply.audio or reply.voice or reply.document
    status = await message.reply_text("⬇️ Reklam sesi indiriliyor...")
    with tempfile.TemporaryDirectory() as td:
        # download to temp folder, then set_ad_audio copies it into ads/
        path = await reply.download(file_name=os.path.join(td, "ad_src"))
        try:
            dest = await set_ad_audio(path, message.from_user.id)
        except Exception as e:
            return await status.edit_text(f"❌ Hata: `{type(e).__name__}: {e}`")
    dur = getattr(media, "duration", None) or 0
    size_kb = os.path.getsize(dest) / 1024 if os.path.isfile(dest) else 0
    await status.edit_text(
        f"✅ **Reklam (audio) kaydedildi.**\n"
        f"• Dosya: `{dest}`\n"
        f"• Süre: ~{int(dur)}s\n"
        f"• Boyut: {size_kb:.0f} KB\n\n"
        f"Reklam **açık**. Kapatmak için /adoff."
    )


# ---------------------------------------------------------------------------
# /adstatus
# ---------------------------------------------------------------------------
@app.on_message(filters.command(["adstatus"]) & sudo_filter)
async def cmd_adstatus(client, message: Message):
    cfg = await get_ad_config()
    icon = "🟢" if cfg["enabled"] else "⚪"
    mode = cfg["mode"] or "none"
    body = (
        f"{icon} **Reklam durumu**\n"
        f"• Açık mı? {'Evet' if cfg['enabled'] else 'Hayır'}\n"
        f"• Mod: `{mode}`\n"
    )
    if mode == "tts":
        body += f"• Ses: `{cfg.get('voice') or '-'}`\n"
        body += f"• Metin: {(cfg.get('text') or '')[:300]}\n"
    elif mode == "audio":
        ap = cfg.get("audio_path") or ""
        exists = os.path.isfile(ap)
        body += f"• Dosya: `{ap}` ({'mevcut' if exists else 'BULUNAMADI'})\n"
    else:
        body += "_(henüz ayarlanmadı; /setad veya /setadfile kullanın)_\n"
    body += (
        "\nKomutlar: /setad · /setadfile · /adon · /adoff · /clearad"
    )
    await message.reply_text(body)


# ---------------------------------------------------------------------------
# /adon  /adoff
# ---------------------------------------------------------------------------
@app.on_message(filters.command(["adon"]) & sudo_filter)
async def cmd_adon(client, message: Message):
    cfg = await get_ad_config()
    if cfg["mode"] == "none":
        return await message.reply_text(
            "Önce bir reklam ayarlayın: `/setad <metin>` veya `/setadfile` (audio reply)."
        )
    await set_ad_enabled(True, message.from_user.id)
    await message.reply_text("🟢 Reklam **açıldı**. Yeni şarkı çağrısında oynayacak.")


@app.on_message(filters.command(["adoff"]) & sudo_filter)
async def cmd_adoff(client, message: Message):
    await set_ad_enabled(False, message.from_user.id)
    await message.reply_text("⚪ Reklam **kapatıldı**.")


# ---------------------------------------------------------------------------
# /clearad
# ---------------------------------------------------------------------------
@app.on_message(filters.command(["clearad"]) & sudo_filter)
async def cmd_clearad(client, message: Message):
    await clear_ad(message.from_user.id)
    await message.reply_text("🗑 Reklam tamamen silindi.")
