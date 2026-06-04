#
# Modernized 2026 - tolerant startup; bot stays alive without assistants.
#

import asyncio
import importlib
import os

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

    # 2026-02 fix: register the Telegram client commands menu (the blue
    # "Menu" button next to the chat input) so users see /start /play /help
    # etc. on a fresh chat. This was previously missing — the bot answered
    # commands but the menu was empty.
    try:
        from pyrogram.types import BotCommand
        await app.set_bot_commands([
            BotCommand("start",        "Botu başlat / hoş geldin mesajı"),
            BotCommand("help",         "Komut listesini göster"),
            BotCommand("play",         "Şarkı çal (link veya isim)"),
            BotCommand("vplay",        "Video çal (link veya isim)"),
            BotCommand("playforce",    "Sırayı atlayıp hemen çal"),
            BotCommand("vplayforce",   "Video — sırayı atlayıp hemen çal"),
            BotCommand("pause",        "Çalmayı duraklat"),
            BotCommand("resume",       "Çalmaya devam et"),
            BotCommand("skip",         "Sonraki şarkıya geç"),
            BotCommand("stop",         "Çalmayı durdur"),
            BotCommand("end",          "Sesli sohbeti bitir"),
            BotCommand("queue",        "Sıradaki şarkıları göster"),
            BotCommand("shuffle",      "Sırayı karıştır"),
            BotCommand("loop",         "Tekrar modunu aç/kapa"),
            BotCommand("song",         "MP3 / video indir"),
            BotCommand("lyrics",       "Şarkı sözlerini göster"),
            BotCommand("search",       "YouTube'da ara"),
            BotCommand("ping",         "Bot gecikmesini ölç"),
            BotCommand("stats",        "Bot istatistikleri"),
            BotCommand("sessions",     "(Sahip) Session slot durumu"),
            BotCommand("genstring",    "(Sahip) Yeni string-session üret"),
            BotCommand("setstring",    "(Sahip) Hazır string-session yapıştır"),
            BotCommand("clearsession", "(Sahip) Session slotunu sil"),
            BotCommand("restart",      "(Sahip) Botu yeniden başlat"),
        ])
        LOGGER("YukkiMusic").info("Bot commands menüsü yüklendi.")
    except Exception as e:
        LOGGER("YukkiMusic").warning(
            f"set_bot_commands başarısız: {type(e).__name__}: {e}"
        )

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

    # Diagnostic: log cookies status at startup so user sees in journalctl
    # whether yt-dlp will have cookies available BEFORE the first /play.
    try:
        from YukkiMusic.platforms.Youtube import _current_cookies
        cf = _current_cookies()
        if cf:
            LOGGER("YukkiMusic").info(
                f"YouTube cookies tespit edildi: {cf} "
                f"({os.path.getsize(cf):,} byte)"
            )
        else:
            LOGGER("YukkiMusic").warning(
                "YouTube cookies BULUNAMADI. yt-dlp YouTube'a erişemeyecek. "
                "Bota PM'den /setcookies ile cookies.txt yükleyin."
            )
    except Exception as e:
        LOGGER("YukkiMusic").error(f"cookies status check failed: {e}")

    # Background autoclean — drops downloaded media 60s after creation
    # so the VPS disk stays small even after thousands of /play calls.
    try:
        from YukkiMusic.utils.autoclean import autoclean_loop
        asyncio.create_task(autoclean_loop())
    except Exception as e:
        LOGGER("YukkiMusic").error(f"autoclean failed to start: {e}")

    # Initialise Webshare proxy pool (if WEBSHARE_API_KEY set in .env).
    # Fetches the proxy list on startup so the first /play already has
    # proxies available.
    try:
        from YukkiMusic.utils import proxy_manager
        proxy_manager.init(os.environ.get("WEBSHARE_API_KEY", ""))
        st = proxy_manager.stats()
        if st["enabled"]:
            LOGGER("YukkiMusic").info(
                f"Webshare proxy: ✅ {st['total']} proxy yüklendi"
            )
        else:
            LOGGER("YukkiMusic").info(
                "Webshare proxy: kapalı (WEBSHARE_API_KEY yok)"
            )
    except Exception as e:
        LOGGER("YukkiMusic").warning(f"Webshare proxy init failed: {e}")

    # Initialise YouTube Data API v3 (if YOUTUBE_API_KEY set in .env).
    # Used for the search step → bypasses yt-dlp's bot-check for search.
    try:
        from YukkiMusic.utils import youtube_api
        youtube_api.configure(os.environ.get("YOUTUBE_API_KEY", ""))
        if youtube_api.is_enabled():
            LOGGER("YukkiMusic").info(
                "YouTube Data API: ✅ aktif (arama API üzerinden)"
            )
        else:
            LOGGER("YukkiMusic").info(
                "YouTube Data API: kapalı (YOUTUBE_API_KEY yok) — arama yt-dlp ile"
            )
    except Exception as e:
        LOGGER("YukkiMusic").warning(f"YT Data API init failed: {e}")

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
