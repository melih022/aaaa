#
# Owner-only .env / update / lifecycle controller.
#
# Commands:
#   /getenv               — list .env keys with masked values
#   /env                  — alias of /getenv
#   /setenv KEY VALUE     — change a value (writes .env on disk)
#   /unsetenv KEY         — remove a key from .env
#   /update               — git fetch + reset --hard origin/<branch> + pip install
#   /stop                 — stop the bot via systemd (no auto-restart)
#   /shutdown             — alias of /stop
#

import os
import re
import sys
import shlex
import asyncio
import subprocess

from pyrogram import filters
from pyrogram.types import Message

from YukkiMusic import app, LOGGER
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
    """Robust git update:
       1. Detect current branch (master/main/...)
       2. git fetch origin <branch> (with GITHUB_TOKEN if set, for private repos)
       3. git reset --hard origin/<branch>  (force-sync, no merge conflicts)
       4. pip install -r requirements.txt (if changed)
       5. restart via os.execv (systemd keeps PID alive)
    """
    status = await message.reply_text("⬇️ Güncelleme başlıyor…")
    cwd = os.getcwd()
    env_vars = _read_env()
    token = env_vars.get("GITHUB_TOKEN", "").strip()

    async def run(*cmd, **kw):
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            **kw,
        )
        out, err = await proc.communicate()
        return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")

    # 0a) Fix "dubious ownership" error when bot runs as root but repo
    # is owned by a regular user (common on VPS deployments).
    await run("git", "config", "--global", "--add", "safe.directory", cwd)

    # 0b) Are we inside a git repo?
    rc, out, err = await run("git", "rev-parse", "--is-inside-work-tree")
    if rc != 0 or "true" not in out:
        return await status.edit_text(
            "❌ Bu klasör bir git deposu değil. Otomatik güncelleme "
            "yapılamıyor.\n\n"
            f"`{cwd}`\n\n"
            "VPS'te terminalden: `cd <kurulum>` → `git pull` → "
            "`systemctl restart musicbot`"
        )

    # 1) Detect branch
    rc, out, err = await run("git", "rev-parse", "--abbrev-ref", "HEAD")
    branch = (out.strip() if rc == 0 else "") or "master"

    # 2) Remote URL (inject token if private/rate-limit)
    rc, out, err = await run("git", "remote", "get-url", "origin")
    remote = out.strip()
    if not remote:
        return await status.edit_text("❌ `origin` remote tanımlı değil.")

    fetch_url = remote
    if token and remote.startswith("https://") and "@" not in remote.split("//", 1)[1]:
        fetch_url = remote.replace(
            "https://", f"https://x-access-token:{token}@", 1
        )

    await status.edit_text(f"⬇️ `git fetch origin {branch}` …")
    rc, out, err = await run("git", "fetch", fetch_url, branch)
    if rc != 0:
        # Sanitize token from error message before showing to user
        sanitized = (out + err).replace(token, "***") if token else (out + err)
        return await status.edit_text(
            f"❌ git fetch hatası:\n```\n{sanitized[-1500:]}\n```"
        )

    # 3) Check if anything new
    rc, out, err = await run(
        "git", "rev-list", "--count", "HEAD..FETCH_HEAD"
    )
    new_commits = (out.strip() if rc == 0 else "0") or "0"
    if new_commits == "0":
        return await status.edit_text("✅ Zaten en güncel sürüm.")

    await status.edit_text(
        f"⬇️ {new_commits} yeni commit bulundu. Senkronize ediliyor…"
    )

    # 4) Hard reset
    rc, out, err = await run("git", "reset", "--hard", "FETCH_HEAD")
    if rc != 0:
        return await status.edit_text(
            f"❌ git reset hatası:\n```\n{(out + err)[-1500:]}\n```"
        )

    # 5) pip install (only if requirements.txt changed in last pull)
    rc, out, _ = await run(
        "git", "diff", "HEAD@{1}", "HEAD", "--name-only"
    )
    changed_files = out.split() if rc == 0 else []
    pip_msg = ""
    if "requirements.txt" in changed_files:
        await status.edit_text("📦 requirements.txt değişti, pip install yapılıyor…")
        pip = os.path.join(cwd, "venv", "bin", "pip")
        if not os.path.isfile(pip):
            pip = sys.executable.replace("python", "pip")
        rc, out, err = await run(pip, "install", "-r", "requirements.txt", "--quiet")
        if rc != 0:
            pip_msg = f"\n⚠️ pip install başarısız (ama kod güncellendi):\n```\n{(out+err)[-800:]}\n```"
        else:
            pip_msg = "\n📦 Bağımlılıklar güncellendi."

    # 6) Show summary
    rc, summary, _ = await run("git", "log", "-3", "--oneline", "--no-decorate")
    await status.edit_text(
        f"✅ **Güncellendi** ({new_commits} commit, branch=`{branch}`)\n"
        f"```\n{summary.strip()[:1500]}\n```{pip_msg}\n\n"
        f"♻️ Bot yeniden başlatılıyor…"
    )
    await asyncio.sleep(2)
    from YukkiMusic.plugins.devs.sessionmgr import _restart_self
    await _restart_self()


