import datetime
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, \
    filters
from training_archive import enhanced_reset_today_constant_trainings_status

from data import load_data, save_data
from validation import is_authorized

DATA_FILE = "users"


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


TYPE, TEAM, COACH, LOCATION, DESCRIPTION, DATE, START, END, WEEKDAY, START_VOTING = range(10)

ONE_TIME_TRAININGS_FILE = "one_time_trainings"
CONSTANT_TRAININGS_FILE = "constant_trainings"

MESSAGES = {
    "unauthorized": "У вас немає дозволу на додавання тренувань.",
    "select_type": "Виберіть тип тренування:",
    "select_team": "Для якої команди це тренування?",
    "with_coach": "Це тренування з тренером?",
    "enter_location": "Введіть місце проведення тренування або посилання на гугл карти,або надішліть '-' якщо локація НаУКМА:",
    "enter_description": "Введіть опис тренування, або надішліть '-' якщо опису немає:",
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

    await query.edit_message_text(MESSAGES["enter_location"])
    return LOCATION


async def training_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    location = update.message.text.strip()
    context.user_data['training_location'] = None if location == '-' else location

    await update.message.reply_text(MESSAGES["enter_description"])
    return DESCRIPTION


async def training_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    description = update.message.text.strip()
    context.user_data['training_description'] = None if description == '-' else description

    if context.user_data['training_type'] == TrainingType.ONE_TIME.value:
        await update.message.reply_text(MESSAGES["enter_date"])
        return DATE
    else:
        await update.message.reply_text(
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
        await save_training_data(update, context)
        await update.message.reply_text(MESSAGES["training_saved"])
        return ConversationHandler.END
    else:
        query = update.callback_query
        await query.answer()
        context.user_data['start_voting'] = int(query.data.split("_")[-1])
        await save_training_data(update, context)
        await query.edit_message_text(MESSAGES["training_saved"])
        return ConversationHandler.END


async def save_training_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    training_data = {
        "team": context.user_data['training_team'],
        "with_coach": context.user_data['with_coach'],
        "location": context.user_data['training_location'],
        "description": context.user_data.get('training_description'),
        "start_hour": context.user_data['start_hour'],
        "start_min": context.user_data['start_min'],
        "end_hour": context.user_data['end_hour'],
        "end_min": context.user_data['end_min'],
        "start_voting": context.user_data['start_voting'],
        "status": "not charged",
        "voting_opened": False
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

    if is_onetime:
        try:
            start_voting_date = datetime.datetime.strptime(training_data['start_voting'], "%d.%m.%Y").date()
            today = datetime.datetime.now().date()

            if start_voting_date <= today:
                await open_onetime_training_voting_immediately(context, training_data, new_id)
                training_data["voting_opened"] = True
                trainings[new_id] = training_data
                save_data(trainings, file_path)
        except:
            pass


async def open_onetime_training_voting_immediately(context, training, training_id):
    users = load_data(DATA_FILE)
    vote_id = f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"

    start_time = f"{training['start_hour']:02d}:{training['start_min']:02d}"
    end_time = f"{training['end_hour']:02d}:{training['end_min']:02d}"

    coach_str = " (З тренером)" if training.get("with_coach") else ""
    location = training.get("location", "")
    location = "" if location and location.lower() == "наукма" else location
    loc_str = f"\n📍 {location}" if location else ""
    description = training.get("description", "")
    desc_str = f"\nℹ️ {description}" if description else ""

    message = (
        f"🏐 Почалося голосування!\n"
        f"Тренування {training['date']}{coach_str}\n"
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
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=message,
                    reply_markup=keyboard
                )
            except Exception as e:
                print(f"❌ ONETIME: Помилка надсилання до {uid}: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Додавання скасоване. Використовуй /add_training щоб спробувати знову.")
    return ConversationHandler.END


def create_training_add_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("add_training", add_training)],
        states={
            TYPE: [CallbackQueryHandler(training_type)],
            TEAM: [CallbackQueryHandler(training_team)],
            COACH: [CallbackQueryHandler(training_coach)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, training_location)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, training_description)],
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
    one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE, {})
    constant_trainings = load_data(CONSTANT_TRAININGS_FILE, {})

    now = datetime.datetime.now()
    current_date = now.date()
    current_time = now.time()
    current_weekday = now.weekday()

    all_trainings = []

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
            "location": training.get("location", ""),
            "description": training.get("description"),
            "type": "constant",
            "days_until": days_until
        })

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
            "location": training.get("location", ""),
            "description": training.get("description"),
            "type": "one-time",
            "days_until": days_until
        })

    all_trainings.sort(key=lambda x: (x["date"], x["start_hour"], x["start_min"]))

    return all_trainings[0] if all_trainings else None


