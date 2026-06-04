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

    # --- Dynamic slot activation (used by /setstring & /genstring) ---------
    #
    # Lets the owner add a session AT RUNTIME (without a process restart)
    # and have the bot immediately discover + start the assistant. Solves the
    # "bot booted with no STRING_SESSION → /setsession does nothing until I
    # restart" bug, and the corresponding
    # `AttributeError: 'NoneType' object has no attribute 'play'`.
    async def activate_slot(self, slot: int, session_string: str):
        """Build + start a Client for ``slot`` (1..5) using the given session,
        wire it up with PyTgCalls, and make it available for /play right away.
        Safe to call from any handler — it is idempotent (stops the existing
        client first if one is already running for that slot).
        """
        if slot not in (1, 2, 3, 4, 5):
            raise ValueError("slot must be 1..5")

        slot_attr = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}[slot]
        label = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}[slot]

        # If a client already runs in this slot — tear it down first.
        existing = getattr(self, slot_attr, None)
        if existing is not None:
            try:
                if existing.is_connected:
                    await existing.stop()
            except Exception:
                pass
            if slot in assistants:
                try:
                    assistants.remove(slot)
                except ValueError:
                    pass

        # Build a new client bound to the running event loop.
        new_client = _make_client(f"Yukki{label}", session_string)
        setattr(self, slot_attr, new_client)

        # Start the client (this populates assistants/assistantids).
        await self._start_slot(slot, new_client, label)

        # Wire it up with PyTgCalls so /play works immediately.
        try:
            from pytgcalls import PyTgCalls
            from YukkiMusic.core.call import Yukki
            call_attr = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}[slot]
            call_userbot_attr = f"userbot{slot}"
            setattr(Yukki, call_userbot_attr, new_client)
            pytg = PyTgCalls(new_client, cache_duration=100)
            setattr(Yukki, call_attr, pytg)
            await pytg.start()
            # Re-register decorators so update events fire on the new instance.
            try:
                await Yukki.decorators()
            except Exception as e:
                LOGGER(__name__).warning(f"decorators re-register failed: {e}")
        except Exception as e:
            LOGGER(__name__).error(
                f"Assistant {label} PyTgCalls bind failed: {type(e).__name__}: {e}"
            )

        # Reflect the new value into the runtime config so other modules
        # that read config.STRING{n} pick it up without a restart.
        try:
            import config as _cfg
            setattr(_cfg, f"STRING{slot}", session_string)
            if slot == 1:
                _cfg.STRING1 = session_string
        except Exception:
            pass

        return slot in assistants
