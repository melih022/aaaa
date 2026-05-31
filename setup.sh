#!/usr/bin/env bash
#
# Melih Music Bot — interactive VPS setup script (2026)
# Usage:   sudo bash setup.sh
# Re-run safe.  Requires:  Ubuntu/Debian, root (or sudo).
#

set -e

GREEN=$'\033[1;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[1;31m'; NC=$'\033[0m'
log()  { echo "${GREEN}[+]${NC} $*"; }
warn() { echo "${YELLOW}[!]${NC} $*"; }
err()  { echo "${RED}[x]${NC} $*"; }

if [[ $EUID -ne 0 ]]; then
  err "Lütfen root olarak çalıştırın:  sudo bash setup.sh"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ────────────────────────────────────────────────────────────────────────
# 1) System packages
# ────────────────────────────────────────────────────────────────────────
log "Apt güncelleniyor..."
apt-get update -y >/dev/null

log "Bağımlılıklar kuruluyor (ffmpeg, python3, git, curl, gnupg)..."
apt-get install -y ffmpeg python3 python3-pip python3-venv git curl gnupg wget ca-certificates >/dev/null

# MongoDB (only if not installed)
if ! command -v mongod >/dev/null 2>&1; then
  log "MongoDB kuruluyor (yerel, dış erişimsiz)..."
  curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --yes -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor 2>/dev/null || true
  CODENAME=$(. /etc/os-release && echo "${VERSION_CODENAME:-jammy}")
  DISTRO_ID=$(. /etc/os-release && echo "${ID:-ubuntu}")
  if [[ "$DISTRO_ID" == "debian" ]]; then
    echo "deb [signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg] https://repo.mongodb.org/apt/debian ${CODENAME}/mongodb-org/7.0 main" \
      > /etc/apt/sources.list.d/mongodb-org-7.0.list
  else
    echo "deb [signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg] https://repo.mongodb.org/apt/ubuntu ${CODENAME}/mongodb-org/7.0 multiverse" \
      > /etc/apt/sources.list.d/mongodb-org-7.0.list
  fi
  apt-get update -y >/dev/null
  if apt-get install -y mongodb-org >/dev/null 2>&1; then
    systemctl enable --now mongod
  else
    warn "MongoDB 7.0 paketi bulunamadı. Genel mongodb deneniyor..."
    apt-get install -y mongodb >/dev/null 2>&1 || warn "MongoDB kurulamadı, manuel kurulum gerekebilir."
    systemctl enable --now mongodb 2>/dev/null || systemctl enable --now mongod 2>/dev/null || true
  fi
else
  log "MongoDB zaten kurulu."
  systemctl is-active --quiet mongod || systemctl start mongod 2>/dev/null || true
fi

# ────────────────────────────────────────────────────────────────────────
# 2) Python venv & deps
# ────────────────────────────────────────────────────────────────────────
if [[ ! -d venv ]]; then
  log "Python venv oluşturuluyor..."
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

log "pip + temel araçlar güncelleniyor..."
pip install --upgrade pip wheel setuptools >/dev/null

log "Python paketleri kuruluyor (birkaç dakika sürebilir)..."
pip install -r requirements.txt >/dev/null

# kurigram patch (kurigram pyrogram namespace'ine kurulur; yan-pyrogram olursa kaldır)
pip uninstall -y pyrogram >/dev/null 2>&1 || true
pip install --force-reinstall "kurigram>=2.2.23" --no-deps >/dev/null
pip install --upgrade "py-tgcalls>=2.2.12" "yt-dlp>=2026.3.17" "lyricsgenius" >/dev/null

