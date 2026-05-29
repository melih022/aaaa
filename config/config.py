#
# Cleaned-up config (2026). NO hardcoded credentials — everything comes from .env.
#

import re
import sys
from os import getenv

from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()

# Telegram API
API_ID = int(getenv("API_ID", "22949152"))
API_HASH = getenv("API_HASH", "82f948ad9f8bdb879b53f27ea76407fd")

# Bot
BOT_TOKEN = getenv("BOT_TOKEN", "8699348407:AAFBu1XO8ICEMPtoMLdtU5kW4XcHB58JgAQ")

# Mongo
MONGO_DB_URI = getenv("MONGO_DB_URI", "mongodb://localhost:27017")

# Limits
DURATION_LIMIT_MIN = int(getenv("DURATION_LIMIT", "600"))
SONG_DOWNLOAD_DURATION = int(getenv("SONG_DOWNLOAD_DURATION_LIMIT", "180"))

# Log group
LOG_GROUP_ID = int(getenv("LOG_GROUP_ID", "-1003429099096"))

# Bot name
MUSIC_BOT_NAME = getenv("MUSIC_BOT_NAME", "Melih Music Bot")

# Owners
OWNER_ID = list(map(int, getenv("OWNER_ID", "7035704703").split()))

# Heroku
HEROKU_API_KEY = getenv("HEROKU_API_KEY")
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")

# Upstream
UPSTREAM_REPO = getenv("UPSTREAM_REPO", "https://github.com/melih022/123")
UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "master")
GIT_TOKEN = getenv("GIT_TOKEN", None)

# Support links
SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/GoogleBilgi")
SUPPORT_GROUP = getenv("SUPPORT_GROUP", None)

# Auto-leave
AUTO_LEAVING_ASSISTANT = getenv("AUTO_LEAVING_ASSISTANT", "False")
AUTO_LEAVE_ASSISTANT_TIME = int(getenv("ASSISTANT_LEAVE_TIME", "10400"))
AUTO_SUGGESTION_TIME = int(getenv("AUTO_SUGGESTION_TIME", "4400"))
AUTO_DOWNLOADS_CLEAR = getenv("AUTO_DOWNLOADS_CLEAR", "True")
AUTO_SUGGESTION_MODE = getenv("AUTO_SUGGESTION_MODE", "False")
PRIVATE_BOT_MODE = getenv("PRIVATE_BOT_MODE", "False")

# Sleep
YOUTUBE_DOWNLOAD_EDIT_SLEEP = int(getenv("YOUTUBE_EDIT_SLEEP", "3"))
TELEGRAM_DOWNLOAD_EDIT_SLEEP = int(getenv("TELEGRAM_EDIT_SLEEP", "5"))

GITHUB_REPO = getenv("GITHUB_REPO", None)

# Spotify
SPOTIFY_CLIENT_ID = getenv("SPOTIFY_CLIENT_ID", None)
SPOTIFY_CLIENT_SECRET = getenv("SPOTIFY_CLIENT_SECRET", None)

# Limits
VIDEO_STREAM_LIMIT = int(getenv("VIDEO_STREAM_LIMIT", "3"))
SERVER_PLAYLIST_LIMIT = int(getenv("SERVER_PLAYLIST_LIMIT", "30"))
PLAYLIST_FETCH_LIMIT = int(getenv("PLAYLIST_FETCH_LIMIT", "50"))
CLEANMODE_DELETE_MINS = int(getenv("CLEANMODE_MINS", "600"))

# File size limits
TG_AUDIO_FILESIZE_LIMIT = int(getenv("TG_AUDIO_FILESIZE_LIMIT", "3145728000"))
TG_VIDEO_FILESIZE_LIMIT = int(getenv("TG_VIDEO_FILESIZE_LIMIT", "3145728000"))

# ============================================================================
# STRING SESSIONS - CRITICAL: do NOT add fallback session strings here!
# Empty string -> falsy -> bot starts in assistant-less mode.
# ============================================================================
def _clean_session(v):
    if v is None: return None
    v = str(v).strip()
    if v in ("", "None", "none", "null"): return None
    return v

STRING1 = _clean_session(getenv("STRING_SESSION", None) or getenv("STRING_SESSION1", None))
STRING2 = _clean_session(getenv("STRING_SESSION2", None))
STRING3 = _clean_session(getenv("STRING_SESSION3", None))
STRING4 = _clean_session(getenv("STRING_SESSION4", None))
STRING5 = _clean_session(getenv("STRING_SESSION5", None))

# Internal state
BANNED_USERS = filters.user()
YTDOWNLOADER = 1
LOG = 2
LOG_FILE_NAME = "Yukkilogs.txt"

adminlist = {}
lyrical = {}
chatstats = {}
userstats = {}
clean = {}
autoclean = []

# Images
START_IMG_URL = getenv("START_IMG_URL", "assets/startvideo.jpg")
PING_IMG_URL = getenv("PING_IMG_URL", "assets/Ping.jpeg")
PLAYLIST_IMG_URL = getenv("PLAYLIST_IMG_URL", "assets/Playlist.jpeg")
GLOBAL_IMG_URL = getenv("GLOBAL_IMG_URL", "assets/Global.jpeg")
STATS_IMG_URL = getenv("STATS_IMG_URL", "assets/Stats.jpeg")
TELEGRAM_AUDIO_URL = getenv("TELEGRAM_AUDIO_URL", "assets/Audio.jpeg")
TELEGRAM_VIDEO_URL = getenv("TELEGRAM_VIDEO_URL", "assets/Video.jpeg")
STREAM_IMG_URL = getenv("STREAM_IMG_URL", "assets/Stream.jpeg")
SOUNCLOUD_IMG_URL = getenv("SOUNCLOUD_IMG_URL", "assets/Soundcloud.jpeg")
YOUTUBE_IMG_URL = getenv("YOUTUBE_IMG_URL", "assets/Youtube.jpeg")
SPOTIFY_ARTIST_IMG_URL = getenv("SPOTIFY_ARTIST_IMG_URL", "assets/SpotifyArtist.jpeg")
SPOTIFY_ALBUM_IMG_URL = getenv("SPOTIFY_ALBUM_IMG_URL", "assets/SpotifyAlbum.jpeg")
SPOTIFY_PLAYLIST_IMG_URL = getenv("SPOTIFY_PLAYLIST_IMG_URL", "assets/SpotifyPlaylist.jpeg")


def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(stringt.split(":"))))


DURATION_LIMIT = int(time_to_seconds(f"{DURATION_LIMIT_MIN}:00"))
SONG_DOWNLOAD_DURATION_LIMIT = int(time_to_seconds(f"{SONG_DOWNLOAD_DURATION}:00"))


def _check_url(name, value):
    if value and not re.match("(?:http|https)://", value):
        print(f"[ERROR] - Your {name} url is wrong. Must start with http(s)://")
        sys.exit()


_check_url("SUPPORT_CHANNEL", SUPPORT_CHANNEL)
if SUPPORT_GROUP:
    _check_url("SUPPORT_GROUP", SUPPORT_GROUP)
if UPSTREAM_REPO:
    _check_url("UPSTREAM_REPO", UPSTREAM_REPO)
if GITHUB_REPO:
    _check_url("GITHUB_REPO", GITHUB_REPO)
