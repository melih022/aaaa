#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram import Client as app
from strings import get_command, get_string
from YukkiMusic import app
from YukkiMusic.misc import SUDOERS
from YukkiMusic.utils.database import (get_lang, is_maintenance,
                                       maintenance_off,
                                       maintenance_on)
from YukkiMusic.utils.decorators.language import language

# Commands
MAINTENANCE_COMMAND = get_command("MAINTENANCE_COMMAND")
TEMIZLEME_COMMAND = get_command("TEMIZLEME_COMMAND")
SAHIP_COMMAND = get_command("SAHIP_COMMAND")

@app.on_message(filters.command(MAINTENANCE_COMMAND) & SUDOERS)
async def maintenance(client, message: Message):
    try:
        language = await get_lang(message.chat.id)
        _ = get_string(language)
    except:
        _ = get_string("tr")
    usage = _["maint_1"]
    if len(message.command) != 2:
        return await message.reply_text(usage)
    message.chat.id
    state = message.text.split(None, 1)[1].strip()
    state = state.lower()
    if state == "enable":
        if await is_maintenance() is False:
            await message.reply_text(
                "Bakım modu zaten etkin"
            )
        else:
            await maintenance_on()
            await message.reply_text(_["maint_2"])
    elif state == "disable":
        if await is_maintenance() is False:
            await maintenance_off()
            await message.reply_text(_["maint_3"])
        else:
            await message.reply_text(
                "Bakım modu zaten devre dışı"
            )
    else:
        await message.reply_text(usage)

downloads = os.path.realpath("downloads")
raw = os.path.realpath(".")

@app.on_message(filters.command(TEMIZLEME_COMMAND) & SUDOERS)     
async def clear_downloads(_, message: Message):
    ls_dir = os.listdir(downloads)
    if ls_dir:
        for file in os.listdir(downloads):
            os.remove(os.path.join(downloads, file))
        await message.reply_text("**downloads klasoru silindi**")
    else:
        await message.reply_text("**temiz zaten**")
        
        
@app.on_message(filters.command(SAHIP_COMMAND) & SUDOERS)
async def mesaj(client, message: Message):
  await message.reply("**               ●𝐒𝐀𝐇İ𝐁İ𝐌●   **\n\n⫸⫸⫸⫸⫸⬇️⬇️⬇️⫷⫷⫷⫷⫷\n\n      @Deeperim\n @MissSahip ♚♚ @intikamKurucusu")
