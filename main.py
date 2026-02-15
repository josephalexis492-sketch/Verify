import os
import asyncio
import asyncio
import logging
import os
import random
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("8237376549:AAGd5ldO4SIHnIaPr6J7AdhUKIaM_-wd0G8")
OWNER_ID = int(os.getenv("6548935235", "0"))
VERIFY_TIMEOUT = 60  # seconds before auto kick
RAID_LIMIT = 5       # users within 10 sec triggers raid alert

logging.basicConfig(level=logging.INFO)

verification_data = {}
join_tracker = []

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "🤖 Advanced Verification Bot Online\n\n"
            "Add me to a group and give me admin with restrict permission."
        )

# ================= NEW MEMBER =================
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        chat_id = update.effective_chat.id
        user_id = member.id

        # Anti-raid tracker
        join_tracker.append(datetime.now())
        join_tracker[:] = [t for t in join_tracker if datetime.now() - t < timedelta(seconds=10)]

        if len(join_tracker) >= RAID_LIMIT:
            await context.bot.send_message(
                OWNER_ID,
                "🚨 RAID ALERT: Multiple users joined quickly!"
            )

        # Restrict user
        await context.bot.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions(can_send_messages=False)
        )

        # Generate question
        a = random.randint(1, 15)
        b = random.randint(1, 15)
        answer = a + b

        verification_data[user_id] = {
            "answer": answer,
            "chat_id": chat_id,
            "join_time": datetime.now()
        }

        keyboard = [
            [
                InlineKeyboardButton(str(answer), callback_data=f"verify_{user_id}_{answer}"),
                InlineKeyboardButton(str(answer+2), callback_data=f"verify_{user_id}_{answer+2}")
            ]
        ]

        await update.message.reply_text(
            f"👋 Welcome {member.first_name}\n\n"
            f"Solve to verify:\n\n"
            f"{a} + {b} = ?\n\n"
            f"You have {VERIFY_TIMEOUT} seconds.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Start timeout task
        asyncio.create_task(verify_timeout(context, user_id))

# ================= TIMEOUT =================
async def verify_timeout(context, user_id):
    await asyncio.sleep(VERIFY_TIMEOUT)

    if user_id in verification_data:
        data = verification_data[user_id]
        chat_id = data["chat_id"]

        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)

            await context.bot.send_message(
                chat_id,
                f"❌ User <code>{user_id}</code> failed verification and was removed.",
                parse_mode="HTML"
            )

            await context.bot.send_message(
                OWNER_ID,
                f"❌ User {user_id} auto-kicked (failed verification)."
            )

        except Exception as e:
            logging.error(e)

        verification_data.pop(user_id, None)

# ================= BUTTON VERIFY =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    user_id = int(data[1])
    chosen = int(data[2])

    if query.from_user.id != user_id:
        await query.answer("❌ Not your verification!", show_alert=True)
        return

    correct = verification_data.get(user_id, {}).get("answer")

    if chosen == correct:
        chat_id = verification_data[user_id]["chat_id"]

        await context.bot.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )

        await query.edit_message_text("✅ VERIFIED SUCCESSFULLY!")

        await context.bot.send_message(
            OWNER_ID,
            f"✅ User {user_id} verified successfully."
        )

        verification_data.pop(user_id, None)

    else:
        await query.answer("❌ Wrong answer!", show_alert=True)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))

    print("Advanced Verifier Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()