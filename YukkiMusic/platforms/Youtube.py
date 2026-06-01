#
# Modernized 2026: yt-dlp powered search (no youtubesearchpython dependency).
#

import asyncio
import os
import shutil
import sys

# Resolve the yt-dlp invocation once.
# 2026 fix: Always use `[sys.executable, "-m", "yt_dlp"]` because:
#   1. systemd/supervisor strips PATH → literal "yt-dlp" lookup fails
#   2. `pip install yt-dlp` sometimes does NOT create the `yt-dlp` script
#      in venv/bin (depends on installer version), causing FileNotFoundError
#   3. Running the Python module is guaranteed to work whenever `import yt_dlp`
#      succeeds (which it does — see `import yt_dlp` below)
def _resolve_ytdlp_cmd():
    # Prefer Python module invocation (always works under systemd).
    return [sys.executable, "-m", "yt_dlp"]

# YTDLP_CMD is a LIST (e.g. ["/path/to/python3", "-m", "yt_dlp"]) — use with
# `*YTDLP_CMD` when building subprocess argv. Backwards-compat alias YTDLP_BIN
# kept as a list too (callers spread it with `*`).
YTDLP_CMD = _resolve_ytdlp_cmd()
YTDLP_BIN = YTDLP_CMD  # legacy alias — already a list, callers must use *YTDLP_BIN
import re
from typing import Union

import yt_dlp

# Optional cookies.txt — auto-detected at *runtime* so /setcookies hot-loads
# without requiring a restart. Re-scans on every call.
# IMPORTANT: paths must be ABSOLUTE so detection works regardless of cwd at
# call time (e.g. PyTgCalls subprocesses, threads).
_BOT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _detect_cookies() -> str | None:
    candidates = [
        os.path.join(_BOT_ROOT, "cookies", "cookies.txt"),
        os.path.join(_BOT_ROOT, "cookies.txt"),
        os.path.join(os.getcwd(), "cookies", "cookies.txt"),
        os.path.join(os.getcwd(), "cookies.txt"),
        os.environ.get("YT_COOKIES", ""),
    ]
    for p in candidates:
        if p and os.path.isfile(p) and os.path.getsize(p) > 100:
            return os.path.abspath(p)
    return None


def _cookies_look_valid(path: str | None) -> bool:
    """Heuristic check: real YouTube login cookies should contain
    SAPISID + __Secure-3PAPISID. If both critical cookies are present
    we treat the file as valid regardless of size (some valid exports
    are 2-3 KB). A small file (<1.5 KB) AND missing markers is
    considered partial and skipped to avoid the 'Sign in to confirm
    you're not a bot' trap that partial cookies trigger."""
    if not path:
        return False
    try:
        size = os.path.getsize(path)
        with open(path, "r", errors="replace") as f:
            text = f.read(80000)
        text_l = text.lower()
        has_sapisid = "sapisid" in text_l
        has_secure  = (
            "__secure-3papisid" in text_l
            or "__secure-1papisid" in text_l
        )
        # If both critical markers are present → valid regardless of size
        if has_sapisid and has_secure:
            return True
        # Otherwise need a reasonably-large file
        return size >= 3000 and has_sapisid
    except Exception:
        return False


# Backwards-compat constant — still imported by other modules. Lazy-evaluated
# via _current_cookies() everywhere it matters.
COOKIES_FILE = _detect_cookies()


def _current_cookies() -> str | None:
    """Always re-detect so a freshly uploaded cookies.txt is picked up
    without restarting the bot.
    NOTE: Returns the path even if cookies look incomplete — caller
    decides via _cookies_look_valid() whether to actually use them."""
    return _detect_cookies()

# Common yt-dlp options to bypass YouTube 403/anti-bot:
# NOTE (2026): mediaconnect + android_music + tv_embedded are the most reliable
# clients in early 2026 (other clients keep returning "No video formats found"
# from datacenter IPs). When cookies are provided, we ALSO pass them — but
# cookies from a residential IP can hurt rather than help on a datacenter host,
# so a USE_COOKIES env flag lets the operator turn them off.
_USE_COOKIES = os.environ.get("USE_COOKIES", "true").lower() not in ("false", "0", "no", "off")
_YDL_BYPASS = {
    "geo_bypass": True,
    "geo_bypass_country": "US",
    "nocheckcertificate": True,
    "source_address": "0.0.0.0",
    "extractor_args": {
        "youtube": {
            # Modern (Feb 2026) client list — handles SABR + format coverage
            "player_client": ["default", "ios", "mweb", "android_music", "tv_embedded"],
        }
    },
}


