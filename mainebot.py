
import json
from json import JSONDecodeError
from datetime import datetime
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, filters

ADVENT_FILE = "advent_messages.json"
ADMIN_ID = 435439281   # Replace with your Telegram user ID
USER_ID = 649982388    # Additional authorized user for /day

def load_messages():
    try:
        with open(ADVENT_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, JSONDecodeError):
        return {}

def save_messages(messages):
    with open(ADVENT_FILE, "w") as f:
        json.dump(messages, f)

advent_messages = load_messages()

async def get_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    day = datetime.now().day
    msg = update.effective_message

    if str(day) in advent_messages:
        await msg.reply_text(f"Day {day}: {advent_messages[str(day)]}")
    else:
        await msg.reply_text(f"No message set for day {day}")

async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if len(context.args) < 2:
        await msg.reply_text("Usage: /update_day <day> <message>")
        return
    try:
        day = int(context.args[0])
        if day < 1 or day > 25:
            await msg.reply_text("Day must be between 1 and 25")
            return
        message = " ".join(context.args[1:])
        advent_messages[str(day)] = message
        save_messages(advent_messages)
        await msg.reply_text(f"✅ Day {day} updated!")
    except ValueError:
        await msg.reply_text("First argument must be a number")

if __name__ == "__main__":
    load_dotenv()  # harmless in production; useful locally
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables.")

    app = ApplicationBuilder().token(token).build()

    # Enforce authorization at the handler level
    app.add_handler(CommandHandler("day", get_day, filters=filters.User(user_id=[ADMIN_ID, USER_ID])))
    app.add_handler(CommandHandler("update_day", update_message, filters=filters.User(user_id=[ADMIN_ID])))

