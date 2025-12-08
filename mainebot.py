import json
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes


ADVENT_FILE = "advent_messages.json"
ADMIN_ID = 435439281  # Replace with your Telegram user ID

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

async def get_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    day = datetime.now().day
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

if __name__ == "__main__":
    app = ApplicationBuilder().token("8455371476:AAHwh6cxPD6EO1SvZgIMNv5_moUhXK3s-KE").build()
    app.add_handler(CommandHandler("day", get_day))
    app.add_handler(CommandHandler("update_day", update_message))
    app.run_polling()
