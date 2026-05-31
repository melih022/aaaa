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

# Fix "fatal: detected dubious ownership in repository" — happens when
# the bot is run as root (via systemd) but the repo is owned by another
# user (e.g. cloned into /home/google/...). Make this directory safe
# for every git invocation regardless of user.
git config --global --add safe.directory "$ROOT" 2>/dev/null || true

# ────────────────────────────────────────────────────────────────────────
# Banner
# ────────────────────────────────────────────────────────────────────────
clear
cat <<BANNER
${GREEN}
 ╔══════════════════════════════════════════════════════════════╗
 ║                                                              ║
 ║          ${YELLOW}🎵  GOOGLE MUSİC  🎵${GREEN}                            ║
 ║                                                              ║
 ║          ${YELLOW}EGOİST KOMUTAN  •  DEVELOPER${GREEN}                    ║
 ║                                                              ║
 ║          ${NC}Telegram Voice-Chat Music Bot${GREEN}                   ║
 ║          ${NC}One-shot installer  •  v2026${GREEN}                    ║
 ║                                                              ║
 ╚══════════════════════════════════════════════════════════════╝
${NC}
BANNER
sleep 1

# ────────────────────────────────────────────────────────────────────────
# Startup menu — if the bot is already installed, offer quick actions
# instead of forcing a full re-install every time.
# ────────────────────────────────────────────────────────────────────────
INSTALLED="no"
if [[ -f "$ROOT/.env" && -d "$ROOT/venv" ]]; then
  INSTALLED="yes"
fi

if [[ "$INSTALLED" == "yes" ]]; then
  echo
  echo "════════════════════════════════════════════════════════════════"
  echo "  ${GREEN}Mevcut kurulum tespit edildi.${NC}"
  echo "════════════════════════════════════════════════════════════════"
  if systemctl is-active --quiet musicbot 2>/dev/null; then
    echo "  ${GREEN}● Servis durumu: ÇALIŞIYOR${NC}"
  else
    echo "  ${YELLOW}● Servis durumu: durduruldu / yok${NC}"
  fi
  echo
  echo "  ${YELLOW}Ne yapmak istersiniz?${NC}"
  echo
  echo "    ${GREEN}1)${NC} Botu başlat / yeniden başlat"
  echo "    ${GREEN}2)${NC} Yeniden kurulum yap (kod güncelle + bağımlılıklar + .env)"
  echo "    ${GREEN}3)${NC} Botu durdur"
  echo "    ${GREEN}4)${NC} Canlı log göster (Ctrl+C ile çık)"
  echo "    ${GREEN}5)${NC} Tüm dosyaları sil (kurulumu kaldır)"
  echo "    ${GREEN}6)${NC} Çık"
  echo
  read -r -p "  Seçim [1-6] (Enter=1): " start_choice </dev/tty
  case "${start_choice:-1}" in
    1)
      log "Bot başlatılıyor..."
      systemctl restart musicbot
      sleep 3
      if systemctl is-active --quiet musicbot; then
        log "Bot çalışıyor 🎵"
        echo
        echo "Canlı log için:  journalctl -u musicbot -f"
      else
        warn "Bot başlatılamadı. Log:  journalctl -u musicbot -n 50"
      fi
      exit 0
      ;;
    2)
      log "Yeniden kurulum yapılacak. .env değerleri korunacak (Enter ile geçilebilir)."
      ;;
    3)
      log "Bot durduruluyor (auto-restart kapalı)..."
      systemctl stop musicbot
      log "Bot durduruldu. Tekrar başlatmak için:  systemctl start musicbot"
      exit 0
      ;;
    4)
      log "Canlı log gösteriliyor. Ctrl+C ile çık."
      exec journalctl -u musicbot -f
      ;;
    5)
      warn "Tüm dosyalar silinecek!"
      read -r -p "  Emin misiniz? (yazın: SIL) " confirm </dev/tty
      if [[ "$confirm" == "SIL" ]]; then
        systemctl stop musicbot 2>/dev/null || true
        systemctl disable musicbot 2>/dev/null || true
        rm -f /etc/systemd/system/musicbot.service
        systemctl daemon-reload
        log "Servis kaldırıldı."
        log "Dosyalar siliniyor: $ROOT"
        cd "$HOME"
        rm -rf "$ROOT"
        log "Kurulum tamamen kaldırıldı."
      else
        warn "İptal edildi."
      fi
      exit 0
      ;;
    6)
      log "Çıkılıyor."
      exit 0
      ;;
    *)
      warn "Geçersiz seçim, yeniden kurulum yapılacak."
      ;;
  esac
fi

