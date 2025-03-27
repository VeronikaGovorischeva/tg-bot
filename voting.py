import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from config import JSON_FILE
from trainings import get_next_training
from data import load_data, save_data

VOTES_FILE = "training_votes.json"
DEFAULT_VOTES_STRUCTURE = {"votes": {}}


def load_votes():
    if not os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "w") as f:
            json.dump(DEFAULT_VOTES_STRUCTURE, f, indent=4)

    try:
        with open(VOTES_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict) or "votes" not in data:
                raise ValueError("Invalid JSON structure")
            return data
    except (json.JSONDecodeError, ValueError):
        save_data(DEFAULT_VOTES_STRUCTURE, VOTES_FILE)
        return DEFAULT_VOTES_STRUCTURE


def save_votes(votes):
    save_data(votes, VOTES_FILE)


async def vote_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = str(user.id)
    username = user.username or user.full_name

    training = get_next_training()
    if not training:
        await update.message.reply_text("Немає запланованих тренувань.")
        return

    date_str = training["date"].strftime("%d.%m.%Y")
    start_time = f"{training['start_hour']:02d}:{training['start_min']:02d}"
    end_time = f"{training['end_hour']:02d}:{training['end_min']:02d}"

    keyboard = [
        [InlineKeyboardButton("✅ Так", callback_data=f"vote_yes_{user_id}"),
         InlineKeyboardButton("❌ Ні", callback_data=f"vote_no_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Наступне тренування: {date_str} {start_time}-{end_time}\nВиберіть свою відповідь:",
        reply_markup=reply_markup
    )


async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    vote = data[1]  # yes, no
    user_id = data[2]

    user_data = load_data(JSON_FILE)
    user_name = user_data.get(user_id, {}).get("name", "Невідомий користувач")

    votes = load_votes()
    votes["votes"][user_id] = {"name": user_name, "vote": vote}
    save_votes(votes)

    await query.edit_message_text(f"Ваш голос: {vote.upper()} записано!")


async def view_votes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    votes = load_votes()
    if not votes["votes"]:
        await update.message.reply_text("Ще ніхто не проголосував.")
        return

    will_attend = [info["name"] for info in votes["votes"].values() if info["vote"] == "yes"]
    wont_attend = [info["name"] for info in votes["votes"].values() if info["vote"] == "no"]

    message = "📊 Результати голосування:\n"
    message += "Буде:\n" + "\n".join(will_attend) + "\n\n" if will_attend else "Буде: Ніхто\n\n"
    message += "Не буде:\n" + "\n".join(wont_attend) if wont_attend else "Не буде: Ніхто"

    await update.message.reply_text(message)


# Adding command handlers
def register_handlers(app):
    app.add_handler(CommandHandler("vote_training", vote_training))
    app.add_handler(CommandHandler("view_votes", view_votes))
    app.add_handler(CallbackQueryHandler(handle_vote, pattern=r"^vote_"))


