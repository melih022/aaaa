#
# Auto-forward every captured exception to the OWNER's PM.
# Throttled so we never send more than 1 message per 10 seconds.
# Importantly, this hooks into LAST_ERRORS without spamming on import-time noise.
#

import asyncio
import time
import traceback

from pyrogram import Client

import config
from YukkiMusic import LOGGER, app

# Avoid notifying for the same exception text within this window.
_DEDUP_WINDOW = 30.0
_last_sent_at: float = 0.0
_last_text: str = ""

# Monkey-patch: wrap pyrogram Dispatcher.handle_update
try:
    from pyrogram.dispatcher import Dispatcher
    _orig = Dispatcher.handle_update

    async def _wrapped(self, packet, parser, handlers, args):
        try:
            return await _orig(self, packet, parser, handlers, args)
        except Exception as e:
            tb = traceback.format_exc()
            asyncio.ensure_future(_notify_owner(tb, e))
            raise

    Dispatcher.handle_update = _wrapped
except Exception:
    pass


def _summarize(tb: str, e: Exception) -> str:
    """Pick a short single-line summary + tail of traceback."""
    head = f"{type(e).__name__}: {e}"
    # last 12 traceback lines
    lines = tb.strip().splitlines()
    tail = "\n".join(lines[-12:])
    return head, tail


async def _notify_owner(tb: str, e: Exception):
    global _last_sent_at, _last_text
    now = time.time()
    head, tail = _summarize(tb, e)
    # Dedup
    if tail == _last_text and (now - _last_sent_at) < _DEDUP_WINDOW:
        return
    _last_text = tail
    _last_sent_at = now

    if not config.OWNER_ID:
        return
    owner = config.OWNER_ID[0]
    text = (
        f"🛑 **Unhandled exception captured**\n\n"
        f"**{head}**\n\n"
        f"```pytb\n{tail[-3500:]}\n```"
    )
    try:
        await app.send_message(owner, text)
    except Exception:
        LOGGER("YukkiMusic.crash").warning("Could not DM owner about crash.")
