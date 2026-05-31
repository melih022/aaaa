#
# Ad system (pre-roll). Owner-only.
#
# Storage: MongoDB collection `ad_config` doc { _id: "ad" }
#   {
#     "enabled": bool,
#     "mode":    "tts" | "audio" | "none",
#     "text":    str,        # for tts
#     "voice":   str,        # edge-tts voice name (default tr-TR-AhmetNeural)
#     "audio_path": str,     # absolute path to a stored audio file (for audio mode)
#     "updated_by": int,     # user id
#     "updated_at": str,     # iso
#   }
#
# Public API (async):
#   get_ad_config()        -> dict   (always returns a doc, defaults if missing)
#   set_ad_text(text, voice, by)
#   set_ad_audio(path, by)
#   clear_ad(by)
#   set_ad_enabled(flag, by)
#   prepare_ad_file()      -> str | None   (path to playable audio file or None)
#

import asyncio
import os
import shutil
from datetime import datetime, timezone

from YukkiMusic.core.mongo import mongodb

_coll = mongodb.ad_config
_DOC_ID = "ad"

_DEFAULTS = {
    "_id": _DOC_ID,
    "enabled": False,
    "mode": "none",
    "text": "",
    "voice": "tr-TR-AhmetNeural",
    "audio_path": "",
    "updated_by": 0,
    "updated_at": "",
}

ADS_DIR = "ads"
TTS_CACHE = os.path.join(ADS_DIR, "ad_tts.mp3")
os.makedirs(ADS_DIR, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).isoformat()


async def get_ad_config() -> dict:
    doc = await _coll.find_one({"_id": _DOC_ID})
    if not doc:
        return dict(_DEFAULTS)
    out = dict(_DEFAULTS)
    out.update(doc)
    return out


async def _save(patch: dict, by: int):
    patch = {**patch, "updated_by": int(by), "updated_at": _now()}
    await _coll.update_one(
        {"_id": _DOC_ID},
        {"$set": patch},
        upsert=True,
    )


async def set_ad_text(text: str, voice: str, by: int):
    # Invalidate cached TTS render
    if os.path.exists(TTS_CACHE):
        try:
            os.remove(TTS_CACHE)
        except OSError:
            pass
    await _save(
        {
            "enabled": True,
            "mode": "tts",
            "text": text,
            "voice": voice or _DEFAULTS["voice"],
            "audio_path": "",
        },
        by,
    )


async def set_ad_audio(src_path: str, by: int):
    """Copy src_path into ads/ad_audio.<ext> and store path."""
    if not os.path.isfile(src_path):
        raise FileNotFoundError(src_path)
    ext = os.path.splitext(src_path)[1].lower() or ".ogg"
    dest = os.path.join(ADS_DIR, f"ad_audio{ext}")
    # Remove old variants
    for old in os.listdir(ADS_DIR):
        if old.startswith("ad_audio"):
            try:
                os.remove(os.path.join(ADS_DIR, old))
            except OSError:
                pass
    shutil.copyfile(src_path, dest)
    await _save(
        {"enabled": True, "mode": "audio", "audio_path": dest, "text": ""},
        by,
    )
    return dest


async def clear_ad(by: int):
    if os.path.exists(TTS_CACHE):
        try:
            os.remove(TTS_CACHE)
        except OSError:
            pass
    for old in os.listdir(ADS_DIR):
        if old.startswith("ad_audio"):
            try:
                os.remove(os.path.join(ADS_DIR, old))
            except OSError:
                pass
    await _save(
        {"enabled": False, "mode": "none", "text": "", "audio_path": ""},
        by,
    )


async def set_ad_enabled(flag: bool, by: int):
    await _save({"enabled": bool(flag)}, by)


# ---------------------------------------------------------------------------
# TTS rendering (edge-tts)
# ---------------------------------------------------------------------------
async def _render_tts(text: str, voice: str, out_path: str) -> str:
    """Render text → out_path using edge-tts. Returns out_path on success."""
    import edge_tts

    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(out_path)
    return out_path


async def prepare_ad_file() -> str | None:
    """Return a playable audio file path for the current ad, or None if disabled/empty."""
    cfg = await get_ad_config()
    if not cfg.get("enabled"):
        return None
    mode = cfg.get("mode", "none")

    if mode == "audio":
        p = cfg.get("audio_path") or ""
        return p if p and os.path.isfile(p) else None

    if mode == "tts":
        text = (cfg.get("text") or "").strip()
        if not text:
            return None
        # Cache valid as long as text+voice unchanged. We invalidate on set_ad_text.
        if os.path.isfile(TTS_CACHE) and os.path.getsize(TTS_CACHE) > 256:
            return TTS_CACHE
        try:
            await _render_tts(text, cfg.get("voice") or _DEFAULTS["voice"], TTS_CACHE)
        except Exception:
            # If edge-tts fails, fall back to gTTS
            try:
                from gtts import gTTS
                def _gtts():
                    tts = gTTS(text=text, lang="tr")
                    tts.save(TTS_CACHE)
                await asyncio.get_running_loop().run_in_executor(None, _gtts)
            except Exception:
                return None
        return TTS_CACHE if os.path.isfile(TTS_CACHE) else None

    return None
