import json
import os
import random
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters

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

# Ensure required tracking keys exist in settings
if "timezones" not in settings:
    settings["timezones"] = {}

if "decide_history" not in settings:
    settings["decide_history"] = []

if "date_ideas" not in settings:
    settings["date_ideas"] = []

if "completed_dates" not in settings:
    settings["completed_dates"] = []

# Convert string keys back to int for runtime use
user_timezones = {int(k): v for k, v in settings["timezones"].items()}

# --- Original Commands ---
async def get_daily_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gets the message for the current date, with a countdown."""
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS:
        await update.effective_message.reply_text("You are not authorized! ❌")
        return

    tz_name = user_timezones.get(user_id, "UTC")
    now = datetime.now(ZoneInfo(tz_name))
    today_str = now.strftime("%Y-%m-%d") 
    formatted_date = now.strftime("%B %d, %Y") 

    countdown_text = ""
    end_date_str = settings.get("ldr_end_date")
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        today_date = now.date()
        days_left = (end_date - today_date).days

        if days_left > 0:
            countdown_text = f"⏳ **{days_left} days remaining until I see you!** 🧸\n"
        elif days_left == 0:
            countdown_text = f"🎉 **IT'S TODAY! YAY! It's finally over!** 🎉\n"
        else:
            countdown_text = f"💕 **No more LDR! It's been {-days_left} days since we reunited!**\n"

    header = f"{countdown_text} Today is: {formatted_date}\n\n"

    if today_str in daily_messages:
        await update.effective_message.reply_text(f"{header} 💌 {daily_messages[today_str]}", parse_mode='Markdown')
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

    try:
        datetime.strptime(context.args[0], "%Y-%m-%d")
        date_str = context.args[0]
        message = " ".join(context.args[1:])
        if not message:
            await update.effective_message.reply_text("You forgot to include the message!")
            return
    except ValueError:
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
        datetime.strptime(date_str, "%Y-%m-%d") 
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
    
    try:
        pretty_date = datetime.strptime(date_key, "%Y-%m-%d").strftime("%B %d, %Y")
    except:
        pretty_date = date_key

    await update.effective_message.reply_text(f"🎁 Random Memory from {pretty_date}:\n\n{msg}")

# --- Date Night Ideas Feature ---

def get_idea_emoji(idea_text: str) -> str:
    """Scans the date idea text for keywords and returns a matching emoji."""
    text = idea_text.lower()

    emoji_rules = {
        ("brunch", "breakfast", "coffee", "cafe", "tea"): "☕",
        ("lunch", "dinner", "food", "eat", "supper", "restaurant"): "🍳",
        ("movie", "cinema", "film", "netflix", "disney", "watch"): "🎬",
        ("shopping", "shop"): "🛍️",
        ("bbt", "chagee", "chicha", "tarik", "drink"): "🧋",
        ("dessert", "cake","ice cream", "cookie", "brownie"): "🍰"
    }

    for keywords, emoji in emoji_rules.items():
        if any(word in text for word in keywords):
            return emoji

    return "🦖"  # Default fallback emoji

async def add_date_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds a new date idea to the list with automatic keyword-based emojis."""
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS:
        return

    raw_idea = " ".join(context.args).strip()
    if not raw_idea:
        await update.effective_message.reply_text(
            "Usage: /add_date <your date idea>\nExample: /add_date brunch at sip sip"
        )
        return

    emoji = get_idea_emoji(raw_idea)
    formatted_idea = f"{emoji} {raw_idea}"

    added_by = update.effective_user.first_name
    entry = {
        "idea": formatted_idea,
        "added_by": added_by,
        "date_added": datetime.now().strftime("%Y-%m-%d"),
    }

    settings["date_ideas"].append(entry)
    save_json(SETTINGS_FILE, settings)

    await update.effective_message.reply_text(
        f"💡 Added to Date Night Ideas:\n{formatted_idea} (by {added_by})"
    )

async def list_date_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays all active date night ideas."""
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS: return

    ideas = settings.get("date_ideas", [])
    if not ideas:
        await update.effective_message.reply_text("No date ideas saved yet! Use /add_date to add one. 🕯️")
        return

    lines = ["🕯️ *Shared Date Night Ideas* 🕯️\n"]
    for idx, item in enumerate(ideas, 1):
        added_by = item.get('added_by', 'Someone')
        # Clean text formatting to prevent Markdown parser crashes
        lines.append(f"{idx}. {item['idea']} (added by {added_by})")

    lines.append("\n🎲 Use /random_date to pick one at random!")
    lines.append("🎉 Use /done_date <number> to mark an idea as completed.")
    lines.append("🏆 Use /past_dates to view your completed memories archive.")
    
    # Send without parse_mode to guarantee delivery regardless of special characters in user entries
    await update.effective_message.reply_text("\n".join(lines))
    
async def random_date_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Picks a random date idea from the list."""
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS: return

    ideas = settings.get("date_ideas", [])
    if not ideas:
        await update.effective_message.reply_text("No date ideas saved yet! Add some with /add_date 🎟️")
        return

    chosen = random.choice(ideas)
    msg = f"🎟️ **Random Date Pick:**\n\n✨ {chosen['idea']}\n*(Added by {chosen.get('added_by', 'Someone')})*"
    await update.effective_message.reply_text(msg, parse_mode="Markdown")

