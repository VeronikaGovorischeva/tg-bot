import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, \
    filters
from data import load_data, save_data
from trainings import get_next_week_trainings
from telegram.ext import ConversationHandler
from validation import is_authorized
import uuid

VOTE_TYPE, VOTE_QUESTION, VOTE_OPTIONS, VOTE_TEAM = range(200, 204)

GENERAL_VOTES_FILE = "general_votes"
GENERAL_VOTE_RESPONSES_FILE = "general_vote_responses"


class VoteType:
    YES_NO = "yes_no"
    MULTIPLE_CHOICE_SINGLE = "multiple_choice_single"
    MULTIPLE_CHOICE_MULTI = "multiple_choice_multi"
    TEXT_RESPONSE = "text_response"


class VoteManager:
    def __init__(self):
        self.vote_types = {
            VoteType.YES_NO: "Так/Ні",
            VoteType.MULTIPLE_CHOICE_SINGLE: "Множинний вибір (1 відповідь)",
            VoteType.MULTIPLE_CHOICE_MULTI: "Множинний вибір (багато відповідей)",
            VoteType.TEXT_RESPONSE: "Текстова відповідь"
        }

    def create_vote_type_keyboard(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Так/Ні", callback_data=f"vote_type_{VoteType.YES_NO}")],
            [InlineKeyboardButton("Множинний вибір (1 відповідь)",
                                  callback_data=f"vote_type_{VoteType.MULTIPLE_CHOICE_SINGLE}")],
            [InlineKeyboardButton("Множинний вибір (багато відповідей)",
                                  callback_data=f"vote_type_{VoteType.MULTIPLE_CHOICE_MULTI}")],
            [InlineKeyboardButton("Текстова відповідь", callback_data=f"vote_type_{VoteType.TEXT_RESPONSE}")]
        ])

    def create_team_selection_keyboard(self):
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Чоловіча", callback_data="general_vote_team_Male"),
                InlineKeyboardButton("Жіноча", callback_data="general_vote_team_Female")
            ],
            [InlineKeyboardButton("Обидві команди", callback_data="general_vote_team_Both")]
        ])


vote_manager = VoteManager()


async def create_vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ У вас немає прав для створення голосувань.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Створення нового голосування\n\nОберіть тип голосування:",
        reply_markup=vote_manager.create_vote_type_keyboard()
    )
    return VOTE_TYPE


async def handle_vote_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    vote_type = query.data.replace("vote_type_", "")
    context.user_data['general_vote_type'] = vote_type

    await query.edit_message_text("Введіть питання для голосування:")
    return VOTE_QUESTION


async def handle_vote_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    question = update.message.text
    context.user_data['general_vote_question'] = question

    vote_type = context.user_data['general_vote_type']

    if vote_type in [VoteType.MULTIPLE_CHOICE_SINGLE, VoteType.MULTIPLE_CHOICE_MULTI]:
        await update.message.reply_text(
            "Введіть варіанти відповідей (кожен з нового рядка, максимум 5 варіантів):\n\n"
            "Приклад:\n"
            "Варіант 1\n"
            "Варіант 2\n"
            "Варіант 3"
        )
        return VOTE_OPTIONS
    else:
        context.user_data['general_vote_options'] = []
        await update.message.reply_text(
            "Оберіть для якої команди це голосування:",
            reply_markup=vote_manager.create_team_selection_keyboard()
        )
        return VOTE_TEAM


async def handle_vote_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    options_text = update.message.text
    options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]

    if len(options) < 2:
        await update.message.reply_text(
            "⚠️ Потрібно мінімум 2 варіанти. Спробуйте ще раз:"
        )
        return VOTE_OPTIONS

    if len(options) > 5:
        await update.message.reply_text(
            "⚠️ Максимум 5 варіантів. Спробуйте ще раз:"
        )
        return VOTE_OPTIONS

    context.user_data['general_vote_options'] = options

    await update.message.reply_text(
        "Оберіть для якої команди це голосування:",
        reply_markup=vote_manager.create_team_selection_keyboard()
    )
    return VOTE_TEAM


async def handle_vote_team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    team = query.data.replace("general_vote_team_", "")

    vote_id = str(uuid.uuid4())[:8]
    now = datetime.datetime.now()

    vote_data = {
        "vote_id": vote_id,
        "question": context.user_data['general_vote_question'],
        "type": context.user_data['general_vote_type'],
        "options": context.user_data.get('general_vote_options', []),
        "team": team,
        "creator_id": str(query.from_user.id),
        "created_at": now.isoformat(),
        "is_active": True
    }

    votes = load_data(GENERAL_VOTES_FILE, {})
    votes[vote_id] = vote_data
    save_data(votes, GENERAL_VOTES_FILE)

    await send_vote_to_users(context, vote_data)

    team_display = {"Male": "чоловічої команди", "Female": "жіночої команди", "Both": "обох команд"}[team]

    await query.edit_message_text(
        f"✅ Голосування створено!\n\n"
        f"Питання: {vote_data['question']}\n"
        f"Команда: {team_display}\n\n"
        f"Повідомлення надіслано учасникам команди.\n\n"
    )

    return ConversationHandler.END


