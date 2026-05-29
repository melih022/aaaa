#
# Owner-only download-folder cleanup with configurable retention.
#
# /setcleanup <minutes>  – schedule auto-cleanup of downloads/ every N minutes
# /setcleanup 0          – disable auto cleanup
# /cleanup               – clean immediately (now)
# /cleanupstatus         – show current settings + disk usage
#

import asyncio
import os
import shutil
import time
from pathlib import Path

from pyrogram import filters
from pyrogram.types import Message

import config
from YukkiMusic import LOGGER, app

DOWNLOAD_DIRS = [
    Path("downloads"),
    Path("downloads/insta"),
    Path("downloads/universal"),
    Path("downloads/tts"),
    Path("cache"),
]

# Settings persisted in-memory + .env  
SETTINGS = {
    "interval_min": int(os.getenv("AUTO_CLEAN_MIN", "0") or 0),
    "age_min": int(os.getenv("CLEAN_AGE_MIN", "30") or 30),
    "task": None,
}


def _is_owner(uid):
    try:
        return int(uid) in config.OWNER_ID
    except Exception:
        return False


def _disk_usage():
    total = 0
    files = 0
    for d in DOWNLOAD_DIRS:
        if not d.exists():
            continue
        for root, _, fs in os.walk(d):
            for f in fs:
                fp = Path(root) / f
                try:
                    total += fp.stat().st_size
                    files += 1
                except Exception:
                    pass
    return files, total


