# YukkiMusic — Telegram Music Bot

## Original Problem
Turkish user reported that `/play <metin>` (örn. `/play yaşanırsa`) `Unsupported URL`
hatası ile çöküyordu ve müziğin başlaması 15+ saniye sürüyordu.

## Root Cause
1. **`utils/proxy_manager.py`** — Webshare proxy aramaları başlangıçta ve her
   `_ytdl_extract` çağrısında 15+ saniyelik hang'lere neden oluyordu; başarısız
   3 proxy denemesi yt-dlp'nin `Unsupported URL` hata zincirini tetikliyordu.
2. **`platforms/Youtube.py`** — `_YDL_BYPASS` ve `_build_opts` içinde
   `socket_timeout` yoktu; bağlantı bekleyişleri sınırsızdı.

## Fix Applied (Şubat 2026)
- `proxy_manager.enabled` artık her zaman `False` döner (zorla devre dışı).
- `proxy_manager.init()` artık ağa hiç dokunmuyor.
- `Youtube.py` — hem `_YDL_BYPASS` hem `_build_opts` opt dict'lerine
  `socket_timeout=8`, `retries=1`, `fragment_retries=1`, `extractor_retries=1`
  eklendi.

## Verified
- `python /app/aaaa/test_fix.py` çıktısı:
  - proxy disabled ✓
  - text query `yaşanırsa` → `ytsearch1:yaşanırsa` ✓
  - sonuç 1.08 saniyede dönüyor (önceki 15s+ yerine) ✓
  - "Unsupported URL" hatası gitti ✓

## Backlog
- **P2**: Telegram userbot `AUTH_KEY_UNREGISTERED` — kullanıcı `.env` içinde
  `STRING_SESSION` değerini Pyrogram session generator ile yenilemeli
  (kod hatası değil; oturum süresi dolmuş).
