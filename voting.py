import json
import os
import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from data import load_data, save_data
from trainings import get_next_week_trainings

WEEKDAYS = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]

# File paths for Google Drive storage
REGISTRATION_FILE = "user_data.json"
VOTES_FILE = "training_votes.json"
DEFAULT_VOTES_STRUCTURE = {"votes": {}}
VOTES_LIMIT = 14


def load_votes():
    """
    Load votes from Google Drive storage.
    Returns a dictionary with votes data or default structure if none exists.
    """
    votes_data = load_data(VOTES_FILE, DEFAULT_VOTES_STRUCTURE)
    if not isinstance(votes_data, dict) or "votes" not in votes_data:
        # If the data format is incorrect, reset to default
        votes_data = DEFAULT_VOTES_STRUCTURE
        save_votes(votes_data)
    return votes_data


def save_votes(votes):
    """
    Save votes to Google Drive storage.
    """
    save_data(votes, VOTES_FILE)


def generate_training_id(training):
    """
    Generate a consistent training ID for both vote_training command and notifier

    Args:
        training (dict): Training data dictionary

    Returns:
        str: Unique identifier for the training
    """
    if training["type"] == "one-time":
        date_str = training["date"] if isinstance(training["date"], str) else training["date"].strftime("%d.%m.%Y")
        return f"{date_str}_{training['start_hour']:02d}:{training['start_min']:02d}"
    else:
        return f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"


