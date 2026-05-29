#
# /tts <metin>  – Text-to-Speech via edge-tts (high-quality neural voices).
# Falls back to gTTS if edge-tts is unavailable.
#

import asyncio
import os
import uuid

from pyrogram import filters
from pyrogram.types import Message

from config import BANNED_USERS
from YukkiMusic import app

TTS_DIR = "downloads/tts"
os.makedirs(TTS_DIR, exist_ok=True)


async def _edge_tts(text: str, voice: str, out: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=voice)
    await communicate.save(out)


def _gtts(text: str, out: str, lang: str = "tr"):
    from gtts import gTTS
    gTTS(text, lang=lang).save(out)


@app.on_message(filters.command(["tts", "ses"]) & ~BANNED_USERS)
async def tts_cmd(client, message: Message):
    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply_text(
            "🗣️ **Metni Sese Çevir**\n\n"
            "Kullanım: `/tts <metin>` veya yanıtlanan mesajla `/tts`\n"
            "Belirli ses: `/tts [tr|en|es|de] <metin>`"
        )

    parts = message.text.split(None, 2)
    lang = "tr"
    if len(parts) >= 3 and parts[1].lower() in ("tr", "en", "es", "de", "fr", "ru"):
        lang = parts[1].lower()
        text = parts[2]
    elif len(parts) >= 2:
        text = message.text.split(None, 1)[1]
    elif message.reply_to_message and (
        message.reply_to_message.text or message.reply_to_message.caption
    ):
        text = message.reply_to_message.text or message.reply_to_message.caption
    else:
        return await message.reply_text("❌ Metin yok.")

    text = text[:1500]
    out = os.path.join(TTS_DIR, f"{uuid.uuid4().hex}.mp3")

    voices = {
        "tr": "tr-TR-EmelNeural",
        "en": "en-US-AriaNeural",
        "es": "es-ES-ElviraNeural",
        "de": "de-DE-KatjaNeural",
        "fr": "fr-FR-DeniseNeural",
        "ru": "ru-RU-SvetlanaNeural",
    }

    status = await message.reply_text("🔊 Oluşturuluyor…")
    try:
        await _edge_tts(text, voices.get(lang, voices["tr"]), out)
    except Exception:
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _gtts, text, out, lang)
        except Exception as e:
            return await status.edit_text(f"❌ Hata: `{type(e).__name__}`")

    try:
        await message.reply_voice(voice=out)
    except Exception:
        await message.reply_audio(audio=out, title="TTS")
    finally:
        try:
            os.remove(out)
        except Exception:
            pass
    await status.delete()
