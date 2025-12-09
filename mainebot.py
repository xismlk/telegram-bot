import json
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

ADVENT_FILE = "advent_messages.json"
ADMIN_ID = 435439281
USER_ID = 649982388
AUTHORISED_IDS = {ADMIN_ID, USER_ID}

# Store advent messages
def load_messages():
    try:
        with open(ADVENT_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_messages(messages):
    with open(ADVENT_FILE, "w") as f:
        json.dump(messages, f)

advent_messages = load_messages()

# Store user timezones
user_timezones = {}  # {user_id: "Asia/Singapore"}

# --- Commands ---
async def get_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    tz_name = user_timezones.get(user_id, "UTC")
    now = datetime.now(ZoneInfo(tz_name))
    day = now.day

    if str(day) in advent_messages:
        await update.message.reply_text(f"Day {day}: {advent_messages[str(day)]}")
    else:
        await update.message.reply_text(f"No message set for day {day}")

async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /update_day <day> <message>")
        return

    try:
        day = int(context.args[0])
        if day < 1 or day > 25:
            await update.message.reply_text("Day must be between 1 and 25")
            return
        message = " ".join(context.args[1:])
        advent_messages[str(day)] = message
        save_messages(advent_messages)
        await update.message.reply_text(f"✅ Day {day} updated!")
    except ValueError:
        await update.message.reply_text("First argument must be a number")

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow user to set their timezone, e.g. /set_timezone Asia/Singapore"""
    if not context.args:
        await update.message.reply_text("Usage: /set_timezone <Region/City>")
        return

    tz_name = context.args[0]
    try:
        ZoneInfo(tz_name)  # validate
        user_id = update.effective_user.id
        user_timezones[user_id] = tz_name
        await update.message.reply_text(f"✅ Timezone set to {tz_name}")

        # Schedule midnight job for this user
        job_queue = context.application.job_queue
        job_queue.run_daily(
            send_midnight_message,
            time=time(0, 0),  # midnight
            chat_id=user_id,
            name=f"midnight_{user_id}",
            tz=ZoneInfo(tz_name)
        )
        await update.message.reply_text("Midnight advent message scheduled!")
    except Exception:
        await update.message.reply_text("Invalid timezone. Example: Asia/Singapore")

# --- Job ---
async def send_midnight_message(context: ContextTypes.DEFAULT_TYPE):
    """Send advent message at midnight in user's timezone"""
    user_id = context.job.chat_id
    tz_name = user_timezones.get(user_id, "UTC")
    now = datetime.now(ZoneInfo(tz_name))
    day = now.day

    if str(day) in advent_messages:
        await context.bot.send_message(user_id, f"🎄 Day {day}: {advent_messages[str(day)]}")
    else:
        await context.bot.send_message(user_id, f"No message set for day {day}")

# --- Main ---
if __name__ == "__main__":
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables.")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("day", get_day))
    app.add_handler(CommandHandler("update_day", update_message))
    app.add_handler(CommandHandler("set_timezone", set_timezone))

    app.run_polling()