def get_next_week_trainings(team=None):
    from datetime import datetime, timedelta

    one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE, {})
    constant_trainings = load_data(CONSTANT_TRAININGS_FILE, {})

    now = datetime.now()
    current_date = now.date()

    end_date = current_date + timedelta(days=7)
    trainings = []

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
                    "location": training.get("location", ""),
                    "description": training.get("description", ""),
                    "type": "constant"
                })

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
                "location": training.get("location", ""),
                "description": training.get("description", ""),
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
        time_str = f"{t['start_hour']:02d}:{t['start_min']:02d}-{t['end_hour']:02d}:{t['end_min']:02d}"
        day = weekday_names[t["date"].weekday()]

        main_line = f"• {day} {date_str} {time_str}"

        if t["with_coach"]:
            main_line += ", з тренером"

        if t["team"] != "Both":
            team_name = "чоловіча" if t["team"] == "Male" else "жіноча"
            main_line += f", {team_name} команда"

        message += main_line + "\n"

        location = t.get("location", "")
        if location and location.lower() != "наукма":
            message += f"  📍 {location}\n"

        description = t.get("description", "")
        if description:
            message += f"  ℹ️ {description}\n"

        message += "\n"

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
    team_str = f" для {'чоловічої' if training_info['team'] == 'Male' else 'жіночої'} команди" if training_info[
                                                                                                      "team"] != "Both" else " для обох команд"
    coach_str = " (З тренером)" if training_info["with_coach"] else ""

    location = training_info.get("location", "")
    location = "" if location and location.lower() == "наукма" else location
    loc_str = f"\n📍{location}" if location else ""

    description = training_info.get("description", "")
    desc_str = f"\nℹ️ {description}" if description else ""

    weekday_names = ['понеділок', 'вівторок', 'середу', 'четвер', "п'ятницю", 'суботу', 'неділю']
    weekday_name = weekday_names[training_info["date"].weekday()]

    if training_info["days_until"] == 0:
        day_text = "Сьогодні"
    elif training_info["days_until"] == 1:
        day_text = "Завтра"
    else:
        day_text = f"Через {training_info['days_until']} дні(в)"

    return (
        f"🏐 Наступне тренування{team_str}{coach_str}\n"
        f"📅 {day_text} в {weekday_name}, {date_str}\n"
        f"⏰ З {start_time} до {end_time}"
        f"{loc_str}"
        f"{desc_str}"
    )

