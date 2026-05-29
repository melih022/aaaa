#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.
import asyncio

from pyrogram import filters
from pyrogram.types import CallbackQuery, Message

from config import BANNED_USERS, MUSIC_BOT_NAME, adminlist, lyrical
from strings import get_command
from YukkiMusic import app
from YukkiMusic.core.call import Yukki
from YukkiMusic.misc import db
from YukkiMusic.utils.database import get_authuser_names, get_cmode
from YukkiMusic.utils.decorators import (ActualAdminCB, AdminActual,
                                         language)
from YukkiMusic.utils.formatters import alpha_to_int

### Multi-Lang Commands
RELOAD_COMMAND = get_command("RELOAD_COMMAND")
RESTART_COMMAND = get_command("RESTART_COMMAND")
KOMUTLAR_COMMAND = get_command("KOMUTLAR_COMMAND")
CKOMUTLAR_COMMAND = get_command("CKOMUTLAR_COMMAND")

@app.on_message(
    filters.command(RELOAD_COMMAND)
    & filters.group
    & ~BANNED_USERS
)
@language
async def reload_admin_cache(client, message: Message, _):
    try:
        from pyrogram.enums import ChatMembersFilter
        chat_id = message.chat.id
        authusers = await get_authuser_names(chat_id)
        adminlist[chat_id] = []
        try:
            async for member in app.get_chat_members(
                chat_id, filter=ChatMembersFilter.ADMINISTRATORS
            ):
                priv = getattr(member, "privileges", None)
                can_manage = (
                    getattr(priv, "can_manage_video_chats", False) if priv
                    else getattr(member, "can_manage_video_chats", False)
                )
                is_owner = False
                try:
                    from pyrogram.enums import ChatMemberStatus
                    is_owner = (member.status == ChatMemberStatus.OWNER)
                except Exception:
                    pass
                if is_owner or can_manage:
                    adminlist[chat_id].append(member.user.id)
        except Exception as inner_e:
            # Fallback: try iter_chat_members API (kurigram older)
            try:
                members = await app.get_chat_members(chat_id)
                for member in members:
                    priv = getattr(member, "privileges", None)
                    can_manage = (
                        getattr(priv, "can_manage_video_chats", False) if priv
                        else getattr(member, "can_manage_video_chats", False)
                    )
                    if can_manage:
                        adminlist[chat_id].append(member.user.id)
            except Exception:
                raise inner_e

        for user in authusers:
            user_id = await alpha_to_int(user)
            adminlist[chat_id].append(user_id)
        await message.reply_text(
            f"{_['admin_20']}\n\n✅ {len(adminlist[chat_id])} admin/auth user cached."
        )
    except Exception as e:
        await message.reply_text(
            f"❌ Admin listesi yüklenemedi.\n\n"
            f"`{type(e).__name__}: {e}`\n\n"
            f"Bot'un sohbette **admin** olduğundan ve **Manage Video Chats** "
            f"yetkisine sahip olduğundan emin olun."
        )


@app.on_message(
    filters.command(RESTART_COMMAND)
    & filters.group
  #  & ~filters.edited
    & ~BANNED_USERS
)
@AdminActual
async def restartbot(client, message: Message, _):
    mystic = await message.reply_text(
        f"Lütfen bekleyiniz. {MUSIC_BOT_NAME} Yeniden Başlatılıyor.."
    )
    await asyncio.sleep(1)
    try:
        db[message.chat.id] = []
        await Yukki.stop_stream(message.chat.id)
    except:
        pass
    chat_id = await get_cmode(message.chat.id)
    if chat_id:
        try:
            await app.get_chat(chat_id)
        except:
            pass
        try:
            db[chat_id] = []
            await Yukki.stop_stream(chat_id)
        except:
            pass
    return await mystic.edit_text(
        "Başarıyla yeniden başlatıldı.Tekrardan Kullanabilirsiniz.."
    )


@app.on_callback_query(filters.regex("close") & ~BANNED_USERS)
async def close_menu(_, CallbackQuery):
    try:
        await CallbackQuery.message.delete()
        await CallbackQuery.answer()
    except:
        return


@app.on_callback_query(filters.regex("close") & ~BANNED_USERS)
async def close_menu(_, CallbackQuery):
    try:
        await CallbackQuery.message.delete()
        await CallbackQuery.answer()
    except:
        return


