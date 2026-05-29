#
# Simple .env writer & string-session persistence helpers.
#

import os
from pathlib import Path
from typing import Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient

import config

ENV_PATH = Path(os.getenv("BOT_ENV_FILE", ".env")).resolve()


def _parse_env(text: str) -> Dict[str, str]:
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v
    return out


def update_env(key: str, value: str) -> None:
    """Idempotently set KEY=value in .env file."""
    if not ENV_PATH.exists():
        ENV_PATH.write_text("", encoding="utf-8")
    text = ENV_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    found = False
    out = []
    for raw in lines:
        stripped = raw.strip()
        if (
            stripped
            and not stripped.startswith("#")
            and "=" in stripped
            and stripped.split("=", 1)[0].strip() == key
        ):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(raw)
    if not found:
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------- Mongo-backed persistence ----------

_mongo_client = None


def _mongo():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(config.MONGO_DB_URI)
    return _mongo_client["MelihBot"]["sessions"]


async def save_session(slot: int, session_string: str) -> None:
    """Persist STRING_SESSION{n} both to MongoDB and to .env."""
    if slot not in (1, 2, 3, 4, 5):
        raise ValueError("Slot must be 1..5")
    key = "STRING_SESSION" if slot == 1 else f"STRING_SESSION{slot}"
    update_env(key, session_string)
    try:
        coll = _mongo()
        await coll.update_one(
            {"_id": f"slot_{slot}"},
            {"$set": {"string": session_string}},
            upsert=True,
        )
    except Exception:
        # Mongo offline – .env still wins
        pass


async def load_sessions_from_db() -> Dict[int, str]:
    """Restore all stored sessions from MongoDB to env vars at startup."""
    out = {}
    try:
        coll = _mongo()
        async for doc in coll.find({}):
            slot = doc.get("_id", "")
            if not slot.startswith("slot_"):
                continue
            try:
                n = int(slot.split("_", 1)[1])
            except Exception:
                continue
            s = doc.get("string")
            if s and 1 <= n <= 5:
                out[n] = s
    except Exception:
        pass
    return out


def find_next_free_slot() -> Optional[int]:
    """Return the first STRING slot that is not yet set in config."""
    slots = [config.STRING1, config.STRING2, config.STRING3, config.STRING4, config.STRING5]
    for i, v in enumerate(slots, start=1):
        if not v or v in ("None", "none", ""):
            return i
    return None
