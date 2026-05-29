#
# Unified /help command — tek sayfada tüm komutlar (TR + EN destekli).
#

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import (CallbackQuery, InlineKeyboardButton,
                            InlineKeyboardMarkup, Message)

from config import BANNED_USERS
from YukkiMusic import app
from YukkiMusic.utils.database import get_lang, set_lang


HELP_TR = """🎵 **MELİH MUSIC BOT — TÜM KOMUTLAR**

━━━━ 🎶 **Müzik (sesli sohbet)** ━━━━
• `/oynat` `/play` `<şarkı/link>` — sesli sohbette müzik çal
• `/voynat` `/vplay` `<şarkı/link>` — video oynat
• `/oynathemen` `/playforce` — ilk sonucu doğrudan çal (slider'sız)
• `/durdur` `/pause` — duraklat
• `/devam` `/resume` — devam ettir
• `/atla` `/skip` `[n]` — atla / n. parçaya
• `/son` `/stop` — sesli sohbeti sonlandır
• `/sira` `/queue` — sırayı göster
• `/karistir` `/shuffle` — sırayı karıştır
• `/tekrarla` `/loop` `<1-10>` — tekrarla
• `/ileri` `/seek` `<sn>` — ileri
• `/gerial` `/seekback` `<sn>` — geri
• `/botmute` `/mute` — sustur
• `/botunmute` `/unmute` — sesi aç

━━━━ 📥 **İndirme (her platform)** ━━━━
• `/song` `/mp3` `<link/sorgu>` — MP3 indir (Spotify/Apple → YouTube)
• `/dl` `<link>` — universal indir (YouTube canlı, Twitter, TikTok, Twitch, 1000+ site)
• `/video` `<link>` — video indir
• `/reels` `/insta` `<link>` — Instagram Reels/Post/IGTV
• `/bul` `/search` `<sorgu>` — YouTube'da ara

━━━━ 🤖 **Bot Araçları** ━━━━
• `/start` — botu başlat (özel mesajda)
• `/help` `/yardım` — bu menü
• `/ping` — gecikme
• `/stats` — istatistikler
• `/lang` `/dil` — dil değiştir (Türkçe/English)
• `/tts` `[tr/en/es/de/fr/ru]` `<metin>` — metni sese çevir
• `/lyrics` `/söz` `<şarkı>` — şarkı sözleri

━━━━ ⚙️ **Yönetim (grup admini)** ━━━━
• `/oynatmodu` `/playmode` — oynatma modu
• `/kanalmodu` `/channelplay` — kanal modu
• `/yetkiver` `/auth` — yetki ver
• `/yetkial` `/unauth` — yetki al
• `/yetkilistesi` `/authusers` — yetkililer
• `/reload` `/admincache` — admin listesini yenile
• `/restart` — botu sıfırla
• `/ayarlar` `/settings` — ayar paneli

━━━━ 🛡️ **Sahip (Owner-only PM)** ━━━━
• `/genstring` — interaktif asistan session üret
• `/setstring` `<session>` `[slot]` — hazır session yapıştır
• `/sessions` — slot durumu
• `/clearsession` `<1-5>` — slotu sil
• `/logs` `[N]` — supervisor log
• `/lasterror` — son 5 exception
• `/testytdlp` `<sorgu>` — yt-dlp test
• `/pyver` — sürüm bilgisi
• `/env` — .env (maskeli)
• `/setcleanup` `<dk>` `[yaş]` — auto-cleanup ayarla
• `/cleanup` `[yaş]` — anlık temizle
• `/cleanupstatus` — disk durumu
• `/getrepo` — güncel ZIP'i Telegram'dan al
• `/broadcast` — duyuru
• `/gban` `/ungban` — global ban
• `/block` `/unblock` — bot kullanım banı
• `/blacklistchat` `/whitelistchat` — grup banı
• `/addsudo` `/delsudo` — sudo yetkisi
• `/maintenance` — bakım modu
• `/speedtest` — hız testi

💡 _Komutları hem Türkçe hem İngilizce yazabilirsiniz._
"""

