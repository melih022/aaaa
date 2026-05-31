# Melih Music Bot — VPS Deployment Guide

## 🚀 Hızlı kurulum (önerilen yöntem)

```bash
# 1) Repo'yu VPS'e kopyalayın (örn. SCP veya git clone):
git clone https://github.com/melih022/aaaa.git melih_bot
cd melih_bot

# 2) Cookies dosyanız varsa (opsiyonel — VEVO/age-restricted için)
mkdir -p cookies
nano cookies/cookies.txt          # içeriği yapıştırın
# (Boş bırakırsanız da çoğu video çalışır)

# 3) İnteraktif kurulum
sudo bash setup.sh
```

`setup.sh` size sırayla şunları soracak:
1. `API_ID` (https://my.telegram.org → API development tools)
2. `API_HASH`
3. `BOT_TOKEN` (@BotFather → /newbot)
4. `OWNER_ID` (Sizin Telegram user ID'niz — @userinfobot ile öğrenin)
5. `LOG_GROUP_ID` (Bot ve asistanın admin olduğu log grubu, yoksa boş bırakın)
6. (Opsiyonel) `STRING_SESSION` — Asistan account. Bilmiyorsanız boş bırakın, sonra `/genstring` ile yaparsınız.

Script otomatik olarak:
- Python, ffmpeg, MongoDB kurar
- `requirements.txt` + kurigram 2.2.23 + py-tgcalls 2.2.12 + yt-dlp 2026.x kurar
- pyrogram.emoji uyumluluk stub'ı oluşturur
- `.env` yazar
- `systemd` servisi (`musicbot.service`) kurar ve başlatır

---

## 📋 Manuel komutlarla yönetim
```bash
journalctl -u musicbot -f          # canlı log
systemctl restart musicbot         # yeniden başlat
systemctl stop musicbot            # durdur
systemctl status musicbot          # durum
nano .env                          # config düzenle (sonra restart)
```

---

## 🤖 Telegram içinden ayarlar (kurulumdan sonra)

### İlk açılışta yapılacaklar
1. Bot'un PM'sine `/start` yazın → genel bilgi gelir
2. (Eğer setup'ta STRING_SESSION girmediyseniz)
   - PM'de `/genstring` → telefon → OTP (`1 2 3 4 5` şeklinde boşluklu) → ✅
3. Bot ve asistan hesabını **log grubuna** ve **kullanılacak gruplara** ekleyin, hepsini **admin** yapın

### Reklam (pre-roll) sistemi
Her **ilk** `/play` çağrısında çalmak istediğiniz reklamı tanımlayabilirsiniz:

```
/setad <reklam metni>                    → TTS ile sesli reklam (Türkçe Ahmet sesi)
/setad [voice=tr-TR-EmelNeural] <metin>  → Ses seçimi (bayan/erkek)
/setadfile                               → Bir audio/voice mesajına REPLY atıp set
/adstatus                                → mevcut reklam durumu
/adon  /adoff                            → açık/kapalı
/clearad                                 → reklamı sil
```

**Akış:** Bir grupta `/play <şarkı>` yazıldığında, asistan VC'ye girdiğinde önce:
- `🎙 Lütfen medyanın başlaması için reklamın bitmesini bekleyin...` mesajı gönderilir
- Reklam (TTS veya audio dosya) çalınır
- Reklam bittiğinde otomatik olarak istenen şarkı çalmaya başlar

### Müzik komutları
```
/play <şarkı veya YouTube link>
/vplay <link>                            (video stream)
/skip /pause /resume /stop /end
/song <şarkı>                            (Telegram'a MP3 indir)
/lyrics <şarkı>
/lang [tr/en]                            (dil değiştir)
```

### Sahibe özel (PM)
```
/genstring                               (interaktif session üretici)
/setstring <STRING> [1-5]                (manuel session ekle)
/sessions                                (slot durumu)
/clearsession <1-5>
/restart                                 (botu yeniden başlat)
/logs [N]                                (son N satır supervisor log dosyası)
/lasterror                               (son 5 handler exception traceback)
/testytdlp <sorgu>                       (yt-dlp aramasını anında test)
/pyver                                   (Python + paket sürümleri)
/env                                     (.env içeriği — şifreler maskeli)
```

---

## 🍪 Cookies (YouTube)
- Konum: `cookies/cookies.txt`  (Netscape format)
- `.env` içinde `USE_COOKIES=True` / `False` ile kontrol edilir
- **Önemli**: Cookies, sizin IP'nizden export edildiyse VPS'inizin de YAKIN bir bölgeden olması gerekir (Türkiye cookies + ABD VPS = YouTube "şüpheli oturum" diyebilir). Sorun çıkarsa `.env`'de `USE_COOKIES=False` yapın

## 🔧 Pre-flight checklist
- ✅ Bot **admin** kullanıldığı her grupta
- ✅ Asistan üye + (mümkünse) admin
- ✅ Voice chat **açık** komutu vermeden önce
- ✅ `journalctl -u musicbot -f` ile log izlenebilir

## ⚠️ Troubleshooting

| Hata | Çözüm |
|---|---|
| `FloodWait 420 auth.ImportBotAuthorization` | Aynı bot ID'ye çok auth → 20-40 dk bekleyin VEYA yeni bot oluşturun (@BotFather /newbot). Bot disk-session kullandığı için bir kez başlayınca aynı sorun tekrarlamaz. |
| `Sign in to confirm you're not a bot` | `cookies/cookies.txt` ekleyin **VEYA** `USE_COOKIES=False` deneyin |
| Asistan VC'ye girmedi | Botu **admin** yapın (asistanı davet edebilsin) veya asistanı manuel ekleyin. `/lasterror` ile gerçek nedeni görün |
| `AttributeError: MEDIUM` | py-tgcalls 2.2.12+ ama `memorydatabase.py` eski. Bu fork'ta zaten düzeltildi |
| `HTTP 403: Forbidden` (yt-dlp download) | Audio artık **dosyaya indirilmiyor**, direkt stream URL kullanılıyor. Bu hatayı görmüyor olmalısınız |
| `Peer id invalid: -100...` | Log grubuna bot ve asistanı henüz eklemediniz — eklerseniz uyarı durur |
| `Reklam çalmıyor` | `/adstatus` → enabled olduğundan emin olun. Edge-TTS fail olursa otomatik gTTS'e geçer |

## 🧰 Manuel kurulum (setup.sh'i atlamak isteyenler için)
DEPLOY-MANUAL.md → eski adımlar
