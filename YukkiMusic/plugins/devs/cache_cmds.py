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
