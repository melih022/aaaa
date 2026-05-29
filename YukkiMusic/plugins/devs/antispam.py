#
# Lightweight in-memory anti-spam (flood) protection.
# Triggers on rapid commands from the same user OR same chat.
# Bans the user from BANNED_USERS filter for 60 seconds after 8 commands in 5 seconds.
#

import asyncio
import time
from collections import defaultdict, deque

from pyrogram import filters
from pyrogram.types import Message

import config
from config import BANNED_USERS
from YukkiMusic import app

# (user_id) -> deque[timestamps]
_user_hits: dict[int, deque] = defaultdict(lambda: deque(maxlen=20))
# (chat_id) -> deque[timestamps]
_chat_hits: dict[int, deque] = defaultdict(lambda: deque(maxlen=40))

# user_id -> unban_at
_temp_banned: dict[int, float] = {}

WINDOW = 5.0           # 5-second window
USER_LIMIT = 8         # max commands / user / window
CHAT_LIMIT = 25        # max commands / chat / window
BAN_DURATION = 60.0    # seconds


async def _notify(client, chat_id, text):
    try:
        await client.send_message(chat_id, text)
    except Exception:
        pass


@app.on_message(filters.command([], "/") & ~filters.me, group=-2)
async def spam_guard(client, message: Message):
    """Runs BEFORE all other handlers (group=-2)."""
    now = time.time()
    uid = message.from_user.id if message.from_user else 0
    cid = message.chat.id

    # Whitelist owners
    if uid in config.OWNER_ID:
        return

    # Currently in temp-ban?
    unban_at = _temp_banned.get(uid, 0)
    if unban_at > now:
        try:
            await message.stop_propagation()  # block downstream handlers
        except Exception:
            pass
        return
    if uid in _temp_banned and unban_at <= now:
        _temp_banned.pop(uid, None)
        BANNED_USERS.remove(uid) if uid in BANNED_USERS else None

    # Track hits
    if uid:
        dq = _user_hits[uid]
        dq.append(now)
        recent = sum(1 for t in dq if now - t <= WINDOW)
        if recent > USER_LIMIT:
            _temp_banned[uid] = now + BAN_DURATION
            BANNED_USERS.add(uid)
            await _notify(
                client, cid,
                f"🛑 Flood detected from [user](tg://user?id={uid}). "
                f"Muted for {int(BAN_DURATION)} seconds.",
            )
            try:
                await message.stop_propagation()
            except Exception:
                pass
            return

    dq = _chat_hits[cid]
    dq.append(now)
    recent = sum(1 for t in dq if now - t <= WINDOW)
    if recent > CHAT_LIMIT:
        await _notify(
            client, cid,
            f"🛑 Chat-wide flood detected. Calm down for a moment please.",
        )
        try:
            await message.stop_propagation()
        except Exception:
            pass
        return
