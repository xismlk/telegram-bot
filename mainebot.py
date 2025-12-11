
import json
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# --- Config ---
ADVENT_FILE = "advent_messages.json"
ADMIN_ID = 435439281
USER_ID = 649982388
AUTHORISED_IDS = {ADMIN_ID, USER_ID}

# Set to True if you want the love & compliment easter eggs to reply to anyone
# Set to False to reply only to AUTHORISED_IDS
REPLY_TO_ANYONE = False

# --- Storage: Advent messages ---
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

# --- Storage: User timezones ---
user_timezones = {}  # {user_id: "Asia/Singapore"}

# --- Commands ---
async def get_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS:
        await update.effective_message.reply_text("You are not authorized to use this command.")
        return

    tz_name = user_timezones.get(user_id, "UTC")
    now = datetime.now(ZoneInfo(tz_name))
    day = now.day

    if str(day) in advent_messages:
        await update.effective_message.reply_text(f"Day {day}: {advent_messages[str(day)]}")
    else:
        await update.effective_message.reply_text(f"No message set for day {day}")

async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.effective_message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await update.effective_message.reply_text("Usage: /update_day <day> <message>")
        return

    try:
        day = int(context.args[0])
        if day < 1 or day > 25:
            await update.effective_message.reply_text("Day must be between 1 and 25")
            return
        message = " ".join(context.args[1:])
        advent_messages[str(day)] = message
        save_messages(advent_messages)
        await update.effective_message.reply_text(f"✅ Day {day} updated!")
    except ValueError:
        await update.effective_message.reply_text("First argument must be a number")

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Usage: /set_timezone <Region/City>")
        return

    tz_name = context.args[0].strip()
    user_id = update.effective_user.id

    try:
        _ = ZoneInfo(tz_name)  # validate timezone
    except Exception:
        await update.effective_message.reply_text("❌ Invalid timezone. Example: Asia/Singapore")
        return

    user_timezones[user_id] = tz_name
    await update.effective_message.reply_text(f"✅ Timezone set to {tz_name}")

async def surprise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a random Advent message from the stored list (authorized users only)."""
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS:
        await update.effective_message.reply_text("You are not authorized to use this command.")
        return

    if not advent_messages:
        await update.effective_message.reply_text("No advent messages set yet. Use /update_day to add one.")
        return

    # Pick a random existing day key
    day_key = random.choice(list(advent_messages.keys()))
    msg = advent_messages[day_key]
    await update.effective_message.reply_text(f"🎁 Surprise Advent Message: Day {day_key}\n{msg}")

# --- Easter eggs / auto-replies ---
async def love_and_easter_eggs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-reply to fun triggers in plain text messages (non-commands)."""
    msg = update.effective_message
    user_id = update.effective_user.id

    # Respect the toggle: restrict replies to authorised IDs if REPLY_TO_ANYONE is False
    if not REPLY_TO_ANYONE and user_id not in AUTHORISED_IDS:
        return

    text = (msg.text or msg.caption or "").strip().lower()

    # Love reply
    if "i love you" in text:
        await msg.reply_text("i love you the most 🧸❤️")
        return

    # Compliment Easter egg
    if text == "compliment me":
        compliments = [
            "you're amazing bae!🏆 ",
            "you're the prettiest ever baby!😍 ",
            "you got this my love you're doing so well!😘 ",
            "you make my world ❤️🌎",
            "you're the greatest girlfriend, wife and partner ever in the whole universe my love💫",
            "your smile is so cute and adorable🥰",
            "you're the hottest sexiest girl ever baby😋",
        ]
        await msg.reply_text(random.choice(compliments))
        return

    # (Removed) hidden 'surprise' text triggers:
    # if text in {"surprise me", "gimme surprise", "random advent"}:
    #     ...

# --- Main ---
if __name__ == "__main__":
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables.")

    app = ApplicationBuilder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("day", get_day))
    app.add_handler(CommandHandler("update_day", update_message))
    app.add_handler(CommandHandler("set_timezone", set_timezone))
    app.add_handler(CommandHandler("surprise", surprise))

    # Message handler for love & easter eggs (non-command text)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, love_and_easter_eggs_handler))

    app.run_polling()
