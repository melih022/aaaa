"""
LRU cache + sticky-strategy memory for YouTube extraction (2026-06).

Speedup techniques implemented here:
  1. Search result cache (query → top result) — TTL 30 min
  2. Stream-URL cache (video_id → direct URL) — TTL 5 hours (URLs expire ~6h)
  3. Sticky strategy memory — remember the last player_client combo that
     worked, try it FIRST next time (saves ~70% of failed attempts when
     a strategy is consistently working)

All caches are in-memory with a per-key timestamp. No disk persistence —
keeps it simple and stale entries auto-expire.

Thread-safe via a single RLock since the bot does parallel /play across
many groups simultaneously.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Optional


class _TTLCache:
    """Tiny LRU + TTL cache. Not async-safe by itself but guarded by lock."""

    def __init__(self, max_size: int = 256, ttl_seconds: int = 1800):
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max = max_size
        self._ttl = ttl_seconds
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, val = entry
            if (time.time() - ts) > self._ttl:
                # expired — remove
                self._store.pop(key, None)
                return None
            # touch LRU
            self._store.move_to_end(key)
            return val

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (time.time(), value)
            while len(self._store) > self._max:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        with self._lock:
            now = time.time()
            fresh = sum(
                1 for ts, _ in self._store.values()
                if (now - ts) <= self._ttl
            )
            return {
                "total": len(self._store),
                "fresh": fresh,
                "max": self._max,
                "ttl": self._ttl,
            }


# ----- Singleton instances -----
# Search results: cache for 30 minutes (queries are often repeated)
search_cache = _TTLCache(max_size=512, ttl_seconds=30 * 60)

# Stream URLs: cache for 5 hours (YouTube URLs expire ~6h)
stream_cache = _TTLCache(max_size=512, ttl_seconds=5 * 60 * 60)

# Video metadata (title, duration, thumbnail) — same TTL as search
meta_cache = _TTLCache(max_size=512, ttl_seconds=30 * 60)


# ----- Sticky strategy memory -----
_strategy_lock = threading.RLock()
_last_good_strategy: Optional[str] = None
_strategy_history: dict[str, int] = {}  # strategy_id -> success_count


def remember_strategy(strategy_id: str) -> None:
    """Mark this strategy as the last-known-good one. Caller can then put
    it FIRST in the strategy list for the next request."""
    global _last_good_strategy
    with _strategy_lock:
        _last_good_strategy = strategy_id
        _strategy_history[strategy_id] = _strategy_history.get(strategy_id, 0) + 1


def last_good_strategy() -> Optional[str]:
    with _strategy_lock:
        return _last_good_strategy


def strategy_stats() -> dict[str, int]:
    with _strategy_lock:
        return dict(_strategy_history)


# ----- Helpers -----
def all_stats() -> dict:
    return {
        "search_cache": search_cache.stats(),
        "stream_cache": stream_cache.stats(),
        "meta_cache": meta_cache.stats(),
        "last_good_strategy": last_good_strategy(),
        "strategy_history": strategy_stats(),
    }


def clear_all() -> None:
    search_cache.clear()
    stream_cache.clear()
    meta_cache.clear()