# pyrogram.emoji stub (pykeyboard'un bayrak emojileri için gerekli)
PY_EMOJI=$(python3 - <<'PYEOF'
import pyrogram, os
print(os.path.join(os.path.dirname(pyrogram.__file__), "emoji.py"))
PYEOF
)
cat > "$PY_EMOJI" <<'PYEOF'
FLAG_BELARUS        = "\U0001F1E7\U0001F1FE"
FLAG_CHINA          = "\U0001F1E8\U0001F1F3"
FLAG_FRANCE         = "\U0001F1EB\U0001F1F7"
FLAG_GERMANY        = "\U0001F1E9\U0001F1EA"
FLAG_INDONESIA      = "\U0001F1EE\U0001F1E9"
FLAG_ITALY          = "\U0001F1EE\U0001F1F9"
FLAG_RUSSIA         = "\U0001F1F7\U0001F1FA"
FLAG_SOUTH_KOREA    = "\U0001F1F0\U0001F1F7"
FLAG_SPAIN          = "\U0001F1EA\U0001F1F8"
FLAG_TURKEY         = "\U0001F1F9\U0001F1F7"
FLAG_UKRAINE        = "\U0001F1FA\U0001F1E6"
FLAG_UNITED_KINGDOM = "\U0001F1EC\U0001F1E7"
FLAG_UZBEKISTAN     = "\U0001F1FA\U0001F1FF"
PYEOF
log "pyrogram.emoji stub yazıldı → $PY_EMOJI"

deactivate || true
log "Python bağımlılıkları tamam."

# ────────────────────────────────────────────────────────────────────────
# 3) Interactive .env builder
# ────────────────────────────────────────────────────────────────────────
ENV_FILE="$ROOT/.env"

# Try to keep existing values if any
get_existing() {
  local name="$1"
  [[ -f "$ENV_FILE" ]] || { echo ""; return; }
  grep -E "^${name}=" "$ENV_FILE" 2>/dev/null | head -1 | sed "s/^${name}=//" || true
}

