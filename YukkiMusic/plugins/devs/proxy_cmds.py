#
# /proxystatus and /proxytest — Webshare proxy management commands
#

import asyncio
import os

from pyrogram import filters
from pyrogram.types import Message

import config
from YukkiMusic import app
from YukkiMusic.utils import proxy_manager


def _is_owner(uid: int) -> bool:
    try:
        return int(uid) == int(getattr(config, "OWNER_ID", 0))
    except Exception:
        return False


@app.on_message(filters.command(["proxystatus", "proxy"]) & filters.private)
async def cmd_proxystatus(client, message: Message):
    if not _is_owner(message.from_user.id):
        return
    st = proxy_manager.stats()
    api_key = os.environ.get("WEBSHARE_API_KEY", "")
    key_disp = (f"{api_key[:6]}…{api_key[-4:]}"
                if len(api_key) > 10 else ("yok" if not api_key else api_key))

    lines = [
        "🌐 **Webshare Proxy Durumu**",
        "",
        f"🔑 API key: `{key_disp}`",
        f"⚡ Aktif: {'✅ Evet' if st['enabled'] else '❌ Hayır'}",
        f"📦 Toplam proxy: `{st['total']}`",
        f"💚 Sağlıklı: `{st['healthy']}`",
        f"❌ Bench'te: `{st['bad']}`",
    ]
    if st["last_refresh_age"] is not None:
        lines.append(f"🔄 Son refresh: `{st['last_refresh_age']}s önce`")
    if st["quota_exceeded"]:
        lines.append("⚠️ **KOTA DOLDU — proxy kapatıldı**")

    if not api_key:
        lines.append("")
        lines.append(
            "💡 Kullanmak için:\n"
            "1) https://dashboard.webshare.io/api/keys → API key alın\n"
            "2) `/setenv WEBSHARE_API_KEY <key>` yazın\n"
            "3) `/restart` ile botu yeniden başlatın"
        )
    await message.reply_text("\n".join(lines))


@app.on_message(filters.command(["proxytest"]) & filters.private)
async def cmd_proxytest(client, message: Message):
    """Try every healthy proxy against httpbin to verify they actually work."""
    if not _is_owner(message.from_user.id):
        return
    if not proxy_manager.is_enabled():
        return await message.reply_text(
            "❌ Proxy aktif değil. `/proxystatus` ile kontrol edin."
        )
    status = await message.reply_text("🔍 Proxy'ler test ediliyor…")

    try:
        import requests
    except ImportError:
        return await status.edit_text("❌ requests modülü kurulu değil.")

    # Force a refresh first
    proxy_manager._pool.refresh_if_due(force=True)
    st = proxy_manager.stats()

    if st["total"] == 0:
        return await status.edit_text("❌ Hiç proxy fetch edilemedi.")

    results = [f"📦 {st['total']} proxy üzerinde test…", ""]
    ok = 0
    bad = 0

    def _test_one(url: str) -> tuple[bool, str]:
        try:
            r = requests.get(
                "https://api.ipify.org?format=json",
                proxies={"http": url, "https": url},
                timeout=8,
            )
            if r.status_code == 200:
                ip = r.json().get("ip", "?")
                return True, ip
            return False, f"HTTP {r.status_code}"
        except Exception as e:
            return False, f"{type(e).__name__}"

    # Sample max 10 proxies to keep test fast
    proxies = proxy_manager._pool._proxies[:10]
    loop = asyncio.get_running_loop()
    for p in proxies:
        host_only = p.url.split("@")[-1]
        ok_flag, info = await loop.run_in_executor(None, _test_one, p.url)
        if ok_flag:
            results.append(f"✅ `{host_only}` → exit IP `{info}`")
            ok += 1
        else:
            results.append(f"❌ `{host_only}` → {info}")
            bad += 1

    results.append("")
    results.append(f"**Sonuç:** ✅ {ok} ok, ❌ {bad} fail")
    text = "\n".join(results)
    if len(text) > 3800:
        text = text[:3800] + "\n…(kesildi)"
    await status.edit_text(text)


@app.on_message(filters.command(["proxyrefresh"]) & filters.private)
async def cmd_proxyrefresh(client, message: Message):
    """Force re-fetch the proxy list from Webshare API."""
    if not _is_owner(message.from_user.id):
        return
    if not os.environ.get("WEBSHARE_API_KEY"):
        return await message.reply_text("❌ WEBSHARE_API_KEY yok.")
    status = await message.reply_text("🔄 Webshare API'den proxy listesi alınıyor…")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: proxy_manager._pool.refresh_if_due(force=True),
    )
    st = proxy_manager.stats()
    await status.edit_text(
        f"✅ Refresh tamam.\n"
        f"📦 Toplam: `{st['total']}`  •  💚 Sağlıklı: `{st['healthy']}`"
    )