HELP_EN = """🎵 **MELIH MUSIC BOT — ALL COMMANDS**

━━━━ 🎶 **Music (voice chat)** ━━━━
• `/play` `<song/link>` — play music in voice chat
• `/vplay` `<song/link>` — play video
• `/playforce` — instant play (skip slider)
• `/pause` — pause
• `/resume` — resume
• `/skip` `[n]` — skip / to nth track
• `/stop` `/end` — end voice chat
• `/queue` — show queue
• `/shuffle` — shuffle queue
• `/loop` `<1-10>` — loop track
• `/seek` `<sec>` — seek forward
• `/seekback` `<sec>` — seek backward
• `/mute` `/unmute` — mute / unmute

━━━━ 📥 **Downloaders (all platforms)** ━━━━
• `/song` `/mp3` `<link/query>` — download MP3 (Spotify/Apple → YouTube)
• `/dl` `<link>` — universal downloader (YT live, X/Twitter, TikTok, Twitch, 1000+ sites)
• `/video` `<link>` — download video
• `/reels` `/insta` `<link>` — Instagram Reels/Post/IGTV
• `/search` `<query>` — search YouTube

━━━━ 🤖 **Bot Tools** ━━━━
• `/start` — start bot (in PM)
• `/help` — this menu
• `/ping` — latency
• `/stats` — statistics
• `/lang` — switch language (Turkish/English)
• `/tts` `[tr/en/es/de/fr/ru]` `<text>` — text-to-speech
• `/lyrics` `<song>` — get lyrics

━━━━ ⚙️ **Group Admin** ━━━━
• `/playmode` — change playmode
• `/channelplay` — channel mode
• `/auth` `/unauth` — authorize users
• `/authusers` — list authorized
• `/reload` `/admincache` — refresh admin cache
• `/restart` — reset bot in group
• `/settings` — settings panel

━━━━ 🛡️ **Owner-only (PM)** ━━━━
• `/genstring` — interactive session generator
• `/setstring` `<session>` `[slot]` — paste a session
• `/sessions` — slot status
• `/clearsession` `<1-5>` — clear slot
• `/logs` `[N]` — view supervisor log
• `/lasterror` — last 5 exceptions
• `/testytdlp` `<query>` — test yt-dlp search
• `/pyver` — version info
• `/env` — .env (masked)
• `/setcleanup` `<min>` `[age]` — auto-cleanup
• `/cleanup` `[age]` — clean now
• `/cleanupstatus` — disk status
• `/getrepo` — receive latest ZIP via Telegram
• `/broadcast` — broadcast message
• `/gban` `/ungban` — global ban
• `/block` `/unblock` — usage ban
• `/blacklistchat` `/whitelistchat` — chat ban
• `/addsudo` `/delsudo` — sudo rights
• `/maintenance` — maintenance mode
• `/speedtest` — speed test

💡 _All commands work in both Turkish & English._
"""


def _lang_kb(current: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                ("✅ " if current == "tr" else "") + "🇹🇷 Türkçe",
                callback_data="help_lang|tr",
            ),
            InlineKeyboardButton(
                ("✅ " if current == "en" else "") + "🇬🇧 English",
                callback_data="help_lang|en",
            ),
        ],
        [InlineKeyboardButton("❌ Kapat / Close", callback_data="help_close")],
    ])


@app.on_message(filters.command(["help", "yardım", "yardim"]) & ~BANNED_USERS)
async def help_cmd(client, message: Message):
    chat_id = message.chat.id
    try:
        lang = await get_lang(chat_id)
    except Exception:
        lang = "tr"
    text = HELP_EN if lang == "en" else HELP_TR
    try:
        await message.reply_text(
            text,
            reply_markup=_lang_kb(lang),
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        await message.reply_text(text, disable_web_page_preview=True)


@app.on_callback_query(filters.regex(r"^help_lang\|"))
async def help_lang_cb(client, query: CallbackQuery):
    code = query.data.split("|", 1)[1]
    chat_id = query.message.chat.id
    if code not in ("tr", "en"):
        return await query.answer("Unknown language")
    await set_lang(chat_id, code)
    text = HELP_EN if code == "en" else HELP_TR
    try:
        await query.message.edit_text(
            text,
            reply_markup=_lang_kb(code),
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
        )
        await query.answer("✅ " + ("English" if code == "en" else "Türkçe"))
    except Exception as e:
        await query.answer(f"❌ {type(e).__name__}", show_alert=True)


@app.on_callback_query(filters.regex(r"^help_close$"))
async def help_close_cb(client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer()
