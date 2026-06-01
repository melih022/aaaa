"""
YouTube Data API v3 client (2026-06).

Provides reliable SEARCH and METADATA lookups via the official YouTube API,
bypassing yt-dlp's bot-check entirely for the search step. yt-dlp is still
needed for the actual audio stream download (the API doesn't provide
streamable URLs by design — Google wants you to use their iframe embed).

Free tier:
  - 10,000 units/day
  - search.list  = 100 units / call
  - videos.list  = 1 unit / call (per ID, batched up to 50)
  - So ~100 searches/day cookie-less + unlimited metadata if you cache video IDs

To get a key:
  1. https://console.cloud.google.com → create project
  2. APIs & Services → Library → enable "YouTube Data API v3"
  3. APIs & Services → Credentials → Create Credentials → API key
  4. Restrict to "YouTube Data API v3" for safety

Environment variable: YOUTUBE_API_KEY
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

log = logging.getLogger("YukkiMusic.yt_api")

YT_API_BASE = "https://www.googleapis.com/youtube/v3"

# Lazy global key — read from env at first use
_api_key: Optional[str] = None
_key_lock = threading.Lock()
_quota_exceeded = False
_notified_quota = False


def configure(api_key: str | None = None) -> None:
    """Set the API key explicitly (otherwise read from env)."""
    global _api_key, _quota_exceeded, _notified_quota
    with _key_lock:
        _api_key = (api_key or os.environ.get("YOUTUBE_API_KEY", "")).strip() or None
        _quota_exceeded = False
        _notified_quota = False
        if _api_key:
            log.info("YouTube Data API: configured")
        else:
            log.info("YouTube Data API: disabled (no YOUTUBE_API_KEY)")


def is_enabled() -> bool:
    return bool(_api_key) and not _quota_exceeded and requests is not None


def _mark_quota_exceeded() -> None:
    global _quota_exceeded
    with _key_lock:
        _quota_exceeded = True
    log.warning("YouTube Data API: quota exceeded — disabling for now.")


def should_notify_quota() -> bool:
    """Returns True ONCE the first time quota gets exceeded."""
    global _notified_quota
    with _key_lock:
        if _quota_exceeded and not _notified_quota:
            _notified_quota = True
            return True
        return False


def _request(path: str, params: dict, timeout: int = 10) -> Optional[dict]:
    if not is_enabled():
        return None
    params = dict(params)
    params["key"] = _api_key
    try:
        r = requests.get(f"{YT_API_BASE}/{path}", params=params, timeout=timeout)
    except Exception as e:
        log.warning(f"YT API {path} request failed: {type(e).__name__}: {e}")
        return None
    if r.status_code == 403:
        try:
            err = r.json().get("error", {})
            reason = (err.get("errors") or [{}])[0].get("reason", "")
        except Exception:
            reason = ""
        if reason in ("quotaExceeded", "dailyLimitExceeded"):
            _mark_quota_exceeded()
            return None
        log.warning(f"YT API {path} 403: {r.text[:200]}")
        return None
    if r.status_code != 200:
        log.warning(f"YT API {path} HTTP {r.status_code}: {r.text[:200]}")
        return None
    try:
        return r.json()
    except Exception:
        return None


def _parse_iso8601_duration(s: str) -> int:
    """Convert PT4M13S → 253 (seconds)."""
    import re
    m = re.match(r"^P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", s or "")
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    se = int(m.group(3) or 0)
    return h * 3600 + mi * 60 + se


def _hms(seconds: int) -> str:
    if not seconds:
        return "LIVE"
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def search(query: str, limit: int = 1) -> list[dict]:
    """Search YouTube. Returns list of dicts compatible with the rest of
    the bot:
      [{"id": "...", "title": "...", "duration": "3:42",
        "duration_seconds": 222, "thumbnail": "...", "channel": "...",
        "link": "https://www.youtube.com/watch?v=..."}]
    Costs 100 quota units. Falls back to empty list on any failure.
    """
    if not is_enabled():
        return []
    data = _request("search", {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max(1, min(limit, 10)),
        "safeSearch": "none",
        # videoEmbeddable=true filters out a lot of restricted content,
        # which is good for our use case (we need to stream them)
    })
    if not data:
        return []
    items = data.get("items", [])
    ids = [it["id"]["videoId"] for it in items if it.get("id", {}).get("videoId")]
    if not ids:
        return []
    # Batch fetch durations (1 quota unit, regardless of ID count up to 50)
    details = _request("videos", {
        "part": "contentDetails,snippet",
        "id": ",".join(ids),
    })
    detail_map = {}
    if details:
        for it in details.get("items", []):
            vid = it["id"]
            dur_iso = it.get("contentDetails", {}).get("duration", "PT0S")
            secs = _parse_iso8601_duration(dur_iso)
            detail_map[vid] = secs
    out: list[dict] = []
    for it in items:
        vid = it.get("id", {}).get("videoId")
        if not vid:
            continue
        sn = it.get("snippet", {})
        thumbs = sn.get("thumbnails", {})
        thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
        secs = detail_map.get(vid, 0)
        out.append({
            "id": vid,
            "title": sn.get("title", ""),
            "duration": _hms(secs),
            "duration_seconds": secs,
            "thumbnail": thumb.split("?")[0],
            "channel": sn.get("channelTitle", ""),
            "link": f"https://www.youtube.com/watch?v={vid}",
        })
    return out


def video_details(video_id: str) -> Optional[dict]:
    """Fetch metadata for a known video ID (1 quota unit)."""
    if not is_enabled():
        return None
    data = _request("videos", {
        "part": "contentDetails,snippet",
        "id": video_id,
    })
    if not data:
        return None
    items = data.get("items", [])
    if not items:
        return None
    it = items[0]
    sn = it.get("snippet", {})
    dur_iso = it.get("contentDetails", {}).get("duration", "PT0S")
    secs = _parse_iso8601_duration(dur_iso)
    thumbs = sn.get("thumbnails", {})
    thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
    return {
        "id": video_id,
        "title": sn.get("title", ""),
        "duration": _hms(secs),
        "duration_seconds": secs,
        "thumbnail": thumb.split("?")[0],
        "channel": sn.get("channelTitle", ""),
        "link": f"https://www.youtube.com/watch?v={video_id}",
    }


def schedule_quota_notice() -> None:
    """One-shot Telegram DM to the owner when quota gets exhausted."""
    if not should_notify_quota():
        return
    import asyncio
    try:
        from YukkiMusic import app  # type: ignore
        import config  # type: ignore
    except Exception:
        return
    owner_id = getattr(config, "OWNER_ID", None)
    if not owner_id:
        return

    async def _notify():
        try:
            await app.send_message(
                int(owner_id),
                "⚠️ **YouTube Data API günlük kotası doldu (10,000 birim)**\n\n"
                "Arama artık yt-dlp'ye düşecek (bot-check yeme riski daha "
                "yüksek). Kota gece yarısı PT (Pasifik Saati) sıfırlanır.\n\n"
                "Çözümler:\n"
                "• Yarın bekleyin (otomatik resetlenir)\n"
                "• Google Cloud Console → Billing aktif edin (yine ücretsiz "
                "10k kota, üstü ödeme)\n"
                "• 2. proje açıp ek API key oluşturun",
            )
        except Exception as e:
            log.warning(f"YT API quota notify failed: {e}")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(_notify(), loop)
        else:
            loop.create_task(_notify())
    except Exception:
        threading.Thread(
            target=lambda: asyncio.run(_notify()),
            daemon=True,
        ).start()


def stats() -> dict:
    return {
        "enabled": is_enabled(),
        "has_key": bool(_api_key),
        "quota_exceeded": _quota_exceeded,
    }
