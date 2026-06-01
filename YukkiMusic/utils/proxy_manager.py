"""
Webshare proxy manager (2026-06).

Fetches a pool of HTTP/HTTPS proxies from Webshare's API on startup,
then serves them to yt-dlp callers. Strategy:
  - Each yt-dlp call asks for `get_proxy()` → returns the current best proxy
  - On failure (anti-bot or connection error), caller calls `mark_bad()` which
    rotates to the next healthy proxy
  - If `mark_quota_exceeded()` is called or all proxies fail repeatedly,
    proxy support is DISABLED and the bot notifies the owner once via Telegram
  - The pool is auto-refreshed every 6 hours (Webshare rotates user/pass
    occasionally on free plans)

Environment variables:
  WEBSHARE_API_KEY  — your Webshare API token (from
                      https://dashboard.webshare.io/api/keys)
                      Leave empty to fully disable proxy support.

This module is self-contained and never imports the bot's pyrogram client at
import time, so it's safe to use from any thread/subprocess.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import threading
import time
from typing import Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

log = logging.getLogger("YukkiMusic.proxy")

WEBSHARE_API = "https://proxy.webshare.io/api/v2/proxy/list/"

# How often (seconds) to refresh the proxy list from Webshare API
_REFRESH_INTERVAL = 6 * 60 * 60  # 6 hours

# How long (seconds) a "bad" proxy is benched before being retried
_BAD_PROXY_COOLDOWN = 10 * 60  # 10 minutes


class _ProxyEntry:
    __slots__ = ("url", "bad_until")

    def __init__(self, url: str):
        self.url = url
        self.bad_until: float = 0.0

    @property
    def is_healthy(self) -> bool:
        return time.time() >= self.bad_until


class _ProxyPool:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._proxies: list[_ProxyEntry] = []
        self._last_refresh: float = 0.0
        self._quota_exceeded: bool = False
        self._notified_quota: bool = False
        self._api_key: str = ""

    # ----- config -----
    def configure(self, api_key: str) -> None:
        self._api_key = (api_key or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self._api_key) and not self._quota_exceeded

    # ----- pool management -----
    def _fetch_from_webshare(self) -> list[str]:
        """Hit Webshare API, return list of `http://user:pass@host:port` URLs."""
        if not self._api_key or requests is None:
            return []
        try:
            r = requests.get(
                WEBSHARE_API,
                params={"mode": "direct", "page_size": 50},
                headers={"Authorization": f"Token {self._api_key}"},
                timeout=15,
            )
        except Exception as e:
            log.warning(f"Webshare API fetch failed: {type(e).__name__}: {e}")
            return []
        if r.status_code == 429:
            log.warning("Webshare API rate-limited (429). Will retry later.")
            return []
        if r.status_code in (401, 403):
            log.error(
                f"Webshare API auth failed ({r.status_code}). Check "
                "WEBSHARE_API_KEY in .env."
            )
            return []
        if r.status_code != 200:
            log.warning(f"Webshare API HTTP {r.status_code}: {r.text[:200]}")
            return []
        try:
            data = r.json()
        except Exception:
            log.warning("Webshare API returned non-JSON")
            return []
        urls: list[str] = []
        for p in data.get("results", []):
            host = p.get("proxy_address")
            port = p.get("port")
            user = p.get("username")
            pwd = p.get("password")
            valid = p.get("valid", True)
            if not (host and port and user and pwd and valid):
                continue
            urls.append(f"http://{user}:{pwd}@{host}:{port}")
        return urls

    def refresh_if_due(self, force: bool = False) -> None:
        if not self._api_key:
            return
        now = time.time()
        with self._lock:
            if not force and (now - self._last_refresh) < _REFRESH_INTERVAL:
                return
            new_urls = self._fetch_from_webshare()
            if not new_urls:
                if not self._proxies:
                    log.warning(
                        "Webshare: no proxies fetched and pool is empty. "
                        "Proxy mode disabled for this run."
                    )
                return
            existing_urls = {p.url for p in self._proxies}
            new_set = set(new_urls)
            # Drop removed; add new (preserve bad_until for survivors)
            self._proxies = [p for p in self._proxies if p.url in new_set]
            for url in new_urls:
                if url not in existing_urls:
                    self._proxies.append(_ProxyEntry(url))
            random.shuffle(self._proxies)
            self._last_refresh = now
            log.info(
                f"Webshare proxy pool refreshed: {len(self._proxies)} proxies "
                "loaded."
            )

    def get_proxy(self) -> Optional[str]:
        """Return a healthy proxy URL, or None if no proxy available."""
        if not self.enabled:
            return None
        self.refresh_if_due()
        with self._lock:
            healthy = [p for p in self._proxies if p.is_healthy]
            if not healthy:
                # All proxies are bad — clear cooldowns and try again
                if self._proxies:
                    log.warning(
                        "All Webshare proxies are temporarily marked bad. "
                        "Clearing cooldowns."
                    )
                    for p in self._proxies:
                        p.bad_until = 0.0
                    healthy = list(self._proxies)
                else:
                    return None
            choice = random.choice(healthy)
            return choice.url

    def mark_bad(self, url: str | None) -> None:
        """Bench a proxy for a few minutes after it failed."""
        if not url:
            return
        with self._lock:
            for p in self._proxies:
                if p.url == url:
                    p.bad_until = time.time() + _BAD_PROXY_COOLDOWN
                    log.info(f"Marked proxy bad until {_BAD_PROXY_COOLDOWN}s: "
                             f"{p.url.split('@')[-1]}")
                    return

    def mark_quota_exceeded(self, reason: str = "") -> None:
        """Disable proxy mode entirely (e.g. Webshare 1GB free quota used).
        Will trigger a one-shot owner notification via maybe_notify_owner()."""
        with self._lock:
            if self._quota_exceeded:
                return
            self._quota_exceeded = True
            log.warning(f"Webshare quota exceeded: {reason} — proxy disabled.")

    def stats(self) -> dict:
        with self._lock:
            now = time.time()
            return {
                "enabled": self.enabled,
                "total": len(self._proxies),
                "healthy": sum(1 for p in self._proxies if p.is_healthy),
                "bad": sum(1 for p in self._proxies if not p.is_healthy),
                "quota_exceeded": self._quota_exceeded,
                "last_refresh_age": (int(now - self._last_refresh)
                                     if self._last_refresh else None),
            }

    # ----- notification helpers -----
    def should_notify_quota(self) -> bool:
        """Return True ONCE, the first time quota-exceeded is hit."""
        with self._lock:
            if self._quota_exceeded and not self._notified_quota:
                self._notified_quota = True
                return True
            return False


# ----- module-level singleton -----
_pool = _ProxyPool()


def init(api_key: str | None = None) -> None:
    """Initialise from explicit api_key OR environment WEBSHARE_API_KEY."""
    key = api_key if api_key is not None else os.environ.get("WEBSHARE_API_KEY", "")
    _pool.configure(key)
    if key:
        log.info("Webshare proxy: configured with API key. Fetching pool…")
        _pool.refresh_if_due(force=True)
    else:
        log.info("Webshare proxy: disabled (no WEBSHARE_API_KEY)")


def get_proxy() -> Optional[str]:
    return _pool.get_proxy()


def mark_bad(url: str | None) -> None:
    _pool.mark_bad(url)


def mark_quota_exceeded(reason: str = "") -> None:
    _pool.mark_quota_exceeded(reason)


def is_enabled() -> bool:
    return _pool.enabled


def stats() -> dict:
    return _pool.stats()


def should_notify_quota() -> bool:
    return _pool.should_notify_quota()


# ----- error classification helper -----
def is_quota_error(err_text: str) -> bool:
    """Detect Webshare 'monthly bandwidth exceeded' or '402 Payment Required'."""
    e = (err_text or "").lower()
    return any(s in e for s in (
        "monthly bandwidth",
        "bandwidth exceeded",
        "payment required",
        "quota exceeded",
        "402 payment",
    ))


def is_proxy_connection_error(err_text: str) -> bool:
    """Detect proxy-side errors (vs YouTube-side errors)."""
    e = (err_text or "").lower()
    return any(s in e for s in (
        "proxy connection",
        "proxyerror",
        "tunnel connection",
        "connection refused",
        "connection reset",
        "connect timeout",
        "407",  # Proxy Authentication Required
        "502 bad gateway",
        "504 gateway",
    ))


# ----- owner notification (fire-and-forget) -----
def schedule_quota_notice() -> None:
    """If quota was just hit, fire a one-shot DM to the bot owner.
    Safe to call from any thread — schedules an async task on the bot's
    event loop if one exists."""
    if not _pool.should_notify_quota():
        return
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
                "⚠️ **Webshare proxy limiti doldu**\n\n"
                "1 GB ücretsiz kotanız bitti — bot şu andan itibaren "
                "**proxy KULLANMADAN** çalışacak (cookie-less / cookies-li "
                "fallback). YouTube bot-check'i artarsa şarkı çalmama olabilir.\n\n"
                "Çözümler:\n"
                "• 1 ay bekleyin (kota yenilenir)\n"
                "• Webshare paid plana geçin\n"
                "• /unsetenv WEBSHARE_API_KEY ile tamamen kapatın",
            )
        except Exception as e:
            log.warning(f"owner notify failed: {e}")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(_notify(), loop)
        else:
            loop.create_task(_notify())
    except Exception:
        # No running loop — fire a quick threaded notice
        threading.Thread(
            target=lambda: asyncio.run(_notify()),
            daemon=True,
        ).start()