def _ydl_opts(extra):
    o = dict(_YDL_BYPASS)
    # Dynamic cookies — picks up freshly uploaded cookies.txt.
    # 2026-06: always attach cookies if present (regardless of heuristic
    # validity check). yt-dlp's bot-check on datacenter IPs is so
    # aggressive that even partial cookies sometimes help.
    cf = _current_cookies()
    if cf and _USE_COOKIES:
        o["cookiefile"] = cf
    o.update(extra)
    return o


def _cookie_cli_args():
    """Return CLI args list for yt-dlp -g subprocess calls. Re-checks
    cookies file on every call so /setcookies works without restart.
    Always attach if file present (let yt-dlp decide if cookies help)."""
    cf = _current_cookies()
    if cf and _USE_COOKIES:
        return ["--cookies", cf]
    return []

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
        "source_address": "0.0.0.0",
        "extractor_args": {"youtube": {"player_client": ["mediaconnect", "android_music", "tv_embedded"]}},
    }
    # Always re-detect cookies — module-level COOKIES_FILE is set at import
    # time and never updates after /setcookies, which caused ALL searches to
    # hit YouTube cookie-less.
    cf = _current_cookies()
    if cf and _USE_COOKIES:
        opts["cookiefile"] = cf
    else:
        import logging
        logging.getLogger("YukkiMusic.ytsearch").warning(
            "yt-dlp search called WITHOUT cookies — YouTube will likely "
            "block. Upload cookies.txt then /setcookies."
        )
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
            *YTDLP_BIN, "-g", "-f",
            "best[height<=?720][width<=?1280]",
            "--extractor-args", "youtube:player_client=mediaconnect,android_music,tv_embedded",
            "--geo-bypass",
            "--source-address", "0.0.0.0",
            "--no-warnings",
            *_cookie_cli_args(),
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
        import shlex
        cookies_arg = f"--cookies {shlex.quote(_current_cookies())} " if _current_cookies() else ""
        ytdlp_str = " ".join(shlex.quote(x) for x in YTDLP_BIN)
        playlist = await shell_cmd(
            f"{ytdlp_str} {cookies_arg}-i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
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
        is_url = bool(re.match(r"^https?://", link))
        # For URL: single result. For text query: search up to 6 results and
        # smart-pick one that's actually playable.
        results = await _ytsearch(link, 1 if is_url else 6)
        if not results:
            raise Exception("No results")
        if is_url:
            r = results[0]
        else:
            r = self._pick_best(results)
        td = {
            "title": r["title"],
            "link": r["link"],
            "vidid": r["id"],
            "duration_min": r["duration"],
            "thumb": r["thumbnails"][0]["url"].split("?")[0],
        }
        return td, r["id"]

    @staticmethod
    def _pick_best(results):
        """Pick the best candidate, deprioritising VEVO/Official Music Videos
        (often DRM-blocked from datacenter IPs)."""
        BAD_TITLE_HINTS = (
            "official music video",
            "(official video)",
            "[official video]",
            "official vevo",
            "vevo",
        )
        bad = []
        good = []
        for cand in results:
            t = (cand.get("title") or "").lower()
            if any(h in t for h in BAD_TITLE_HINTS):
                bad.append(cand)
            else:
                good.append(cand)
        # Prefer first 'good' (non-VEVO). Fall back to first 'bad' if none.
        return (good[0] if good else (bad[0] if bad else results[0]))

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
            # 2026-06 fix: VPS IPs often hit "Sign in to confirm you're not a
            # bot" even on simple videos. The cure is to try MULTIPLE
            # player_client configurations in sequence — different videos
            # respond to different clients. We also pass `player_skip=webpage`
            # so yt-dlp does NOT fetch the regular webpage (which is what
            # most reliably triggers the bot check).
            #
            # Strategy:
            #   1. If valid cookies → try with cookies first
            #   2. Then try a series of cookie-less player_client combos
            #   3. Last resort: classic clients without player_skip
            import logging
            log = logging.getLogger("YukkiMusic")

            cf = _current_cookies()
            cookies_present = bool(cf) and _USE_COOKIES
            cookies_look_good = cookies_present and _cookies_look_valid(cf)
            if cookies_present and not cookies_look_good:
                log.warning(
                    f"cookies.txt looks partial ({os.path.getsize(cf)} bytes) — "
                    "trying with cookies ANYWAY, then falling back to "
                    "cookie-less if rejected. Re-export full browser cookies "
                    "via /setcookies for best results."
                )

            def _make_opts(player_clients, player_skip=None, cookiefile=None,
                           proxy_url=None):
                youtube_args = {"player_client": list(player_clients)}
                if player_skip:
                    youtube_args["player_skip"] = list(player_skip)
                opts = {
                    "format": "bestaudio/best",
                    "outtmpl": "downloads/%(id)s.%(ext)s",
                    "geo_bypass": True,
                    "nocheckcertificate": True,
                    "quiet": True,
                    "no_warnings": True,
                    "retries": 3,
                    "fragment_retries": 3,
                    "concurrent_fragment_downloads": 4,
                    "extractor_args": {"youtube": youtube_args},
                }
                if cookiefile:
                    opts["cookiefile"] = cookiefile
                if proxy_url:
                    opts["proxy"] = proxy_url
                return opts

            def _try(opts):
                x = yt_dlp.YoutubeDL(opts)
                info = x.extract_info(link, download=False)
                xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                if os.path.exists(xyz):
                    return xyz
                x.download([link])
                return xyz

            # Strategy list — each entry: (label, player_clients, player_skip, use_cookies)
            # 2026-06: try WITH cookies first (always — even if partial), then
            # fall back to cookie-less. YouTube's bot-check is aggressive on
            # datacenter IPs and even partial cookies sometimes work where
            # cookie-less does not.
            strategies = []
            if cookies_present:
                strategies.extend([
                    # 1A) with-cookies + classic combo
                    ("with-cookies default,ios,mweb,android_music,tv_embedded",
                     ["default", "ios", "mweb", "android_music", "tv_embedded"],
                     None, True),
                    # 1B) with-cookies + web (cookies-friendly client)
                    ("with-cookies web,mweb",
                     ["web", "mweb"], None, True),
                ])
            # Cookie-less strategies (ordered by tested reliability)
            strategies.extend([
                # 2) CLASSIC combo — verified most reliable on datacenter IPs
                ("cookie-less default,ios,mweb,android_music,tv_embedded",
                 ["default", "ios", "mweb", "android_music", "tv_embedded"],
                 None, False),
                # 3) mediaconnect variant
                ("cookie-less mediaconnect,android_music,tv_embedded",
                 ["mediaconnect", "android_music", "tv_embedded"],
                 None, False),
                # 4) ios+mweb (lighter)
                ("cookie-less ios,mweb",
                 ["ios", "mweb"], None, False),
                # 5) android_vr only (rare fallback)
                ("cookie-less android_vr",
                 ["android_vr"], None, False),
            ])

            # Import proxy manager (lazy to avoid circular imports at module load)
            try:
                from YukkiMusic.utils import proxy_manager as _pm
            except Exception:
                _pm = None  # proxy mode unavailable

            last_exc = None
            for label, clients, skip, use_cookies in strategies:
                # Try with each strategy up to 3 times, rotating proxy on
                # failure (per user-choice: rotate on error only). Last
                # attempt always runs WITHOUT proxy (final fallback).
                proxy_attempts = 3 if (_pm and _pm.is_enabled()) else 1
                current_proxy = None
                tried_proxies: set[str] = set()
                strategy_success = False

                for attempt in range(proxy_attempts):
                    # Pick proxy for this attempt (None on last try when
                    # proxies exhausted, to fall back to direct connection)
                    if _pm and _pm.is_enabled() and attempt < proxy_attempts - 1:
                        # Pick a proxy we haven't tried yet
                        for _ in range(5):
                            candidate = _pm.get_proxy()
                            if not candidate:
                                current_proxy = None
                                break
                            if candidate not in tried_proxies:
                                current_proxy = candidate
                                tried_proxies.add(candidate)
                                break
                        else:
                            current_proxy = None
                    else:
                        current_proxy = None

                    proxy_label = (f" via proxy {current_proxy.split('@')[-1]}"
                                   if current_proxy else " direct")
                    opts = _make_opts(
                        clients, skip,
                        cookiefile=(cf if (use_cookies and cookies_present) else None),
                        proxy_url=current_proxy,
                    )
                    try:
                        result = _try(opts)
                        if result and os.path.exists(result):
                            log.info(f"audio_dl SUCCESS via: {label}{proxy_label}")
                            strategy_success = True
                            return result
                    except Exception as e:
                        last_exc = e
                        msg = str(e)
                        log.warning(
                            f"audio_dl strategy '{label}'{proxy_label} failed: "
                            f"{type(e).__name__}: {msg[:180]}"
                        )
                        # Classify the error to decide what to do next
                        if _pm and current_proxy:
                            if _pm.is_quota_error(msg):
                                _pm.mark_quota_exceeded("yt-dlp reported quota")
                                _pm.schedule_quota_notice()
                                current_proxy = None
                                break  # don't keep retrying proxies
                            elif _pm.is_proxy_connection_error(msg):
                                _pm.mark_bad(current_proxy)
                                # try next proxy
                                continue
                            elif "sign in to confirm" in msg.lower():
                                # YouTube rejected this proxy IP too — mark bad
                                _pm.mark_bad(current_proxy)
                                continue
                        # Non-proxy error — break out and move to next strategy
                        break

                if strategy_success:
                    return  # unreachable but for clarity

            # All strategies exhausted — re-raise the last exception so the
            # outer code can decide whether to try the -g streaming path.
            if last_exc:
                raise last_exc
            raise Exception("audio_dl: all strategies returned empty (no exception)")

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
                    *YTDLP_BIN, "-g", "-f",
                    "best[height<=?720][width<=?1280]",
                    "--extractor-args", "youtube:player_client=mediaconnect,android_music,tv_embedded",
                    "--no-warnings",
                    *_cookie_cli_args(),
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
            return downloaded_file, direct
        else:
            # AUDIO PATH — Reordered Feb 2026 (per user request):
            # 1) Try direct file download first (simple yt-dlp + cookies = most
            #    reliable; matches the working reference repo melih022/google).
            # 2) Only if download fails, fall back to -g streaming URL with
            #    multiple format/client strategies.
            try:
                downloaded_file = await loop.run_in_executor(None, audio_dl)
                if downloaded_file and os.path.exists(downloaded_file):
                    return downloaded_file, True
            except Exception as e:
                last_err = f"audio_dl: {type(e).__name__}: {str(e)[:300]}"
            else:
                last_err = "audio_dl returned no file"

            # Streaming-URL fallback chain — verified order Jun 2026:
            # classic combo first (most reliable on datacenter IPs).
            stream_url = None
            attempts = [
                # 1: CLASSIC combo — verified most reliable
                [*YTDLP_BIN, "-g", "-f", "ba/b",
                 "--extractor-args",
                 "youtube:player_client=default,ios,mweb,android_music,tv_embedded",
                 "--no-warnings", "--no-call-home", *_cookie_cli_args(),
                 f"{link}"],
                # 2: mediaconnect variant
                [*YTDLP_BIN, "-g", "-f", "bestaudio[ext=m4a]/bestaudio/best/best",
                 "--extractor-args",
                 "youtube:player_client=mediaconnect,android_music,tv_embedded",
                 "--no-warnings", *_cookie_cli_args(),
                 f"{link}"],
                # 3: ios+mweb (lighter)
                [*YTDLP_BIN, "-g", "-f", "bestaudio/best",
                 "--extractor-args", "youtube:player_client=ios,mweb",
                 "--no-warnings", *_cookie_cli_args(),
                 f"{link}"],
                # 4: android_vr fallback
                [*YTDLP_BIN, "-g", "-f", "ba/b/best",
                 "--extractor-args", "youtube:player_client=android_vr",
                 "--no-warnings", "--no-check-formats",
                 "--ignore-no-formats-error",
                 *_cookie_cli_args(),
                 f"{link}"],
            ]
            for idx, cmd in enumerate(attempts, 1):
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await proc.communicate()
                    if stdout and stdout.strip():
                        url = stdout.decode().split("\n")[0].strip()
                        if url.startswith("http"):
                            stream_url = url
                            break
                    last_err = (stderr or b"").decode()[-300:] if stderr else "empty stdout"
                except Exception as e:
                    last_err = f"{type(e).__name__}: {e}"
                    continue
            if stream_url:
                return stream_url, None

            # Everything failed — produce a clear error
            combined_err = last_err.lower()
            cookies_needed = any(s in combined_err for s in [
                "sign in to confirm",
                "use --cookies",
                "cookies-from-browser",
                "confirm you",
                "not a bot",
            ])
            if cookies_needed:
                cf_now = _current_cookies()
                has_cookies = bool(cf_now and os.path.getsize(cf_now) > 100)
                if not has_cookies:
                    raise Exception(
                        "YouTube IP'nizi bot olarak işaretledi (datacenter IP).\n"
                        "ÇÖZÜM: cookies.txt yükleyin.\n"
                        "1) Chrome'a 'Get cookies.txt LOCALLY' eklentisi kurun\n"
                        "2) youtube.com'a giriş yapın → eklentiden export\n"
                        "3) Dosyayı bota PM'den gönderip reply ile /setcookies yazın"
                    )
                else:
                    raise Exception(
                        "YouTube cookies geçersiz veya süresi dolmuş.\n"
                        f"Mevcut dosya: {cf_now} ({os.path.getsize(cf_now)} byte)\n"
                        "Tarayıcıda youtube.com'da yeniden giriş yapıp "
                        "cookies.txt'i yeniden export edin ve /setcookies ile yükleyin."
                    )
            raise Exception(
                f"yt-dlp ile ses çekilemedi.\n"
                f"Son hata: {last_err[-200:]}\n"
                f"İpucu: Yaş kısıtlı/VEVO videolar genelde başarısız. "
                f"Şarkı adına 'lyrics' veya 'audio' ekleyerek tekrar deneyin."
            )
