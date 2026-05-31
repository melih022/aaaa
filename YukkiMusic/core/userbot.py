#
# Modernized 2026: tolerant userbot init.
# Client instances are only created for *configured* string sessions.
# Missing slots stay as None (rather than constructing Client with "None" string).
#

from pyrogram import Client

import config

from ..logging import LOGGER

assistants = []
assistantids = []


def _make_client(name, session):
    if not session:
        return None
    return Client(
        name=name,
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=str(session),
        in_memory=True,
    )


class Userbot:
    def __init__(self):
        self.one = _make_client("YukkiOne", config.STRING1)
        self.two = _make_client("YukkiTwo", config.STRING2)
        self.three = _make_client("YukkiThree", config.STRING3)
        self.four = _make_client("YukkiFour", config.STRING4)
        self.five = _make_client("YukkiFive", config.STRING5)

    async def _start_slot(self, idx, client, label):
        if client is None:
            return
        try:
            await client.start()
        except Exception as e:
            LOGGER(__name__).error(
                f"Assistant {label} failed to start: {type(e).__name__}: {e}"
            )
            return
        assistants.append(idx)
        try:
            await client.send_message(config.LOG_GROUP_ID, "Assistant Started")
        except Exception:
            LOGGER(__name__).error(
                f"Assistant {label} log-group access failed (non-fatal). "
                "Add the assistant to the log group and promote as admin."
            )
        try:
            me = await client.get_me()
            client.username = me.username
            client.id = me.id
            assistantids.append(me.id)
            client.name = (
                f"{me.first_name} {me.last_name}" if me.last_name else (me.first_name or "")
            )
            LOGGER(__name__).info(f"Assistant {label} Started as {client.name}")
        except Exception as e:
            LOGGER(__name__).error(f"Assistant {label} get_me failed: {e}")

    async def start(self):
        LOGGER(__name__).info("Starting Assistant Clients")
        await self._start_slot(1, self.one,   "One")
        await self._start_slot(2, self.two,   "Two")
        await self._start_slot(3, self.three, "Three")
        await self._start_slot(4, self.four,  "Four")
        await self._start_slot(5, self.five,  "Five")
