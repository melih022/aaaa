#
# Owner-only diagnostics: /logs, /lasterror, /testytdlp, /env, /pyver
#

import asyncio
import io
import os
import platform
import subprocess
import sys
import traceback
from pathlib import Path

from pyrogram import filters
from pyrogram.types import Message

import config
from YukkiMusic import LOGGER, app

LOG_PATHS = [
    "/var/log/supervisor/melihbot.err.log",
    "Yukkilogs.txt",
]

# Ring buffer of last 20 exception tracebacks captured anywhere in the bot.
LAST_ERRORS: list[str] = []


def record_exception(prefix: str = ""):
    tb = traceback.format_exc()
    msg = f"{prefix}\n{tb}".strip()
    LAST_ERRORS.append(msg)
    if len(LAST_ERRORS) > 20:
        LAST_ERRORS.pop(0)
    LOGGER("YukkiMusic.diag").error(msg[:500])


def _is_owner(uid):
    try:
        return int(uid) in config.OWNER_ID
    except Exception:
        return False


@app.on_message(filters.command(["logs", "log"]) & filters.private)
async def logs_cmd(client, message: Message):
    if not _is_owner(message.from_user.id):
        return await message.reply_text("⛔ Sadece bot sahibi kullanabilir.")
    # Argument: how many lines
    try:
        lines = int(message.command[1]) if len(message.command) > 1 else 80
    except ValueError:
        lines = 80
    lines = max(10, min(lines, 1000))

    out = []
    for p in LOG_PATHS:
        if not Path(p).exists():
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                txt = f.read().splitlines()[-lines:]
            out.append(f"━━━━━ {p} (son {len(txt)} satır) ━━━━━\n" + "\n".join(txt))
        except Exception as e:
            out.append(f"--- {p} hata: {e} ---")

    if not out:
        return await message.reply_text("📭 Log dosyası bulunamadı.")

    text = "\n\n".join(out)
    if len(text) <= 3800:
        await message.reply_text(f"```log\n{text[-3800:]}\n```")
    else:
        # Send as file
        buf = io.BytesIO(text.encode("utf-8"))
        buf.name = "melihbot.log"
        await message.reply_document(
            document=buf, caption=f"📝 Son {lines} satır log"
        )


@app.on_message(filters.command(["lasterror", "errors"]) & filters.private)
async def lasterror_cmd(client, message: Message):
    if not _is_owner(message.from_user.id):
        return await message.reply_text("⛔ Sadece bot sahibi kullanabilir.")
    if not LAST_ERRORS:
        return await message.reply_text(
            "✅ Kayıtlı hata yok. (Henüz bir handler exception fırlatmadı.)"
        )
    n = min(5, len(LAST_ERRORS))
    text = "\n\n=====\n\n".join(LAST_ERRORS[-n:])
    if len(text) <= 3800:
        await message.reply_text(f"```\n{text[-3800:]}\n```")
    else:
        buf = io.BytesIO(text.encode("utf-8"))
        buf.name = "errors.txt"
        await message.reply_document(buf, caption=f"📛 Son {n} hata")


@app.on_message(filters.command(["testytdlp", "ytdlp"]) & filters.private)
async def testytdlp(client, message: Message):
    if not _is_owner(message.from_user.id):
        return
    args = message.text.split(None, 1)
    query = args[1] if len(args) > 1 else "Ayna Sevdim Seni"
    wait = await message.reply_text(f"🔍 yt-dlp test: `{query}`")
    try:
        from YukkiMusic.platforms.Youtube import _ytsearch
        results = await _ytsearch(query, 3)
    except Exception as e:
        record_exception("testytdlp")
        return await wait.edit_text(
            f"❌ Hata: `{type(e).__name__}: {e}`"[:3800]
        )
    if not results:
        return await wait.edit_text("📭 Sonuç yok. yt-dlp engellenmiş olabilir.")
    text = "✅ Çalışıyor!\n\n"
    for i, r in enumerate(results, 1):
        text += f"{i}. {r['title'][:70]}\n   ⏱ {r['duration']} | 🔗 {r['link']}\n\n"
    await wait.edit_text(text[:3800])


@app.on_message(filters.command(["pyver", "version", "ver"]) & filters.private)
async def pyver_cmd(client, message: Message):
    if not _is_owner(message.from_user.id):
        return
    try:
        import pyrogram, pytgcalls, yt_dlp, motor
        text = (
            f"🐍 **System Info**\n"
            f"  • Python: `{platform.python_version()}`\n"
            f"  • OS: `{platform.platform()}`\n\n"
            f"📦 **Library Versions**\n"
            f"  • pyrogram/kurigram: `{pyrogram.__version__}`\n"
            f"  • pytgcalls: `{pytgcalls.__version__ if hasattr(pytgcalls,'__version__') else 'unknown'}`\n"
            f"  • yt-dlp: `{yt_dlp.version.__version__}`\n"
            f"  • motor: `{motor.version}`\n\n"
            f"⚙️ **Config**\n"
            f"  • Owner: `{config.OWNER_ID}`\n"
            f"  • Log group: `{config.LOG_GROUP_ID}`\n"
            f"  • Mongo: `{config.MONGO_DB_URI[:40]}...`\n"
        )
    except Exception as e:
        text = f"❌ {type(e).__name__}: {e}"
    await message.reply_text(text)


@app.on_message(filters.command(["env"]) & filters.private)
async def env_cmd(client, message: Message):
    if not _is_owner(message.from_user.id):
        return
    p = Path("/app/melih_bot_v2/.env")
    if not p.exists():
        return await message.reply_text(".env yok.")
    txt = p.read_text(encoding="utf-8")
    # Sanitize sensitive values
    out = []
    for line in txt.splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            if v.strip():
                v = v[:6] + "..." + v[-6:] if len(v) > 16 else "***"
            out.append(f"{k}={v}")
        else:
            out.append(line)
    await message.reply_text(f"```env\n{chr(10).join(out)[-3800:]}\n```")


# Global pyrogram exception logger: catch any unhandled exception in handlers.
import pyrogram

_orig_dispatcher_handle_update = None
try:
    from pyrogram.dispatcher import Dispatcher
    _orig = Dispatcher.handle_update

    async def _patched(self, packet, parser, handlers, args):
        try:
            return await _orig(self, packet, parser, handlers, args)
        except Exception:
            record_exception("dispatcher.handle_update")
            raise

    Dispatcher.handle_update = _patched
except Exception:
    pass
