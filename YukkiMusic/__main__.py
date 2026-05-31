#
# Modernized 2026 - tolerant startup; bot stays alive without assistants.
#

import asyncio
import importlib

from pyrogram import idle

try:
    from pytgcalls.exceptions import NoActiveGroupCall
except ImportError:
    class NoActiveGroupCall(Exception):
        pass

import config
from config import BANNED_USERS
from YukkiMusic import LOGGER, app, userbot
from YukkiMusic.core.call import Yukki
from YukkiMusic.plugins import ALL_MODULES
from YukkiMusic.utils.database import get_banned_users, get_gbanned


async def init():
    has_assistants = bool(
        config.STRING1 or config.STRING2 or config.STRING3
        or config.STRING4 or config.STRING5
    )

    if not has_assistants:
        LOGGER("YukkiMusic").warning(
            "Asistan (STRING_SESSION) yok. Bot çalışmaya devam edecek; "
            "owner /genstring veya /setstring ile session ekleyebilir."
        )

    try:
        users = await get_gbanned()
        for u in users:
            BANNED_USERS.add(u)
        users = await get_banned_users()
        for u in users:
            BANNED_USERS.add(u)
    except Exception:
        pass

    # Robust bot start: handle FloodWait gracefully (sleep then retry once).
    from pyrogram.errors import FloodWait
    while True:
        try:
            await app.start()
            break
        except FloodWait as fw:
            wait_s = int(getattr(fw, "value", 0) or 60)
            LOGGER("YukkiMusic").warning(
                f"Bot login FloodWait: sleeping {wait_s}s before retry."
            )
            await asyncio.sleep(wait_s + 5)
        except Exception as e:
            LOGGER("YukkiMusic").error(f"Bot start fatal: {type(e).__name__}: {e}")
            raise

    for m in ALL_MODULES:
        importlib.import_module("YukkiMusic.plugins" + m)
    LOGGER("Yukkimusic.plugins").info("Moduller iceri aktarildi")

    if has_assistants:
        try:
            await userbot.start()
        except Exception as e:
            LOGGER("YukkiMusic").error(f"Userbot start error: {e}")
        try:
            await Yukki.start()
        except Exception as e:
            LOGGER("YukkiMusic").error(f"PyTgCalls start error: {e}")
        try:
            await Yukki.stream_call(
                "http://docs.evostream.com/sample_content/assets/sintel1m720p.mp4"
            )
        except NoActiveGroupCall:
            LOGGER("YukkiMusic").warning(
                "Log grubunda sesli sohbet kapali. Lutfen acin."
            )
        except Exception:
            pass
        try:
            await Yukki.decorators()
        except Exception as e:
            LOGGER("YukkiMusic").error(f"PyTgCalls decorators error: {e}")
    else:
        LOGGER("YukkiMusic").info(
            "Asistansiz mod: bot komutlari aktif, sesli sohbet kapali."
        )

    LOGGER("YukkiMusic").info("Melih Music Bot basariyla baslatildi")
    await idle()


if __name__ == "__main__":
    # NOTE: do NOT use asyncio.run() / new_event_loop — pyrogram Client objects
    # are constructed at module import time and bind to `asyncio.get_event_loop()`.
    # Creating a fresh loop detaches them and triggers
    # "Task got Future attached to a different loop".
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init())
    except KeyboardInterrupt:
        pass
    LOGGER("YukkiMusic").info("Bot durduruldu. Gule gule.")
