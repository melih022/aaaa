# 🎵 Melih Music Bot (2026 modernized fork of YukkiMusicBot)

Telegram sesli sohbet müzik botu — Python 3.12+, kurigram, py-tgcalls 2.2+ ile çalışır.
**Bilingual**: Türkçe + İngilizce. `/lang` ile anında dil değiştir.

---

## 🚀 Hızlı Kurulum

### Gereksinimler
- **Python 3.10+** (önerilen 3.12)
- `ffmpeg` (sistem üzerinde kurulu)
- MongoDB URI (Atlas veya lokal)
- Telegram API kimliği (`my.telegram.org` → API_ID, API_HASH)
- Bot token (@BotFather)

### Adımlar
```bash
git clone <repo>  &&  cd melih_bot_v2
pip install -r requirements.txt

# pyrogram.emoji uyumluluk stub (kurigram + pykeyboard için tek seferlik)
python3 - <<'EOF'
import pyrogram, os
p = os.path.join(os.path.dirname(pyrogram.__file__), 'emoji.py')
open(p, 'w').write("""FLAG_BELARUS=\"🇧🇾\"
FLAG_CHINA=\"🇨🇳\"
FLAG_FRANCE=\"🇫🇷\"
FLAG_GERMANY=\"🇩🇪\"
FLAG_INDONESIA=\"🇮🇩\"
FLAG_ITALY=\"🇮🇹\"
FLAG_RUSSIA=\"🇷🇺\"
FLAG_SOUTH_KOREA=\"🇰🇷\"
FLAG_SPAIN=\"🇪🇸\"
FLAG_TURKEY=\"🇹🇷\"
FLAG_UKRAINE=\"🇺🇦\"
FLAG_UNITED_KINGDOM=\"🇬🇧\"
FLAG_UZBEKISTAN=\"🇺🇿\"
""")
EOF

# .env doldur (sample.env'i kopyala)
cp sample.env .env  &&  $EDITOR .env

# Botu başlat
bash start
# veya doğrudan
python3 -m YukkiMusic
```

### Asistan Hesabı (Sesli sohbet için ZORUNLU)
Bot artık session olmadan da BAŞLAR. Owner olarak Telegram PM'den:

1. `/genstring` → telefon → OTP (`1 2 3 4 5` şeklinde) → (varsa 2FA) → ✅
2. Bot otomatik kaydeder ve kendini yeniden başlatır
3. Session string ayrıca size mesaj olarak iletilir (yedek için)

Veya yerel olarak üret: `python3 genstring.py` ve `/setstring <STRING>` ile paste et.

---

## ✨ Sürüm Notları (Ocak 2026)

### Kütüphane Güncellemeleri
- ✅ **py-tgcalls 2.2.12** — yeni `MediaStream` API
- ✅ **kurigram 2.2.23** — modern Pyrogram fork
- ✅ **yt-dlp 2026.x** — güncel YouTube imzaları
- ✅ Python 3.12 Docker image
- ❌ `youtubesearchpython` (terkedilmiş) tamamen kaldırıldı

### Pyrogram 2.x Uyumluluğu
- `message.message_id` → `message.id` (25 yerde fix)
- `can_manage_voice_chats` → `privileges.can_manage_video_chats`
- Bilingual hata mesajları + exception type+message kullanıcıya gösteriliyor

### Yeni Özellikler
| Komut | Açıklama |
|---|---|
| `/play <şarkı>` veya `/play` + audio reply | Sesli sohbette müzik çal (YouTube ana kaynak) |
| `/vplay <link>` | Video stream |
| `/reels <link>` | Instagram Reels/Post/IGTV indir + private chat auto-detect |
| `/dl <link>` | Universal indirici (YouTube canlı, Twitter/X, TikTok, Twitch, Vimeo, 1000+ site) |
| `/mp3 <link veya sorgu>` | Sadece ses indir (MP3 192kbps). Spotify/Apple linklerini YouTube'a yönlendirir. |
| `/tts [tr/en/es/de/fr/ru] <metin>` | Yapay zeka sesi (Edge Neural) |
| `/lang [tr/en]` | Dil değiştir — komut yanıtları seçilen dilde gelir |
| `/song <şarkı>` | Müzik indir + Telegram'a ses olarak gönder |
| `/lyrics <şarkı>` | Şarkı sözleri |

### Owner-Only Komutlar (PM)
| Komut | Açıklama |
|---|---|
| `/genstring` | Interaktif session üretici (telefon + OTP) |
| `/setstring <string> [slot]` | Hazır session yapıştır (5 slot) |
| `/sessions` | Slot durumu |
| `/clearsession <1-5>` | Slotu sil |
| `/restart` | Botu yeniden başlat (os.execv) |
| `/logs [N]` | Son N satır supervisor log (dosya olarak) |
| `/lasterror` | Son 5 handler exception traceback'i |
| `/testytdlp <sorgu>` | yt-dlp aramasını anında test et |
| `/pyver` | Python + kütüphane sürümleri |
| `/env` | `.env` içeriği (şifreler maskeli) |

### Hata Bildirimi
- ⚡ Tüm yakalanmamış handler exception'ları **otomatik olarak OWNER'a DM** gönderilir (30 sn dedup)
- Owner her zaman `/lasterror` ile son 5 hatayı görüntüleyebilir
- `Sorgu işlenemedi!` mesajları artık altında **gerçek exception** gösteriyor

### Anti-Spam Koruması
- Kullanıcı başına: 5 saniyede 8 komut üstü → 60 sn temp-ban
- Grup başına: 5 saniyede 25 komut üstü → uyarı
- Owner'lar bağışıklı

### Medya Kaynak Önceliği
- **YouTube ana kaynak**: Tüm aramalar yt-dlp ile YouTube'a düşer
- Spotify, Apple Music, Resso linkleri otomatik olarak YouTube karşılığına yönlendirilir
- `/dl` 1000+ siteye native destek

---

## 🐳 Docker

```bash
docker build -t melih-music-bot .
docker run -d --env-file .env --name melih-bot melih-music-bot
```

---

## ⚠️ Güvenlik

- `sample.env`'deki kimlik bilgileri **public GitHub repo'da sızdırılmıştır**.
- Production'a almadan **kesinlikle**:
  1. @BotFather'dan **yeni bot token** alın
  2. MongoDB Atlas'ta **kullanıcı şifresini değiştirin**
  3. `OWNER_ID`'yi kontrol edin (sadece sizin Telegram ID'niz olmalı)

---

## 📂 Dizin Yapısı

```
melih_bot_v2/
├── YukkiMusic/
│   ├── core/         # Bot + PyTgCalls + Userbot
│   ├── platforms/    # YouTube (ana), Spotify, Apple, Resso, Soundcloud
│   ├── plugins/
│   │   ├── play/     # Play command + queue + admins
│   │   ├── tools/    # /dl, /reels, /tts, /lang (YENİ)
│   │   ├── devs/     # /genstring, /logs, /lasterror, antispam (YENİ)
│   │   └── ...
│   └── utils/
├── strings/
│   ├── command.yml   # TR + EN aliases
│   └── langs/
│       ├── tr.yml    # Türkçe
│       └── en.yml    # English (YENİ)
├── config/
├── requirements.txt
├── Dockerfile
└── .env
```
