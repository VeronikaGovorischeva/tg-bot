from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import datetime
from config import TRAINING_SCHEDULE, JSON_FILE
import json
import pytz
from data import load_data, save_data
from validation import is_authorized

TYPE, TEAM, COACH, DATE, START, END, WEEKDAY, START_VOTING, END_VOTING = range(9)

# Path for storing one-time trainings
ONE_TIME_TRAININGS_FILE = "one_time_trainings.json"
CONSTANT_TRAININGS_FILE = "constant_trainings.json"


async def add_training(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("У вас немає дозволу на додавання тренувань.")
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton("Одноразове", callback_data="training_onetime"),
            InlineKeyboardButton("Постійне", callback_data="training_recurring"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Виберіть тип тренування:",
        reply_markup=reply_markup
    )

    return TYPE


async def training_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    training_type = query.data
    context.user_data['training_type'] = training_type

    keyboard = [
        [
            InlineKeyboardButton("Чоловіча", callback_data="training_team_male"),
            InlineKeyboardButton("Жіноча", callback_data="training_team_female"),
        ],
        [
            InlineKeyboardButton("Обидві команди", callback_data="training_team_both"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Для якої команди це тренування?",
        reply_markup=reply_markup
    )

    return TEAM


async def training_team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    team_data = query.data.replace("training_team_", "")
    if team_data == "male":
        team = "Male"
    elif team_data == "female":
        team = "Female"
    else:
        team = "Both"

    context.user_data['training_team'] = team

    keyboard = [
        [
            InlineKeyboardButton("Так", callback_data="training_coach_yes"),
            InlineKeyboardButton("Ні", callback_data="training_coach_no"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Це тренування з тренером?",
        reply_markup=reply_markup
    )

    return COACH


async def training_coach(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    with_coach = query.data == "training_coach_yes"
    context.user_data['with_coach'] = with_coach

    if context.user_data['training_type'] == "training_onetime":
        await query.edit_message_text(
            "Введіть дату тренування у форматі ДД.ММ.РРРР (наприклад, 25.03.2025)"
        )
        return DATE
    else:
        keyboard = [
            [InlineKeyboardButton("Понеділок", callback_data="weekday_0")],
            [InlineKeyboardButton("Вівторок", callback_data="weekday_1")],
            [InlineKeyboardButton("Середа", callback_data="weekday_2")],
            [InlineKeyboardButton("Четвер", callback_data="weekday_3")],
            [InlineKeyboardButton("П'ятниця", callback_data="weekday_4")],
            [InlineKeyboardButton("Субота", callback_data="weekday_5")],
            [InlineKeyboardButton("Неділя", callback_data="weekday_6")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Виберіть день тижня для регулярного тренування:",
            reply_markup=reply_markup
        )
        return WEEKDAY


async def training_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        date_text = update.message.text
        date_obj = datetime.datetime.strptime(date_text, "%d.%m.%Y").date()

        context.user_data['training_date'] = date_text

        await update.message.reply_text(
            "Введіть час початку тренування у форматі ГГ:ХХ (наприклад, 19:00)"
        )
        return START
    except ValueError:
        await update.message.reply_text(
            "Неправильний формат дати. Будь ласка, використовуйте формат ДД.ММ.РРРР (наприклад, 25.03.2025)"
        )
        return DATE


async def training_weekday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    weekday = int(query.data.replace("weekday_", ""))
    context.user_data['training_weekday'] = weekday

    await query.edit_message_text(
        "Введіть час початку тренування у форматі ГГ:ХХ (наприклад, 19:00)"
    )
    return START


async def training_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        time_text = update.message.text
        time_obj = datetime.datetime.strptime(time_text, "%H:%M").time()

        context.user_data['start_hour'] = time_obj.hour
        context.user_data['start_min'] = time_obj.minute

        await update.message.reply_text(
            "Введіть час закінчення тренування у форматі ГГ:ХХ (наприклад, 21:00)"
        )
        return END
    except ValueError:
        await update.message.reply_text(
            "Неправильний формат часу. Будь ласка, використовуйте формат ГГ:ХХ (наприклад, 19:00)"
        )
        return START


async def training_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        end_time_text = update.message.text
        end_time_obj = datetime.datetime.strptime(end_time_text, "%H:%M").time()

        context.user_data['end_hour'] = end_time_obj.hour
        context.user_data['end_min'] = end_time_obj.minute
        is_onetime = context.user_data['training_type'] == "training_onetime"
        team = context.user_data['training_team']
        with_coach = context.user_data['with_coach']
        start_hour = context.user_data['start_hour']
        start_min = context.user_data['start_min']
        end_hour = context.user_data['end_hour']
        end_min = context.user_data['end_min']
        if is_onetime:
            await update.message.reply_text("Введіть дату початку голосування (ДД.ММ.РРРР):")
            return START_VOTING
        else:
            keyboard = [[InlineKeyboardButton(day, callback_data=f"voting_day_{i}")]
                        for i, day in
                        enumerate(["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"])]
            await update.message.reply_text("Оберіть день тижня для початку голосування:",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
            return START_VOTING
    except ValueError:
        await update.message.reply_text(
            "Неправильний формат часу. Будь ласка, використовуйте формат ГГ:ХХ (наприклад, 21:00)"
        )
        return END
async def training_start_voting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data['training_type'] == "training_onetime":
        context.user_data['start_voting'] = update.message.text
        await update.message.reply_text("Введіть дату завершення голосування (ДД.ММ.РРРР):")
        return END_VOTING
    else:
        query = update.callback_query
        await query.answer()
        context.user_data['start_voting'] = int(query.data.replace("voting_day_", ""))
        keyboard = [[InlineKeyboardButton(day, callback_data=f"voting_end_day_{i}")]
                    for i, day in enumerate(["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"])]
        await query.edit_message_text("Оберіть день тижня для завершення голосування:", reply_markup=InlineKeyboardMarkup(keyboard))
        return END_VOTING

async def training_end_voting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    is_onetime = context.user_data['training_type'] == "training_onetime"

    if is_onetime:
        context.user_data['end_voting'] = update.message.text
    else:
        query = update.callback_query
        await query.answer()
        context.user_data['end_voting'] = int(query.data.replace("voting_end_day_", ""))

    is_onetime = context.user_data['training_type'] == "training_onetime"
    team = context.user_data['training_team']
    with_coach = context.user_data['with_coach']
    start_hour = context.user_data['start_hour']
    start_min = context.user_data['start_min']
    end_hour = context.user_data['end_hour']
    end_min = context.user_data['end_min']
    start_voting = context.user_data['start_voting']
    end_voting = context.user_data['end_voting']

    if is_onetime:
        date_str = context.user_data['training_date']
        one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE)

        new_training = {
            "date": date_str,
            "start_hour": start_hour,
            "start_min": start_min,
            "end_hour": end_hour,
            "end_min": end_min,
            "team": team,
            "with_coach": with_coach,
            "start_voting": start_voting,
            "end_voting": end_voting
        }
        last_id = list(one_time_trainings)[-1] if one_time_trainings else 0
        one_time_trainings[int(last_id) + 1] = new_training
        save_data(one_time_trainings, ONE_TIME_TRAININGS_FILE)
    else:
        constant_trainings = load_data(CONSTANT_TRAININGS_FILE)
        last_id = list(constant_trainings)[-1] if constant_trainings else 0
        weekday = context.user_data['training_weekday']
        new_training = {
            "weekday": weekday,
            "start_hour": start_hour,
            "start_min": start_min,
            "end_hour": end_hour,
            "end_min": end_min,
            "team": team,
            "with_coach": with_coach,
            "start_voting": start_voting,
            "end_voting": end_voting
        }
        constant_trainings[int(last_id) + 1] = new_training
        save_data(constant_trainings, CONSTANT_TRAININGS_FILE)

    if update.message:
        await update.message.reply_text("Тренування успішно збережено!")
    elif update.callback_query:
        await update.callback_query.message.reply_text("Тренування успішно збережено!")
    return ConversationHandler.END


def get_next_training(team=None):
    """
    Fetch the next training session, considering both one-time and recurring trainings.

    Returns:
        dict | None: A dictionary containing training details, or None if no training is found.
    """
    one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE, {})
    constant_trainings = load_data(CONSTANT_TRAININGS_FILE, {})

    now = datetime.datetime.now()
    current_date = now.date()
    current_time = now.time()
    current_weekday = now.weekday()

    all_trainings = []

    # Process constant trainings
    for training in constant_trainings.values():
        if not isinstance(training, dict) or training.get("team") not in [team, "Both", None]:
            continue

        training_weekday = training.get("weekday", -1)
        training_time = datetime.time(hour=training.get("start_hour", 0), minute=training.get("start_min", 0))

        if training_weekday == -1:
            continue

        days_until = (training_weekday - current_weekday) % 7
        if days_until == 0 and training_time <= current_time:
            days_until = 7

        next_date = current_date + datetime.timedelta(days=days_until)

        all_trainings.append({
            "date": next_date,
            "start_hour": training.get("start_hour", 0),
            "start_min": training.get("start_min", 0),
            "end_hour": training.get("end_hour", 0),
            "end_min": training.get("end_min", 0),
            "team": str(training.get("team", "Both")),
            "with_coach": bool(training.get("with_coach", False)),
            "type": "constant",
            "days_until": days_until
        })

    # Process one-time trainings
    for training in one_time_trainings.values():
        if not isinstance(training, dict) or training.get("team") not in [team, "Both", None]:
            continue

        try:
            training_date = datetime.datetime.strptime(training.get("date", ""), "%d.%m.%Y").date()
        except (ValueError, TypeError):
            continue

        if training_date < current_date:
            continue

        days_until = (training_date - current_date).days
        training_time = datetime.time(hour=training.get("start_hour", 0), minute=training.get("start_min", 0))
        if training_date == current_date and training_time <= current_time:
            continue

        all_trainings.append({
            "date": training_date,
            "start_hour": training.get("start_hour", 0),
            "start_min": training.get("start_min", 0),
            "end_hour": training.get("end_hour", 0),
            "end_min": training.get("end_min", 0),
            "team": str(training.get("team", "Both")),
            "with_coach": bool(training.get("with_coach", False)),
            "type": "one-time",
            "days_until": days_until
        })

    # Sort trainings by date and start time
    all_trainings.sort(key=lambda x: (x["date"], x["start_hour"], x["start_min"]))

    return all_trainings[0] if all_trainings else None

def get_next_week_trainings(team=None):
    from datetime import datetime, timedelta

    one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE, {})
    constant_trainings = load_data(CONSTANT_TRAININGS_FILE, {})

    now = datetime.now()
    current_date = now.date()
    current_time = now.time()
    current_weekday = now.weekday()

    end_date = current_date + timedelta(days=7)
    trainings = []

    # Constant trainings
    for training in constant_trainings.values():
        if training.get("team") not in [team, "Both", None]:
            continue
        training_weekday = training.get("weekday")
        if training_weekday is None:
            continue
        for i in range(1, 8):  # next 7 days
            training_date = current_date + timedelta(days=i)
            if training_date.weekday() == training_weekday:
                trainings.append({
                    "weekday": training_weekday,
                    "start_voting": training.get("start_voting"),
                    "end_voting": training.get("end_voting"),
                    "date": training_date,
                    "start_hour": training["start_hour"],
                    "start_min": training["start_min"],
                    "end_hour": training["end_hour"],
                    "end_min": training["end_min"],
                    "team": training["team"],
                    "with_coach": training["with_coach"],
                    "type": "constant"
                })

    # One-time trainings
    for training in one_time_trainings.values():
        if training.get("team") not in [team, "Both", None]:
            continue
        try:
            training_date = datetime.strptime(training["date"], "%d.%m.%Y").date()
        except Exception:
            continue
        if current_date <= training_date <= end_date:
            trainings.append({
                "start_voting": training.get("start_voting"),
                "end_voting": training.get("end_voting"),
                "date": training_date,
                "start_hour": training["start_hour"],
                "start_min": training["start_min"],
                "end_hour": training["end_hour"],
                "end_min": training["end_min"],
                "team": training["team"],
                "with_coach": training["with_coach"],
                "type": "one-time"
            })

    trainings.sort(key=lambda x: (x["date"], x["start_hour"], x["start_min"]))
    return trainings


async def week_trainings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = load_data(JSON_FILE)

    if user_id not in user_data or "team" not in user_data[user_id]:
        await update.message.reply_text("Будь ласка, завершіть реєстрацію.")
        return

    team = user_data[user_id]["team"]
    trainings = get_next_week_trainings(team)

    if not trainings:
        await update.message.reply_text("Немає тренувань у найближчі 7 днів.")
        return

    message = "📅 Тренування на тиждень:\n\n"
    weekday_names = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', "П'ятниця", 'Субота', 'Неділя']
    for t in trainings:
        date_str = t["date"].strftime("%d.%m.%Y")
        start = f"{t['start_hour']:02d}:{t['start_min']:02d}"
        end = f"{t['end_hour']:02d}:{t['end_min']:02d}"
        coach_str = " з тренером" if t["with_coach"] else ""
        team_str = "" if t["team"] == "Both" else f" ({'чоловіча' if t['team'] == 'Male' else 'жіноча'} команда)"
        day = weekday_names[t["date"].weekday()]
        message += f"• {day}, {date_str} з {start} до {end}{coach_str}{team_str} ({t['type']})\n"

    await update.message.reply_text(message)



# def get_next_training(team=None):
#     """
#     Get the next training session for a specified team from both constant and one-time trainings.
#
#     Args:
#         team (str): The team name ('Male' or 'Female')
#
#     Returns:
#         dict: Information about the next training session or None if no future trainings
#     """
#     # Load training data
#     with open('constant_trainings.json', 'r') as f:
#         constant_trainings = json.load(f)
#
#     with open('one_time_trainings.json', 'r') as f:
#         one_time_trainings = json.load(f)
#
#     # Get current date and time
#     now = datetime.datetime.now()
#     current_date = now.date()
#     current_time = now.time()
#     current_weekday = now.weekday()  # 0 is Monday, 6 is Sunday
#
#     # Calculate days until next occurrence of each constant training
#     next_constant_trainings = []
#     for training_id, training in constant_trainings.items():
#         if training["team"] != team:
#             continue
#
#         training_weekday = training["weekday"]
#         training_time = datetime.time(hour=training["start_hour"], minute=training["start_min"])
#
#         # Calculate days until next occurrence
#         days_until = (training_weekday - current_weekday) % 7
#
#         # If it's the same day, check if the training has already passed
#         if days_until == 0 and training_time <= current_time:
#             days_until = 7  # Move to next week
#
#         # Calculate the date of the next occurrence
#         next_date = current_date + datetime.timedelta(days=days_until)
#
#         next_constant_trainings.append({
#             "date": next_date,
#             "start_hour": training["start_hour"],
#             "start_min": training["start_min"],
#             "end_hour": training["end_hour"],
#             "end_min": training["end_min"],
#             "team": training["team"],
#             "with_coach": training["with_coach"],
#             "type": "constant"
#         })
#
#     # Filter and convert one-time trainings
#     next_one_time_trainings = []
#     for training_id, training in one_time_trainings.items():
#         if training["team"] != team:
#             continue
#
#         # Parse the date string (format: DD.MM.YYYY)
#         day, month, year = map(int, training["date"].split('.'))
#         training_date = datetime.date(year, month, day)
#
#         # Skip if the training is in the past
#         if training_date < current_date:
#             continue
#
#         # If it's today, check if the training has already passed
#         if training_date == current_date:
#             training_time = datetime.time(hour=training["start_hour"], minute=training["start_min"])
#             if training_time <= current_time:
#                 continue
#
#         # Check if end_hour is less than start_hour (invalid time)
#         if training["end_hour"] < training["start_hour"] or (
#                 training["end_hour"] == training["start_hour"] and training["end_min"] < training["start_min"]):
#             continue
#
#         next_one_time_trainings.append({
#             "date": training_date,
#             "start_hour": training["start_hour"],
#             "start_min": training["start_min"],
#             "end_hour": training["end_hour"],
#             "end_min": training["end_min"],
#             "team": training["team"],
#             "with_coach": training["with_coach"],
#             "type": "one-time"
#         })
#
#     # Combine and sort all trainings
#     all_trainings = next_constant_trainings + next_one_time_trainings
#
#     if not all_trainings:
#         return None
#
#     # Sort by date, then by start time
#     all_trainings.sort(key=lambda x: (
#         x["date"],
#         x["start_hour"],
#         x["start_min"]
#     ))
#
#     # Return the next training
#     next_training = all_trainings[0]
#
#     # Format the result
#     result = {
#         "date": next_training["date"].strftime("%d.%m.%Y"),
#         "start_time": f"{next_training['start_hour']:02d}:{next_training['start_min']:02d}",
#         "end_time": f"{next_training['end_hour']:02d}:{next_training['end_min']:02d}",
#         "team": next_training["team"],
#         "with_coach": next_training["with_coach"],
#         "type": next_training["type"]
#     }


async def next_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /next_training command, fetching and formatting the next training session.
    """
    user_id = str(update.message.from_user.id)
    user_data = load_data(JSON_FILE)

    if user_id not in user_data or "team" not in user_data[user_id]:
        await update.message.reply_text("Будь ласка, завершіть реєстрацію, щоб отримувати інформацію про тренування.")
        return

    team = user_data[user_id]["team"]
    training_info = get_next_training(team)

    if not training_info:
        await update.message.reply_text("Немає запланованих тренувань.")
        return

    # Formatting message
    date_str = training_info["date"].strftime("%d.%m.%Y")
    start_time = f"{training_info['start_hour']:02d}:{training_info['start_min']:02d}"
    end_time = f"{training_info['end_hour']:02d}:{training_info['end_min']:02d}"
    team_str = f" для {'чоловічої' if training_info['team'] == 'Male' else 'жіночої'} команди" if training_info[
                                                                                                      'team'] != "Both" else " для обох команд"
    coach_str = " з тренером" if training_info["with_coach"] else ""

    weekday_names = ['понеділок', 'вівторок', 'середу', 'четвер', "п'ятницю", 'суботу', 'неділю']
    weekday_name = weekday_names[training_info["date"].weekday()]

    if training_info["days_until"] == 0:
        day_text = "сьогодні"
    elif training_info["days_until"] == 1:
        day_text = "завтра"
    else:
        day_text = f"через {training_info['days_until']} дні(в)"

    message = (
        f"Наступне тренування{team_str}{coach_str} {day_text} в {weekday_name}, {date_str} з {start_time} до {end_time}."
    )

    await update.message.reply_text(message)


def get_last_training():
    one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE, {})
    constant_trainings = load_data(CONSTANT_TRAININGS_FILE, {})

    all_trainings = []

    for tid, training in one_time_trainings.items():
        date_obj = datetime.datetime.strptime(training["date"], "%d.%m.%Y").date()
        if date_obj < datetime.date.today():
            all_trainings.append((date_obj, tid))

    today_weekday = datetime.date.today().weekday()
    for tid, training in constant_trainings.items():
        if training["weekday"] < today_weekday:
            last_training_date = datetime.date.today() - datetime.timedelta(days=(today_weekday - training["weekday"]))
            all_trainings.append((last_training_date, tid))

    if not all_trainings:
        return None, None

    last_training = max(all_trainings, key=lambda x: x[0])
    return last_training[0].strftime("%d.%m.%Y"), last_training[1]


async def last_training(update, context: ContextTypes.DEFAULT_TYPE):
    last_training_date, training_id = get_last_training()
    if last_training_date:
        message = f"Останнє тренування було {last_training_date} (ID: {training_id})."
    else:
        message = "Немає записаних тренувань."
    await update.message.reply_text(message)


# def get_next_training(user_team=None):
#     # Get current time in Ukraine (Kyiv)
#     now = datetime.datetime.now(pytz.timezone('Europe/Kiev'))
#
#     # Load one-time trainings
#     one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE)
#
#     # Filter out past one-time trainings
#     current_one_time_trainings = []
#     for training in one_time_trainings:
#         training_date = datetime.datetime.strptime(training["date"], "%d.%m.%Y").date()
#         if training_date >= now.date():
#             # If user team is specified, filter by team
#             if user_team is None or training["team"] == user_team or training["team"] == "Both":
#                 current_one_time_trainings.append(training)
#
#     # Find the closest one-time training
#     closest_one_time = None
#     days_to_closest_one_time = float('inf')
#
#     for training in current_one_time_trainings:
#         training_date = datetime.datetime.strptime(training["date"], "%d.%m.%Y").date()
#         days_diff = (training_date - now.date()).days
#
#         if days_diff < days_to_closest_one_time:
#             closest_one_time = training
#             days_to_closest_one_time = days_diff
#
#     # Find the closest recurring training from schedule
#     current_weekday = now.weekday()
#     next_recurring = None
#     days_to_next_recurring = 7  # Maximum days to next training
#
#     for training in TRAINING_SCHEDULE:
#         # Check if training has team info (in case of older entries without it)
#         if len(training) >= 6:  # New format includes team and coach info
#             weekday, start_hour, start_min, end_hour, end_min, team, *rest = training
#             # Filter by team if user_team is specified
#             if user_team is not None and team != user_team and team != "Both":
#                 continue
#         else:  # Old format without team info
#             weekday, start_hour, start_min, end_hour, end_min = training
#
#         # Calculate days until this training
#         days_diff = (weekday - current_weekday) % 7
#
#         # If training is today, check if it's already passed
#         if days_diff == 0:
#             training_time = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
#             if now.time() >= training_time.time():
#                 days_diff = 7  # Move to next week
#
#         if days_diff < days_to_next_recurring:
#             next_recurring = training
#             days_to_next_recurring = days_diff
#
#     # Determine which is sooner: one-time or recurring
#     if closest_one_time and days_to_closest_one_time <= days_to_next_recurring:
#         # One-time training is sooner
#         training_date = datetime.datetime.strptime(closest_one_time["date"], "%d.%m.%Y").date()
#         start_hour = closest_one_time["start_hour"]
#         start_min = closest_one_time["start_min"]
#         end_hour = closest_one_time["end_hour"]
#         end_min = closest_one_time["end_min"]
#         team = closest_one_time["team"]
#         with_coach = closest_one_time.get("with_coach", False)
#
#         date_str = training_date.strftime("%d.%m.%Y")
#         days_diff = days_to_closest_one_time
#         is_one_time = True
#
#     elif next_recurring:
#         # Recurring training is sooner
#         if len(next_recurring) >= 6:  # New format with team info
#             weekday, start_hour, start_min, end_hour, end_min, team, *rest = next_recurring
#             with_coach = rest[0] if rest else False
#         else:  # Old format without team info
#             weekday, start_hour, start_min, end_hour, end_min = next_recurring
#             team = "Both"  # Default
#             with_coach = False
#
#         next_date = now + datetime.timedelta(days=days_to_next_recurring)
#         date_str = next_date.strftime("%d.%m.%Y")
#         days_diff = days_to_next_recurring
#         is_one_time = False
#
#     else:
#         return "Не вдалося визначити наступне тренування."
#
#     # Format message
#     weekday_names = ['понеділок', 'вівторок', 'середу', 'четвер', "п'ятницю", 'суботу', 'неділю']
#
#     if is_one_time:
#         weekday_name = weekday_names[training_date.weekday()]
#     else:
#         weekday_name = weekday_names[next_recurring[0]]
#
#     # Day text
#     if days_diff == 0:
#         day_text = "сьогодні"
#     elif days_diff == 1:
#         day_text = "завтра"
#     else:
#         day_text = f"через {days_diff} дні(в)"
#
#     # Team text
#     team_text = ""
#     if team != "Both":
#         team_text = f" для {'чоловічої' if team == 'Male' else 'жіночої'} команди"
#
#     # Coach text
#     coach_text = " з тренером" if with_coach else ""
#
#     message = (f"Наступне тренування{team_text}{coach_text} {day_text} ({weekday_name}), {date_str} "
#                f"з {start_hour:02d}:{start_min:02d} до {end_hour:02d}:{end_min:02d}")
#
#     return message