async def send_vote_to_users(context: ContextTypes.DEFAULT_TYPE, vote_data: dict):
    users = load_data("users", {})
    vote_id = vote_data["vote_id"]

    if vote_data["type"] == VoteType.YES_NO:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Так", callback_data=f"general_vote_{vote_id}_yes"),
                InlineKeyboardButton("❌ Ні", callback_data=f"general_vote_{vote_id}_no")
            ]
        ])
    elif vote_data["type"] in [VoteType.MULTIPLE_CHOICE_SINGLE, VoteType.MULTIPLE_CHOICE_MULTI]:
        buttons = []
        for i, option in enumerate(vote_data["options"]):
            buttons.append([InlineKeyboardButton(
                f"{i + 1}. {option}",
                callback_data=f"general_vote_{vote_id}_option_{i}"
            )])

        if vote_data["type"] == VoteType.MULTIPLE_CHOICE_MULTI:
            buttons.append(
                [InlineKeyboardButton("✅ Підтвердити вибір", callback_data=f"general_vote_{vote_id}_confirm")])

        keyboard = InlineKeyboardMarkup(buttons)
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Відповісти", callback_data=f"general_vote_{vote_id}_text")]
        ])

    message = f"📊 Нове голосування!\n\n"
    message += f"❓ {vote_data['question']}\n\n"

    if vote_data["type"] == VoteType.TEXT_RESPONSE:
        message += "Натисніть кнопку нижче, щоб залишити відповідь."
    elif vote_data["type"] == VoteType.MULTIPLE_CHOICE_MULTI:
        message += "Оберіть один або кілька варіантів, потім натисніть 'Підтвердити вибір':"
    else:
        message += "Оберіть ваш варіант:"

    count = 0
    for uid, user_info in users.items():
        if vote_data["team"] in [user_info.get("team"), "Both"]:
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=message,
                    reply_markup=keyboard
                )
                count += 1
            except Exception as e:
                print(f"❌ Помилка надсилання голосування до {uid}: {e}")

    return count


