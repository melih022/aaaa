#
# Background task: keep `downloads/` (and ads/ cache) trimmed.
# Deletes any file older than CLEAN_AGE_SECONDS. Runs every CLEAN_INTERVAL_SECONDS.
#
# Started from YukkiMusic.__main__ after the bot boots.
#

import asyncio
import os
import time

from YukkiMusic import LOGGER

LOG = LOGGER("YukkiMusic.autoclean")

# User-requested: any media file 1 minute after creation should be removed
# to keep the VPS disk healthy.
CLEAN_AGE_SECONDS = 60
CLEAN_INTERVAL_SECONDS = 30

# Resolve bot root from this file's path so cwd doesn't matter.
_BOT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Directories scanned. cookies/ is intentionally excluded.
WATCH_DIRS = [
    os.path.join(_BOT_ROOT, "downloads"),
    os.path.join(_BOT_ROOT, "raw_files"),
]

# Extensions we feel safe deleting (avoid wiping logs/code accidentally)
DELETABLE_EXTS = (
    ".mp3", ".mp4", ".m4a", ".webm", ".opus", ".aac",
    ".mkv", ".flac", ".ogg", ".wav", ".part", ".ytdl",
)


def _try_delete(path: str) -> bool:
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        LOG.warning(f"autoclean: failed to delete {path}: {e}")
        return False


async def _sweep_once():
    now = time.time()
    deleted = 0
    for d in WATCH_DIRS:
        if not os.path.isdir(d):
            continue
        try:
            for name in os.listdir(d):
                if not name.lower().endswith(DELETABLE_EXTS):
                    continue
                p = os.path.join(d, name)
                if not os.path.isfile(p):
                    continue
                try:
                    age = now - os.path.getmtime(p)
                except OSError:
                    continue
                if age >= CLEAN_AGE_SECONDS:
                    if _try_delete(p):
                        deleted += 1
        except Exception as e:
            LOG.warning(f"autoclean: sweep error in {d}: {e}")
    if deleted:
        LOG.info(f"autoclean: removed {deleted} stale media file(s).")


async def autoclean_loop():
    LOG.info(
        f"autoclean started — files older than {CLEAN_AGE_SECONDS}s in "
        f"{WATCH_DIRS} will be deleted every {CLEAN_INTERVAL_SECONDS}s."
    )
    while True:
        try:
            await _sweep_once()
        except Exception as e:
            LOG.error(f"autoclean loop error: {e}")
        await asyncio.sleep(CLEAN_INTERVAL_SECONDS)