@app.on_callback_query(
    filters.regex("stop_downloading") & ~BANNED_USERS
)
@ActualAdminCB
async def stop_download(client, CallbackQuery: CallbackQuery, _):
    message_id = CallbackQuery.message.id
    task = lyrical.get(message_id)
    if not task:
        return await CallbackQuery.answer(
            "İndirme zaten Tamamlandı.", show_alert=True
        )
    if task.done() or task.cancelled():
        return await CallbackQuery.answer(
            "İndirme zaten Tamamlandı veya İptal Edildi.",
            show_alert=True,
        )
    if not task.done():
        try:
            task.cancel()
            try:
                lyrical.pop(message_id)
            except:
                pass
            await CallbackQuery.answer(
                "İndirme İptal Edildi", show_alert=True
            )
            return await CallbackQuery.edit_message_text(
                f"İndirme Tarafından {CallbackQuery.from_user.mention} İptal Edildi"
            )
        except:
            return await CallbackQuery.answer(
                "İndirme durdurulamadı.", show_alert=True
            )
    await CallbackQuery.answer(
        "Çalışan görev tanınmadı", show_alert=True
    )

@app.on_message(
    filters.command(KOMUTLAR_COMMAND)
    & filters.group
    #& ~filters.edited
    & ~BANNED_USERS
)    
async def mesaj(client, message: Message):
  await message.reply("Botun Komutları:\n\n➥ /oynat - Şarkı oynatır.\n✦ /oynat komutu aynı zamanda canlı yayında destekler.(örnek: /oynat kralfm canlı)\n➥ /voynat - Video Oynatır.\n✦ /voynat komutu aynı zamanda canlı yayınıda destekler.(örnek: /voynat kralfm canlı)\n➥ /devam - Akışı devam ettirir.\n➥ /durdur - Akışı duraklatır.\n➥ /son - Akışı Sonlandırır.\n➥ /atla - Diğer parça ya atlar.\n✦ atla komutu aynı zamanda sıraya aldığınız istediğiniz parçaya atlar.( Örnek : /atla 3 -  3. Parçaya atlar )\n➥ /sira - sıraya alınan parçaları gösterir.\n➥ /ileri - Oynatılan parçayı ileri alır.\n✦(örneğin: /ileri 30 - parçayı 30 saniye ileri alır)\n➥ /gerial - Oynatılan parçayı geri alır.\n✦(örneğin: /gerial 30 - parçayı 30 saniye geriye alır)\n➥ /karistir - Sıraya alınan Parçaları karışık oynatır.\n➥ /tekrarla - oynatılan parçayı istediğiniz kadar tekrar eder.\n✦(örneğin: /tekrarla 4 - Parçayı 4 kez tekrarlar.)\n➥/bul {şarkı - video ismi veya linki} - komutunu kullanarak şarkı indirebilirsiniz.\n➥ /yetkiver - Grubunuzda yetkisiz üyeye yetki vererek botu kullandırabilirsiz.\n➥ /yetkial - Grubunuzdaki botu kullanan yetkisiz üyeden bot yetkisini alır.\n➥ /yetkilistesi - Komutunu kullanarak Bottan yetkili olan üyelerinizi Görebilirsiniz.\n➥ /oynatmodu - Botun kullanım ayarlarını yapabilirsiniz.\n➥ /restart - komutunu kullanarak admin listenizi güncelleyebilirsiniz.\n\n Detaylı Komutlar İçin @VideoMuzikKomutlar Kanalına Göz Atınız.")  
  
  
@app.on_message(
    filters.command(CKOMUTLAR_COMMAND)
    & filters.group
   # & ~filters.edited
    & ~BANNED_USERS
)    
async def mesaj(client, message: Message):
  await message.reply("Botun Kanal Komutları:\n\n➥ /koynat - Şarkı oynatır.\n✦ /koynat komutu aynı zamanda canlı yayında destekler.(örnek: /koynat kralfm canlı)\n➥ /kvoynat - Video Oynatır.\n✦ /kvoynat komutu aynı zamanda canlı yayınıda destekler.(örnek: /kvoynat kralfm canlı)\n➥ /kdevam - Akışı devam ettirir.\n➥ /kdurdur - Akışı duraklatır.\n➥ /kson - Akışı Sonlandırır.\n➥ /katla - Diğer parça ya atlar.\n✦ atla komutu aynı zamanda sıraya aldığınız istediğiniz parçaya atlar.( Örnek : /katla 3 -  3. Parçaya atlar )\n➥ /ksira - sıraya alınan parçaları gösterir.\n➥ /kileri - Oynatılan parçayı ileri alır.\n✦(örneğin: /kileri 30 - parçayı 30 saniye ileri alır)\n➥ /kgerial - Oynatılan parçayı geri alır.\n✦(örneğin: /kgerial 30 - parçayı 30 saniye geriye alır)\n➥ /kkaristir - Sıraya alınan Parçaları karışık oynatır.\n➥ /ktekrarla - oynatılan parçayı istediğiniz kadar tekrar eder.\n✦(örneğin: /ktekrarla 4 - Parçayı 4 kez tekrarlar.)\n➥ /yetkilistesi - Komutunu kullanarak Bottan yetkili olan üyelerinizi Görebilirsiniz.\n➥ Detaylı Komutlar İçin @VideoMuzikKomutlar Kanalına Göz Atınız.")  
    
