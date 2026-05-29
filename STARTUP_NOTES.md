# Startup Notes - Önemli

## Kurulum sonrası pyrogram.emoji uyumluluk

`kurigram` (yeni Pyrogram), `pyrogram.emoji` modülünü artık içermiyor.
`pykeyboard` kütüphanesi bu modüldeki bayrak emojilerini kullandığı için,
kurulum sonrası bu küçük uyumluluk dosyasını oluşturun:

```bash
python3 -c "
import pyrogram, os
p = os.path.join(os.path.dirname(pyrogram.__file__), 'emoji.py')
open(p, 'w').write('''
FLAG_BELARUS        = \"🇧🇾\"
FLAG_CHINA          = \"🇨🇳\"
FLAG_FRANCE         = \"🇫🇷\"
FLAG_GERMANY        = \"🇩🇪\"
FLAG_INDONESIA      = \"🇮🇩\"
FLAG_ITALY          = \"🇮🇹\"
FLAG_RUSSIA         = \"🇷🇺\"
FLAG_SOUTH_KOREA    = \"🇰🇷\"
FLAG_SPAIN          = \"🇪🇸\"
FLAG_TURKEY         = \"🇹🇷\"
FLAG_UKRAINE        = \"🇺🇦\"
FLAG_UNITED_KINGDOM = \"🇬🇧\"
FLAG_UZBEKISTAN     = \"🇺🇿\"
''')
print('Created', p)
"
```

## İlk başlatma (asistansız)
- `.env` içinde `STRING_SESSION` boş bırakılabilir.
- Bot başlatılır → `@Googlemusicsbot` Telegram'da `/start` ile yanıt verir.
- **Sahip (OWNER_ID=7035704703)** botun özel mesajına `/genstring` yazarak interaktif olarak session üretebilir.
- Session üretildikten sonra bot otomatik yeniden başlatır (`os.execv`) ve sesli sohbet özellikleri aktif olur.

## /genstring akışı
1. Bot'a PM'den `/genstring` yaz
2. Telefon numarasını gir: `+90...`
3. Telegram'dan gelen OTP kodunu **boşluklarla** gir (Telegram güvenlik kuralı): `1 2 3 4 5`
4. (2FA varsa) Cloud password'ünü gir
5. ✅ Session kaydedildi, bot 5 saniye sonra yeniden başlar