async def complete_date_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Moves a date idea from the active list into the completed archive."""
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS: return

    ideas = settings.get("date_ideas", [])
    if not ideas:
        await update.effective_message.reply_text("The date ideas list is empty! 🕯️")
        return

    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("Usage: /done_date <number>\nExample: /done_date 2")
        return

    index = int(context.args[0]) - 1

    if 0 <= index < len(ideas):
        completed_item = ideas.pop(index)
        completed_item["completed_by"] = update.effective_user.first_name
        completed_item["completed_date"] = datetime.now().strftime("%Y-%m-%d")

        settings["completed_dates"].append(completed_item)
        save_json(SETTINGS_FILE, settings)

        await update.effective_message.reply_text(
            f"🎉 Marked as completed: \"{completed_item['idea']}\"!\nSaved to your memories history. 💕",
            parse_mode="Markdown"
        )
    else:
        await update.effective_message.reply_text(f"❌ Invalid number. Pick a number between 1 and {len(ideas)}.")

async def list_completed_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays all archived/completed date ideas."""
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS: return

    archive = settings.get("completed_dates", [])
    if not archive:
        await update.effective_message.reply_text("No completed dates in your archive yet! Keep going! 💖")
        return

    lines = ["🏆 **Completed Dates Archive** 🏆\n"]
    for idx, item in enumerate(archive, 1):
        completed_date = item.get('completed_date', 'N/A')
        completed_by = item.get('completed_by', 'Someone')
        lines.append(f"{idx}. {item['idea']}\n   └ Done on {completed_date} by {completed_by}")

    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")

# --- Arbitrator Features ---

async def decide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates two interactive card buttons to settle a split choice."""
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS: return

    user_input = " ".join(context.args)
    match = re.search(r'(?:"([^"]+)"|(.+?))\s+vs\s+(?:"([^"]+)"|(.+))', user_input, re.IGNORECASE)
    
    if not match:
        await update.effective_message.reply_text('Format it like this:\n/decide "Sushi" vs "Burgers"\nor simply:\n/decide Sushi vs Burgers')
        return

    groups = match.groups()
    opt1 = (groups[0] or groups[1]).strip()
    opt2 = (groups[2] or groups[3]).strip()

    msg = await update.effective_message.reply_text("The choice is locked in. Flip a card to reveal the winner...")
    
    context.bot_data[f"decide_{msg.message_id}"] = [opt1, opt2]

    keyboard = [
        [
            InlineKeyboardButton("🃏 1", callback_data=f"flip_1_{msg.message_id}"),
            InlineKeyboardButton("🃏 2", callback_data=f"flip_2_{msg.message_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await msg.edit_reply_markup(reply_markup)

async def card_flip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the card selection button press, logs the result, and displays the outcome."""
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split("_")
    chosen_card = data_parts[1]
    msg_id = data_parts[2]
    game_key = f"decide_{msg_id}"
    
    if game_key in context.bot_data:
        opt1, opt2 = context.bot_data[game_key]
        winner = random.choice([opt1, opt2])
        flipper = query.from_user.first_name
        
        history_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": flipper,
            "opt1": opt1,
            "opt2": opt2,
            "winner": winner
        }
        settings["decide_history"].append(history_entry)
        save_json(SETTINGS_FILE, settings)
        
        new_text = f"🃏 **Card {chosen_card}** was flipped by {flipper}!\n\n🏆 **Winner:** {winner}"
        await query.edit_message_text(text=new_text, parse_mode="Markdown")
        
        del context.bot_data[game_key]
    else:
        await query.edit_message_text(text="Session expired or already flipped!")

async def get_tally(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Compiles and prints total historical usage analytics for the arbitrator."""
    user_id = update.effective_user.id
    if user_id not in AUTHORISED_IDS: return

    history = settings.get("decide_history", [])
    total = len(history)

    if total == 0:
        await update.effective_message.reply_text("No decisions have been made yet! 🃏")
        return

    user_flips = {}
    for entry in history:
        user_name = entry.get("user", "Unknown")
        user_flips[user_name] = user_flips.get(user_name, 0) + 1

    lines = [
        "📊 **Maine's Decisions** 📊\n",
        f"🔢 **Total Decisions Made:** {total}\n",
        "👤 **Card Flips Initiated:**"
    ]
    
    for name, count in user_flips.items():
        lines.append(f" └ {name}: {count} flips")

    lines.append("\n🕒 **Most Recent Choices:**")
    for entry in history[-3:]:
        lines.append(f" • {entry['opt1']} vs {entry['opt2']} → 🎉 **{entry['winner']}**")

    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")

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
            "you're the hottest girl ever baby😋",
            "i'm so proud of you my love😘",
            "you're my everything🌎",
            "you make the happiest ever🥰",
            "you're doing so well baby🏆",
            "i can't wait to touch you😋",
            "i'm proud of you forever🥰"
        ]
        await msg.reply_text(random.choice(compliments))

# --- Main ---
if __name__ == "__main__":
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    app = ApplicationBuilder().token(token).build()

    # Base Handlers
    app.add_handler(CommandHandler("daily", get_daily_message))
    app.add_handler(CommandHandler("set_msg", update_message))
    app.add_handler(CommandHandler("set_end", set_end_date))
    app.add_handler(CommandHandler("set_tz", set_timezone))
    app.add_handler(CommandHandler("surprise", surprise))
    
    # Date Night Ideas Handlers
    app.add_handler(CommandHandler("add_date", add_date_idea))
    app.add_handler(CommandHandler("date_list", list_date_ideas))
    app.add_handler(CommandHandler("random_date", random_date_idea))
    app.add_handler(CommandHandler("done_date", complete_date_idea))
    app.add_handler(CommandHandler("past_dates", list_completed_dates))

    # Arbitrator Handlers
    app.add_handler(CommandHandler("decide", decide))
    app.add_handler(CommandHandler("tally", get_tally))
    app.add_handler(CallbackQueryHandler(card_flip_callback, pattern=r"^flip_"))
    
    # Free Text Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, egg_handler))

    print("LDR Bot is running...")
    app.run_polling()
