import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from data import load_data, save_data
from trainings import get_next_week_trainings
import uuid
from validation import is_authorized


async def unlock_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("У вас немає прав для цієї команди.")
        return

    one_time = load_data("one_time_trainings", {})
    constant = load_data("constant_trainings", {})

    options = []

    for tid, t in one_time.items():
        if t.get("team") in ["Male", "Female"]:
            label = f"{t['date']} о {t['start_hour']:02d}:{t['start_min']:02d}"
            options.append((tid, "one_time", label))

    for tid, t in constant.items():
        if t.get("team") in ["Male", "Female"]:
            weekday = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"][t["weekday"]]
            label = f"{weekday} о {t['start_hour']:02d}:{t['start_min']:02d}"
            options.append((tid, "constant", label))

    if not options:
        await update.message.reply_text("Немає тренувань, які потребують розблокування.")
        return

    context.user_data["unlock_options"] = options

    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"unlock_training_{i}")]
        for i, (_, _, label) in enumerate(options)
    ]

    await update.message.reply_text(
        "Оберіть тренування, щоб дозволити голосування обом командам:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_unlock_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("unlock_training_", ""))
    options = context.user_data.get("unlock_options", [])

    if idx >= len(options):
        await query.edit_message_text("⚠️ Помилка: тренування не знайдено.")
        return

    tid, ttype, _ = options[idx]
    trainings = load_data("one_time_trainings" if ttype == "one_time" else "constant_trainings", {})

    if tid not in trainings:
        await query.edit_message_text("⚠️ Тренування не знайдено.")
        return

    trainings[tid]["team"] = "Both"
    save_data(trainings, "one_time_trainings" if ttype == "one_time" else "constant_trainings")

    await query.edit_message_text("✅ Тренування оновлено. Тепер обидві команди можуть голосувати.")


WEEKDAYS = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]

REGISTRATION_FILE = "users"
VOTES_FILE = "training_votes"
DEFAULT_VOTES_STRUCTURE = {"votes": {}}
VOTES_LIMIT = 14

VOTE_OTHER_NAME, VOTE_OTHER_SELECT = range(2)


