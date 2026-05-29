#
# Modernized 2026: yt-dlp powered search (no youtubesearchpython dependency).
#

import asyncio
import os
import re
from typing import Union

import yt_dlp

# Common yt-dlp options to bypass YouTube 403/anti-bot:
_YDL_BYPASS = {
    "geo_bypass": True,
    "geo_bypass_country": "US",
    "extractor_args": {
        "youtube": {
            # 2026 working clients (no "Sign in to confirm you're not a bot"):
            # mediaconnect = TV streaming, ios_music = music app, tv_embedded = legacy TV embed.
            "player_client": ["mediaconnect", "ios_music", "tv_embedded"],
            "formats": ["missing_pot"],
        }
    },
    "nocheckcertificate": True,
}


def _ydl_opts(extra):
    o = dict(_YDL_BYPASS)
    o.update(extra)
    return o

from pyrogram.types import Message
from pyrogram.enums import MessageEntityType

import config
from YukkiMusic.utils.database import is_on_off
from YukkiMusic.utils.formatters import time_to_seconds


def _ytdl_extract(query: str, limit: int = 1, flat: bool = False):
    """Search YouTube via yt-dlp. Returns dict with 'entries'.
    - If query is a URL, fetches metadata directly.
    - Otherwise prefixes with ytsearchN: to force a YouTube search.
    """
    # Detect URL vs search query
    is_url = bool(re.match(r"^https?://", query))
    if not is_url:
        # Force YouTube search regardless of default_search
        query = f"ytsearch{max(1, limit)}:{query}"
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "format": "bestaudio/best",
        # For search we keep extract_flat=False so yt-dlp resolves each entry.
        # extract_flat="in_playlist" returns shallow URLs only.
        "extract_flat": "in_playlist" if flat else False,
        "geo_bypass": True,
        "geo_bypass_country": "US",
        # Lightweight extractor_args for search (no formats restrictions):
        "extractor_args": {"youtube": {"player_client": ["web", "android"]}},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(query, download=False)


