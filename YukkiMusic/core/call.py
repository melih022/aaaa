#
# Modernized 2026 for py-tgcalls 2.2+, kurigram, Python 3.12+.
#

import asyncio
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pyrogram.errors import (ChatAdminRequired,
                             UserAlreadyParticipant,
                             UserNotParticipant)
from pyrogram.types import InlineKeyboardMarkup

from pytgcalls import PyTgCalls
from pytgcalls.types import (AudioQuality, ChatUpdate, GroupCallConfig,
                             MediaStream, StreamEnded, Update,
                             VideoQuality)

try:
    from pytgcalls.exceptions import NoActiveGroupCall, NotInCallError
except ImportError:
    class NoActiveGroupCall(Exception):
        pass

    class NotInCallError(Exception):
        pass


# Legacy alias kept for backward compat with rest of codebase
class AlreadyJoinedError(Exception):
    pass


class TelegramServerError(Exception):
    pass


import config
from strings import get_string
from YukkiMusic import LOGGER, YouTube, app
from YukkiMusic.misc import db
from YukkiMusic.utils.database import (add_active_chat,
                                       add_active_video_chat,
                                       get_assistant,
                                       get_audio_bitrate, get_lang,
                                       get_loop, get_video_bitrate,
                                       group_assistant, is_autoend,
                                       music_on, mute_off,
                                       remove_active_chat,
                                       remove_active_video_chat,
                                       set_loop)
from YukkiMusic.utils.exceptions import AssistantErr
from YukkiMusic.utils.inline.play import (stream_markup,
                                          telegram_markup)
from YukkiMusic.utils.stream.autoclear import auto_clean
from YukkiMusic.utils.thumbnails import gen_thumb

autoend = {}
counter = {}
AUTO_END_TIME = 3


def _audio_quality(bitrate):
    if isinstance(bitrate, AudioQuality):
        return bitrate
    b = str(bitrate).lower() if bitrate is not None else ""
    if b in ("studio", "highest"):
        return AudioQuality.STUDIO
    if b == "high":
        return AudioQuality.HIGH
    if b in ("medium", "mid"):
        return AudioQuality.MEDIUM
    if b == "low":
        return AudioQuality.LOW
    return AudioQuality.HIGH


def _video_quality(bitrate):
    if isinstance(bitrate, VideoQuality):
        return bitrate
    b = str(bitrate).lower() if bitrate is not None else ""
    if "1080" in b or b in ("fhd", "full_hd"):
        return VideoQuality.FHD_1080p
    if "720" in b or b == "hd":
        return VideoQuality.HD_720p
    if "480" in b or b == "sd":
        return VideoQuality.SD_480p
    if "360" in b:
        return VideoQuality.SD_360p
    return VideoQuality.HD_720p


def _media(link, video=None, audio_quality=None, video_quality=None,
           extra_ffmpeg=None):
    kwargs = {"audio_parameters": _audio_quality(audio_quality)}
    if video:
        kwargs["video_parameters"] = _video_quality(video_quality)
    else:
        kwargs["video_flags"] = MediaStream.IGNORE
    if extra_ffmpeg:
        kwargs["ffmpeg_parameters"] = extra_ffmpeg
    return MediaStream(link, **kwargs)


async def _clear_(chat_id):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


