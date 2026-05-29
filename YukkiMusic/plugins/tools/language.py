#
# /lang [en|tr]  — per-chat language switcher.
#

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import (CallbackQuery, InlineKeyboardButton,
                            InlineKeyboardMarkup, Message)

import config
from config import BANNED_USERS
from strings import get_string, languages
from YukkiMusic import app
from YukkiMusic.utils.database import get_lang, set_lang


def _lang_kb(current: str):
    rows = []
    for code, mod in languages.items():
        name = mod.get("name") or code.upper()
        prefix = "✅ " if code == current else ""
        rows.append([
            InlineKeyboardButton(f"{prefix}{name}", callback_data=f"set_lang|{code}")
        ])
    return InlineKeyboardMarkup(rows)


@app.on_message(
    filters.command(["lang", "language", "dil", "langs"]) & ~BANNED_USERS
)
async def lang_cmd(client, message: Message):
    chat_id = message.chat.id
    current = await get_lang(chat_id)
    # Direct arg: /lang en
    parts = message.text.split()
    if len(parts) >= 2:
        code = parts[1].lower()
        if code not in languages:
            return await message.reply_text(
                f"❌ Unknown language `{code}`.\nAvailable: " + ", ".join(languages.keys())
            )
        await set_lang(chat_id, code)
        _ = get_string(code)
        return await message.reply_text(
            _.get("lang_2", "✅ Language set to **{0}**.").format(languages[code].get("name") or code)
        )

    _ = get_string(current)
    await message.reply_text(
        _.get("lang_1", "🌐 **Select a language:**"),
        reply_markup=_lang_kb(current),
    )


@app.on_callback_query(filters.regex(r"^set_lang\|"))
async def lang_cb(client, query: CallbackQuery):
    code = query.data.split("|", 1)[1]
    chat_id = query.message.chat.id
    if code not in languages:
        return await query.answer("Unknown language", show_alert=True)
    await set_lang(chat_id, code)
    _ = get_string(code)
    name = languages[code].get("name") or code
    try:
        await query.message.edit_text(
            _.get("lang_2", "✅ Language set to **{0}**.").format(name)
        )
    except Exception:
        pass
    await query.answer("✅ OK")