async def handle_general_vote_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split("_")
    vote_id = data_parts[2]
    response_type = data_parts[3]

    user_id = str(query.from_user.id)
    users = load_data("users", {})
    user_name = users.get(user_id, {}).get("name", "Невідомий")

    votes = load_data(GENERAL_VOTES_FILE, {})
    if vote_id not in votes:
        await query.edit_message_text("⚠️ Голосування не знайдено.")
        return

    vote_data = votes[vote_id]

    if not vote_data.get("is_active", True):
        await query.edit_message_text("⚠️ Це голосування вже закрито.")
        return

    responses = load_data(GENERAL_VOTE_RESPONSES_FILE, {})
    if vote_id not in responses:
        responses[vote_id] = {}

    if response_type == "text":
        context.user_data[f"text_vote_{vote_id}"] = True
        await query.edit_message_text(
            f"Введіть вашу відповідь на питання:\n\n{vote_data['question']}"
        )
        return

    elif response_type in ["yes", "no"]:
        response_value = "Так" if response_type == "yes" else "Ні"

        responses[vote_id][user_id] = {
            "name": user_name,
            "response": response_value,
            "timestamp": datetime.datetime.now().isoformat()
        }
        save_data(responses, GENERAL_VOTE_RESPONSES_FILE)

        await query.edit_message_text(f"✅ Ваш голос '{response_value}' збережено!")

    elif response_type == "option":
        option_index = int(data_parts[4])
        option_value = vote_data["options"][option_index]

        if vote_data["type"] == VoteType.MULTIPLE_CHOICE_SINGLE:
            responses[vote_id][user_id] = {
                "name": user_name,
                "response": option_value,
                "timestamp": datetime.datetime.now().isoformat()
            }
            save_data(responses, GENERAL_VOTE_RESPONSES_FILE)
            await query.edit_message_text(f"✅ Ваш вибір '{option_value}' збережено!")

        elif vote_data["type"] == VoteType.MULTIPLE_CHOICE_MULTI:
            if f"multi_vote_{vote_id}" not in context.user_data:
                context.user_data[f"multi_vote_{vote_id}"] = set()

            selected = context.user_data[f"multi_vote_{vote_id}"]
            if option_value in selected:
                selected.remove(option_value)
            else:
                selected.add(option_value)
            buttons = []
            for i, option in enumerate(vote_data["options"]):
                prefix = "☑️" if option in selected else "☐"
                buttons.append([InlineKeyboardButton(
                    f"{prefix} {i + 1}. {option}",
                    callback_data=f"general_vote_{vote_id}_option_{i}"
                )])

            buttons.append(
                [InlineKeyboardButton("✅ Підтвердити вибір", callback_data=f"general_vote_{vote_id}_confirm")])

            await query.edit_message_text(
                f"{vote_data['question']}\n\n"
                f"Оберіть один або кілька варіантів, потім натисніть 'Підтвердити вибір':",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    elif response_type == "confirm":
        if f"multi_vote_{vote_id}" in context.user_data:
            selected = list(context.user_data[f"multi_vote_{vote_id}"])
            if selected:
                response_value = ", ".join(selected)

                responses[vote_id][user_id] = {
                    "name": user_name,
                    "response": response_value,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                save_data(responses, GENERAL_VOTE_RESPONSES_FILE)

                del context.user_data[f"multi_vote_{vote_id}"]

                await query.edit_message_text(f"✅ Ваш вибір '{response_value}' збережено!")
            else:
                await query.answer("⚠️ Оберіть хоча б один варіант!", show_alert=True)
        else:
            await query.edit_message_text("⚠️ Помилка: дані не знайдено.")


async def handle_text_vote_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    active_vote = None
    for key in context.user_data:
        if key.startswith("text_vote_"):
            vote_id = key.replace("text_vote_", "")
            active_vote = vote_id
            del context.user_data[key]
            break

    if not active_vote:
        return

    users = load_data("users", {})
    user_name = users.get(user_id, {}).get("name", "Невідомий")

    votes = load_data(GENERAL_VOTES_FILE, {})
    vote_data = votes.get(active_vote)

    if not vote_data:
        await update.message.reply_text("⚠️ Голосування не знайдено.")
        return

    responses = load_data(GENERAL_VOTE_RESPONSES_FILE, {})
    if active_vote not in responses:
        responses[active_vote] = {}

    responses[active_vote][user_id] = {
        "name": user_name,
        "response": update.message.text,
        "timestamp": datetime.datetime.now().isoformat()
    }
    save_data(responses, GENERAL_VOTE_RESPONSES_FILE)

    await update.message.reply_text("✅ Вашу відповідь збережено!")


async def close_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ У вас немає прав для закриття голосувань.")
        return

    if not context.args:
        await update.message.reply_text(
            "Використання: /close_vote [ID_голосування]\n"
            "Щоб побачити активні голосування, використайте /view_votes"
        )
        return

    vote_id = context.args[0]
    votes = load_data(GENERAL_VOTES_FILE, {})

    if vote_id not in votes:
        await update.message.reply_text("⚠️ Голосування з таким ID не знайдено.")
        return

    votes[vote_id]["is_active"] = False
    save_data(votes, GENERAL_VOTES_FILE)

    await update.message.reply_text(f"✅ Голосування {vote_id} закрито.")


async def vote_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed results for a specific vote"""
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ У вас немає прав для перегляду детальних результатів.")
        return

    if not context.args:
        await update.message.reply_text(
            "Використання: /vote_results [ID_голосування]\n"
            "Щоб побачити всі голосування, використайте /view_votes"
        )
        return

    vote_id = context.args[0]
    votes = load_data(GENERAL_VOTES_FILE, {})
    responses = load_data(GENERAL_VOTE_RESPONSES_FILE, {})

    if vote_id not in votes:
        await update.message.reply_text("⚠️ Голосування з таким ID не знайдено.")
        return

    vote_data = votes[vote_id]
    vote_responses = responses.get(vote_id, {})

    # Format results
    message = f"📊 Результати голосування\n\n"
    message += f"🆔 ID: {vote_id}\n"
    message += f"❓ Питання: {vote_data['question']}\n"
    message += f"👥 Всього відповідей: {len(vote_responses)}\n"
    message += f"✅ Статус: {'Активне' if vote_data.get('is_active', True) else 'Закрито'}\n\n"

    if vote_data["type"] == VoteType.YES_NO:
        yes_count = sum(1 for r in vote_responses.values() if r["response"] == "Так")
        no_count = len(vote_responses) - yes_count
        message += f"✅ Так: {yes_count}\n❌ Ні: {no_count}\n\n"

        # Always show names
        yes_names = [r["name"] for r in vote_responses.values() if r["response"] == "Так"]
        no_names = [r["name"] for r in vote_responses.values() if r["response"] == "Ні"]

        if yes_names:
            message += f"✅ Так: {', '.join(yes_names)}\n"
        if no_names:
            message += f"❌ Ні: {', '.join(no_names)}\n"

    elif vote_data["type"] in [VoteType.MULTIPLE_CHOICE_SINGLE, VoteType.MULTIPLE_CHOICE_MULTI]:
        # Count responses for each option
        option_counts = {}
        for option in vote_data["options"]:
            option_counts[option] = 0

        for response in vote_responses.values():
            if vote_data["type"] == VoteType.MULTIPLE_CHOICE_MULTI:
                # Split by comma for multi-select
                selected_options = [opt.strip() for opt in response["response"].split(",")]
                for opt in selected_options:
                    if opt in option_counts:
                        option_counts[opt] += 1
            else:
                # Single choice
                if response["response"] in option_counts:
                    option_counts[response["response"]] += 1

        for option, count in option_counts.items():
            percentage = (count / len(vote_responses) * 100) if vote_responses else 0
            message += f"• {option}: {count} ({percentage:.1f}%)\n"

        # Always show detailed responses with names
        message += "\n📝 Детальні відповіді:\n"
        for response in vote_responses.values():
            message += f"• {response['name']}: {response['response']}\n"

    else:  # TEXT_RESPONSE
        message += "Відповіді:\n\n"
        for i, response in enumerate(vote_responses.values(), 1):
            message += f"{i}. {response['name']}: {response['response']}\n\n"

    # Split long messages
    if len(message) > 4000:
        parts = [message[i:i + 4000] for i in range(0, len(message), 4000)]
        for part in parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(message)


async def cancel_vote_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel vote creation"""
    await update.message.reply_text("❌ Створення голосування скасовано.")
    return ConversationHandler.END


# Conversation handler for creating votes
def create_general_vote_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("create_vote", create_vote)],
        states={
            VOTE_TYPE: [CallbackQueryHandler(handle_vote_type, pattern=r"^vote_type_")],
            VOTE_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vote_question)],
            VOTE_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vote_options)],
            VOTE_TEAM: [CallbackQueryHandler(handle_vote_team, pattern=r"^general_vote_team_")]
        },
        fallbacks=[CommandHandler("cancel", cancel_vote_creation)]
    )


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
    # Check for unpaid payments
    payments = load_data("payments", {})
    unpaid = [p for p in payments.values() if p["user_id"] == user_id and not p.get("paid", False)]

    if len(unpaid) >= 2:
        await update.message.reply_text(
            "❌ У тебе два або більше неоплачених тренувань. Спочатку погаси борг через /pay_debt.")
        return
    elif len(unpaid) == 1:
        await update.message.reply_text(
            "⚠️ У тебе є неоплачене тренування. Будь ласка, погаси борг через /pay_debt якнайшвидше.")

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
            voting_started = ((today.weekday() - start_voting) % 7) <= 6
            if voting_started:
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
        button_text = f"{date_str} {time_str}"

        extra_info = []

        # Add coach info
        if t.get("with_coach"):
            extra_info.append("З тренером")

        # Add location
        location = t.get("location", "")
        if location and location.lower() != "наукма" and not location.startswith("http"):
            extra_info.append(location)

        # Add description
        description = t.get("description", "")
        if description:
            extra_info.append(description)

        if extra_info:
            button_text += f" ({' - '.join(extra_info)})"

        keyboard.append(
            [InlineKeyboardButton(button_text, callback_data=f"training_vote_{idx}")])

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

    def get_training_info(training_id):
        if training_id.startswith("const_"):
            for tid, tr in constant.items():
                tr_id = f"const_{tr['weekday']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                if tr_id == training_id:
                    return tr
        else:
            for tid, tr in one_time.items():
                tr_id = f"{tr['date']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                if tr_id == training_id:
                    return tr
        return {}

    keyboard = []
    for i, tid in enumerate(context.user_data["view_votes_options"]):
        training_info = get_training_info(tid)

        base_label = format_training_id(tid)

        extra_info = []

        team = training_info.get("team", "Both")
        if team == "Male":
            extra_info.append("чоловіча команда")
        elif team == "Female":
            extra_info.append("жіноча команда")

        if training_info.get("with_coach"):
            extra_info.append("З тренером")

        location = training_info.get("location", "")
        if location and location.lower() != "наукма" and not location.startswith("http"):
            extra_info.append(location)

        description = training_info.get("description", "")
        if description:
            extra_info.append(description)

        if extra_info:
            label = f"{base_label} ({' - '.join(extra_info)})"
        else:
            label = base_label

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


def format_training_id(tid: str) -> str:
    if tid.startswith("Понеділок") or tid.startswith("const_"):
        try:
            if tid.startswith("const_"):
                parts = tid.split("_")
                weekday_index = int(parts[1])
                time_str = parts[2]
                return f"{WEEKDAYS[weekday_index]} о {time_str}"
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
