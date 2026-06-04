#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import os

from config import autoclean


async def auto_clean(popped):
    """Delete a finished-playback file from disk immediately.

    2026-02 fix: the previous OR-chain was a no-op (always True), so this
    function only deleted files by accident. We now AND the guards so we
    *skip* live/index streams (which would break ongoing playback) and
    delete every other downloaded media file the second its queue item is
    popped. Combined with the 60s `autoclean_loop` (utils/autoclean.py)
    this keeps the VPS disk near-empty even under heavy /play traffic.
    """
    try:
        rem = popped["file"]
        try:
            autoclean.remove(rem)
        except ValueError:
            pass
        count = autoclean.count(rem)
        if count == 0:
            is_stream = (
                "vid_" in rem
                or "live_" in rem
                or "index_" in rem
            )
            if not is_stream:
                try:
                    if os.path.exists(rem):
                        os.remove(rem)
                except Exception:
                    pass
    except Exception:
        pass
