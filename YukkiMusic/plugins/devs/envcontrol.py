#
# Owner-only .env / update controller.
#
# Commands:
#   /getenv               — list .env keys with masked values
#   /env                  — alias of /getenv
#   /setenv KEY VALUE     — change a value (writes .env on disk)
#   /unsetenv KEY         — remove a key from .env
#   /update               — git pull origin master (uses GITHUB_TOKEN if set)
#

import os
import re
import asyncio
import subprocess

from pyrogram import filters
from pyrogram.types import Message

from YukkiMusic import app
from YukkiMusic.misc import SUDOERS


# Sensitive keys whose values are masked in /getenv
_SECRET_KEYS = {
    "API_HASH", "BOT_TOKEN", "STRING_SESSION", "STRING1", "STRING2",
    "STRING3", "STRING4", "STRING5", "MONGO_DB_URI", "GITHUB_TOKEN",
    "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET",
}

ENV_FILE = os.path.join(os.getcwd(), ".env")


def _is_sudo(_, __, m: Message):
    return bool(m.from_user) and m.from_user.id in SUDOERS


sudo_filter = filters.create(_is_sudo)


def _mask(val: str) -> str:
    if not val:
        return ""
    if len(val) <= 10:
        return "***"
    return f"{val[:6]}…{val[-4:]}"


def _read_env() -> dict:
    if not os.path.isfile(ENV_FILE):
        return {}
    out = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v
    return out


def _write_env(d: dict) -> None:
    """Preserve order of existing keys, append new keys at end."""
    existing_order = []
    if os.path.isfile(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.rstrip("\n")
                if "=" in line and not line.startswith("#"):
                    k = line.split("=", 1)[0].strip()
                    if k not in existing_order:
                        existing_order.append(k)
    lines = []
    seen = set()
    for k in existing_order:
        if k in d:
            lines.append(f"{k}={d[k]}")
            seen.add(k)
    for k, v in d.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(ENV_FILE, 0o600)


@app.on_message(filters.command(["getenv", "env"]) & sudo_filter & filters.private)
async def cmd_getenv(client, message: Message):
    d = _read_env()
    if not d:
        return await message.reply_text("❌ `.env` bulunamadı veya boş.")
    body = ["📄 **Mevcut .env**\n"]
    for k, v in d.items():
        shown = _mask(v) if k in _SECRET_KEYS else v
        body.append(f"• `{k}` = `{shown}`")
    body.append(
        "\n_Düzenlemek için:_ `/setenv KEY YENİ_DEĞER`"
        "\n_Silmek için:_ `/unsetenv KEY`"
        "\n_Sonra:_ `/restart`"
    )
    text = "\n".join(body)
    if len(text) > 4000:
        text = text[:3900] + "\n…(kesildi)"
    await message.reply_text(text)


@app.on_message(filters.command(["setenv"]) & sudo_filter & filters.private)
async def cmd_setenv(client, message: Message):
    parts = message.text.split(None, 2)
    if len(parts) < 3:
        return await message.reply_text(
            "**Kullanım:** `/setenv KEY DEĞER`\n\n"
            "Örnek: `/setenv LOG_GROUP_ID -1001234567890`\n"
            "Örnek: `/setenv BOT_TOKEN 1234:abc...`\n\n"
            "Sonra `/restart` ile bot yeniden başlatılır."
        )
    key = parts[1].strip().upper()
    val = parts[2]
    # Don't accept obviously wrong keys
    if not re.fullmatch(r"[A-Z0-9_]+", key):
        return await message.reply_text(
            "❌ Geçersiz anahtar. Sadece A-Z, 0-9, _ karakterleri kabul edilir."
        )
    d = _read_env()
    old = d.get(key, "")
    d[key] = val
    try:
        _write_env(d)
    except Exception as e:
        return await message.reply_text(f"❌ Yazma hatası: `{type(e).__name__}: {e}`")
    old_shown = _mask(old) if key in _SECRET_KEYS else (old or "_(yoktu)_")
    new_shown = _mask(val) if key in _SECRET_KEYS else val
    await message.reply_text(
        f"✅ `.env` güncellendi.\n"
        f"• `{key}` :  ~~{old_shown}~~  →  `{new_shown}`\n\n"
        f"Değişikliğin geçerli olması için: `/restart`"
    )


@app.on_message(filters.command(["unsetenv"]) & sudo_filter & filters.private)
async def cmd_unsetenv(client, message: Message):
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        return await message.reply_text("**Kullanım:** `/unsetenv KEY`")
    key = parts[1].strip().upper()
    d = _read_env()
    if key not in d:
        return await message.reply_text(f"`{key}` `.env`'de yok.")
    del d[key]
    _write_env(d)
    await message.reply_text(
        f"🗑 `{key}` `.env`'den silindi. `/restart` ile etkinleştirin."
    )


@app.on_message(filters.command(["update"]) & sudo_filter & filters.private)
async def cmd_update(client, message: Message):
    """Git pull + smart restart. Uses GITHUB_TOKEN from .env if present
    (for private repos or rate-limit avoidance)."""
    status = await message.reply_text("⬇️ Güncelleme aranıyor (git pull)…")
    env_vars = _read_env()
    token = env_vars.get("GITHUB_TOKEN", "").strip()

    # Construct remote URL with token if present
    proc = await asyncio.create_subprocess_exec(
        "git", "remote", "get-url", "origin",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    remote = out.decode().strip()

    pull_url = remote
    if token and remote.startswith("https://") and "@" not in remote.split("//", 1)[1]:
        # inject token
        pull_url = remote.replace("https://", f"https://x-access-token:{token}@", 1)

    # git pull with optional credential
    proc = await asyncio.create_subprocess_exec(
        "git", "pull", pull_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    output = (out.decode() + err.decode()).strip()
    if "Already up to date" in output or "Already up-to-date" in output:
        return await status.edit_text("✅ Zaten en güncel sürüm.")
    if proc.returncode != 0:
        return await status.edit_text(
            f"❌ Güncelleme hatası:\n```\n{output[-1500:]}\n```"
        )
    await status.edit_text(
        f"✅ **Güncellendi.**\n```\n{output[-1500:]}\n```\n\nBot yeniden başlatılıyor…"
    )
    await asyncio.sleep(2)
    # Trigger /restart
    from YukkiMusic.plugins.devs.sessionmgr import _restart_self
    await _restart_self()