# ---------- /stop : full shutdown (no auto-restart) ----------

@app.on_message(filters.command(["stop", "shutdown"]) & sudo_filter & filters.private)
async def cmd_stop(client, message: Message):
    """Stop the bot completely. Tries `systemctl stop musicbot` first
    (so systemd doesn't auto-restart). Falls back to a plain exit, which
    will trigger systemd's Restart=always — in that case, the user is told
    to use `systemctl stop musicbot` from the terminal.
    """
    await message.reply_text(
        "🛑 **Bot durduruluyor…**\n\n"
        "Auto-restart devre dışı bırakılıyor. Bu mesajdan sonra bot offline kalır.\n"
        "Tekrar başlatmak için VPS terminalinde: `systemctl start musicbot`"
    )
    await asyncio.sleep(1)
    LOGGER("YukkiMusic").warning("⛔ /stop received from owner — shutting down.")

    # Detached systemctl stop so it survives our own death
    try:
        subprocess.Popen(
            ["systemctl", "stop", "musicbot"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        LOGGER("YukkiMusic").error(f"systemctl stop failed: {e}")

    # Give systemd a moment, then exit ourselves anyway
    await asyncio.sleep(2)
    try:
        await app.stop()
    except Exception:
        pass
    os._exit(0)


# ---------- /setcookies : upload cookies.txt via Telegram ----------

@app.on_message(filters.command(["setcookies", "setcookie"]) & sudo_filter & filters.private)
async def cmd_setcookies(client, message: Message):
    """Reply to a cookies.txt document (or any text file) with /setcookies
    and the bot will install it at cookies/cookies.txt."""
    reply = message.reply_to_message
    if not reply or not reply.document:
        return await message.reply_text(
            "📎 **Kullanım:**\n\n"
            "1️⃣ `cookies.txt` dosyasını bot'a PM'den **yükle** (drag-drop).\n"
            "2️⃣ O dosyaya **reply** atıp `/setcookies` yaz.\n\n"
            "Dosya `cookies/cookies.txt` olarak kaydedilir, "
            "yt-dlp otomatik kullanır. Bot tekrar başlatma gerek yok."
        )
    doc = reply.document
    if doc.file_size and doc.file_size > 5 * 1024 * 1024:
        return await message.reply_text("❌ Dosya 5 MB'dan büyük, cookies.txt olamaz.")
    fname = (doc.file_name or "").lower()
    if not (fname.endswith(".txt") or fname == "cookies" or "cookie" in fname):
        # Allow anyway but warn
        await message.reply_text(
            f"⚠️ Dosya adı `cookies.txt` değil (`{doc.file_name}`). "
            "Yine de kaydediyorum…"
        )

    # Save to BOT ROOT (resolved from this file's path), not cwd — robust
    # against systemd cwd quirks.
    _BOT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )))
    cookies_dir = os.path.join(_BOT_ROOT, "cookies")
    os.makedirs(cookies_dir, exist_ok=True)
    target = os.path.join(cookies_dir, "cookies.txt")

    status = await message.reply_text("⬇️ Dosya indiriliyor…")
    try:
        await client.download_media(reply, file_name=target)
    except Exception as e:
        return await status.edit_text(f"❌ İndirme hatası: `{type(e).__name__}: {e}`")

    # Quick sanity check
    try:
        size = os.path.getsize(target)
        with open(target, "r", errors="replace") as f:
            head = f.read(2048)
    except Exception as e:
        return await status.edit_text(f"❌ Okuma hatası: `{e}`")

    looks_netscape = "# Netscape HTTP Cookie File" in head or "\t" in head
    youtube_line = "youtube.com" in head.lower()

    msg = [
        "✅ Cookies kaydedildi → `cookies/cookies.txt`",
        f"📦 Boyut: `{size:,} byte`",
        f"🔍 Netscape format: {'✅' if looks_netscape else '⚠️ tespit edilemedi'}",
        f"🎬 youtube.com içeriği: {'✅' if youtube_line else '⚠️ yok'}",
        "",
        "Yt-dlp bir sonraki çağrıda otomatik kullanır.",
        "Yine de hata alırsanız `/restart` deneyin.",
    ]
    if not (looks_netscape and youtube_line):
        msg.append(
            "\n⚠️ Dosya geçerli görünmüyor olabilir. Chrome'a "
            "'Get cookies.txt LOCALLY' eklentisi kurup youtube.com'da "
            "iken export edin."
        )
    await status.edit_text("\n".join(msg))