# ────────────────────────────────────────────────────────────────────────
# Clean up stale repo files from previous failed runs
# (older noble/7.0 entries break apt-get update)
# ────────────────────────────────────────────────────────────────────────
log "Eski yarım kurulum izleri temizleniyor..."
rm -f /etc/apt/sources.list.d/mongodb-org-*.list 2>/dev/null
rm -f /usr/share/keyrings/mongodb-server-*.gpg 2>/dev/null

# ────────────────────────────────────────────────────────────────────────
# 1) System packages
# ────────────────────────────────────────────────────────────────────────
log "Apt güncelleniyor..."
apt-get update -y >/dev/null

log "Bağımlılıklar kuruluyor (ffmpeg, python3, git, curl, gnupg)..."
apt-get install -y ffmpeg python3 python3-pip python3-venv git curl gnupg wget ca-certificates >/dev/null

# ────────────────────────────────────────────────────────────────────────
# MongoDB — local install only if user wants it (default behavior).
# If the user has an Atlas / external MongoDB URI, they can enter it later
# in the .env prompts and we skip local installation entirely.
# ────────────────────────────────────────────────────────────────────────
INSTALL_LOCAL_MONGO=""
EXISTING_MONGO_URI=$(grep -E "^MONGO_DB_URI=" "$ROOT/.env" 2>/dev/null | head -1 | sed 's/^MONGO_DB_URI=//')
if [[ -n "$EXISTING_MONGO_URI" && "$EXISTING_MONGO_URI" != "mongodb://localhost:27017" ]]; then
  log "Mevcut external MongoDB URI tespit edildi (Atlas/uzak). Yerel kurulum atlanıyor."
  INSTALL_LOCAL_MONGO="no"
else
  echo
  echo "${YELLOW}MongoDB seçimi:${NC}"
  echo "  1) Yerel MongoDB kur (varsayılan, VPS'inize kurulur)"
  echo "  2) Uzak MongoDB kullan (Atlas, mongodb+srv://... gibi). Şu an kurulum atlanır,"
  echo "     URI'yi az sonra .env adımında girersiniz."
  read -r -p "Seçiminiz [1/2] (Enter=1): " mongo_choice </dev/tty
  if [[ "$mongo_choice" == "2" ]]; then
    INSTALL_LOCAL_MONGO="no"
  else
    INSTALL_LOCAL_MONGO="yes"
  fi
fi

if [[ "$INSTALL_LOCAL_MONGO" == "yes" ]] && ! command -v mongod >/dev/null 2>&1; then
  log "MongoDB kuruluyor (yerel, dış erişimsiz)..."
  CODENAME=$(. /etc/os-release && echo "${VERSION_CODENAME:-jammy}")
  DISTRO_ID=$(. /etc/os-release && echo "${ID:-ubuntu}")
  case "$CODENAME" in
    noble|trixie)  MONGO_VER="8.0" ;;
    jammy|focal|bookworm|bullseye)  MONGO_VER="7.0" ;;
    *)  MONGO_VER="7.0" ;;
  esac

  curl -fsSL "https://www.mongodb.org/static/pgp/server-${MONGO_VER}.asc" \
    | gpg --yes -o "/usr/share/keyrings/mongodb-server-${MONGO_VER}.gpg" --dearmor 2>/dev/null || true

  if [[ "$DISTRO_ID" == "debian" ]]; then
    echo "deb [signed-by=/usr/share/keyrings/mongodb-server-${MONGO_VER}.gpg] https://repo.mongodb.org/apt/debian ${CODENAME}/mongodb-org/${MONGO_VER} main" \
      > "/etc/apt/sources.list.d/mongodb-org-${MONGO_VER}.list"
  else
    echo "deb [signed-by=/usr/share/keyrings/mongodb-server-${MONGO_VER}.gpg] https://repo.mongodb.org/apt/ubuntu ${CODENAME}/mongodb-org/${MONGO_VER} multiverse" \
      > "/etc/apt/sources.list.d/mongodb-org-${MONGO_VER}.list"
  fi

  apt-get update -y >/dev/null 2>&1 || warn "Bazı repolar güncellenemedi"
  if apt-get install -y mongodb-org >/dev/null 2>&1; then
    systemctl enable --now mongod
    log "MongoDB ${MONGO_VER} kuruldu ve başlatıldı."
  else
    warn "MongoDB kurulamadı. Uzak MongoDB (Atlas) kullanmayı düşünün."
    warn "https://cloud.mongodb.com adresinden ücretsiz cluster oluşturabilirsiniz."
  fi