async def vote_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /vote_training command.
    Shows a list of available trainings for voting.
    """
    user_id = str(update.message.from_user.id)
    user_data = load_data(REGISTRATION_FILE)

    if user_id not in user_data or "team" not in user_data[user_id]:
        await update.message.reply_text("Будь ласка, завершіть реєстрацію перед голосуванням.")
        return

    team = user_data[user_id]["team"]
    today = datetime.datetime.today().date()
    current_hour = datetime.datetime.now().hour
    trainings = get_next_week_trainings(team)
    filtered = []

    for idx, training in enumerate(trainings):
        start_voting = training.get("start_voting")
        end_voting = training.get("end_voting")

        if training["type"] == "one-time":
            try:
                if isinstance(start_voting, str):
                    start_date = datetime.datetime.strptime(start_voting, "%d.%m.%Y").date()
                else:
                    start_date = start_voting

                if isinstance(end_voting, str):
                    end_date = datetime.datetime.strptime(end_voting, "%d.%m.%Y").date()
                else:
                    end_date = end_voting
            except Exception:
                continue

            if (start_date < today or (start_date == today and current_hour >= 18)) and today <= end_date:
                training_id = generate_training_id(training)
                filtered.append((idx, training_id, training))
        else:
            if not isinstance(start_voting, int) or not isinstance(end_voting, int):
                continue

            weekday_condition = (
                    start_voting < today.weekday() or
                    (start_voting == today.weekday() and current_hour >= 18)
            )

            if weekday_condition and today.weekday() <= end_voting:
                training_id = generate_training_id(training)
                filtered.append((idx, training_id, training))

    if not filtered:
        await update.message.reply_text("Наразі немає тренувань для голосування.")
        return

    keyboard = []
    for i, tid, t in filtered:
        if t["type"] == "one-time":
            date_str = t["date"].strftime("%d.%m.%Y") if isinstance(t["date"], datetime.date) else t["date"]
        else:
            date_str = WEEKDAYS[t["date"].weekday()]
        time_str = f"{t['start_hour']:02d}:{t['start_min']:02d}"
        keyboard.append([InlineKeyboardButton(f"{date_str} {time_str}", callback_data=f"training_vote_{i}")])

    context.user_data["vote_options"] = filtered

    await update.message.reply_text("Оберіть тренування для голосування:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_training_vote_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the selection of a training for voting.
    Shows the voting options (yes/no) for the selected training.
    """
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    idx = int(query.data.replace("training_vote_", ""))

    try:
        _, training_id, _ = context.user_data["vote_options"][idx]
    except (KeyError, IndexError):
        await query.edit_message_text("Помилка: тренування не знайдено.")
        return

    votes = load_votes()
    if training_id in votes["votes"]:
        yes_votes = sum(1 for v in votes["votes"][training_id].values() if v["vote"] == "yes")
        if yes_votes >= VOTES_LIMIT:
            await query.edit_message_text("⚠️ Досягнуто максимум голосів 'так'. Голосування закрито.")
            return

    keyboard = [
        [
            InlineKeyboardButton("✅ Так", callback_data=f"vote_yes_{training_id}"),
            InlineKeyboardButton("❌ Ні", callback_data=f"vote_no_{training_id}")
        ]
    ]
    training_info = format_training_id(training_id)

    current_vote = None
    if training_id in votes["votes"] and user_id in votes["votes"][training_id]:
        current_vote = votes["votes"][training_id][user_id]["vote"]

    message = f"Тренування: {training_info}\n"
    if current_vote:
        message += f"Ваш поточний голос: {'✅' if current_vote == 'yes' else '❌'}\n"
    message += "Чи будете на тренуванні?"

    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the vote (yes/no) for a training.
    Updates the vote in the Google Drive storage.
    """
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    vote = data[1]  # yes, no
    training_id = "_".join(data[2:])

    user_id = str(query.from_user.id)
    user_data = load_data(REGISTRATION_FILE)
    user_name = user_data.get(user_id, {}).get("name", "Невідомий користувач")

    votes = load_votes()

    if training_id not in votes["votes"]:
        votes["votes"][training_id] = {}

    current_yes_votes = sum(1 for v in votes["votes"][training_id].values() if v["vote"] == "yes")

    # Check if changing vote from "no" to "yes" when limit reached
    changing_to_yes = (
            vote == "yes" and
            user_id in votes["votes"][training_id] and
            votes["votes"][training_id][user_id]["vote"] == "no"
    )

    # If already 14 people voted "yes" and new vote is "yes", show warning
    if vote == "yes" and current_yes_votes >= VOTES_LIMIT and (
            user_id not in votes["votes"][training_id] or changing_to_yes):
        await query.edit_message_text("⚠️ Досягнуто максимум голосів 'так'. Ви не можете проголосувати.")
        return

    # Update user's vote
    votes["votes"][training_id][user_id] = {"name": user_name, "vote": vote}
    save_votes(votes)

    # Check if limit reached after update
    updated_yes_votes = sum(1 for v in votes["votes"][training_id].values() if v["vote"] == "yes")

    message = f"Ваш голос: {'✅' if vote == 'yes' else '❌'} записано!"

    if updated_yes_votes == VOTES_LIMIT:
        message += "\n⚠️ Досягнуто максимум учасників."

    await query.edit_message_text(message)


async def view_votes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /view_votes command.
    Shows a list of trainings with active voting.
    """
    votes = load_votes()
    if not votes["votes"]:
        await update.message.reply_text("Ще ніхто не голосував.")
        return

    today = datetime.datetime.today().date()
    active_votes = {}

    for vote_id in votes["votes"].keys():
        if is_vote_active(vote_id, today):
            active_votes[vote_id] = votes["votes"][vote_id]

    if not active_votes:
        await update.message.reply_text("Наразі немає активних голосувань.")
        return

    context.user_data["view_votes_options"] = list(active_votes.keys())

    keyboard = [
        [
            InlineKeyboardButton(
                f"{format_training_id(tid)}",
                callback_data=f"view_votes_{i}"
            )
        ]
        for i, tid in enumerate(context.user_data["view_votes_options"])
    ]

    await update.message.reply_text(
        "Оберіть тренування для перегляду результатів голосування:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def is_vote_active(vote_id, today):
    """
    Checks if a vote is currently active.

    Args:
        vote_id (str): Training ID
        today (datetime.date): Current date

    Returns:
        bool: True if the vote is active, False otherwise
    """
    # Always return True for simplicity - could be extended to check date ranges
    return True


def format_training_id(tid: str) -> str:
    """
    Formats a training ID for display.

    Args:
        tid (str): Training ID

    Returns:
        str: Formatted training description
    """
    if tid.startswith("const_"):
        try:
            parts = tid.split("_")
            weekday_index = int(parts[1])
            time_str = parts[2]
            return f"{WEEKDAYS[weekday_index]} о {time_str} (регулярне)"
        except:
            return tid
    else:
        try:
            return f"{tid[:10]} о {tid[11:]}"
        except:
            return tid


async def handle_view_votes_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the selection of a training for viewing votes.
    Shows the list of users who voted yes/no for the selected training.
    """
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("view_votes_", ""))
    vote_keys = context.user_data.get("view_votes_options")

    if not vote_keys or idx >= len(vote_keys):
        await query.edit_message_text("Помилка: не знайдено тренування.")
        return

    training_id = vote_keys[idx]
    votes = load_votes()
    voters = votes["votes"].get(training_id, {})

    yes_list = [v["name"] for v in voters.values() if v["vote"] == "yes"]
    no_list = [v["name"] for v in voters.values() if v["vote"] == "no"]

    label = format_training_id(training_id)

    message = f"📅 Тренування: {label}\n"
    message += "Буде:\n" + ("\n".join(yes_list) if yes_list else "Ніхто") + "\n"
    message += "Не буде:\n" + ("\n".join(no_list) if no_list else "Ніхто") + "\n"

    await query.edit_message_text(message)