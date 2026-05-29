#
# Universal media downloader plugin – /dl <url>
# Powered by yt-dlp; supports YouTube (incl. live), Twitter/X, TikTok,
# Facebook, Reddit, SoundCloud, Vimeo, Dailymotion, and many more.
#

import asyncio
import os
import re
import uuid

import yt_dlp
from pyrogram import filters
from pyrogram.enums import ChatAction
from pyrogram.types import Message

from config import BANNED_USERS
from YukkiMusic import app

DL_DIR = "downloads/universal"
os.makedirs(DL_DIR, exist_ok=True)

URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)

MAX_BYTES = 2_000_000_000  # ~2 GB (Telegram premium limit)


def _ydl_download(url: str, audio_only: bool = False):
    file_id = uuid.uuid4().hex
    if audio_only:
        opts = {
            "outtmpl": os.path.join(DL_DIR, f"{file_id}.%(ext)s"),
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
    else:
        opts = {
            "outtmpl": os.path.join(DL_DIR, f"{file_id}.%(ext)s"),
            "format": "best[height<=?1080]/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "merge_output_format": "mp4",
        }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    ext = "mp3" if audio_only else info.get("ext", "mp4")
    # On some sites yt-dlp rewrites the extension; locate by glob
    candidates = [
        os.path.join(DL_DIR, f"{file_id}.{ext}"),
        os.path.join(DL_DIR, f"{file_id}.mp4"),
        os.path.join(DL_DIR, f"{file_id}.webm"),
        os.path.join(DL_DIR, f"{file_id}.mkv"),
        os.path.join(DL_DIR, f"{file_id}.m4a"),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if path is None:
        # Fallback: pick any file starting with file_id
        for f in os.listdir(DL_DIR):
            if f.startswith(file_id):
                path = os.path.join(DL_DIR, f)
                break
    title = info.get("title") or "Media"
    uploader = info.get("uploader") or info.get("channel") or ""
    duration = info.get("duration") or 0
    return path, title, uploader, duration


@app.on_message(
    filters.command(["dl", "download", "mp4", "video"]) & ~BANNED_USERS
)
async def universal_dl(client, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2 or not URL_RE.search(args[1]):
        return await message.reply_text(
            "📥 **Evrensel İndirici**\n\n"
            "Kullanım:\n"
            "  • `/dl <link>` → video\n"
            "  • `/mp3 <link>` → sadece ses (MP3)\n\n"
            "Destekli platformlar: YouTube (canlı dahil), Twitter/X, "
            "TikTok, Facebook, Reddit, Vimeo, Dailymotion, SoundCloud, "
            "Twitch ve 1000+ site."
        )
    url = URL_RE.search(args[1]).group(0)
    status = await message.reply_text("⏬ İndiriliyor…")
    await client.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)

    try:
        loop = asyncio.get_running_loop()
        path, title, uploader, duration = await loop.run_in_executor(
            None, _ydl_download, url, False
        )
    except Exception as e:
        return await status.edit_text(f"❌ İndirilemedi: `{type(e).__name__}: {e}`"[:400])

    if not path or not os.path.exists(path):
        return await status.edit_text("❌ Dosya bulunamadı.")

    size = os.path.getsize(path)
    if size > MAX_BYTES:
        try:
            os.remove(path)
        except Exception:
            pass
        return await status.edit_text("❌ Dosya 2GB sınırını aşıyor.")

    caption = f"🎬 **{title[:200]}**"
    if uploader:
        caption += f"\n👤 {uploader}"
    caption += f"\n📎 [Kaynak]({url})"

    try:
        await message.reply_video(
            video=path,
            caption=caption,
            duration=int(duration or 0),
            supports_streaming=True,
        )
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


@app.on_message(
    filters.command(["mp3", "song", "audio"]) & ~BANNED_USERS
)
async def universal_audio(client, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2 or not URL_RE.search(args[1]):
        return await message.reply_text(
            "🎵 **Şarkı/Ses İndirici**\n\n"
            "Kullanım: `/mp3 <link>` veya `/song <youtube_arama>`\n\n"
            "Spotify, Apple Music gibi DRM korumalı kaynaklar için "
            "YouTube'dan eşleşen ses indirilir."
        )
    url_or_query = args[1]
    url_match = URL_RE.search(url_or_query)

    if url_match:
        url = url_match.group(0)
    else:
        # treat as YouTube search query
        url = f"ytsearch1:{url_or_query}"

    # Spotify / Apple Music links: redirect to YouTube search
    if "open.spotify.com" in url or "music.apple.com" in url:
        try:
            from YukkiMusic import Spotify, Apple
            details = None
            if "open.spotify.com" in url and "track" in url:
                details, _ = await Spotify.track(url)
            elif "music.apple.com" in url:
                details, _ = await Apple.track(url)
            if details and details.get("link"):
                url = details["link"]
        except Exception:
            pass

    status = await message.reply_text("⏬ İndiriliyor…")
    await client.send_chat_action(message.chat.id, ChatAction.UPLOAD_AUDIO)
    try:
        loop = asyncio.get_running_loop()
        path, title, uploader, duration = await loop.run_in_executor(
            None, _ydl_download, url, True
        )
    except Exception as e:
        return await status.edit_text(f"❌ İndirilemedi: `{type(e).__name__}: {e}`"[:400])

    if not path or not os.path.exists(path):
        return await status.edit_text("❌ Dosya bulunamadı.")

    caption = f"🎵 **{title[:200]}**"
    if uploader:
        caption += f"\n👤 {uploader}"

    try:
        await message.reply_audio(
            audio=path,
            caption=caption,
            title=title[:64],
            performer=uploader[:64] if uploader else "Unknown",
            duration=int(duration or 0),
        )
    except Exception as e:
        await status.edit_text(f"❌ Gönderilemedi: `{type(e).__name__}`")
        return
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
    await status.delete()