elif [[ "$INSTALL_LOCAL_MONGO" == "yes" ]]; then
  log "MongoDB zaten kurulu."
  systemctl is-active --quiet mongod || systemctl start mongod 2>/dev/null \
    || systemctl start mongodb 2>/dev/null || true
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
  local prompt_label="   ${GREEN}>${NC} ${name} = "
  if [[ -n "$current" ]]; then
    local shown="$current"
    if [[ "$hidden" == "y" && ${#current} -gt 10 ]]; then
      shown="${current:0:6}...${current: -4}"
    fi
    echo "   ${YELLOW}mevcut:${NC} ${shown}"
    read -r -p "${prompt_label}(Enter=mevcudu koru) " val </dev/tty
    [[ -z "$val" ]] && val="$current"
  else
    if [[ -n "$default" ]]; then
      read -r -p "${prompt_label}(Enter=${default}) " val </dev/tty
      [[ -z "$val" ]] && val="$default"
    else
      read -r -p "${prompt_label}" val </dev/tty
    fi
  fi
  printf "%s=%s\n" "$name" "$val"
}

echo
echo "════════════════════════════════════════════════════════════════"
echo "  ${GREEN}.env yapılandırması${NC}"
echo "  Aşağıdaki değerleri sırayla girin. Boş bırakırsanız varsayılan"
echo "  veya mevcut değer kullanılır. Diğer ayarları bot içinden"
echo "  Telegram komutlarıyla yönetebilirsiniz."
echo "════════════════════════════════════════════════════════════════"

API_ID_LINE=$(prompt_var "API_ID" \
  "1) ${YELLOW}API_ID${NC} — Telegram API kimliği (sayı, ~8 hane). https://my.telegram.org → 'API development tools' sayfasından alın." \
  "" "n")

API_HASH_LINE=$(prompt_var "API_HASH" \
  "2) ${YELLOW}API_HASH${NC} — API_ID ile aynı yerden gelen hash (~32 karakter)." \
  "" "y")

BOT_TOKEN_LINE=$(prompt_var "BOT_TOKEN" \
  "3) ${YELLOW}BOT_TOKEN${NC} — Bot için Token. Telegram'da @BotFather'a /newbot yazıp alın. (Format: 1234567890:AbCdEf...)" \
  "" "y")

OWNER_ID_LINE=$(prompt_var "OWNER_ID" \
  "4) ${YELLOW}OWNER_ID${NC} — Bot sahibinin Telegram user ID'si (sayı). @userinfobot'a yazıp öğrenin." \
  "" "n")

LOG_GROUP_LINE=$(prompt_var "LOG_GROUP_ID" \
  "5) ${YELLOW}LOG_GROUP_ID${NC} — Log grubu ID. Bot ve asistanı admin yaptığınız grup. (-100... ile başlar) Yoksa 0 girin." \
  "0" "n")

MONGO_DEFAULT="mongodb://localhost:27017"
[[ "$INSTALL_LOCAL_MONGO" == "no" ]] && MONGO_DEFAULT=""
MONGO_LINE=$(prompt_var "MONGO_DB_URI" \
  "6) ${YELLOW}MONGO_DB_URI${NC} — MongoDB bağlantı adresi. Yerel için Enter, Atlas için 'mongodb+srv://...' yapıştırın." \
  "$MONGO_DEFAULT" "y")

STRING_LINE=$(prompt_var "STRING_SESSION" \
  "7) ${YELLOW}STRING_SESSION${NC} (opsiyonel) — Asistan hesabının Pyrogram string session. Boş bırakırsanız bot çalışır, sonradan PM'den /genstring komutuyla oluşturabilirsiniz." \
  "" "y")

GH_TOKEN_LINE=$(prompt_var "GITHUB_TOKEN" \
  "8) ${YELLOW}GITHUB_TOKEN${NC} (opsiyonel) — /update komutuyla bot içinden 'git pull' yapabilmek için. Boş bırakırsanız da bot çalışır." \
  "" "y")

cat > "$ENV_FILE" <<EOF
${API_ID_LINE}
${API_HASH_LINE}
${BOT_TOKEN_LINE}
${MONGO_LINE}
${LOG_GROUP_LINE}
MUSIC_BOT_NAME=Melih Music Bot
${OWNER_ID_LINE}
${STRING_LINE}
${GH_TOKEN_LINE}
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
log "Servis etkin (musicbot.service)."

echo
echo "════════════════════════════════════════════════════════════════"
echo "  ${GREEN}KURULUM TAMAMLANDI 🎉${NC}"
echo "════════════════════════════════════════════════════════════════"
echo
echo "  ${YELLOW}Şimdi ne yapmak istersiniz?${NC}"
echo
echo "    ${GREEN}1)${NC} Botu tam başlat  (bot + asistan + sesli sohbet)"
echo "    ${GREEN}2)${NC} Asistansız başlat  (sadece bot komutları, VC yok)"
echo "    ${GREEN}3)${NC} Tüm dosyayı sil  (geri al, kurulumu tamamen kaldır)"
echo "    ${GREEN}4)${NC} Şimdi başlatma  (manuel: systemctl start musicbot)"
echo
read -r -p "  Seçim [1/2/3/4] (Enter=1): " final_choice </dev/tty
case "${final_choice:-1}" in
  1)
    log "Bot başlatılıyor (tam mod)..."
    systemctl restart musicbot
    sleep 5
    if systemctl is-active --quiet musicbot; then
      log "Bot çalışıyor 🎵"
    else
      warn "Bot start hatalı görünüyor. Log için:  journalctl -u musicbot -n 50"
    fi
    ;;
  2)
    log "Asistansız mod ayarlanıyor (STRING_SESSION boşaltılıyor)..."
    sed -i 's|^STRING_SESSION=.*|STRING_SESSION=|' "$ENV_FILE"
    systemctl restart musicbot
    sleep 5
    log "Bot asistansız modda çalıştı. Asistan eklemek için PM'de /genstring kullanın."
    ;;
  3)
    warn "Tüm dosyalar silinecek!"
    read -r -p "  Emin misiniz? (yazın: SIL) " confirm </dev/tty
    if [[ "$confirm" == "SIL" ]]; then
      log "Servis durduruluyor..."
      systemctl stop musicbot 2>/dev/null || true
      systemctl disable musicbot 2>/dev/null || true
      rm -f /etc/systemd/system/musicbot.service
      systemctl daemon-reload
      log "Servis kaldırıldı."
      log "Dosyalar siliniyor: $ROOT"
      cd "$HOME"
      rm -rf "$ROOT"
      echo
      log "Kurulum tamamen kaldırıldı. Hoşçakalın."
      exit 0
    else
      warn "İptal edildi."
      systemctl restart musicbot
    fi
    ;;
  4)
    log "Bot şimdi başlatılmadı. Manuel başlatma:  systemctl start musicbot"
    ;;
  *)
    warn "Geçersiz seçim. Bot başlatılmadı."
    ;;