async def delete_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін-команда: показати ТІЛЬКИ тренування, за які вже є голоси, і видалити обране.
       Кнопки показують дату/день тижня + час. Використовуються ЛИШЕ наявні ID тренувань."""
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ У вас немає прав для цієї команди.")
        return

    one_time = load_data("one_time_trainings", {})
    constant = load_data("constant_trainings", {})
    votes_map = load_data("votes", {"votes": {}}).get("votes", {})

    buttons = []

    # One-time trainings: vote key = "DD.MM.YYYY_HH:MM"
    for tid, t in one_time.items():
        try:
            vote_key = f"{t['date']}_{t['start_hour']:02d}:{t['start_min']:02d}"
        except KeyError:
            continue
        if vote_key in votes_map and votes_map[vote_key]:
            label = f"{t['date']} {t['start_hour']:02d}:{t['start_min']:02d}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"deltr_select_one_{tid}")])

    # Constant trainings: vote key = "const_<weekday>_HH:MM"
    for tid, t in constant.items():
        try:
            vote_key = f"const_{t['weekday']}_{t['start_hour']:02d}:{t['start_min']:02d}"
        except KeyError:
            continue
        if vote_key in votes_map and votes_map[vote_key]:
            weekdays = ["Понеділок","Вівторок","Середа","Четвер","П'ятниця","Субота","Неділя"]
            label = f"{weekdays[t['weekday']]} {t['start_hour']:02d}:{t['start_min']:02d}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"deltr_select_const_{tid}")])

    if not buttons:
        await update.message.reply_text("Немає тренувань з активними голосами.")
        return

    await update.message.reply_text(
        "Оберіть тренування для видалення:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_delete_training_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # deltr_select_(one|const)_<tid>
    parts = query.data.split("_", 3)
    if len(parts) != 4:
        await query.edit_message_text("⚠️ Помилка: тренування не знайдено.")
        return

    _, _, col_tag, tid = parts
    collection = "one_time_trainings" if col_tag == "one" else "constant_trainings"
    trainings = load_data(collection, {})
    t = trainings.get(tid)
    if not t:
        await query.edit_message_text("⚠️ Тренування не знайдено.")
        return

    # Build human label (using only existing fields)
    if col_tag == "one":
        label = f"{t['date']} {t['start_hour']:02d}:{t['start_min']:02d}"
    else:
        weekdays = ["Понеділок","Вівторок","Середа","Четвер","П'ятниця","Субота","Неділя"]
        label = f"{weekdays[t['weekday']]} {t['start_hour']:02d}:{t['start_min']:02d}"

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑 Підтвердити видалення", callback_data=f"deltr_confirm_yes_{col_tag}_{tid}"),
            InlineKeyboardButton("↩️ Скасувати",            callback_data=f"deltr_confirm_no_{col_tag}_{tid}")
        ]
    ])
    await query.edit_message_text(f"Видалити тренування: {label}?", reply_markup=kb)


async def handle_delete_training_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # deltr_confirm_(yes|no)_(one|const)_<tid>
    parts = query.data.split("_", 4)
    if len(parts) != 5:
        await query.edit_message_text("⚠️ Помилка підтвердження.")
        return

    _, _, decision, col_tag, tid = parts
    if decision == "no":
        await query.edit_message_text("Скасовано.")
        return

    collection = "one_time_trainings" if col_tag == "one" else "constant_trainings"
    trainings = load_data(collection, {})
    t = trainings.get(tid)
    if not t:
        await query.edit_message_text("⚠️ Тренування не знайдено.")
        return

    # Build label before deletion (only from existing fields)
    if col_tag == "one":
        label = f"{t['date']} {t['start_hour']:02d}:{t['start_min']:02d}"
    else:
        weekdays = ["Понеділок","Вівторок","Середа","Четвер","П'ятниця","Субота","Неділя"]
        label = f"{weekdays[t['weekday']]} {t['start_hour']:02d}:{t['start_min']:02d}"

    trainings.pop(tid, None)
    save_data(trainings, collection)

    await query.edit_message_text(f"✅ Видалено: {label}")

async def next_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    await update.message.reply_text(format_next_training_message(user_id))


async def reset_today_constant_trainings_status():
    await enhanced_reset_today_constant_trainings_status()


def setup_training_handlers(app):
    # /next_training
    app.add_handler(CommandHandler("next_training", next_training))
    # /week_trainings
    app.add_handler(CommandHandler("week_trainings", week_trainings))

    # Admin: /delete_training
    app.add_handler(CommandHandler("delete_training", delete_training))
    app.add_handler(CallbackQueryHandler(handle_delete_training_selection, pattern=r"^deltr_select_(one|const)_.+$"))
    app.add_handler(
        CallbackQueryHandler(handle_delete_training_confirm, pattern=r"^deltr_confirm_(yes|no)_(one|const)_.+$"))
    # Admin: /add_training
    app.add_handler(create_training_add_handler())
