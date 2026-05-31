# Melih Music Bot

> Telegram **müzik / sesli sohbet (voice chat)** botu. YouTube'dan şarkı çalar,
> her grup için reklam (TTS veya ses dosyası) destekler, çoklu asistan slotu,
> grup admin yönetimi, log grubu, vs.
>
> Tek komutla VPS'inize kurulur.

---

## 🚀 Hızlı kurulum (Ubuntu/Debian VPS)

```bash
git clone https://github.com/melih022/aaaa.git melih_bot
cd melih_bot
sudo bash setup.sh
```

Script size sırayla şunları soracak:
1. **API_ID** — https://my.telegram.org → API development tools'tan alın
2. **API_HASH** — aynı yerden
3. **BOT_TOKEN** — @BotFather'a `/newbot` yazıp alın
4. **OWNER_ID** — Telegram user ID'niz (@userinfobot'tan)
5. **LOG_GROUP_ID** — Botu ve asistanı admin yaptığınız log grubu (yoksa 0)
6. *(Opsiyonel)* **STRING_SESSION** — asistan hesabı için. Boş bırakırsanız sonra `/genstring` ile yaparsınız.

Script otomatik yapacaklar:
- ffmpeg, Python 3, MongoDB kurulumu
- Python venv + tüm bağımlılıklar (kurigram, py-tgcalls, yt-dlp 2026+)
- pyrogram.emoji uyumluluk stub'ı
- `.env` dosyası oluşturma
- `systemd` servisi (`musicbot.service`)
- Bot'u arkaplanda başlatma

Kurulum sonrası bot **otomatik çalışır** ve sunucu yeniden başlasa da kalkar.

---

## 🎛 Yönetim komutları (VPS shell)

```bash
journalctl -u musicbot -f       # canlı log
systemctl restart musicbot      # yeniden başlat
systemctl stop musicbot         # durdur
systemctl start musicbot        # başlat
systemctl status musicbot       # durum
nano .env                       # config düzenle (sonra restart)
```

---

## 🤖 Telegram içi komutlar

### Müzik
| Komut | Açıklama |
|---|---|
| `/play <şarkı veya YouTube link>` | Sesli sohbette müzik çalar |
| `/vplay <link>` | Video stream |
| `/skip` `/pause` `/resume` `/end` | Kontrol |
| `/song <şarkı>` | MP3 indirip Telegram'a gönderir |
| `/lyrics <şarkı>` | Şarkı sözlerini gösterir |

### Reklam sistemi (sahibi)
| Komut | Açıklama |
|---|---|
| `/setad <metin>` | TTS reklam (Türkçe Ahmet sesi varsayılan) |
| `/setad [voice=tr-TR-EmelNeural] <metin>` | Bayan sesi |
| `/setadfile` (audio'ya reply) | Ses dosyası reklam |
| `/adon` `/adoff` | Aç/kapa |
| `/adstatus` | Mevcut reklam |
| `/clearad` | Reklamı sil |

**Akış**: Her `/play` çağrısında (ilk şarkı) asistan VC'ye girer →
"🎙 Lütfen medyanın başlaması için reklamın bitmesini bekleyin..." mesajı →
reklam çalar → şarkı çalar.

### Sahibe özel (PM)
| Komut | Açıklama |
|---|---|
| `/genstring` | Asistan session interaktif üretici |
| `/setstring <STRING> [1-5]` | Manuel session ekle |
| `/sessions` | Slot durumu |
| `/restart` | Botu yeniden başlat |
| `/logs [N]` | Son N satır log dosyası |
| `/lasterror` | Son hata tracebackleri |
| `/pyver` | Sürümler |

---

## 🍪 Cookies (opsiyonel, YouTube)
- Konum: `cookies/cookies.txt` (Netscape format)
- `.env`'de `USE_COOKIES=True` (varsayılan)
- VEVO/yaş-kısıtlı videolar için gerekli olabilir

---

## ⚠️ Hızlı Troubleshooting

| Sorun | Çözüm |
|---|---|
| `FloodWait 420 auth.ImportBotAuthorization` | Çok restart → 20-40 dk bekle veya yeni bot oluştur |
| Asistan VC'ye girdi ama ses gelmiyor | Container/host NAT kararsız olabilir. Stable IP'li VPS gerekli. K8s pod'larında 403 yaşanabilir |
| `Sign in to confirm you're not a bot` | `cookies/cookies.txt` ekle veya `USE_COOKIES=False` dene |
| `Reklam çalmıyor` | `/adstatus` ile kontrol; `/setad <metin>` ile yeniden ayarla |

Detay: [`DEPLOY.md`](DEPLOY.md)

---

## 📋 Teknik altyapı

- Python 3.11+ (3.12 da destekli)
- [kurigram](https://pypi.org/project/Kurigram/) 2.2.23+ (Pyrogram fork)
- [py-tgcalls](https://pypi.org/project/py-tgcalls/) 2.2.12+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) 2026.3.17+ (mediaconnect/android_music/tv_embedded clients)
- [edge-tts](https://pypi.org/project/edge-tts/) (reklam TTS)
- MongoDB 7 (local, yerel storage)
- ffmpeg (system)
- systemd (process supervisor)

---

## 📄 Lisans
GPL-3.0 — bkz. [LICENSE](LICENSE)
