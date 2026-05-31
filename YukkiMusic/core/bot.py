#
# Modernized 2026: tolerant bot startup (don't sys.exit on log-group issues).
#

from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import BotCommand

import config

from ..logging import LOGGER


class YukkiBot(Client):
    def __init__(self):
        LOGGER(__name__).info("Starting Bot")
        super().__init__(
            name="YukkiMusicBot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            workdir=".",
        )

    async def start(self):
        await super().start()
        get_me = await self.get_me()
        self.username = get_me.username
        self.id = get_me.id
        try:
            await self.send_message(config.LOG_GROUP_ID, "Bot Started")
        except Exception as e:
            LOGGER(__name__).error(
                f"Log group {config.LOG_GROUP_ID} access failed: {type(e).__name__}: {e}. "
                "Add the bot to the log group and promote as admin to fix. "
                "Continuing tolerantly."
            )
        else:
            try:
                a = await self.get_chat_member(config.LOG_GROUP_ID, self.id)
                if a.status != ChatMemberStatus.ADMINISTRATOR:
                    LOGGER(__name__).warning(
                        "Bot is not Administrator in the log group. "
                        "Some features (e.g. message edit/delete in log) may fail."
                    )
            except Exception as e:
                LOGGER(__name__).warning(
                    f"Could not verify bot admin status in log group: {e}"
                )
        self.name = (
            f"{get_me.first_name} {get_me.last_name}" if get_me.last_name else (get_me.first_name or "")
        )
        LOGGER(__name__).info(f"MusicBot Started as {self.name}")