class Call(PyTgCalls):
    def __init__(self):
        # PyTgCalls instances are created lazily in start() (after Client.start),
        # to ensure they bind to the *running* asyncio event loop.
        # Until then, attribute access raises a clear error.
        self.userbot1 = None
        self.userbot2 = None
        self.userbot3 = None
        self.userbot4 = None
        self.userbot5 = None
        self.one = None
        self.two = None
        self.three = None
        self.four = None
        self.five = None

    async def pause_stream(self, chat_id):
        a = await group_assistant(self, chat_id)
        await a.pause(chat_id)

    async def resume_stream(self, chat_id):
        a = await group_assistant(self, chat_id)
        await a.resume(chat_id)

    async def mute_stream(self, chat_id):
        a = await group_assistant(self, chat_id)
        await a.mute(chat_id)

    async def unmute_stream(self, chat_id):
        a = await group_assistant(self, chat_id)
        await a.unmute(chat_id)

    async def stop_stream(self, chat_id):
        a = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await a.leave_call(chat_id)
        except Exception:
            pass

    async def force_stop_stream(self, chat_id):
        a = await group_assistant(self, chat_id)
        try:
            check = db.get(chat_id)
            check.pop(0)
        except Exception:
            pass
        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)
        try:
            await a.leave_call(chat_id)
        except Exception:
            pass

    async def skip_stream(self, chat_id, link, video=None):
        a = await group_assistant(self, chat_id)
        aq = await get_audio_bitrate(chat_id)
        vq = await get_video_bitrate(chat_id)
        await a.play(chat_id, _media(link, video, aq, vq))

    async def seek_stream(self, chat_id, file_path, to_seek, duration, mode):
        a = await group_assistant(self, chat_id)
        aq = await get_audio_bitrate(chat_id)
        vq = await get_video_bitrate(chat_id)
        await a.play(chat_id, _media(
            file_path, video=(mode == "video"),
            audio_quality=aq, video_quality=vq,
            extra_ffmpeg=f"-ss {to_seek} -to {duration}",
        ))

    async def stream_call(self, link):
        a = await group_assistant(self, config.LOG_GROUP_ID)
        await a.play(config.LOG_GROUP_ID, _media(link, video=True))
        await asyncio.sleep(0.5)
        await a.leave_call(config.LOG_GROUP_ID)

    async def join_assistant(self, original_chat_id, chat_id):
        language = await get_lang(original_chat_id)
        _ = get_string(language)
        userbot = await get_assistant(chat_id)
        try:
            try:
                get = await app.get_chat_member(chat_id, userbot.id)
            except ChatAdminRequired:
                raise AssistantErr(_["call_1"])
            from pyrogram.enums import ChatMemberStatus
            if get.status == ChatMemberStatus.BANNED:
                raise AssistantErr(_["call_2"].format(userbot.username, userbot.id))
        except UserNotParticipant:
            chat = await app.get_chat(chat_id)
            if chat.username:
                try:
                    await userbot.join_chat(chat.username)
                except UserAlreadyParticipant:
                    pass
                except Exception as e:
                    raise AssistantErr(_["call_3"].format(e))
            else:
                try:
                    try:
                        invitelink = chat.invite_link
                        if invitelink is None:
                            invitelink = await app.export_chat_invite_link(chat_id)
                    except Exception:
                        invitelink = await app.export_chat_invite_link(chat_id)
                    m = await app.send_message(original_chat_id, _["call_5"])
                    if invitelink.startswith("https://t.me/+"):
                        invitelink = invitelink.replace(
                            "https://t.me/+", "https://t.me/joinchat/"
                        )
                    await asyncio.sleep(3)
                    await userbot.join_chat(invitelink)
                    await asyncio.sleep(4)
                    await m.edit(_["call_6"].format(userbot.name))
                except UserAlreadyParticipant:
                    pass
                except Exception as e:
                    raise AssistantErr(_["call_3"].format(e))

    async def join_call(self, chat_id, original_chat_id, link, video=None):
        a = await group_assistant(self, chat_id)
        aq = await get_audio_bitrate(chat_id)
        vq = await get_video_bitrate(chat_id)
        stream = _media(link, video, aq, vq)
        try:
            await a.play(chat_id, stream)
        except NoActiveGroupCall:
            try:
                await self.join_assistant(original_chat_id, chat_id)
            except Exception as e:
                raise e
            try:
                await a.play(chat_id, stream)
            except Exception:
                raise AssistantErr(
                    "**Aktif Sesli Sohbet Bulunamadı**\n\n"
                    "Lütfen grubun sesli sohbetinin aktif olduğundan emin olun."
                )

        await add_active_chat(chat_id)
        await mute_off(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)
        if await is_autoend():
            counter[chat_id] = {}
            try:
                users = len(await a.get_participants(chat_id))
            except Exception:
                users = 0
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=AUTO_END_TIME)

    async def change_stream(self, client, chat_id):
        check = db.get(chat_id)
        popped = None
        loop = await get_loop(chat_id)
        try:
            if loop == 0:
                popped = check.pop(0)
            else:
                await set_loop(chat_id, loop - 1)
            await auto_clean(popped)
            if not check:
                await _clear_(chat_id)
                try:
                    return await client.leave_call(chat_id)
                except Exception:
                    return
        except Exception:
            try:
                await _clear_(chat_id)
                return await client.leave_call(chat_id)
            except Exception:
                return

        queued = check[0]["file"]
        language = await get_lang(chat_id)
        _ = get_string(language)
        title = (check[0]["title"]).title()
        user = check[0]["by"]
        original_chat_id = check[0]["chat_id"]
        videoid = check[0]["vidid"]
        check[0]["played"] = 0
        is_video = (
            "video" == str(check[0].get("type") or check[0].get("streamtype"))
        )

        if "vid_" in queued:
            n, link = await YouTube.video(
                f"https://www.youtube.com/watch?v={videoid}"
            )
            if n == 0:
                return await app.send_message(original_chat_id, text=_["call_8"])
            stream = _media(link, video=True if is_video else None)
        elif "live_" in queued:
            n, link = await YouTube.video(
                f"https://www.youtube.com/watch?v={videoid}"
            )
            if n == 0:
                return await app.send_message(original_chat_id, text=_["call_8"])
            stream = _media(link, video=True if is_video else None)
        elif "index_" in queued:
            stream = _media(videoid, video=True)
        else:
            stream = _media(queued, video=True if is_video else None)

        try:
            await client.play(chat_id, stream)
        except Exception:
            return await app.send_message(original_chat_id, text=_["call_7"])

        try:
            await gen_thumb(videoid)
        except Exception:
            pass
        button = stream_markup(_, videoid, chat_id)
        run = await app.send_message(
            original_chat_id,
            _["stream_1"].format(
                title, check[0]["dur"], user,
                f"https://t.me/{app.username}?start=info_{videoid}",
            ),
            reply_markup=InlineKeyboardMarkup(button),
        )
        db[chat_id][0]["mystic"] = run
        db[chat_id][0]["markup"] = "stream"

    async def ping(self):
        pings = []
        if config.STRING1 and self.one: pings.append(await self.one.ping)
        if config.STRING2 and self.two: pings.append(await self.two.ping)
        if config.STRING3 and self.three: pings.append(await self.three.ping)
        if config.STRING4 and self.four: pings.append(await self.four.ping)
        if config.STRING5 and self.five: pings.append(await self.five.ping)
        if not pings:
            return "0"
        return str(round(sum(pings) / len(pings), 3))

    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls Clients")
        from YukkiMusic import userbot
        # Bind to userbot's *already-started* clients on the running loop.
        if config.STRING1:
            self.userbot1 = userbot.one
            self.one = PyTgCalls(self.userbot1, cache_duration=100)
            await self.one.start()
        if config.STRING2:
            self.userbot2 = userbot.two
            self.two = PyTgCalls(self.userbot2, cache_duration=100)
            await self.two.start()
        if config.STRING3:
            self.userbot3 = userbot.three
            self.three = PyTgCalls(self.userbot3, cache_duration=100)
            await self.three.start()
        if config.STRING4:
            self.userbot4 = userbot.four
            self.four = PyTgCalls(self.userbot4, cache_duration=100)
            await self.four.start()
        if config.STRING5:
            self.userbot5 = userbot.five
            self.five = PyTgCalls(self.userbot5, cache_duration=100)
            await self.five.start()

    async def decorators(self):
        # Guard against missing instances (only register on configured slots)
        targets = [t for t in (self.one, self.two, self.three, self.four, self.five) if t is not None]
        def _multi_on_update(func):
            for t in targets:
                t.on_update()(func)
            return func
        @_multi_on_update
        async def stream_services_handler(client, update: Update):
            chat_id = getattr(update, "chat_id", None)
            if chat_id is None:
                return
            if isinstance(update, ChatUpdate):
                statuses = ChatUpdate.Status
                left = (
                    statuses.LEFT_GROUP
                    | statuses.CLOSED_VOICE_CHAT
                    | statuses.KICKED
                )
                if update.status & left:
                    await _clear_(chat_id)
                    return
            if isinstance(update, StreamEnded):
                await self.change_stream(client, chat_id)


Yukki = Call()