esac

echo
echo "════════════════════════════════════════════════════════════════"
echo "  ${GREEN}YÖNETİM KOMUTLARI${NC}"
echo "════════════════════════════════════════════════════════════════"
echo "  ${YELLOW}Sistem (terminal):${NC}"
echo "    journalctl -u musicbot -f       # canlı log"
echo "    systemctl restart musicbot      # yeniden başlat"
echo "    systemctl stop musicbot         # durdur"
echo "    systemctl start musicbot        # başlat"
echo "    systemctl status musicbot       # durum"
echo "    nano $ENV_FILE                  # .env düzenle"
echo
echo "  ${YELLOW}Telegram (bot PM, sadece sahibi):${NC}"
echo "    /env                            # .env'i görüntüle (gizli alanlar maskeli)"
echo "    /setenv KEY DEĞER               # .env'de bir değeri değiştir"
echo "    /unsetenv KEY                   # .env'den bir alan sil"
echo "    /update                         # git fetch+reset + restart (GITHUB_TOKEN ile)"
echo "    /restart                        # botu yeniden başlat"
echo "    /stop                           # botu tamamen durdur (auto-restart kapalı)"
echo "    /setcookies                     # cookies.txt yükle (dosyaya reply)"
echo "    /cookiestatus                   # cookies durumu"
echo "    /sunucurepo                     # sunucudaki repoyu .zip olarak al"
echo "    /genstring                      # asistan session üret"
echo "    /setad <metin>                  # TTS sesli reklam"
echo "    /setadfile                      # audio'ya reply, set"
echo "    /adon /adoff /adstatus          # reklam yönetimi"
echo "    /lasterror                      # son hata tracebackleri"
echo "    /logs                           # son log satırları"
echo
echo "  ${YELLOW}İlk açılış kontrol listesi:${NC}"
echo "    ✓ Bot'u log grubuna admin olarak ekleyin"
echo "    ✓ Asistan hesabını log grubuna ekleyin"
echo "    ✓ Müzik çalacağınız her gruba bot+asistanı ekleyin"
echo "    ✓ Bot'u admin yapın (asistan davet edebilsin)"
echo "    ✓ Grupta voice chat başlatın, sonra /play deneyin"
echo "════════════════════════════════════════════════════════════════"
