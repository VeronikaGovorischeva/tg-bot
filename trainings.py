from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, \
    filters
import datetime
from data import load_data, save_data
from validation import is_authorized

DATA_FILE="users"
class TrainingType(Enum):
    ONE_TIME = "training_onetime"
    RECURRING = "training_recurring"


class Team(Enum):
    MALE = "Male"
    FEMALE = "Female"
    BOTH = "Both"

    def to_json(self):
        return self.value


class VotingType(Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"


# Conversation states
TYPE, TEAM, COACH, DATE, START, END, WEEKDAY, START_VOTING = range(8)

# File paths
ONE_TIME_TRAININGS_FILE = "one_time_trainings"
CONSTANT_TRAININGS_FILE = "constant_trainings"

# UI Text constants
MESSAGES = {
    "unauthorized": "У вас немає дозволу на додавання тренувань.",
    "select_type": "Виберіть тип тренування:",
    "select_team": "Для якої команди це тренування?",
    "with_coach": "Це тренування з тренером?",
    "enter_date": "Введіть дату тренування у форматі ДД.ММ.РРРР (наприклад, 25.03.2025)",
    "enter_start_time": "Введіть час початку тренування у форматі ГГ:ХХ (наприклад, 19:00)",
    "enter_end_time": "Введіть час закінчення тренування у форматі ГГ:ХХ (наприклад, 21:00)",
    "select_weekday": "Виберіть день тижня для регулярного тренування:",
    "invalid_date": "Неправильний формат дати. Будь ласка, використовуйте формат ДД.ММ.РРРР",
    "invalid_time": "Неправильний формат часу. Будь ласка, використовуйте формат ГГ:ХХ",
    "enter_voting_start_date": "Введіть дату початку голосування (ДД.ММ.РРРР):",
    "select_voting_start_day": "Оберіть день тижня для початку голосування:",
    "training_saved": "Тренування успішно збережено!"

}


def create_training_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Одноразове", callback_data=TrainingType.ONE_TIME.value),
        InlineKeyboardButton("Постійне", callback_data=TrainingType.RECURRING.value)
    ]])


def create_team_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Чоловіча", callback_data="training_team_male"),
            InlineKeyboardButton("Жіноча", callback_data="training_team_female")
        ],
        [InlineKeyboardButton("Обидві команди", callback_data="training_team_both")]
    ])


def create_coach_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Так", callback_data="training_coach_yes"),
        InlineKeyboardButton("Ні", callback_data="training_coach_no")
    ]])


def create_weekday_keyboard() -> InlineKeyboardMarkup:
    weekdays = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
    return InlineKeyboardMarkup([[InlineKeyboardButton(day, callback_data=f"weekday_{i}")]
                                 for i, day in enumerate(weekdays)])


def create_voting_day_keyboard(prefix: str) -> InlineKeyboardMarkup:
    weekdays = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(day, callback_data=f"{prefix}{i}")]
        for i, day in enumerate(weekdays)
    ])