@app.on_message(filters.command(["cookiestatus", "getcookies"]) & sudo_filter & filters.private)
async def cmd_cookiestatus(client, message: Message):
    """Show whether cookies.txt is loaded."""
    candidates = [
        os.path.join(os.getcwd(), "cookies", "cookies.txt"),
        os.path.join(os.getcwd(), "cookies.txt"),
    ]
    found = next((p for p in candidates if os.path.isfile(p)), None)
    if not found:
        return await message.reply_text(
            "❌ `cookies/cookies.txt` yok.\n\n"
            "Yüklemek için: dosyayı bota gönder → reply `/setcookies`"
        )
    size = os.path.getsize(found)
    if size == 0:
        return await message.reply_text(
            f"⚠️ Dosya var ama **boş** → `{found}`\n"
            "Geçerli cookies yükleyin."
        )
    try:
        with open(found, "r", errors="replace") as f:
            head = f.read(2048)
        yt_lines = sum(1 for line in head.split("\n") if "youtube" in line.lower())
    except Exception:
        yt_lines = 0
    await message.reply_text(
        f"✅ Cookies aktif\n"
        f"📂 `{found}`\n"
        f"📦 `{size:,} byte`\n"
        f"🎬 youtube satır sayısı (head): `{yt_lines}`"
    )


# ---------- /cookietest : verify cookies actually work against YouTube ----------

@app.on_message(filters.command(["cookietest", "ytdebug"]) & sudo_filter & filters.private)
async def cmd_cookietest(client, message: Message):
    """Try to fetch a stream URL from a known-good YouTube video to validate
    that cookies + yt-dlp work end-to-end on this VPS."""
    status = await message.reply_text("🔍 yt-dlp + cookies testi başlıyor…")

    # "Despacito" — most-viewed video on YouTube, always available
    test_url = "https://www.youtube.com/watch?v=kJQP7kiw5Fk"

    from YukkiMusic.platforms.Youtube import _current_cookies, YTDLP_BIN
    cf = _current_cookies()
    cookies_info = f"`{cf}` ({os.path.getsize(cf):,} byte)" if cf else "❌ YOK"

    attempts = [
        ("ba/b", "default,ios,mweb,android_music,tv_embedded"),
        ("bestaudio[ext=m4a]/bestaudio/best", "mediaconnect,android_music,tv_embedded"),
        ("bestaudio/best", "ios,mweb"),
    ]

    results = [f"📂 cookies: {cookies_info}", ""]
    success = False
    for idx, (fmt, clients) in enumerate(attempts, 1):
        cmd = [*YTDLP_BIN, "-g", "-f", fmt,
               "--extractor-args", f"youtube:player_client={clients}",
               "--no-warnings"]
        if cf:
            cmd += ["--cookies", cf]
        cmd.append(test_url)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate()
            if proc.returncode == 0 and out.strip().startswith(b"http"):
                results.append(f"✅ Deneme #{idx} (`{fmt}`, `{clients}`): **OK**")
                success = True
                break
            else:
                err_short = (err.decode(errors="replace") or "boş")[-200:].strip()
                results.append(f"❌ Deneme #{idx} (`{fmt}`):\n   `{err_short}`")
        except Exception as e:
            results.append(f"❌ Deneme #{idx}: `{type(e).__name__}: {e}`")

    results.append("")
    if success:
        results.append("✅ **Sonuç: yt-dlp + cookies çalışıyor.** /play denemeye hazır.")
    else:
        results.append(
            "❌ **Sonuç: Hiçbir strateji çalışmadı.**\n"
            "• Cookies süresi dolmuş olabilir → yenile, /setcookies ile yükle\n"
            "• Veya VPS IP'si tamamen banlanmış → IP/Proxy değişimi gerekebilir"
        )
    text = "\n".join(results)
    if len(text) > 3800:
        text = text[:3800] + "\n…(kesildi)"
    await status.edit_text(text)