def _format_bytes(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            return f"{n:.1f} {u}"
        n /= 1024.0
    return f"{n:.1f} PB"


def _clean_once(age_min: int = 0) -> tuple[int, int]:
    """Delete files older than age_min minutes (0 = delete all)."""
    cutoff = time.time() - (age_min * 60)
    removed_files = 0
    removed_bytes = 0
    for d in DOWNLOAD_DIRS:
        if not d.exists():
            continue
        for root, _, fs in os.walk(d):
            for f in fs:
                fp = Path(root) / f
                try:
                    st = fp.stat()
                    if age_min == 0 or st.st_mtime < cutoff:
                        size = st.st_size
                        fp.unlink()
                        removed_files += 1
                        removed_bytes += size
                except Exception:
                    pass
    return removed_files, removed_bytes


async def _auto_cleanup_loop():
    """Background task: every interval_min minutes, remove files older than age_min."""
    while True:
        interval = SETTINGS.get("interval_min", 0)
        if interval <= 0:
            return  # disabled, exit loop
        await asyncio.sleep(interval * 60)
        try:
            n, b = _clean_once(SETTINGS.get("age_min", 30))
            if n:
                LOGGER("YukkiMusic.cleanup").info(
                    f"Auto-cleanup removed {n} files / {_format_bytes(b)}"
                )
        except Exception as e:
            LOGGER("YukkiMusic.cleanup").error(f"Auto-cleanup error: {e}")


@app.on_message(filters.command(["setcleanup", "setclean"]) & filters.private)
async def setcleanup_cmd(client, message: Message):
    if not _is_owner(message.from_user.id):
        return await message.reply_text("⛔ Sadece bot sahibi kullanabilir.")
    parts = message.text.split()
    if len(parts) < 2:
        return await message.reply_text(
            "🧹 **Otomatik Cleanup Ayarları**\n\n"
            "Kullanım:\n"
            "  • `/setcleanup <interval_dakika> [yas_dakika]`\n"
            "  • `/setcleanup 0` → otomatik cleanup'ı kapat\n\n"
            "**Örnekler:**\n"
            "  • `/setcleanup 30` → Her 30 dk'da bir, 30 dk'dan eski dosyaları sil\n"
            "  • `/setcleanup 60 120` → Her 1 saatte, 2 saatten eski dosyaları sil\n"
            "  • `/setcleanup 5 0` → Her 5 dk'da bir, **TÜM** dosyaları sil (agresif)\n\n"
            f"📊 Şu an: `interval={SETTINGS['interval_min']}dk, yas={SETTINGS['age_min']}dk`\n"
            f"💡 Anlık silme için: `/cleanup`\n"
            f"💡 Durum için: `/cleanupstatus`"
        )
    try:
        interval = int(parts[1])
    except ValueError:
        return await message.reply_text("❌ Interval rakam olmalı (dakika).")
    age = SETTINGS["age_min"]
    if len(parts) >= 3:
        try:
            age = int(parts[2])
        except ValueError:
            return await message.reply_text("❌ Yaş rakam olmalı (dakika).")

    # Save settings
    SETTINGS["interval_min"] = max(0, interval)
    SETTINGS["age_min"] = max(0, age)

    # Persist to .env
    try:
        from YukkiMusic.utils.env_writer import update_env
        update_env("AUTO_CLEAN_MIN", str(SETTINGS["interval_min"]))
        update_env("CLEAN_AGE_MIN", str(SETTINGS["age_min"]))
    except Exception:
        pass

    # Restart background task
    old = SETTINGS.get("task")
    if old and not old.done():
        old.cancel()
    if interval > 0:
        SETTINGS["task"] = asyncio.create_task(_auto_cleanup_loop())
        await message.reply_text(
            f"✅ **Otomatik cleanup ayarlandı**\n\n"
            f"  • Her: `{interval} dakika`\n"
            f"  • Sil: `{age} dakikadan eski` dosyaları (0=tümü)\n"
            f"  • Klasörler: {', '.join(str(d) for d in DOWNLOAD_DIRS)}"
        )
    else:
        await message.reply_text("✅ Otomatik cleanup **devre dışı** bırakıldı.")


@app.on_message(filters.command(["cleanup", "tempclean", "clean"]) & filters.private)
async def cleanup_now_cmd(client, message: Message):
    if not _is_owner(message.from_user.id):
        return await message.reply_text("⛔ Sadece bot sahibi.")
    parts = message.text.split()
    age = 0  # default: delete all
    if len(parts) >= 2:
        try:
            age = int(parts[1])
        except ValueError:
            pass
    status = await message.reply_text(
        f"🧹 Cleanup başlatılıyor… (yaş ≥ `{age} dk`)"
    )
    n, b = _clean_once(age)
    files_left, bytes_left = _disk_usage()
    await status.edit_text(
        f"✅ **Cleanup tamamlandı**\n\n"
        f"  🗑️ Silinen: `{n} dosya` / `{_format_bytes(b)}`\n"
        f"  📦 Kalan: `{files_left} dosya` / `{_format_bytes(bytes_left)}`"
    )


@app.on_message(
    filters.command(["cleanupstatus", "cleanstatus", "diskusage"]) & filters.private
)
async def cleanup_status_cmd(client, message: Message):
    if not _is_owner(message.from_user.id):
        return
    files, total = _disk_usage()
    interval = SETTINGS.get("interval_min", 0)
    age = SETTINGS.get("age_min", 30)
    next_run = "—"
    task = SETTINGS.get("task")
    if task and not task.done() and interval > 0:
        next_run = f"≤{interval} dakika içinde"
    await message.reply_text(
        f"📊 **Cleanup Durumu**\n\n"
        f"  ⏱️ Interval: `{interval} dk` ({'aktif' if interval > 0 else 'kapalı'})\n"
        f"  📅 Yaş filtresi: `>{age} dk`\n"
        f"  ⏭️ Sonraki çalışma: `{next_run}`\n\n"
        f"📦 **Mevcut kullanım:**\n"
        f"  • {files} dosya / {_format_bytes(total)}\n"
        f"  • Klasörler: {', '.join(str(d) for d in DOWNLOAD_DIRS if d.exists())}\n\n"
        f"Komutlar:\n"
        f"  • `/setcleanup <dk> [yas]` → otomatik\n"
        f"  • `/cleanup [yas]` → anlık (yaş=0 tümü)\n"
    )


# Auto-start the task at module load if AUTO_CLEAN_MIN > 0
async def _start_task():
    if SETTINGS.get("interval_min", 0) > 0 and (
        not SETTINGS.get("task") or SETTINGS["task"].done()
    ):
        SETTINGS["task"] = asyncio.create_task(_auto_cleanup_loop())


try:
    asyncio.get_event_loop().create_task(_start_task())
except Exception:
    pass
