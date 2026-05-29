#!/usr/bin/env python3
import sys
import traceback

print("=" * 60)
print("YUKKI BOT - DEBUG BAŞLAYICI")
print("=" * 60)

try:
    print("\n[1] Python versiyonu kontrol ediliyor...")
    print(f"    Python: {sys.version}")
    
    print("\n[2] .env dosyası okunuyor...")
    from dotenv import load_dotenv
    load_dotenv()
    import os
    
    API_ID = os.getenv("API_ID")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    MONGO_DB_URI = os.getenv("MONGO_DB_URI")
    LOG_GROUP_ID = os.getenv("LOG_GROUP_ID")
    STRING_SESSION = os.getenv("STRING_SESSION")
    
    print(f"    ✓ API_ID: {API_ID}")
    print(f"    ✓ BOT_TOKEN: {BOT_TOKEN[:20]}..." if BOT_TOKEN else "    ✗ BOT_TOKEN: YOK")
    print(f"    ✓ MONGO_DB_URI: {MONGO_DB_URI[:30]}..." if MONGO_DB_URI else "    ✗ MONGO_DB_URI: YOK")
    print(f"    ✓ LOG_GROUP_ID: {LOG_GROUP_ID}")
    print(f"    ✓ STRING_SESSION: {'VAR' if STRING_SESSION else 'YOK'}")
    
    print("\n[3] Config modülü yükleniyor...")
    import config
    print("    ✓ Config yüklendi")
    
    print("\n[4] YukkiMusic paketi yükleniyor...")
    from YukkiMusic import app, LOGGER
    print("    ✓ YukkiMusic app başlatıldı")
    
    print("\n[5] Bot başlatılıyor...")
    import asyncio
    
    async def test_start():
        try:
            await app.start()
            me = await app.get_me()
            print(f"    ✓ Bot başarıyla başladı!")
            print(f"    ✓ Bot adı: {me.first_name}")
            print(f"    ✓ Bot username: @{me.username}")
            print(f"    ✓ Bot ID: {me.id}")
            
            print("\n[6] LOG_GROUP_ID'ye test mesajı gönderiliyor...")
            try:
                await app.send_message(config.LOG_GROUP_ID, "✅ Bot test başarılı!")
                print(f"    ✓ Mesaj gönderildi")
            except Exception as e:
                print(f"    ✗ Log grubu hatası: {e}")
            
            await app.stop()
            print("\n" + "=" * 60)
            print("✅ BOT BAŞLATMA TESTİ BAŞARILI")
            print("=" * 60)
            
        except Exception as e:
            print(f"    ✗ Bot başlatma hatası: {e}")
            traceback.print_exc()
            sys.exit(1)
    
    asyncio.run(test_start())
    
except Exception as e:
    print(f"\n✗ HATA: {e}")
    traceback.print_exc()
    sys.exit(1)