# ---------- /sunucurepo : send the install folder as a zip ----------

@app.on_message(filters.command(["sunucurepo", "serverrepo", "getrepo"]) & sudo_filter & filters.private)
async def cmd_sunucurepo(client, message: Message):
    """Zip the current install directory (excluding secrets, venv, downloads)
    and send to owner as a Telegram document. Owner-only, PM-only."""
    import shutil
    import tempfile
    from datetime import datetime

    cwd = os.getcwd()
    status = await message.reply_text(
        f"📦 Sunucu repo paketleniyor…\n📂 `{cwd}`"
    )

    # Exclusion patterns. Keep cookies.txt OUT for safety (contains session tokens).
    EXCLUDE_DIRS = {
        ".git", "venv", "__pycache__", ".venv", "node_modules",
        "downloads", "cache", "raw_files", ".pytest_cache",
    }
    EXCLUDE_FILES = {
        ".env", "cookies.txt",
    }
    EXCLUDE_SUFFIXES = (
        ".session", ".session-journal", ".pyc", ".log",
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmpdir = tempfile.mkdtemp(prefix="repo_export_")
    archive_base = os.path.join(tmpdir, f"melih_bot_repo_{ts}")

    # Build staging dir with filtered copy
    staging = os.path.join(tmpdir, "staging")
    os.makedirs(staging, exist_ok=True)

    skipped_files = 0
    copied_files = 0
    try:
        for root, dirs, files in os.walk(cwd):
            # Filter excluded dirs in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            rel_root = os.path.relpath(root, cwd)
            dest_root = os.path.join(staging, rel_root) if rel_root != "." else staging
            os.makedirs(dest_root, exist_ok=True)
            for fname in files:
                if fname in EXCLUDE_FILES:
                    skipped_files += 1
                    continue
                if fname.endswith(EXCLUDE_SUFFIXES):
                    skipped_files += 1
                    continue
                # Skip ads/*.mp3 — generated TTS files, huge & not needed
                if rel_root.startswith("ads") and fname.endswith(".mp3"):
                    skipped_files += 1
                    continue
                src = os.path.join(root, fname)
                # Skip files larger than 25 MB (Telegram doc limit safety)
                try:
                    if os.path.getsize(src) > 25 * 1024 * 1024:
                        skipped_files += 1
                        continue
                    shutil.copy2(src, os.path.join(dest_root, fname))
                    copied_files += 1
                except Exception:
                    skipped_files += 1

        await status.edit_text(
            f"📦 {copied_files} dosya hazır, sıkıştırılıyor…"
        )

        # Create zip
        archive_path = shutil.make_archive(archive_base, "zip", staging)
        size_mb = os.path.getsize(archive_path) / (1024 * 1024)

        if size_mb > 2000:
            return await status.edit_text(
                f"❌ Arşiv çok büyük ({size_mb:.1f} MB). Telegram limit 2 GB."
            )

        await status.edit_text(
            f"⬆️ Yükleniyor… ({size_mb:.1f} MB, {copied_files} dosya)"
        )

        caption = (
            f"📦 **Sunucu Repo Yedeği**\n\n"
            f"📂 Kaynak: `{cwd}`\n"
            f"🕐 Zaman: `{ts}`\n"
            f"📊 Dosya: `{copied_files}` dahil, `{skipped_files}` atlandı\n"
            f"💾 Boyut: `{size_mb:.1f} MB`\n\n"
            f"❌ **Dahil değil** (güvenlik/boyut):\n"
            f"• `.env`  • `cookies.txt`  • `.git/`\n"
            f"• `venv/`  • `downloads/`  • `cache/`\n"
            f"• `*.session`  • `ads/*.mp3`  • `*.log`\n"
            f"• 25 MB'dan büyük dosyalar"
        )

        await client.send_document(
            chat_id=message.chat.id,
            document=archive_path,
            caption=caption,
            file_name=f"melih_bot_repo_{ts}.zip",
        )
        await status.delete()

    except Exception as e:
        LOGGER("YukkiMusic").exception("sunucurepo error")
        await status.edit_text(f"❌ Hata: `{type(e).__name__}: {e}`")
    finally:
        # Cleanup
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
