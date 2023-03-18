import os
import traceback
import logging

from pyrogram import Client
from pyrogram import StopPropagation, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

import config
from handlers.broadcast import broadcast
from handlers.check_user import handle_user_status
from handlers.database import Database

LOG_CHANNEL = config.LOG_CHANNEL
AUTH_USERS = config.AUTH_USERS
DB_URL = config.DB_URL
DB_NAME = config.DB_NAME

db = Database(DB_URL, DB_NAME)


Bot = Client(
    "BroadcastBot",
    bot_token=config.BOT_TOKEN,
    api_id=config.API_ID,
    api_hash=config.API_HASH,
)

@Bot.on_message(filters.private)
async def _(bot, cmd):
    await handle_user_status(bot, cmd)




@Bot.on_message(filters.command("settings"))
async def opensettings(bot, cmd):
    user_id = cmd.from_user.id
    await cmd.reply_text(
        f"`هنا يمكنك ضبط إعداداتك:`\n\nتم إعداد الإشعارات بنجاح إلى **{await db.get_notif(user_id)}**",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"إعلام  {'🔔' if ((await db.get_notif(user_id)) is True) else '🔕'}",
                        callback_data="notifon",
                    )
                ],
                [InlineKeyboardButton("❎", callback_data="closeMeh")],
            ]
        ),
    )


@Bot.on_message(filters.private & filters.command("broadcast"))
async def broadcast_handler_open(_, m):
    if m.from_user.id not in AUTH_USERS:
        await m.delete()
        return
    if m.reply_to_message is None:
        await m.delete()
    else:
        await broadcast(m, db)


@Bot.on_message(filters.private & filters.command("stats"))
async def sts(c, m):
    if m.from_user.id not in AUTH_USERS:
        await m.delete()
        return
    await m.reply_text(
        text=f"**إجمالي المستخدمين في قاعدة البيانات 📂:** `{await db.total_users_count()}`\n\n**إجمالي المستخدمين الذين تم تمكين الإشعارات 🔔 :** `{await db.total_notif_users_count()}`",
        quote=True
    )


@Bot.on_message(filters.private & filters.command("ban_user"))
async def ban(c, m):
    if m.from_user.id not in AUTH_USERS:
        await m.delete()
        return
    if len(m.command) == 1:
        await m.reply_text(
            f"استخدم هذا الأمر لحظر 🛑 أي مستخدم من الروبوت 🤖.\n\nUsage:\n\n`/ban_user user_id ban_duration ban_reason`\n\nEg: `/ban_user 1234567 28 You misused me.`\n This will ban user with id `1234567` for `28` days for the reason `You misused me`.",
            quote=True,
        )
        return

    try:
        user_id = int(m.command[1])
        ban_duration = int(m.command[2])
        ban_reason = " ".join(m.command[3:])
        ban_log_text = f"حظر المستخدم {user_id} for {ban_duration} أيام للسبب {ban_reason}."

        try:
            await c.send_message(
                user_id,
                f"أنت محظور 🚫 لاستخدام هذا الروبوت من أجل **{ban_duration}** اليوم (الأيام) لهذا السبب __{ban_reason}__ \n\n**رسالة من المشرف 🤠**",
            )
            ban_log_text += "\n\nتم إخطار المستخدم بنجاح!"
        except BaseException:
            traceback.print_exc()
            ban_log_text += (
                f"\n\n ⚠️ فشل إشعار المستخدم! ⚠️ \n\n`{traceback.format_exc()}`"
            )
        await db.ban_user(user_id, ban_duration, ban_reason)
        print(ban_log_text)
        await m.reply_text(ban_log_text, quote=True)
    except BaseException:
        traceback.print_exc()
        await m.reply_text(
            f"خطأ ⚠️! التتبع الوارد أدناه\n\n`{traceback.format_exc()}`",
            quote=True
        )


@Bot.on_message(filters.private & filters.command("unban_user"))
async def unban(c, m):
    if m.from_user.id not in AUTH_USERS:
        await m.delete()
        return
    if len(m.command) == 1:
        await m.reply_text(
            f"Use this command to unban 😃 any user.\n\nUsage:\n\n`/unban_user user_id`\n\nEg: `/unban_user 1234567`\n This will unban user with id `1234567`.",
            quote=True,
        )
        return

    try:
        user_id = int(m.command[1])
        unban_log_text = f"Unbanning user 🤪 {user_id}"

        try:
            await c.send_message(user_id, f"Your ban was lifted!")
            unban_log_text += "\n\n✅ تم إخطار المستخدم بنجاح! ✅"
        except BaseException:
            traceback.print_exc()
            unban_log_text += (
                f"\n\n⚠️ فشل إشعار المستخدم! ⚠️\n\n`{traceback.format_exc()}`"
            )
        await db.remove_ban(user_id)
        print(unban_log_text)
        await m.reply_text(unban_log_text, quote=True)
    except BaseException:
        traceback.print_exc()
        await m.reply_text(
            f"⚠️ Error occoured ⚠️! Traceback given below\n\n`{traceback.format_exc()}`",
            quote=True,
        )


@Bot.on_message(filters.private & filters.command("banned_users"))
async def _banned_usrs(c, m):
    if m.from_user.id not in AUTH_USERS:
        await m.delete()
        return
    all_banned_users = await db.get_all_banned_users()
    banned_usr_count = 0
    text = ""
    async for banned_user in all_banned_users:
        user_id = banned_user["id"]
        ban_duration = banned_user["ban_status"]["ban_duration"]
        banned_on = banned_user["ban_status"]["banned_on"]
        ban_reason = banned_user["ban_status"]["ban_reason"]
        banned_usr_count += 1
        text += f"> **User_id**: `{user_id}`, **مدة الحظر**: `{ban_duration}`, **محظور على**: `{banned_on}`, **Reason**: `{ban_reason}`\n\n"
    reply_text = f"إجمالي المستخدم (المستخدمين) المحظورين 🤭: `{banned_usr_count}`\n\n{text}"
    if len(reply_text) > 4096:
        with open("banned-users.txt", "w") as f:
            f.write(reply_text)
        await m.reply_document("banned-users.txt", True)
        os.remove("banned-users.txt")
        return
    await m.reply_text(reply_text, True)


@Bot.on_callback_query()
async def callback_handlers(bot: Client, cb: CallbackQuery):
    user_id = cb.from_user.id
    if cb.data == "notifon":
        notif = await db.get_notif(cb.from_user.id)
        if notif is True:
            await db.set_notif(user_id, notif=False)
        else:
            await db.set_notif(user_id, notif=True)
        await cb.message.edit(
            f"`هنا يمكنك ضبط إعداداتك:`\n\nتم إعداد الإشعارات بنجاح إلى **{await db.get_notif(user_id)}**",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"إعلام  {'🔔' if ((await db.get_notif(user_id)) is True) else '🔕'}",
                            callback_data="notifon",
                        )
                    ],
                    [InlineKeyboardButton("❎", callback_data="closeMeh")],
                ]
            ),
        )
        await cb.answer(
            f"تم إعداد الإشعارات بنجاح إلى {await db.get_notif(user_id)}"
        )
    else:
        await cb.message.delete(True)


Bot.run()
