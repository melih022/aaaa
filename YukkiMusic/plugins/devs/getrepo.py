#
# /getrepo  – Owner sends himself the latest repo zip via Telegram.
# /makerepo – Owner forces a fresh re-zip from disk and then sends.
#

import io
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

from pyrogram import filters
from pyrogram.types import Message

import config
from YukkiMusic import LOGGER, app

REPO_DIR = Path("/app/melih_bot_v2")
REPO_ZIP = REPO_DIR / "melih_bot_repo.zip"

EXCLUDES = {
    "__pycache__", ".git", "downloads", "cache",
    "Yukkilogs.txt", "melih_bot_repo.zip",
}


def _is_owner(uid):
    try:
        return int(uid) in config.OWNER_ID
    except Exception:
        return False


def _make_zip():
    if REPO_ZIP.exists():
        REPO_ZIP.unlink()
    with zipfile.ZipFile(REPO_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(REPO_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDES]
            for f in files:
                if f in EXCLUDES or f.endswith(".pyc"):
                    continue
                full = Path(root) / f
                if full == REPO_ZIP:
                    continue
                arc = full.relative_to(REPO_DIR.parent)
                zf.write(full, arc)
    return REPO_ZIP


@app.on_message(filters.command(["getrepo", "repo"]) & filters.private)
async def get_repo(client, message: Message):
    if not _is_owner(message.from_user.id):
        return await message.reply_text("⛔ Sadece bot sahibi.")
    status = await message.reply_text("📦 ZIP hazırlanıyor…")
    try:
        zip_path = _make_zip()
        size_mb = zip_path.stat().st_size / (1024 * 1024)
    except Exception as e:
        return await status.edit_text(f"❌ {type(e).__name__}: {e}")

    await status.edit_text(f"📤 Gönderiliyor… ({size_mb:.1f} MB)")
    try:
        await message.reply_document(
            document=str(zip_path),
            caption=(
                f"📦 **Melih Music Bot — full repo**\n\n"
                f"📁 Boyut: `{size_mb:.1f} MB`\n"
                f"🐍 Python: 3.12+\n"
                f"📌 Sürüm: 2026-modernized\n\n"
                f"Kurulum: `unzip melih_bot_repo.zip && cd melih_bot_v2 && "
                f"pip install -r requirements.txt && bash start`\n\n"
                f"⚠️ `.env` içindeki kimlik bilgilerini production öncesi yenileyin."
            ),
            file_name="melih_bot_v2.zip",
        )
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Gönderim hatası: {type(e).__name__}: {e}")


@app.on_message(filters.command(["makerepo"]) & filters.private)
async def make_repo(client, message: Message):
    if not _is_owner(message.from_user.id):
        return
    status = await message.reply_text("📦 Yeniden zip'leniyor…")
    try:
        zip_path = _make_zip()
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        await status.edit_text(
            f"✅ Zip yenilendi: `{zip_path}`\n"
            f"📁 Boyut: `{size_mb:.1f} MB`\n\n"
            f"`/getrepo` ile indirin."
        )
    except Exception as e:
        await status.edit_text(f"❌ {type(e).__name__}: {e}")