prompt_var() {
  # $1=name $2=description $3=default $4=hidden(y/n)
  local name="$1"; local desc="$2"; local default="$3"; local hidden="$4"
  local current; current=$(get_existing "$name")
  echo
  echo "${YELLOW}${desc}${NC}"
  local val=""
  if [[ -n "$current" ]]; then
    local shown="$current"
    if [[ "$hidden" == "y" && ${#current} -gt 10 ]]; then
      shown="${current:0:6}...${current: -4}"
    fi
    echo "   mevcut: ${shown}"
    read -r -p "   Yeni değer (Enter=mevcudu koru): " val </dev/tty
    [[ -z "$val" ]] && val="$current"
  else
    if [[ -n "$default" ]]; then
      read -r -p "   Değer (Enter=${default}): " val </dev/tty
      [[ -z "$val" ]] && val="$default"
    else
      read -r -p "   Değer: " val </dev/tty
    fi
  fi
  printf "%s=%s\n" "$name" "$val"
}

echo
echo "════════════════════════════════════════════════════════════════"
echo "  Melih Music Bot — .env kurulumu"
echo "  Sadece zorunlu birkaç değer sorulacak."
echo "  Diğerlerini Telegram'da bot komutlarıyla yönetebilirsiniz."
echo "════════════════════════════════════════════════════════════════"

API_ID_LINE=$(prompt_var "API_ID" "1) Telegram API_ID (my.telegram.org → API development tools)" "" "n")
API_HASH_LINE=$(prompt_var "API_HASH" "2) Telegram API_HASH (aynı yerden)" "" "y")
BOT_TOKEN_LINE=$(prompt_var "BOT_TOKEN" "3) Bot Token (@BotFather → /newbot veya /token)" "" "y")
OWNER_ID_LINE=$(prompt_var "OWNER_ID" "4) Sahibinin Telegram User ID (@userinfobot ile öğren)" "" "n")
LOG_GROUP_LINE=$(prompt_var "LOG_GROUP_ID" "5) Log Grup ID (botu ve asistanı admin yapın). Yoksa 0 girin" "0" "n")
STRING_LINE=$(prompt_var "STRING_SESSION" "6) (Opsiyonel) Asistan STRING_SESSION. Boş bırakırsanız bot çalışır, /genstring ile sonra ekleyebilirsiniz" "" "y")

cat > "$ENV_FILE" <<EOF
${API_ID_LINE}
${API_HASH_LINE}
${BOT_TOKEN_LINE}
MONGO_DB_URI=mongodb://localhost:27017
${LOG_GROUP_LINE}
MUSIC_BOT_NAME=Melih Music Bot
${OWNER_ID_LINE}
${STRING_LINE}
DURATION_LIMIT=60
SONG_DOWNLOAD_DURATION_LIMIT=180
VIDEO_STREAM_LIMIT=3
CLEANMODE_MINS=5
PRIVATE_BOT_MODE=False
YOUTUBE_EDIT_SLEEP=3
TELEGRAM_EDIT_SLEEP=5
AUTO_LEAVING_ASSISTANT=False
ASSISTANT_LEAVE_TIME=5400
AUTO_DOWNLOADS_CLEAR=True
AUTO_SUGGESTION_MODE=False
SUPPORT_CHANNEL=https://t.me/GoogleBilgi
GITHUB_REPO=https://github.com/melih022/aaaa
UPSTREAM_REPO=https://github.com/melih022/aaaa
USE_COOKIES=True
EOF

chmod 600 "$ENV_FILE"
log ".env kaydedildi → $ENV_FILE"

# ────────────────────────────────────────────────────────────────────────
# 4) Folders
# ────────────────────────────────────────────────────────────────────────
mkdir -p cookies downloads ads cache
log "Klasörler hazır: cookies/  downloads/  ads/  cache/"
if [[ ! -s cookies/cookies.txt ]]; then
  warn "cookies/cookies.txt boş/yok. Çoğu video çalışır;"
  warn "VEVO/yaş-kısıtlı için cookies/cookies.txt yükleyin."
fi

# ────────────────────────────────────────────────────────────────────────
# 5) systemd unit
# ────────────────────────────────────────────────────────────────────────
UNIT="/etc/systemd/system/musicbot.service"
log "systemd servisi yazılıyor..."
cat > "$UNIT" <<EOF
[Unit]
Description=Melih Music Bot
After=network.target mongod.service mongodb.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${ROOT}
Environment=PYTHONUNBUFFERED=1
ExecStart=${ROOT}/venv/bin/python3 -m YukkiMusic
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable musicbot >/dev/null
log "Servis etkin. Başlatılıyor..."
systemctl restart musicbot
sleep 4

if systemctl is-active --quiet musicbot; then
  log "Bot servisi çalışıyor. 🎉"
else
  warn "Bot başlatıldı ama henüz aktif değil. Logları inceleyin:"
  warn "  journalctl -u musicbot -n 50 --no-pager"
fi

echo
echo "════════════════════════════════════════════════════════════════"
echo "${GREEN}KURULUM TAMAM!${NC}"
echo
echo "  Logları izlemek:    journalctl -u musicbot -f"
echo "  Yeniden başlat:     systemctl restart musicbot"
echo "  Durdur:             systemctl stop musicbot"
echo "  .env düzenle:       nano $ENV_FILE   (sonra restart)"
echo
echo "  Bot Telegram'da hazır → @botunuzun_kullanıcı_adı /start"
echo
echo "  İlk açılış kontrol listesi:"
echo "    ✓ Bot'u log grubuna (LOG_GROUP_ID) admin olarak ekleyin"
echo "    ✓ Asistan (STRING_SESSION) hesabını log grubuna ekleyin"
echo "    ✓ Müzik çalacağınız her gruba bot+asistanı ekleyin"
echo "    ✓ Bot'u admin yapın (asistan davet edebilsin)"
echo
echo "  Reklam ayarlamak (PM):"
echo "    /setad <metin>      → TTS sesli reklam"
echo "    /setadfile          → audio dosyaya reply, set"
echo "    /adstatus           → durum"
echo "    /adon /adoff        → aç/kapa"
echo "════════════════════════════════════════════════════════════════"
