import json
import os
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from config import JSON_FILE
from data import load_data, save_data
from trainings import get_next_week_trainings
WEEKDAYS = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]

VOTES_FILE = "training_votes.json"
DEFAULT_VOTES_STRUCTURE = {"votes": {}}
VOTES_LIMIT = 14;


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
    user_id = str(update.message.from_user.id)
    user_data = load_data(JSON_FILE)

    if user_id not in user_data or "team" not in user_data[user_id]:
        await update.message.reply_text("Будь ласка, завершіть реєстрацію перед голосуванням.")
        return

    team = user_data[user_id]["team"]
    today = datetime.today().date()

    trainings = get_next_week_trainings(team)
    filtered = []

    for idx, training in enumerate(trainings):
        start_voting = training.get("start_voting")
        end_voting = training.get("end_voting")

        if training["type"] == "one-time":
            try:
                start_date = datetime.strptime(start_voting, "%d.%m.%Y").date()
                end_date = datetime.strptime(end_voting, "%d.%m.%Y").date()
            except:
                continue
            if start_date <= today <= end_date:
                training_id = f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"
                filtered.append((idx, training_id, training))
        else:
            if not isinstance(start_voting, int) or not isinstance(end_voting, int):
                continue
            if start_voting <= today.weekday() <= end_voting:
                training_id = f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"
                filtered.append((idx, training_id, training))

    if not filtered:
        await update.message.reply_text("Наразі немає тренувань для голосування.")
        return

    keyboard = [
        [InlineKeyboardButton(
            f"{t['date'].strftime('%d.%m.%Y') if t['type'] == 'one-time' else WEEKDAYS[t['date'].weekday()]} {t['start_hour']:02d}:{t['start_min']:02d}",
            callback_data=f"training_vote_{i}"
        )] for i, tid, t in filtered
    ]
    context.user_data["vote_options"] = filtered

    await update.message.reply_text("Оберіть тренування для голосування:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_training_vote_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    vote_options = context.user_data.get("vote_options")
    if not vote_options:
        await query.edit_message_text("Помилка: не знайдено тренувань.")
        return

    idx = int(query.data.replace("training_vote_", ""))
    try:
        _, training_id, training = vote_options[idx]
    except IndexError:
        await query.edit_message_text("Помилка: тренування не знайдено.")
        return

    today = datetime.today().date()
    if training["type"] == "one-time":
        start = datetime.strptime(training["start_voting"], "%d.%m.%Y").date()
        end = datetime.strptime(training["end_voting"], "%d.%m.%Y").date()
        if today < start or today > end:
            await query.edit_message_text("Голосування зараз недоступне для цього тренування.")
            return
    else:
        if not isinstance(training["start_voting"], int) or not isinstance(training["end_voting"], int):
            await query.edit_message_text("Невірні параметри голосування для регулярного тренування.")
            return
        if not (training["start_voting"] <= today.weekday() <= training["end_voting"]):
            await query.edit_message_text("Голосування зараз недоступне для цього регулярного тренування.")
            return

    context.user_data["active_vote"] = {"id": training_id, "data": training}

    keyboard = [
        [
            InlineKeyboardButton("✅ Так", callback_data=f"vote_yes_{user_id}"),
            InlineKeyboardButton("❌ Ні", callback_data=f"vote_no_{user_id}")
        ]
    ]

    date_label = training['date'].strftime('%d.%m.%Y') if training['type'] == 'one-time' else WEEKDAYS[
        training['date'].weekday()]

    await query.edit_message_text(
        f"Тренування {date_label} о {training['start_hour']:02d}:{training['start_min']:02d}. Ви будете?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    vote = data[1]  # yes, no
    user_id = data[2]

    user_data = load_data(JSON_FILE)
    user_name = user_data.get(user_id, {}).get("name", "Невідомий користувач")
    vote_context = context.user_data.get("active_vote")

    if not vote_context:
        await query.edit_message_text("Помилка: неможливо визначити тренування для голосування.")
        return

    training_id = vote_context["id"]
    votes = load_votes()

    if training_id not in votes["votes"]:
        votes["votes"][training_id] = {}

    # Count current "yes" votes
    current_yes_votes = sum(1 for v in votes["votes"][training_id].values() if v["vote"] == "yes")

    # If already 14 people voted "yes", prevent more
    if vote == "yes" and user_id not in votes["votes"][training_id] and current_yes_votes >= VOTES_LIMIT:
        await query.edit_message_text("⚠️ Досягнуто максимум голосів 'так'. Ви не можете проголосувати.")
        return

    # Update the user's vote
    votes["votes"][training_id][user_id] = {"name": user_name, "vote": vote}
    save_votes(votes)

    await query.edit_message_text(f"Ваш голос: {vote.upper()} записано!")



async def view_votes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    votes = load_votes()
    if not votes["votes"]:
        await update.message.reply_text("Ще ніхто не голосував.")
        return

    context.user_data["view_votes_options"] = list(votes["votes"].keys())

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


def format_training_id(tid: str) -> str:
    if tid.startswith("Понеділок") or tid.startswith("const_"):
        try:
            if tid.startswith("const_"):
                parts = tid.split("_")
                weekday_index = int(parts[1])
                time_str = parts[2]
                return f"{WEEKDAYS[weekday_index]} о {time_str} (регулярне)"
            return tid
        except:
            return tid
    else:
        try:
            return f"{tid[:10]} о {tid[11:]}"
        except:
            return tid

async def handle_view_votes_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
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




