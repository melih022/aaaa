#
# Instagram Reels / Posts downloader plugin.
# Uses yt-dlp (works for public reels, posts, and IGTV).
#

import asyncio
import os
import re
import uuid

from pyrogram import filters
from pyrogram.types import Message

import yt_dlp

from config import BANNED_USERS
from YukkiMusic import app

INSTA_RE = re.compile(
    r"(https?://)?(www\.)?instagram\.com/(reel|reels|p|tv|stories)/[A-Za-z0-9_\-]+/?",
    re.IGNORECASE,
)

DL_DIR = "downloads/insta"
os.makedirs(DL_DIR, exist_ok=True)


def _ydl_download(url: str, out_dir: str):
    file_id = uuid.uuid4().hex
    opts = {
        "outtmpl": os.path.join(out_dir, f"{file_id}.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    ext = info.get("ext", "mp4")
    path = os.path.join(out_dir, f"{file_id}.{ext}")
    title = info.get("title") or info.get("description") or "Instagram Media"
    uploader = info.get("uploader") or ""
    return path, title, uploader


@app.on_message(
    filters.command(["reels", "insta", "ig", "reel"]) & ~BANNED_USERS
)
async def insta_dl(client, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2 or not INSTA_RE.search(args[1]):
        return await message.reply_text(
            "📥 **Instagram İndirici**\n\n"
            "Kullanım: `/reels <instagram_linki>`\n"
            "Örnek: `/reels https://www.instagram.com/reel/Cxxxxx/`\n\n"
            "Desteklenen: Reels, Posts, IGTV, Stories (genel)."
        )
    url = INSTA_RE.search(args[1]).group(0)
    if not url.startswith("http"):
        url = "https://" + url

    status = await message.reply_text("⏬ İndiriliyor…")
    try:
        loop = asyncio.get_running_loop()
        path, title, uploader = await loop.run_in_executor(
            None, _ydl_download, url, DL_DIR
        )
    except Exception as e:
        return await status.edit_text(f"❌ İndirilemedi: `{type(e).__name__}`")

    caption = f"🎬 **{title[:200]}**"
    if uploader:
        caption += f"\n👤 @{uploader}"
    caption += f"\n📎 [Kaynak]({url})"

    try:
        await message.reply_video(video=path, caption=caption)
    except Exception:
        try:
            await message.reply_document(document=path, caption=caption)
        except Exception as e:
            await status.edit_text(f"❌ Gönderilemedi: `{type(e).__name__}`")
            return
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
    await status.delete()


# Auto-detect Instagram links in chat (optional, only on direct chat)
@app.on_message(
    filters.regex(INSTA_RE) & filters.private & ~BANNED_USERS
)
async def insta_auto(client, message: Message):
    text = message.text or message.caption or ""
    m = INSTA_RE.search(text)
    if not m:
        return
    url = m.group(0)
    if not url.startswith("http"):
        url = "https://" + url

    status = await message.reply_text("⏬ Link tespit edildi, indiriliyor…")
    try:
        loop = asyncio.get_running_loop()
        path, title, uploader = await loop.run_in_executor(
            None, _ydl_download, url, DL_DIR
        )
    except Exception as e:
        return await status.edit_text(f"❌ İndirilemedi: `{type(e).__name__}`")

    caption = f"🎬 **{title[:200]}**"
    if uploader:
        caption += f"\n👤 @{uploader}"
    try:
        await message.reply_video(video=path, caption=caption)
    except Exception:
        try:
            await message.reply_document(document=path, caption=caption)
        except Exception as e:
            await status.edit_text(f"❌ Gönderilemedi: `{type(e).__name__}`")
            return
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
    await status.delete()