async def _ytsearch(query: str, limit: int = 1):
    loop = asyncio.get_running_loop()

    def _run():
        try:
            data = _ytdl_extract(query, limit=limit, flat=True)
        except Exception as e:
            import logging, traceback
            logging.getLogger("YukkiMusic.ytsearch").error(
                f"yt-dlp search failed for {query!r}: {type(e).__name__}: {e}"
            )
            try:
                from YukkiMusic.plugins.devs.diagnostics import LAST_ERRORS
                LAST_ERRORS.append(
                    f"_ytsearch({query!r}) -> {type(e).__name__}: {e}\n"
                    f"{traceback.format_exc()}"
                )
                if len(LAST_ERRORS) > 20:
                    LAST_ERRORS.pop(0)
            except Exception:
                pass
            return []
        entries = data.get("entries") if data else None
        if not entries:
            if data and data.get("id"):
                entries = [data]
            else:
                return []
        results = []
        for e in entries[:limit]:
            if not e:
                continue
            vidid = e.get("id") or ""
            title = e.get("title") or ""
            duration = e.get("duration") or 0
            link = e.get("webpage_url") or e.get("url") or (
                f"https://www.youtube.com/watch?v={vidid}" if vidid else ""
            )
            thumb = (
                e.get("thumbnail")
                or (e.get("thumbnails", [{}])[0] or {}).get("url")
                or (f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg" if vidid else "")
            )
            if duration:
                m, s = divmod(int(duration), 60)
                h, m = divmod(m, 60)
                duration_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
            else:
                duration_str = "None"
            results.append({
                "id": vidid,
                "title": title,
                "duration": duration_str,
                "link": link,
                "thumbnails": [{"url": thumb}],
                "viewCount": {"short": str(e.get("view_count") or "")},
                "channel": {
                    "name": e.get("channel") or e.get("uploader") or "",
                    "link": e.get("channel_url") or e.get("uploader_url") or "",
                },
                "publishedTime": e.get("upload_date") or "",
            })
        return results

    return await loop.run_in_executor(None, _run)


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        return errorz.decode("utf-8")
    return out.decode("utf-8")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link, videoid=None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1):
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset is None:
            return None
        return text[offset: offset + length]

    async def details(self, link, videoid=None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = await _ytsearch(link, 1)
        if not results:
            raise Exception("No results")
        r = results[0]
        title = r["title"]
        duration_min = r["duration"]
        thumbnail = r["thumbnails"][0]["url"].split("?")[0]
        vidid = r["id"]
        duration_sec = 0 if str(duration_min) == "None" else int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link, videoid=None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        r = await _ytsearch(link, 1)
        return r[0]["title"] if r else ""

    async def duration(self, link, videoid=None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        r = await _ytsearch(link, 1)
        return r[0]["duration"] if r else "None"

    async def thumbnail(self, link, videoid=None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        r = await _ytsearch(link, 1)
        return r[0]["thumbnails"][0]["url"].split("?")[0] if r else ""

    async def video(self, link, videoid=None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "-g", "-f",
            "best[height<=?720][width<=?1280]",
            "--extractor-args", "youtube:player_client=mediaconnect,ios_music,tv_embedded;formats=missing_pot",
            "--geo-bypass",
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        return 0, stderr.decode()

    async def playlist(self, link, limit, user_id, videoid=None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = [x for x in playlist.split("\n") if x]
        except Exception:
            result = []
        return result

    async def track(self, link, videoid=None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = await _ytsearch(link, 1)
        if not results:
            raise Exception("No results")
        r = results[0]
        td = {
            "title": r["title"],
            "link": r["link"],
            "vidid": r["id"],
            "duration_min": r["duration"],
            "thumb": r["thumbnails"][0]["url"].split("?")[0],
        }
        return td, r["id"]

    async def formats(self, link, videoid=None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ydl = yt_dlp.YoutubeDL(_ydl_opts({"quiet": True}))
        formats_available = []
        with ydl:
            r = ydl.extract_info(link, download=False)
            for fmt in r["formats"]:
                try:
                    str(fmt["format"])
                except Exception:
                    continue
                if "dash" not in str(fmt["format"]).lower():
                    try:
                        fmt["format"]; fmt["filesize"]; fmt["format_id"]
                        fmt["ext"]; fmt["format_note"]
                    except Exception:
                        continue
                    formats_available.append({
                        "format": fmt["format"],
                        "filesize": fmt["filesize"],
                        "format_id": fmt["format_id"],
                        "ext": fmt["ext"],
                        "format_note": fmt["format_note"],
                        "yturl": link,
                    })
        return formats_available, link

    async def slider(self, link, query_type, videoid=None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        r = await _ytsearch(link, 10)
        if not r or query_type >= len(r):
            raise Exception("No results")
        res = r[query_type]
        return (
            res["title"], res["duration"],
            res["thumbnails"][0]["url"].split("?")[0],
            res["id"],
        )

    async def download(self, link, mystic, video=None, videoid=None,
                       songaudio=None, songvideo=None, format_id=None, title=None):
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()

        def audio_dl():
            opts = {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True, "nocheckcertificate": True,
                "quiet": True, "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(_ydl_opts(opts))
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def video_dl():
            opts = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True, "nocheckcertificate": True,
                "quiet": True, "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(_ydl_opts(opts))
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def song_video_dl():
            formats = f"{format_id}+140"
            fpath = f"downloads/{title}"
            opts = {
                "format": formats, "outtmpl": fpath,
                "geo_bypass": True, "nocheckcertificate": True,
                "quiet": True, "no_warnings": True,
                "prefer_ffmpeg": True, "merge_output_format": "mp4",
            }
            yt_dlp.YoutubeDL(_ydl_opts(opts)).download([link])

        def song_audio_dl():
            opts = {
                "format": format_id,
                "outtmpl": f"downloads/{title}.%(ext)s",
                "geo_bypass": True, "nocheckcertificate": True,
                "quiet": True, "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
            yt_dlp.YoutubeDL(_ydl_opts(opts)).download([link])

        if songvideo:
            await loop.run_in_executor(None, song_video_dl)
            return f"downloads/{title}.mp4"
        if songaudio:
            await loop.run_in_executor(None, song_audio_dl)
            return f"downloads/{title}.mp3"
        if video:
            if await is_on_off(config.YTDOWNLOADER):
                direct = True
                downloaded_file = await loop.run_in_executor(None, video_dl)
            else:
                proc = await asyncio.create_subprocess_exec(
                    "yt-dlp", "-g", "-f",
                    "best[height<=?720][width<=?1280]",
                    f"{link}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    downloaded_file = stdout.decode().split("\n")[0]
                    direct = None
                else:
                    return
        else:
            direct = True
            downloaded_file = await loop.run_in_executor(None, audio_dl)
        return downloaded_file, direct
