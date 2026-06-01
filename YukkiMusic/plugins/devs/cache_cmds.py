#
# /cachestatus and /cacheclear — yt cache management
#

from pyrogram import filters
from pyrogram.types import Message

import config
from YukkiMusic import app
from YukkiMusic.utils import yt_cache


def _is_owner(uid: int) -> bool:
    try:
        return int(uid) == int(getattr(config, "OWNER_ID", 0))
    except Exception:
        return False


@app.on_message(filters.command(["ytapistatus", "ytapi"]) & filters.private)
async def cmd_ytapistatus(client, message: Message):
    if not _is_owner(message.from_user.id):
        return
    import os as _os
    from YukkiMusic.utils import youtube_api
    s = youtube_api.stats()
    api_key = _os.environ.get("YOUTUBE_API_KEY", "")
    key_disp = (f"{api_key[:6]}…{api_key[-4:]}"
                if len(api_key) > 10 else ("yok" if not api_key else api_key))

    lines = [
        "🎬 **YouTube Data API v3 Durumu**",
        "",
        f"🔑 API key: `{key_disp}`",
        f"⚡ Aktif: {'✅ Evet' if s['enabled'] else '❌ Hayır'}",
    ]
    if s["quota_exceeded"]:
        lines.append("⚠️ **Günlük kota doldu** (gece yarısı PT resetlenir)")
    if not s["has_key"]:
        lines.append("")
        lines.append(
            "💡 Aktif etmek için:\n"
            "1) https://console.cloud.google.com → proje oluştur\n"
            "2) APIs & Services → Library → 'YouTube Data API v3' enable\n"
            "3) APIs & Services → Credentials → Create API key\n"
            "4) `/setenv YOUTUBE_API_KEY <key>` → `/restart`"
        )
    await message.reply_text("\n".join(lines))


@app.on_message(filters.command(["cachestatus", "cstat"]) & filters.private)
async def cmd_cachestatus(client, message: Message):
    if not _is_owner(message.from_user.id):
        return
    s = yt_cache.all_stats()
    sc = s["search_cache"]
    st = s["stream_cache"]
    mc = s["meta_cache"]
    hist = s["strategy_history"]

    lines = [
        "📊 **Bot Cache Durumu**",
        "",
        f"🔍 Search cache: `{sc['fresh']}/{sc['total']}` fresh "
        f"(max {sc['max']}, TTL {sc['ttl'] // 60}m)",
        f"🎵 Stream cache: `{st['fresh']}/{st['total']}` fresh "
        f"(max {st['max']}, TTL {st['ttl'] // 3600}h)",
        f"ℹ️ Meta cache:   `{mc['fresh']}/{mc['total']}` fresh",
        "",
        f"🎯 Last good strategy: `{s['last_good_strategy'] or 'none'}`",
    ]
    if hist:
        lines.append("")
        lines.append("📈 Strategy success counts:")
        sorted_hist = sorted(hist.items(), key=lambda kv: -kv[1])[:8]
        for name, cnt in sorted_hist:
            lines.append(f"  • `{cnt}` ✕ {name}")
    await message.reply_text("\n".join(lines))


@app.on_message(filters.command(["cacheclear", "cclear"]) & filters.private)
async def cmd_cacheclear(client, message: Message):
    if not _is_owner(message.from_user.id):
        return
    yt_cache.clear_all()
    await message.reply_text("✅ Tüm cache'ler temizlendi.")
