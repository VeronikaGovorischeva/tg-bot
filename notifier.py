import asyncio
from datetime import datetime, timedelta
from data import load_data, save_data
from telegram.ext import Application
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

REGISTRATION_FILE = "users"
ONE_TIME_TRAININGS_FILE = "one_time_trainings"
CONSTANT_TRAININGS_FILE = "constant_trainings"
VOTES_FILE = "votes"
WEEKDAYS = ['понеділок', 'вівторок', 'середу', 'четвер', "п'ятницю", 'суботу', 'неділю']
VOTES_LIMIT = 14


def generate_training_id(training, training_type):
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
        if (training.get("start_voting") == today.strftime("%d.%m.%Y") and
                not training.get("voting_opened", False)):
            await open_training_voting(app, training, training_id, users, "one-time")
            training["voting_opened"] = True
            one_time_trainings[training_id] = training
            save_data(one_time_trainings, ONE_TIME_TRAININGS_FILE)
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

    start_time = f"{training['start_hour']:02d}:{training['start_min']:02d}"
    end_time = f"{training['end_hour']:02d}:{training['end_min']:02d}"

    # Coach info
    coach_str = " (З тренером)" if training.get("with_coach") else ""

    # Location
    location = training.get("location", "")
    location = "" if location and location.lower() == "наукма" else location
    loc_str = f"\n📍 {location}" if location else ""

    # Description
    description = training.get("description", "")
    desc_str = f"\nℹ️ {description}" if description else ""

    message = (
        f" Почалося голосування!\n"
        f"🏐 Тренування{'в ' if training_type == 'constant' else ' '}{date_str}{coach_str}\n"
        f"⏰ З {start_time} до {end_time}"
        f"{loc_str}"
        f"{desc_str}"
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
    vote_id = generate_training_id(training, training_type)

    if training_type == "one-time":
        date_str = training['date']
    else:
        date_str = WEEKDAYS[training['weekday']]

    start_time = f"{training['start_hour']:02d}:{training['start_min']:02d}"
    end_time = f"{training['end_hour']:02d}:{training['end_min']:02d}"

    votes = votes_data.get("votes", {}).get(vote_id, {})
    voted_users = set(str(uid) for uid in votes.keys())

    # Coach info
    coach_str = " (З тренером)" if training.get("with_coach") else ""

    # Location
    location = training.get("location", "")
    location = "" if location and location.lower() == "наукма" else location
    loc_str = f"\n📍 {location}" if location else ""

    # Description
    description = training.get("description", "")
    desc_str = f"\nℹ️ {description}" if description else ""

    message = (
        f" Нагадування про голосування!\n"
        f"Тренування {'в ' if training_type == 'constant' else ''}{date_str}{coach_str}\n"
        f"⏰ З {start_time} до {end_time}"
        f"{loc_str}"
        f"{desc_str}\n\n"
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


async def check_game_reminders(app: Application):
    users = load_data(REGISTRATION_FILE)
    games = load_data("games", {})
    game_votes = load_data("game_votes", {"votes": {}})
    today = datetime.today().date()
    tomorrow = today + timedelta(days=1)

    for game_id, game in games.items():
        try:
            game_date = datetime.strptime(game["date"], "%d.%m.%Y").date()

            if game_date == tomorrow:
                await send_game_reminder(app, game, game_id, users, game_votes)

        except Exception as e:
            print(f"❌ Помилка обробки гри {game_id}: {e}")
            continue


async def send_game_reminder(app, game, game_id, users, game_votes):
    type_names = {
        "friendly": "Товариська гра",
        "stolichka": "Столична ліга",
        "universiad": "Універсіада"
    }

    type_name = type_names.get(game.get('type'), game.get('type', 'Гра'))
    votes = game_votes.get("votes", {}).get(game_id, {})

    base_message = (
        f"🏆 Нагадування про гру завтра!\n\n"
        f"{type_name}\n"
        f"📅 {game['date']} о {game['time']}\n"
        f"🏆 Проти: {game['opponent']}\n"
        f"📍 Місце: {game['location']}\n"
        f"⏰ Прибуття до: {game['arrival_time']}\n\n"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Буду", callback_data=f"game_vote_yes_{game_id}"),
            InlineKeyboardButton("❌ Не буду", callback_data=f"game_vote_no_{game_id}")
        ]
    ])

    for uid, user_info in users.items():
        if game.get("team") not in [user_info.get("team"), "Both"]:
            continue

        user_vote = votes.get(str(uid))

        if user_vote is None:
            message = base_message + "❗ Ти ще не проголосував! Будь ласка, повідом чи будеш на грі:"
            reply_markup = keyboard

        elif user_vote.get("vote") == "yes":
            message = base_message + "✅ Ти записаний на гру. До зустрічі завтра!"
            reply_markup = None

        else:
            continue

        try:
            await app.bot.send_message(
                chat_id=int(uid),
                text=message,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"❌ GAME REMINDER: Помилка надсилання до {uid}: {e}")
