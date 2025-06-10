import asyncio
from datetime import datetime
from data import load_data
from telegram.ext import Application
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

REGISTRATION_FILE = "users"
ONE_TIME_TRAININGS_FILE = "one_time_trainings"
CONSTANT_TRAININGS_FILE = "constant_trainings"
VOTES_FILE = "votes"
WEEKDAYS = ['понеділок', 'вівторок', 'середу', 'четвер', "п'ятницю", 'суботу', 'неділю']
VOTES_LIMIT = 14


def generate_training_id(training, training_type):
    """
    Генерує унікальний ідентифікатор для тренування
    Формат для разових тренувань: DD.MM.YYYY_HH:MM
    Формат для постійних тренувань: const_WEEKDAY_HH:MM
    """
    if training_type == "one-time":
        return f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"
    else:
        return f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"


async def start_voting(app: Application):
    users = load_data(REGISTRATION_FILE)
    today = datetime.today().date()
    weekday = today.weekday()

    one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE, {})
    constant_trainings = load_data(CONSTANT_TRAININGS_FILE, {})

    for training_id, training in one_time_trainings.items():
        if training.get("start_voting") == today.strftime("%d.%m.%Y"):
            await open_training_voting(app, training, training_id, users, "one-time")
    for training_id, training in constant_trainings.items():
        if training.get("start_voting") == weekday:
            await open_training_voting(app, training, training_id, users, "constant")


async def check_voting_and_notify(app: Application):
    from datetime import datetime, timedelta

    users = load_data(REGISTRATION_FILE)
    today = datetime.today().date()

    one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE, {})
    constant_trainings = load_data(CONSTANT_TRAININGS_FILE, {})
    votes_data = load_data(VOTES_FILE, {"votes": {}})

    for training_id, training in one_time_trainings.items():
        try:
            training_date = datetime.strptime(training["date"], "%d.%m.%Y").date()
        except Exception:
            continue

        if (training_date - today).days == 2:
            await send_voting_reminder(app, training, training_id, users, votes_data, "one-time")

    for training_id, training in constant_trainings.items():
        if "weekday" not in training:
            continue

        training_weekday = training["weekday"]
        training_time = datetime(
            year=today.year, month=today.month, day=today.day,
            hour=training["start_hour"], minute=training["start_min"]
        )
        # Find the date of the next occurrence of the training weekday
        days_ahead = (training_weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        training_date = today + timedelta(days=days_ahead)

        if (training_date - today).days == 2:
            await send_voting_reminder(app, training, training_id, users, votes_data, "constant")


async def open_training_voting(app, training, training_id, users, training_type):
    vote_id = generate_training_id(training, training_type)

    if training_type == "one-time":
        date_str = training['date']
    else:
        date_str = WEEKDAYS[training['weekday']]

    message = (
        f"🗳 Почалося голосування!\n"
        f"Тренування {'в ' if training_type == 'constant' else ''}{date_str} "
        f"з {training['start_hour']:02d}:{training['start_min']:02d} "
        f"до {training['end_hour']:02d}:{training['end_min']:02d}."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Так", callback_data=f"vote_yes_{vote_id}"),
            InlineKeyboardButton("❌ Ні", callback_data=f"vote_no_{vote_id}")
        ]
    ])

    for uid, info in users.items():
        if training.get("team") in [info.get("team"), "Both"]:
            try:
                await app.bot.send_message(
                    chat_id=int(uid),
                    text=message,
                    reply_markup=keyboard
                )
            except Exception as e:
                print(f"❌ {training_type.upper()}: Помилка надсилання до {uid}: {e}")


async def send_voting_reminder(app, training, training_id, users, votes_data, training_type):
    """
    Надсилає нагадування про голосування тим, хто ще не проголосував
    """
    vote_id = generate_training_id(training, training_type)

    if training_type == "one-time":
        date_str = training['date']
    else:
        date_str = WEEKDAYS[training['weekday']]

    votes = votes_data.get("votes", {}).get(vote_id, {})
    voted_users = set(str(uid) for uid in votes.keys())

    message = (
        f"⏰ Нагадування про голосування!\n"
        f"Відбудеться тренування "
        f"{'в ' if training_type == 'constant' else ''}{date_str} "
        f"з {training['start_hour']:02d}:{training['start_min']:02d} "
        f"до {training['end_hour']:02d}:{training['end_min']:02d}.\n"
        f"Будь ласка, проголосуйте!"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Так", callback_data=f"vote_yes_{vote_id}"),
            InlineKeyboardButton("❌ Ні", callback_data=f"vote_no_{vote_id}")
        ]
    ])
    training_team = training.get("team")
    for uid, info in users.items():
        # Надсилаємо нагадування тільки тим, хто ще не проголосував
        if (training_team in [info.get("team"), "Both"]) and (str(uid) not in voted_users):
            try:
                await app.bot.send_message(
                    chat_id=int(uid),
                    text=message,
                    reply_markup=keyboard
                )
            except Exception as e:
                print(f"❌ REMINDER: Помилка надсилання до {uid}: {e}")