async def add_training(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text(MESSAGES["unauthorized"])
        return ConversationHandler.END

    await update.message.reply_text(
        MESSAGES["select_type"],
        reply_markup=create_training_type_keyboard()
    )
    return TYPE


async def training_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['training_type'] = query.data

    await query.edit_message_text(
        MESSAGES["select_team"],
        reply_markup=create_team_keyboard()
    )
    return TEAM


async def training_team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    team_mapping = {
        "training_team_male": Team.MALE.value,
        "training_team_female": Team.FEMALE.value,
        "training_team_both": Team.BOTH.value
    }
    context.user_data['training_team'] = team_mapping[query.data]

    await query.edit_message_text(
        MESSAGES["with_coach"],
        reply_markup=create_coach_keyboard()
    )
    return COACH


async def training_coach(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['with_coach'] = query.data == "training_coach_yes"

    if context.user_data['training_type'] == TrainingType.ONE_TIME.value:
        await query.edit_message_text(MESSAGES["enter_date"])
        return DATE
    else:
        await query.edit_message_text(
            MESSAGES["select_weekday"],
            reply_markup=create_weekday_keyboard()
        )
        return WEEKDAY


class TimeValidator:
    @staticmethod
    def validate_date(date_text: str) -> tuple[bool, datetime.date | None]:
        try:
            return True, datetime.datetime.strptime(date_text, "%d.%m.%Y").date()
        except ValueError:
            return False, None

    @staticmethod
    def validate_time(time_text: str) -> tuple[bool, tuple[int, int] | None]:
        try:
            time_obj = datetime.datetime.strptime(time_text, "%H:%M").time()
            return True, (time_obj.hour, time_obj.minute)
        except ValueError:
            return False, None


async def training_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    is_valid, date_obj = TimeValidator.validate_date(update.message.text)
    if not is_valid:
        await update.message.reply_text(MESSAGES["invalid_date"])
        return DATE

    context.user_data['training_date'] = date_obj.strftime("%d.%m.%Y")
    await update.message.reply_text(MESSAGES["enter_start_time"])
    return START


async def training_weekday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    weekday = int(query.data.replace("weekday_", ""))
    context.user_data['training_weekday'] = weekday

    await query.edit_message_text(MESSAGES["enter_start_time"])
    return START


async def training_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    is_valid, time_tuple = TimeValidator.validate_time(update.message.text)
    if not is_valid:
        await update.message.reply_text(MESSAGES["invalid_time"])
        return START

    context.user_data['start_hour'], context.user_data['start_min'] = time_tuple
    await update.message.reply_text(MESSAGES["enter_end_time"])
    return END


async def training_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    is_valid, time_tuple = TimeValidator.validate_time(update.message.text)
    if not is_valid:
        await update.message.reply_text(MESSAGES["invalid_time"])
        return END

    context.user_data['end_hour'], context.user_data['end_min'] = time_tuple

    if context.user_data['training_type'] == TrainingType.ONE_TIME.value:
        await update.message.reply_text(MESSAGES["enter_voting_start_date"])
        return START_VOTING
    else:
        await update.message.reply_text(
            MESSAGES["select_voting_start_day"],
            reply_markup=create_voting_day_keyboard("voting_day_")
        )
        return START_VOTING


async def training_start_voting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data['training_type'] == TrainingType.ONE_TIME.value:
        if not update.message:
            return START_VOTING
        context.user_data['start_voting'] = update.message.text
        await update.message.reply_text(MESSAGES["enter_voting_end_date"])
        await save_training_data(update, context)
        return ConversationHandler.END
    else:
        query = update.callback_query
        await query.answer()
        context.user_data['start_voting'] = int(query.data.split("_")[-1])
        await query.edit_message_text(
            MESSAGES["select_voting_end_day"],
            reply_markup=create_voting_day_keyboard("voting_end_day_")
        )
        await save_training_data(update, context)
        return ConversationHandler.END


async def save_training_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    training_data = {
        "team": context.user_data['training_team'],
        "with_coach": context.user_data['with_coach'],
        "start_hour": context.user_data['start_hour'],
        "start_min": context.user_data['start_min'],
        "end_hour": context.user_data['end_hour'],
        "end_min": context.user_data['end_min'],
        "start_voting": context.user_data['start_voting'],
        "status": "not charged"
    }

    is_onetime = context.user_data['training_type'] == TrainingType.ONE_TIME.value
    file_path = ONE_TIME_TRAININGS_FILE if is_onetime else CONSTANT_TRAININGS_FILE
    trainings = load_data(file_path, {})

    if is_onetime:
        training_data["date"] = context.user_data['training_date']
    else:
        training_data["weekday"] = context.user_data['training_weekday']

    new_id = str(max(map(int, trainings.keys() or ['0'])) + 1)
    trainings[new_id] = training_data
    save_data(trainings, file_path)

    message = MESSAGES["training_saved"]
    if update.message:
        await update.message.reply_text(message)
    elif update.callback_query:
        await update.callback_query.message.reply_text(message)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles registration cancellation."""
    await update.message.reply_text("Додавання скасоване. Використовуй /add_training щоб спробувати знову.")
    return ConversationHandler.END


def create_training_add_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("add_training", add_training)],
        states={
            TYPE: [CallbackQueryHandler(training_type)],
            TEAM: [CallbackQueryHandler(training_team)],
            COACH: [CallbackQueryHandler(training_coach)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, training_date)],
            START: [MessageHandler(filters.TEXT & ~filters.COMMAND, training_start)],
            END: [MessageHandler(filters.TEXT & ~filters.COMMAND, training_end)],
            WEEKDAY: [CallbackQueryHandler(training_weekday)],
            START_VOTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, training_start_voting),
                           CallbackQueryHandler(training_start_voting, pattern=r"^voting_day_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )


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
    user_data = load_data(DATA_FILE)

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
        message += f"• {day}, {date_str} з {start} до {end}{coach_str}{team_str} \n"

    await update.message.reply_text(message)

def format_next_training_message(user_id: str) -> str:
    user_data = load_data("users")

    if user_id not in user_data or "team" not in user_data[user_id]:
        return "Будь ласка, завершіть реєстрацію, щоб отримувати інформацію про тренування."

    team = user_data[user_id]["team"]
    training_info = get_next_training(team)

    if not training_info:
        return "Немає запланованих тренувань."

    date_str = training_info["date"].strftime("%d.%m.%Y")
    start_time = f"{training_info['start_hour']:02d}:{training_info['start_min']:02d}"
    end_time = f"{training_info['end_hour']:02d}:{training_info['end_min']:02d}"
    team_str = f" для {'чоловічої' if training_info['team'] == 'Male' else 'жіночої'} команди" if training_info["team"] != "Both" else " для обох команд"
    coach_str = " з тренером" if training_info["with_coach"] else ""

    weekday_names = ['понеділок', 'вівторок', 'середу', 'четвер', "п'ятницю", 'суботу', 'неділю']
    weekday_name = weekday_names[training_info["date"].weekday()]

    if training_info["days_until"] == 0:
        day_text = "сьогодні"
    elif training_info["days_until"] == 1:
        day_text = "завтра"
    else:
        day_text = f"через {training_info['days_until']} дні(в)"

    return (
        f"Наступне тренування{team_str}{coach_str} {day_text} в {weekday_name}, {date_str} з {start_time} до {end_time}."
    )
async def next_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /next_training command, fetching and formatting the next training session.
    """
    user_id = str(update.message.from_user.id)

    await update.message.reply_text(format_next_training_message(user_id))


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

import datetime
from data import load_data, save_data

def reset_today_constant_trainings_status():
    today_weekday = datetime.datetime.today().weekday()
    constant_trainings = load_data("constant_trainings", {})

    updated = False
    for tid, training in constant_trainings.items():
        if training.get("weekday") == today_weekday:
            if training.get("status") != "not charged":
                training["status"] = "not charged"
                updated = True

    if updated:
        save_data(constant_trainings, "constant_trainings")
        print("✅ Reset status of constant trainings for today.")
    else:
        print("ℹ️ No constant trainings needed status reset today.")