async def vote_for(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("У вас немає прав для цієї команди.")
        return ConversationHandler.END

    context.user_data["vote_other_id"] = f"admin_{uuid.uuid4().hex[:8]}"
    await update.message.reply_text("Введіть ім'я або прізвище людини, за яку голосуєте:")
    return VOTE_OTHER_NAME


async def vote_other_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data["vote_other_name"] = name

    # Load trainings
    user_data = load_data("users")
    admin_id = str(update.message.from_user.id)
    team = user_data.get(admin_id, {}).get("team", "Both")

    trainings = get_next_week_trainings(team)
    today = datetime.datetime.today().date()
    current_hour = datetime.datetime.now().hour
    filtered = []

    for t in trainings:
        start_voting = t.get("start_voting")
        if t["type"] == "one-time":
            try:
                start_date = datetime.datetime.strptime(start_voting, "%d.%m.%Y").date()
                if (start_date < today or (start_date == today and current_hour >= 18)):
                    tid = f"{t['date']}_{t['start_hour']:02d}:{t['start_min']:02d}"
                    filtered.append((tid, t))
            except:
                continue
        else:
            if isinstance(start_voting, int) and (
                    start_voting < today.weekday() or (start_voting == today.weekday() and current_hour >= 18)
            ):
                tid = f"const_{t['weekday']}_{t['start_hour']:02d}:{t['start_min']:02d}"
                filtered.append((tid, t))

    if not filtered:
        await update.message.reply_text("Немає тренувань для голосування.")
        return ConversationHandler.END

    context.user_data["vote_other_trainings"] = filtered

    keyboard = [
        [InlineKeyboardButton(
            f"{t['date'].strftime('%d.%m.%Y') if t['type'] == 'one-time' else WEEKDAYS[t['weekday']]} {t['start_hour']:02d}:{t['start_min']:02d}",
            callback_data=f"vote_other_{i}"
        )] for i, (_, t) in enumerate(filtered)
    ]

    await update.message.reply_text(
        "Оберіть тренування:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VOTE_OTHER_SELECT


async def handle_vote_other_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("vote_other_", ""))
    selected = context.user_data.get("vote_other_trainings", [])[idx]
    training_id, _ = selected
    context.user_data["vote_other_training_id"] = training_id

    keyboard = [
        [
            InlineKeyboardButton("✅ Так", callback_data="vote_other_cast_yes"),
            InlineKeyboardButton("❌ Ні", callback_data="vote_other_cast_no")
        ]
    ]

    await query.edit_message_text(
        f"Ви обрали тренування: {format_training_id(training_id)}\n"
        "Який голос ви хочете поставити?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_vote_other_cast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    vote_choice = "yes" if "yes" in query.data else "no"
    name = context.user_data["vote_other_name"]
    training_id = context.user_data["vote_other_training_id"]
    user_id = context.user_data["vote_other_id"]

    votes = load_data("votes", DEFAULT_VOTES_STRUCTURE)
    if training_id not in votes["votes"]:
        votes["votes"][training_id] = {}

    votes["votes"][training_id][user_id] = {"name": name, "vote": vote_choice}
    save_data(votes, "votes")

    vote_text = "БУДУ" if vote_choice == "yes" else "НЕ БУДУ"
    await query.edit_message_text(
        f"✅ Голос за '{name}' збережено як '{vote_text}' на тренування {format_training_id(training_id)}.")


def generate_training_id(training):
    """Generate a consistent training ID for both vote_training command and notifier"""
    if training["type"] == "one-time":
        return f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"
    else:
        return f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"


async def vote_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    for training in trainings:
        start_voting = training.get("start_voting")

        if training["type"] == "one-time":
            try:
                if isinstance(start_voting, str):
                    start_date = datetime.datetime.strptime(start_voting, "%d.%m.%Y").date()
                else:
                    start_date = start_voting
            except Exception:
                continue

            if (start_date < today or (start_date == today and current_hour >= 18)):
                date_str = training["date"] if isinstance(training["date"], str) else training["date"].strftime(
                    "%d.%m.%Y")
                training_id = f"{date_str}_{training['start_hour']:02d}:{training['start_min']:02d}"
                filtered.append((training_id, training))
        else:
            if not isinstance(start_voting, int):
                continue
            weekday_condition = (
                    start_voting < today.weekday() or
                    (start_voting == today.weekday() and current_hour >= 18)
            )

            if weekday_condition:
                date_str = training['date'].strftime("%d.%m.%Y") if isinstance(training['date'], datetime.date) else \
                    training['date']
                training_id = generate_training_id(training)
                filtered.append((training_id, training))

    if not filtered:
        await update.message.reply_text("Наразі немає тренувань для голосування.")
        return

    keyboard = []
    for idx, (tid, t) in enumerate(filtered):
        if t["type"] == "one-time":
            date_str = t["date"].strftime("%d.%m.%Y") if isinstance(t["date"], datetime.date) else t["date"]
        else:
            date_str = WEEKDAYS[t["date"].weekday()]
        time_str = f"{t['start_hour']:02d}:{t['start_min']:02d}"
        keyboard.append([InlineKeyboardButton(f"{date_str} {time_str}", callback_data=f"training_vote_{idx}")])

    context.user_data["vote_options"] = filtered

    await update.message.reply_text("Оберіть тренування для голосування:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_training_vote_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    idx = int(query.data.replace("training_vote_", ""))
    vote_options = context.user_data.get("vote_options", [])

    if idx >= len(vote_options):
        await query.edit_message_text("⚠️ Помилка: вибране тренування більше не доступне.")
        return

    training_id, training = vote_options[idx]

    # Не знаю чи потрібно
    # vote_options = context.user_data.get("vote_options")
    # if not vote_options:
    #     await query.edit_message_text("Помилка: не знайдено тренувань.")
    #     return
    # idx = int(query.data.replace("training_vote_", ""))
    # try:
    #     _, training_id, training = vote_options[idx]
    # except IndexError:
    #     await query.edit_message_text("Помилка: тренування не знайдено.")
    #     return

    votes = load_data('votes', DEFAULT_VOTES_STRUCTURE)
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
        message += f"Ваш поточний голос: {'БУДУ' if current_vote == 'yes' else 'НЕ БУДУ'}\n"
    message += "Чи будете на тренуванні?"

    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    vote = data[1]  # yes, no
    training_id = "_".join(data[2:])

    user_id = str(query.from_user.id)
    user_data = load_data(REGISTRATION_FILE)
    user_name = user_data.get(user_id, {}).get("name", "Невідомий користувач")

    votes = load_data('votes', DEFAULT_VOTES_STRUCTURE)

    if training_id not in votes["votes"]:
        votes["votes"][training_id] = {}
    current_yes_votes = sum(1 for v in votes["votes"][training_id].values() if v["vote"] == "yes")

    # Перевіряємо чи не змінюємо голос з "ні" на "так" коли ліміт досягнуто
    changing_to_yes = (
            vote == "yes" and
            user_id in votes["votes"][training_id] and
            votes["votes"][training_id][user_id]["vote"] == "no"
    )

    # Якщо вже 14 людей проголосували "так" і новий голос "так", попереджаємо
    if vote == "yes" and current_yes_votes >= VOTES_LIMIT and (
            user_id not in votes["votes"][training_id] or changing_to_yes):
        await query.edit_message_text("⚠️ Досягнуто максимум голосів 'так'. Ви не можете проголосувати.")
        return

    # Оновлюємо голос користувача
    votes["votes"][training_id][user_id] = {"name": user_name, "vote": vote}
    save_data(votes, 'votes')

    # Перевіряємо, чи досягнуто ліміт після оновлення
    updated_yes_votes = sum(1 for v in votes["votes"][training_id].values() if v["vote"] == "yes")

    message = f"Ваш голос: {'БУДУ' if vote == 'yes' else 'НЕ БУДУ'} записано!"

    if updated_yes_votes == VOTES_LIMIT:
        message += "\n⚠️ Досягнуто максимум учасників."

    await query.edit_message_text(message)


async def view_votes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    votes = load_data('votes', DEFAULT_VOTES_STRUCTURE)
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

    from trainings import load_data as load_trainings

    # Load trainings for team info
    one_time = load_trainings("one_time_trainings", {})
    constant = load_trainings("constant_trainings", {})

    def get_training_team_label(training_id):
        if training_id.startswith("const_"):
            for tid, tr in constant.items():
                tr_id = f"const_{tr['weekday']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                if tr_id == training_id:
                    return tr.get("team", "Both")
        else:
            for tid, tr in one_time.items():
                tr_id = f"{tr['date']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                if tr_id == training_id:
                    return tr.get("team", "Both")
        return "Both"

    def format_team(team):
        if team == "Male":
            return " (чоловіча команда)"
        elif team == "Female":
            return " (жіноча команда)"
        return ""

    keyboard = []
    for i, tid in enumerate(context.user_data["view_votes_options"]):
        team = get_training_team_label(tid)
        label = format_training_id(tid) + format_team(team)
        keyboard.append([InlineKeyboardButton(label, callback_data=f"view_votes_{i}")])

    await update.message.reply_text(
        "Оберіть тренування для перегляду результатів голосування:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def is_vote_active(vote_id, today):
    if "const_" in vote_id:
        return True
    try:
        date = datetime.datetime.strptime(vote_id.split("_")[0], "%d.%m.%Y").date()
        return today <= date
    except Exception:
        return False


# maybe change a bit
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
    votes = load_data('votes', {"votes": {}})
    voters = votes["votes"].get(training_id, {})

    yes_list = [v["name"] for v in voters.values() if v["vote"] == "yes"]
    no_list = [v["name"] for v in voters.values() if v["vote"] == "no"]

    label = format_training_id(training_id)

    message = f"📅 Тренування: {label}\n\n"
    message += f"✅ Буде ({len(yes_list)}):\n" + ("\n".join(yes_list) if yes_list else "Ніхто") + "\n\n"
    message += f"❌ Не буде ({len(no_list)}):\n" + ("\n".join(no_list) if no_list else "Ніхто")

    await query.edit_message_text(message)
