import json
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# --- Config ---
MESSAGES_FILE = "daily_messages.json"
SETTINGS_FILE = "settings.json"
ADMIN_ID = 435439281
USER_ID = 649982388
AUTHORISED_IDS = {ADMIN_ID, USER_ID}

REPLY_TO_ANYONE = False

# --- Storage Logic ---
def load_json(filename, default_type=dict):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return default_type()

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# Initial Load
daily_messages = load_json(MESSAGES_FILE)
settings = load_json(SETTINGS_FILE)

# Ensure 'timezones' dictionary exists in settings
if "timezones" not in settings:
    settings["timezones"] = {}

# Convert string keys back to int for runtime use
user_timezones = {int(k): v for k, v in settings["timezones"].items()}

# --- Commands ---
async def get_daily_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gets the message for the current date, with a countdown."""
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS:
        await update.effective_message.reply_text("You are not authorized! ❌")
        return

    # Get today's date in user's timezone
    tz_name = user_timezones.get(user_id, "UTC")
    now = datetime.now(ZoneInfo(tz_name))
    today_str = now.strftime("%Y-%m-%d") # Format: 2023-10-24
    formatted_date = now.strftime("%B %d, %Y") # Format: October 24, 2023

    # Calculate Countdown
    countdown_text = ""
    end_date_str = settings.get("ldr_end_date")
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        today_date = now.date()
        days_left = (end_date - today_date).days

        if days_left > 0:
            countdown_text = f"⏳ **{days_left} days remaining until I see you!** ✈️\n"
        elif days_left == 0:
            countdown_text = f"🎉 **IT'S TODAY! YAY! It's is finally over!** 🎉\n"
        else:
            countdown_text = f"💕 **No more LDR! It's been {-days_left} days since we reunited!**\n"

    # Build Header
    header = f"{countdown_text}📅 Today is: {formatted_date}\n\n"

    # Fetch Message
    if today_str in daily_messages:
        await update.effective_message.reply_text(f"{header}❤️ {daily_messages[today_str]}", parse_mode='Markdown')
    else:
        await update.effective_message.reply_text(f"{header}No message set for today yet. 🥰", parse_mode='Markdown')

async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin sets a message. If no date is given, defaults to today's date."""
    if update.effective_user.id != ADMIN_ID:
        await update.effective_message.reply_text("Only the Admin can set messages! 🤫")
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /set_msg <message> OR /set_msg YYYY-MM-DD <message>")
        return

    # Check if the first word is a date (YYYY-MM-DD)
    try:
        # Test if it parses as a date
        datetime.strptime(context.args[0], "%Y-%m-%d")
        date_str = context.args[0]
        message = " ".join(context.args[1:])
        if not message:
            await update.effective_message.reply_text("You forgot to include the message!")
            return
    except ValueError:
        # If it's not a date, assume the whole text is for TODAY
        tz_name = user_timezones.get(update.effective_user.id, "UTC")
        now = datetime.now(ZoneInfo(tz_name))
        date_str = now.strftime("%Y-%m-%d")
        message = " ".join(context.args)

    daily_messages[date_str] = message
    save_json(MESSAGES_FILE, daily_messages)
    await update.effective_message.reply_text(f"✅ Message saved for {date_str}!")

async def set_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin sets the target end date for the LDR."""
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.effective_message.reply_text("Usage: /set_end YYYY-MM-DD (e.g., /set_end 2024-12-25)")
        return

    date_str = context.args[0]
    try:
        datetime.strptime(date_str, "%Y-%m-%d") # Validate format
        settings["ldr_end_date"] = date_str
        save_json(SETTINGS_FILE, settings)
        await update.effective_message.reply_text(f"✅ LDR End Date officially set to: {date_str}! The countdown begins.")
    except ValueError:
        await update.effective_message.reply_text("❌ Invalid format. Please use YYYY-MM-DD.")

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Usage: /set_tz Asia/Seoul")
        return

    tz_name = context.args[0].strip()
    user_id = update.effective_user.id

    try:
        ZoneInfo(tz_name)
        user_timezones[user_id] = tz_name
        
        # Save nested settings
        settings["timezones"][str(user_id)] = tz_name
        save_json(SETTINGS_FILE, settings)
        
        await update.effective_message.reply_text(f"✅ Your timezone is now: {tz_name}")
    except Exception:
        await update.effective_message.reply_text("❌ Invalid timezone. Use 'Asia/Seoul'.")

async def surprise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS: return

    if not daily_messages:
        await update.effective_message.reply_text("No messages found! 💬")
        return

    date_key, msg = random.choice(list(daily_messages.items()))
    
    # Try to make the date look pretty
    try:
        pretty_date = datetime.strptime(date_key, "%Y-%m-%d").strftime("%B %d, %Y")
    except:
        pretty_date = date_key

    await update.effective_message.reply_text(f"🎁 Random Memory from {pretty_date}:\n\n{msg}")

# --- Easter Eggs ---
async def egg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_id = update.effective_user.id
    if not REPLY_TO_ANYONE and user_id not in AUTHORISED_IDS: return

    text = (msg.text or "").strip().lower()

    if "i love you" in text:
        await msg.reply_text("i love you the most 🧸❤️")
    elif text == "compliment me":
        compliments = [
            "you're amazing bae!🏆",
            "you're the prettiest ever baby!😍",
            "you make my world ❤️🌎",
            "you're the hottest girl ever baby😋"
            "i'm so proud of you my love😘"
            "you're my everything🌎"
            "you make the happiest ever🥰"
        ]
        await msg.reply_text(random.choice(compliments))

# --- Main ---
if __name__ == "__main__":
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("daily", get_daily_message))
    app.add_handler(CommandHandler("set_msg", update_message))
    app.add_handler(CommandHandler("set_end", set_end_date))
    app.add_handler(CommandHandler("set_tz", set_timezone))
    app.add_handler(CommandHandler("surprise", surprise))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, egg_handler))

    print("LDR Bot is running...")
    app.run_polling()
