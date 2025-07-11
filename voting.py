import datetime
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, \
    filters, ConversationHandler

from data import load_data, save_data
from validation import is_authorized

VOTE_TYPE, VOTE_QUESTION, VOTE_OPTIONS, VOTE_TEAM = range(200, 204)
VOTE_OTHER_NAME, VOTE_OTHER_SELECT = range(2)
WEEKDAYS = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
VOTES_FILE = "training_votes"
REGISTRATION_FILE = "users"
TRAINING_VOTES_FILE = "votes"
GENERAL_FILE = "general"
GENERAL_VOTES_FILE = "general_votes"
GAMES_FILE = "games"
GAME_VOTES_FILE = "game_votes"
DEFAULT_VOTES_STRUCTURE = {"votes": {}}
VOTES_LIMIT = 14
ONE_TIME_TRAININGS_FILE = "one_time_trainings"
CONSTANT_TRAININGS_FILE = "constant_trainings"


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

    def add_vote_type_keyboard(self):
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


class UnifiedVoteManager:
    def __init__(self):
        self.vote_types = {
            "training": "🏐 Тренування",
            "game": "🏆 Гра",
            "general": "📊 Загальне голосування"
        }

    def get_all_available_votes(self, user_id: str, user_team: str):
        all_votes = []

        training_votes = self._get_training_votes(user_id, user_team)
        all_votes.extend(training_votes)

        game_votes = self._get_game_votes(user_id, user_team)
        all_votes.extend(game_votes)

        general_votes = self._get_general_votes(user_id, user_team)
        all_votes.extend(general_votes)

        return all_votes

    def _get_training_votes(self, user_id: str, user_team: str):
        one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE, {})
        constant_trainings = load_data(CONSTANT_TRAININGS_FILE, {})

        training_votes = []
        votes_data = load_data(TRAINING_VOTES_FILE, DEFAULT_VOTES_STRUCTURE)

        for training_id, training in one_time_trainings.items():
            if training.get("team") not in [user_team, "Both"]:
                continue

            if not training.get("voting_opened", False):
                continue

            vote_id = f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"

            yes_votes = 0
            if vote_id in votes_data["votes"]:
                yes_votes = sum(1 for v in votes_data["votes"][vote_id].values() if v["vote"] == "yes")

            if yes_votes < VOTES_LIMIT:
                label = self._format_training_label(training, vote_id)
                training_votes.append({
                    "type": "training",
                    "id": vote_id,
                    "label": label,
                    "data": training
                })

        for training_id, training in constant_trainings.items():
            if training.get("team") not in [user_team, "Both"]:
                continue

            if not training.get("voting_opened", False):
                continue

            vote_id = f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"

            yes_votes = 0
            if vote_id in votes_data["votes"]:
                yes_votes = sum(1 for v in votes_data["votes"][vote_id].values() if v["vote"] == "yes")

            if yes_votes < VOTES_LIMIT:
                label = self._format_training_label(training, vote_id)
                training_votes.append({
                    "type": "training",
                    "id": vote_id,
                    "label": label,
                    "data": training
                })

        return training_votes

    def _get_game_votes(self, user_id: str, user_team: str):
        games = load_data(GAMES_FILE, {})
        now = datetime.datetime.now()
        game_votes = []

        for game in games.values():
            if game.get("team") not in [user_team, "Both"]:
                continue

            try:
                game_datetime = datetime.datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
                if game_datetime > now:
                    game_id = game['id']
                    label = self._format_game_label(game)
                    game_votes.append({
                        "type": "game",
                        "id": game_id,
                        "label": label,
                        "data": game
                    })
            except ValueError:
                continue

        return game_votes

    def _get_general_votes(self, user_id: str, user_team: str):
        votes = load_data(GENERAL_FILE, {})
        general_votes = []

        for vote_id, vote_data in votes.items():
            if not vote_data.get("is_active", True):
                continue

            if vote_data.get("team") not in [user_team, "Both"]:
                continue

            label = f"📊 {vote_data['question'][:50]}{'...' if len(vote_data['question']) > 50 else ''}"
            general_votes.append({
                "type": "general",
                "id": vote_id,
                "label": label,
                "data": vote_data
            })

        return general_votes

    def _format_training_label(self, training, training_id):
        if training.get("type") == "one-time" or "const_" not in training_id:
            date_str = training.get("date", "")
        else:
            weekday = training.get("weekday", 0)
            date_str = WEEKDAYS[weekday] if 0 <= weekday < len(WEEKDAYS) else "Невідомо"

        time_str = f"{training['start_hour']:02d}:{training['start_min']:02d}"
        base_label = f"🏐 {date_str} {time_str}"

        extra_info = []
        if training.get("with_coach"):
            extra_info.append("З тренером")

        location = training.get("location", "")
        if location and location.lower() != "наукма" and not location.startswith("http"):
            if "(" in location and "http" in location:
                clean_location = location.split("(")[0].strip()
                if clean_location and clean_location.lower() != "наукма":
                    extra_info.append(clean_location)
            extra_info.append(location)

        description = training.get("description", "")
        if description:
            extra_info.append(description)

        if extra_info:
            base_label += f" ({' - '.join(extra_info)})"

        return base_label

    def _format_game_label(self, game):
        type_names = {
            "friendly": "Товариський матч",
            "tournament": "Турнір",
            "league": "Чемпіонат/Ліга",
            "training_match": "Тренувальний матч"
        }

        type_name = type_names.get(game.get('type'), game.get('type', 'Гра'))
        label = f"🏆 {type_name} - {game['date']} {game['time']}"
        label += f" проти {game['opponent']}"

        return label


unified_vote_manager = UnifiedVoteManager()


async def unified_vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = load_data(REGISTRATION_FILE)

    if user_id not in user_data or "team" not in user_data[user_id]:
        await update.message.reply_text("Будь ласка, завершіть реєстрацію перед голосуванням.")
        return

    payments = load_data("payments", {})
    unpaid = [p for p in payments.values() if p["user_id"] == user_id and not p.get("paid", False)]

    if len(unpaid) >= 2:
        await update.message.reply_text(
            "❌ У тебе два або більше неоплачених тренувань. Спочатку погаси борг через /pay_debt.")
        return
    elif len(unpaid) == 1:
        await update.message.reply_text(
            "⚠️ У тебе є неоплачене тренування. Будь ласка, погаси борг через /pay_debt якнайшвидше.")

    user_team = user_data[user_id]["team"]
    all_votes = unified_vote_manager.get_all_available_votes(user_id, user_team)

    if not all_votes:
        await update.message.reply_text("Наразі немає доступних голосувань.")
        return

    keyboard = []
    context.user_data["unified_vote_options"] = all_votes

    for idx, vote in enumerate(all_votes):
        keyboard.append([InlineKeyboardButton(vote["label"], callback_data=f"unified_vote_{idx}")])

    await update.message.reply_text(
        "📊 Доступні голосування:\n\nОберіть голосування:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_unified_vote_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("unified_vote_", ""))
    vote_options = context.user_data.get("unified_vote_options", [])

    if idx >= len(vote_options):
        await query.edit_message_text("⚠️ Помилка: вибране голосування більше не доступне.")
        return

    selected_vote = vote_options[idx]
    vote_type = selected_vote["type"]
    vote_id = selected_vote["id"]
    vote_data = selected_vote["data"]

    if vote_type == "training":
        await handle_training_vote_interaction(query, context, vote_id, vote_data)
    elif vote_type == "game":
        await handle_game_vote_interaction(query, context, vote_id, vote_data)
    elif vote_type == "general":
        await handle_general_vote_interaction(query, context, vote_id, vote_data)


async def handle_training_vote_interaction(query, context, training_id, training_data):
    user_id = str(query.from_user.id)

    votes = load_data(TRAINING_VOTES_FILE, DEFAULT_VOTES_STRUCTURE)
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

    message = f"🏐 Тренування: {training_info}\n"
    if current_vote:
        message += f"Ваш поточний голос: {'БУДУ' if current_vote == 'yes' else 'НЕ БУДУ'}\n"
    message += "Чи будете на тренуванні?"

    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_game_vote_interaction(query, context, game_id, game_data):
    user_id = str(query.from_user.id)

    keyboard = [
        [
            InlineKeyboardButton("✅ Буду", callback_data=f"game_vote_yes_{game_id}"),
            InlineKeyboardButton("❌ Не буду", callback_data=f"game_vote_no_{game_id}")
        ]
    ]

    type_names = {
        "friendly": "Товариський матч",
        "tournament": "Турнір",
        "league": "Чемпіонат/Ліга",
        "training_match": "Тренувальний матч"
    }

    type_name = type_names.get(game_data.get('type'), game_data.get('type', 'Гра'))

    message = f"🏆 {type_name}\n\n"
    message += f"📅 {game_data['date']} о {game_data['time']}\n"
    message += f"🏆 Проти: {game_data['opponent']}\n"
    message += f"📍 Місце: {game_data['location']}\n\n"

    game_votes = load_data(GAME_VOTES_FILE, {"votes": {}})  # Add default structure
    if game_id in game_votes["votes"] and user_id in game_votes["votes"][game_id]:  # Add ["votes"]
        current_vote = game_votes["votes"][game_id][user_id]["vote"]  # Add ["votes"]
        message += f"Ваш поточний голос: {'БУДУ' if current_vote == 'yes' else 'НЕ БУДУ'}\n"

    message += "Чи будете брати участь у цій грі?"

    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_general_vote_interaction(query, context, vote_id, vote_data):
    user_id = str(query.from_user.id)

    if vote_data["type"] == "yes_no":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Так", callback_data=f"general_vote_{vote_id}_yes"),
                InlineKeyboardButton("❌ Ні", callback_data=f"general_vote_{vote_id}_no")
            ]
        ])
    elif vote_data["type"] in ["multiple_choice_single", "multiple_choice_multi"]:
        buttons = []
        for i, option in enumerate(vote_data["options"]):
            buttons.append([InlineKeyboardButton(
                f"{i + 1}. {option}",
                callback_data=f"general_vote_{vote_id}_option_{i}"
            )])

        if vote_data["type"] == "multiple_choice_multi":
            buttons.append(
                [InlineKeyboardButton("✅ Підтвердити вибір", callback_data=f"general_vote_{vote_id}_confirm")])

        keyboard = InlineKeyboardMarkup(buttons)
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Відповісти", callback_data=f"general_vote_{vote_id}_text")]
        ])

    message = f"📊 {vote_data['question']}\n\n"

    if vote_data["type"] == "text_response":
        message += "Натисніть кнопку нижче, щоб залишити відповідь."
    elif vote_data["type"] == "multiple_choice_multi":
        message += "Оберіть один або кілька варіантів, потім натисніть 'Підтвердити вибір':"
    else:
        message += "Оберіть ваш варіант:"

    responses = load_data(GENERAL_VOTES_FILE, {"votes": {}})
    if vote_id in responses["votes"] and user_id in responses["votes"][vote_id]:
        current_response = responses["votes"][vote_id][user_id]["response"]
        message += f"\n\nВаша поточна відповідь: {current_response}"

    await query.edit_message_text(message, reply_markup=keyboard)


def format_training_id(tid: str) -> str:
    if tid.startswith("const_"):
        try:
            parts = tid.split("_")
            weekday_index = int(parts[1])
            time_str = parts[2]
            return f"{WEEKDAYS[weekday_index]} о {time_str}"
        except:
            return tid
    else:
        try:
            return f"{tid[:10]} о {tid[11:]}"
        except:
            return tid


async def add_vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ У вас немає прав для створення голосувань.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Створення нового голосування\n\nОберіть тип голосування:",
        reply_markup=vote_manager.add_vote_type_keyboard()
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

    votes = load_data(GENERAL_FILE, {})
    if votes:
        vote_id = str(max(int(k) for k in votes.keys()) + 1)
    else:
        vote_id = "1"

    vote_data = {
        "vote_id": vote_id,
        "question": context.user_data['general_vote_question'],
        "type": context.user_data['general_vote_type'],
        "options": context.user_data.get('general_vote_options', []),
        "team": team,
        "creator_id": str(query.from_user.id),
        "is_active": True
    }

    votes[vote_id] = vote_data
    save_data(votes, GENERAL_FILE)

    await send_vote_to_users(context, vote_data, vote_id)

    team_display = {"Male": "чоловічої команди", "Female": "жіночої команди", "Both": "обох команд"}[team]

    await query.edit_message_text(
        f"✅ Голосування створено!\n\n"
        f"Питання: {vote_data['question']}\n"
        f"Команда: {team_display}\n\n"
        f"Повідомлення надіслано учасникам команди.\n\n"
    )

    return ConversationHandler.END


async def send_vote_to_users(context: ContextTypes.DEFAULT_TYPE, vote_data: dict, vote_id: str):
    users = load_data("users", {})

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

    votes = load_data(GENERAL_FILE, {})
    if vote_id not in votes:
        await query.edit_message_text("⚠️ Голосування не знайдено.")
        return

    vote_data = votes[vote_id]

    if not vote_data.get("is_active", True):
        await query.edit_message_text("⚠️ Це голосування вже закрито.")
        return

    responses = load_data(GENERAL_VOTES_FILE, {"votes": {}})
    if vote_id not in responses["votes"]:
        responses["votes"][vote_id] = {}

    if response_type == "text":
        context.user_data[f"text_vote_{vote_id}"] = True
        await query.edit_message_text(
            f"Введіть вашу відповідь на питання:\n\n{vote_data['question']}"
        )
        return

    elif response_type in ["yes", "no"]:
        response_value = "Так" if response_type == "yes" else "Ні"

        responses["votes"][vote_id][user_id] = {
            "name": user_name,
            "response": response_value,
        }
        save_data(responses, GENERAL_VOTES_FILE)

        await query.edit_message_text(f"✅ Ваш голос '{response_value}' збережено!")

    elif response_type == "option":
        option_index = int(data_parts[4])
        option_value = vote_data["options"][option_index]

        if vote_data["type"] == VoteType.MULTIPLE_CHOICE_SINGLE:
            responses["votes"][vote_id][user_id] = {
                "name": user_name,
                "response": option_value,
            }
            save_data(responses, GENERAL_VOTES_FILE)
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

                responses["votes"][vote_id][user_id] = {
                    "name": user_name,
                    "response": response_value,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                save_data(responses, GENERAL_VOTES_FILE)

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

    votes = load_data(GENERAL_FILE, {})
    vote_data = votes.get(active_vote)

    if not vote_data:
        await update.message.reply_text("⚠️ Голосування не знайдено.")
        return

    responses = load_data(GENERAL_VOTES_FILE, {"votes": {}})
    if active_vote not in responses["votes"]:
        responses["votes"][active_vote] = {}

    responses["votes"][active_vote][user_id] = {
        "name": user_name,
        "response": update.message.text,
        "timestamp": datetime.datetime.now().isoformat()
    }
    save_data(responses, GENERAL_VOTES_FILE)

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
    votes = load_data(GENERAL_FILE, {})

    if vote_id not in votes:
        await update.message.reply_text("⚠️ Голосування з таким ID не знайдено.")
        return

    votes[vote_id]["is_active"] = False
    save_data(votes, GENERAL_FILE)

    await update.message.reply_text(f"✅ Голосування {vote_id} закрито.")


async def cancel_vote_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Створення голосування скасовано.")
    return ConversationHandler.END


async def vote_for(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("У вас немає прав для цієї команди.")
        return ConversationHandler.END

    user_data = load_data("users")
    admin_id = str(update.message.from_user.id)
    admin_team = user_data.get(admin_id, {}).get("team", "Both")
    context.user_data["admin_team"] = admin_team

    await update.message.reply_text("Введіть ім'я або прізвище людини, за яку ви хочете проголосувати:")
    return VOTE_OTHER_NAME


async def vote_other_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["vote_other_name"] = name
    context.user_data["vote_other_id"] = f"admin_{uuid.uuid4().hex[:8]}"

    admin_team = context.user_data.get("admin_team", "Both")

    all_votes = []

    unified_manager = UnifiedVoteManager()
    training_votes = unified_manager._get_training_votes("", admin_team)

    for training_vote in training_votes:
        training_id = training_vote["id"]
        label = training_vote["label"]
        training_data = training_vote["data"]
        all_votes.append(("training", training_id, label, training_data))

    games = load_data(GAMES_FILE, {})
    now = datetime.datetime.now()

    for game in games.values():
        if game.get("team") not in [admin_team, "Both"]:
            continue

        try:
            game_datetime = datetime.datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
            if game_datetime > now:
                type_names = {
                    "friendly": "Товариський матч",
                    "tournament": "Турнір",
                    "league": "Чемпіонат/Ліга",
                    "training_match": "Тренувальний матч"
                }
                type_name = type_names.get(game.get('type'), game.get('type', 'Гра'))
                label = f"🏆 {type_name} - {game['date']} {game['time']} проти {game['opponent']}"
                all_votes.append(("game", game['id'], label, game))
        except ValueError:
            continue

    general_votes = load_data(GENERAL_FILE, {})
    for vote_id, vote_data in general_votes.items():
        if not vote_data.get("is_active", True):
            continue
        if vote_data.get("team") not in [admin_team, "Both"]:
            continue

        label = f"📊 {vote_data['question'][:50]}{'...' if len(vote_data['question']) > 50 else ''}"
        all_votes.append(("general", vote_id, label, vote_data))

    if not all_votes:
        await update.message.reply_text("Немає доступних голосувань.")
        return ConversationHandler.END

    context.user_data["vote_other_options"] = all_votes

    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"vote_other_{i}")]
        for i, (_, _, label, _) in enumerate(all_votes)
    ]

    await update.message.reply_text(
        f"Ви голосуєте за: {name}\n\n📊 Оберіть голосування:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VOTE_OTHER_SELECT


async def handle_vote_other_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("vote_other_", ""))
    options = context.user_data.get("vote_other_options", [])

    if idx >= len(options):
        await query.edit_message_text("⚠️ Помилка: вибране голосування більше не доступне.")
        return ConversationHandler.END

    vote_type, vote_id, label, vote_data = options[idx]
    name = context.user_data["vote_other_name"]

    context.user_data["vote_other_type"] = vote_type
    context.user_data["vote_other_vote_id"] = vote_id
    context.user_data["vote_other_vote_data"] = vote_data

    if vote_type == "training":
        keyboard = [
            [
                InlineKeyboardButton("✅ Так (БУДЕ)", callback_data="vote_other_cast_yes"),
                InlineKeyboardButton("❌ Ні (НЕ БУДЕ)", callback_data="vote_other_cast_no")
            ]
        ]
        message = f"Голосування за: {name}\n🏐 Тренування: {format_training_id(vote_id)}\n\nЯкий голос поставити?"

    elif vote_type == "game":
        keyboard = [
            [
                InlineKeyboardButton("✅ Так (БУДЕ)", callback_data="vote_other_cast_yes"),
                InlineKeyboardButton("❌ Ні (НЕ БУДЕ)", callback_data="vote_other_cast_no")
            ]
        ]
        type_names = {
            "friendly": "Товариський матч",
            "tournament": "Турнір",
            "league": "Чемпіонат/Ліга",
            "training_match": "Тренувальний матч"
        }
        type_name = type_names.get(vote_data.get('type'), vote_data.get('type', 'Гра'))
        message = f"Голосування за: {name}\n🏆 {type_name}\n📅 {vote_data['date']} о {vote_data['time']}\n🏆 Проти: {vote_data['opponent']}\n\nЯкий голос поставити?"

    elif vote_type == "general":
        if vote_data["type"] == "yes_no":
            keyboard = [
                [
                    InlineKeyboardButton("✅ Так", callback_data="vote_other_cast_yes"),
                    InlineKeyboardButton("❌ Ні", callback_data="vote_other_cast_no")
                ]
            ]
            message = f"Голосування за: {name}\n📊 {vote_data['question']}\n\nЯкий голос поставити?"

        elif vote_data["type"] in ["multiple_choice_single", "multiple_choice_multi"]:
            keyboard = []
            for i, option in enumerate(vote_data["options"]):
                keyboard.append([InlineKeyboardButton(
                    f"{i + 1}. {option}",
                    callback_data=f"vote_other_cast_option_{i}"
                )])
            message = f"Голосування за: {name}\n📊 {vote_data['question']}\n\nОберіть варіант:"

        else:  # text_response
            await query.edit_message_text(
                f"Голосування за: {name}\n📊 {vote_data['question']}\n\nВведіть текстову відповідь у наступному повідомленні:"
            )
            return ConversationHandler.END

    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_vote_other_cast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def save_general_response(vote_id: str, user_id: str, name: str, response: str):
        responses = load_data(GENERAL_VOTES_FILE, {"votes": {}})
        if vote_id not in responses["votes"]:
            responses["votes"][vote_id] = {}
        responses["votes"][vote_id][user_id] = {
            "name": name,
            "response": response,
        }
        save_data(responses, GENERAL_VOTES_FILE)

    async def save_training_vote(vote_id: str, user_id: str, name: str, vote: str):
        votes = load_data(TRAINING_VOTES_FILE, DEFAULT_VOTES_STRUCTURE)
        if vote_id not in votes["votes"]:
            votes["votes"][vote_id] = {}
        votes["votes"][vote_id][user_id] = {"name": name, "vote": vote}
        save_data(votes, TRAINING_VOTES_FILE)

    async def save_game_vote(vote_id: str, user_id: str, name: str, vote: str):
        game_votes = load_data(GAME_VOTES_FILE, {"votes": {}})
        if vote_id not in game_votes["votes"]:
            game_votes["votes"][vote_id] = {}
        game_votes["votes"][vote_id][user_id] = {
            "name": name,
            "vote": vote,
        }
        save_data(game_votes, GAME_VOTES_FILE)

    if hasattr(update, 'message') and update.message:
        name = context.user_data["vote_other_name"]
        vote_id = context.user_data["vote_other_vote_id"]
        user_id = context.user_data["vote_other_id"]
        response_text = update.message.text

        await save_general_response(vote_id, user_id, name, response_text)
        await update.message.reply_text(f"✅ Текстова відповідь за '{name}' збережена: '{response_text}'")
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()

    name = context.user_data["vote_other_name"]
    vote_type = context.user_data["vote_other_type"]
    vote_id = context.user_data["vote_other_vote_id"]
    vote_data = context.user_data["vote_other_vote_data"]
    user_id = context.user_data["vote_other_id"]

    if query.data.startswith("vote_other_cast_option_"):
        option_idx = int(query.data.replace("vote_other_cast_option_", ""))
        response_value = vote_data["options"][option_idx]

        if vote_data["type"] == "multiple_choice_single":
            await save_general_response(vote_id, user_id, name, response_value)
            await query.edit_message_text(f"✅ Голос за '{name}' збережено як '{response_value}'")

        elif vote_data["type"] == "multiple_choice_multi":
            multi_key = f"vote_other_multi_{vote_id}"
            if multi_key not in context.user_data:
                context.user_data[multi_key] = []

            selected = context.user_data[multi_key]
            if response_value in selected:
                selected.remove(response_value)
            else:
                selected.append(response_value)

            keyboard = []
            for i, option in enumerate(vote_data["options"]):
                prefix = "☑️" if option in selected else "☐"
                keyboard.append([InlineKeyboardButton(
                    f"{prefix} {i + 1}. {option}",
                    callback_data=f"vote_other_cast_option_{i}"
                )])
            keyboard.append([InlineKeyboardButton(
                "✅ Підтвердити вибір",
                callback_data="vote_other_cast_multi_confirm"
            )])

            await query.edit_message_text(
                f"Голосування за: {name}\n📊 {vote_data['question']}\n\nОберіть варіанти:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "vote_other_cast_multi_confirm":
        multi_key = f"vote_other_multi_{vote_id}"
        selected = context.user_data.get(multi_key, [])

        if selected:
            response_value = ", ".join(selected)
            await save_general_response(vote_id, user_id, name, response_value)

            if multi_key in context.user_data:
                del context.user_data[multi_key]

            await query.edit_message_text(f"✅ Множинний вибір за '{name}' збережено: '{response_value}'")
        else:
            await query.answer("⚠️ Оберіть хоча б один варіант!", show_alert=True)
            return

    elif query.data in ["vote_other_cast_yes", "vote_other_cast_no"]:
        is_yes = query.data == "vote_other_cast_yes"

        if vote_type == "training":
            vote_value = "yes" if is_yes else "no"
            await save_training_vote(vote_id, user_id, name, vote_value)
            action = "БУДЕ" if is_yes else "НЕ БУДЕ"
            await query.edit_message_text(
                f"✅ Голос за '{name}' збережено як '{action}' на тренування {format_training_id(vote_id)}")

        elif vote_type == "game":
            vote_value = "yes" if is_yes else "no"
            await save_game_vote(vote_id, user_id, name, vote_value)
            action = "БУДЕ" if is_yes else "НЕ БУДЕ"
            await query.edit_message_text(f"✅ Голос за '{name}' збережено як '{action}' на гру")

        elif vote_type == "general":
            response_value = "Так" if is_yes else "Ні"
            await save_general_response(vote_id, user_id, name, response_value)
            await query.edit_message_text(f"✅ Голос за '{name}' збережено як '{response_value}'")

    return ConversationHandler.END


def generate_training_id(training):
    if training["type"] == "one-time":
        return f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"
    else:
        return f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"


async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    vote = data[1]
    training_id = "_".join(data[2:])

    user_id = str(query.from_user.id)
    user_data = load_data(REGISTRATION_FILE)
    user_name = user_data.get(user_id, {}).get("name", "Невідомий користувач")

    votes = load_data('votes', DEFAULT_VOTES_STRUCTURE)

    if training_id not in votes["votes"]:
        votes["votes"][training_id] = {}
    current_yes_votes = sum(1 for v in votes["votes"][training_id].values() if v["vote"] == "yes")

    changing_to_yes = (
            vote == "yes" and
            user_id in votes["votes"][training_id] and
            votes["votes"][training_id][user_id]["vote"] == "no"
    )

    if vote == "yes" and current_yes_votes >= VOTES_LIMIT and (
            user_id not in votes["votes"][training_id] or changing_to_yes):
        await query.edit_message_text("⚠️ Досягнуто максимум голосів 'так'. Ви не можете проголосувати.")
        return

    votes["votes"][training_id][user_id] = {"name": user_name, "vote": vote}
    save_data(votes, 'votes')

    updated_yes_votes = sum(1 for v in votes["votes"][training_id].values() if v["vote"] == "yes")

    message = f"Ваш голос: {'БУДУ' if vote == 'yes' else 'НЕ БУДУ'} записано!"

    if updated_yes_votes == VOTES_LIMIT:
        message += "\n⚠️ Досягнуто максимум учасників."

    await query.edit_message_text(message)


def is_vote_active(vote_id, today):
    if "const_" in vote_id:
        return True
    try:
        date = datetime.datetime.strptime(vote_id.split("_")[0], "%d.%m.%Y").date()
        return today <= date
    except Exception:
        return False


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

    old_team = trainings[tid]["team"]

    trainings[tid]["team"] = "Both"
    save_data(trainings, "one_time_trainings" if ttype == "one_time" else "constant_trainings")

    await notify_team_about_unlock(context, trainings[tid], tid, ttype, old_team)

    await query.edit_message_text("✅ Тренування оновлено. Тепер обидві команди можуть голосувати.")


async def notify_team_about_unlock(context, training, training_id, training_type, old_team):
    users = load_data("users", {})

    target_team = "Female" if old_team == "Male" else "Male"

    if training_type == "one_time":
        date_str = training['date']
        vote_id = f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"
    else:
        weekdays = ["понеділок", "вівторок", "середу", "четвер", "п'ятницю", "суботу", "неділю"]
        date_str = weekdays[training['weekday']]
        vote_id = f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"

    start_time = f"{training['start_hour']:02d}:{training['start_min']:02d}"
    end_time = f"{training['end_hour']:02d}:{training['end_min']:02d}"

    coach_str = " (З тренером)" if training.get("with_coach") else ""
    location = training.get("location", "")
    location = "" if location and location.lower() == "наукма" else location
    loc_str = f"\n📍 {location}" if location else ""
    description = training.get("description", "")
    desc_str = f"\nℹ️ {description}" if description else ""

    old_team_name = "чоловічої" if old_team == "Male" else "жіночої"

    message = (
        f"🎉 Доступне нове тренування!\n\n"
        f"Тренування {'в ' if training_type == 'constant' else ''}{date_str}{coach_str}\n"
        f"⏰ З {start_time} до {end_time}"
        f"{loc_str}"
        f"{desc_str}\n\n"
        f"Це тренування було для {old_team_name} команди, але тепер відкрито для всіх!\n"
        f"Чи будете брати участь?"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Так", callback_data=f"vote_yes_{vote_id}"),
            InlineKeyboardButton("❌ Ні", callback_data=f"vote_no_{vote_id}")
        ]
    ])

    count = 0
    for uid, user_info in users.items():
        if user_info.get("team") == target_team:
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=message,
                    reply_markup=keyboard
                )
                count += 1
            except Exception as e:
                print(f"❌ UNLOCK NOTIFY: Помилка надсилання до {uid}: {e}")


class UnifiedViewManager:
    def get_all_active_votes(self):
        all_votes = []

        training_votes = self._get_active_training_votes()
        all_votes.extend(training_votes)

        game_votes = self._get_active_game_votes()
        all_votes.extend(game_votes)

        general_votes = self._get_active_general_votes()
        all_votes.extend(general_votes)

        return all_votes

    def _get_active_training_votes(self):
        one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE, {})
        constant_trainings = load_data(CONSTANT_TRAININGS_FILE, {})

        training_votes = []
        votes_data = load_data(TRAINING_VOTES_FILE, DEFAULT_VOTES_STRUCTURE)

        for training_id, training in one_time_trainings.items():
            if not training.get("voting_opened", False):
                continue

            vote_id = f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"

            if vote_id in votes_data["votes"] and votes_data["votes"][vote_id]:
                label = self._format_training_label(training, vote_id)
                training_votes.append({
                    "type": "training",
                    "id": vote_id,
                    "label": label,
                    "data": training,
                    "votes": votes_data["votes"][vote_id]
                })

        for training_id, training in constant_trainings.items():
            if not training.get("voting_opened", False):
                continue

            vote_id = f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"

            if vote_id in votes_data["votes"] and votes_data["votes"][vote_id]:
                label = self._format_training_label(training, vote_id)
                training_votes.append({
                    "type": "training",
                    "id": vote_id,
                    "label": label,
                    "data": training,
                    "votes": votes_data["votes"][vote_id]
                })

        return training_votes

    def _get_active_game_votes(self):
        games = load_data(GAMES_FILE, {})
        game_votes_data = load_data(GAME_VOTES_FILE, {"votes": {}})
        now = datetime.datetime.now()
        game_votes = []

        for game in games.values():
            try:
                game_datetime = datetime.datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
                if game_datetime > now and game['id'] in game_votes_data["votes"]:
                    label = self._format_game_label(game)
                    game_votes.append({
                        "type": "game",
                        "id": game['id'],
                        "label": label,
                        "data": game,
                        "votes": game_votes_data["votes"][game['id']]
                    })
            except ValueError:
                continue

        return game_votes

    def _get_active_general_votes(self):
        votes = load_data(GENERAL_FILE, {})
        responses = load_data(GENERAL_VOTES_FILE, {"votes": {}})
        general_votes = []

        for vote_id, vote_data in votes.items():
            if not vote_data.get("is_active", True):
                continue

            if vote_id in responses.get("votes", {}) and responses["votes"][vote_id]:
                label = f"📊 {vote_data['question'][:50]}{'...' if len(vote_data['question']) > 50 else ''}"

                team = vote_data.get("team", "Both")
                if team == "Male":
                    label += " (чоловіча)"
                elif team == "Female":
                    label += " (жіноча)"
                elif team == "Both":
                    label += " (обидві)"

                general_votes.append({
                    "type": "general",
                    "id": vote_id,
                    "label": label,
                    "data": vote_data,
                    "votes": responses["votes"][vote_id]
                })

        return general_votes

    def _is_training_active(self, training, today):
        if training["type"] == "one-time":
            try:
                training_date = datetime.datetime.strptime(training["date"], "%d.%m.%Y").date() if isinstance(
                    training["date"], str) else training["date"]
                return training_date >= today
            except:
                return False
        else:
            return True

    def _format_training_label(self, training, training_id):
        # Визначаємо тип тренування по training_id
        if "const_" in training_id:
            # Постійне тренування
            weekday = training.get("weekday", 0)
            date_str = WEEKDAYS[weekday] if 0 <= weekday < len(WEEKDAYS) else "Невідомо"
        else:
            # Одноразове тренування - date завжди рядок з бази
            date_str = training.get("date", "")

        time_str = f"{training.get('start_hour', 0):02d}:{training.get('start_min', 0):02d}"
        base_label = f"🏐 {date_str} {time_str}"

        extra_info = []

        team = training.get("team", "Both")
        if team == "Male":
            extra_info.append("чоловіча")
        elif team == "Female":
            extra_info.append("жіноча")

        if training.get("with_coach"):
            extra_info.append("З тренером")

        location = training.get("location", "")
        if location and location.lower() != "наукма" and not location.startswith("http"):
            extra_info.append(location)

        description = training.get("description", "")
        if description:
            extra_info.append(description)

        if extra_info:
            base_label += f" ({' - '.join(extra_info)})"

        return base_label

    def _format_game_label(self, game):
        type_names = {
            "friendly": "Товариська гра",
            "stolichka": "Столична ліга",
            "universiad": "Універсіада"
        }

        type_name = type_names.get(game.get('type'), game.get('type', 'Гра'))
        label = f"🏆 {type_name} - {game['date']} {game['time']}"
        label += f" проти {game['opponent']}"

        team = game.get("team", "Both")
        if team == "Male":
            label += " (чоловіча)"
        elif team == "Female":
            label += " (жіноча)"

        return label

    def format_vote_results(self, vote_item):
        vote_type = vote_item["type"]
        label = vote_item["label"]
        votes_data = vote_item["votes"]

        if vote_type in ["training", "game"]:
            yes_list = [v["name"] for v in votes_data.values() if v.get("vote") == "yes"]
            no_list = [v["name"] for v in votes_data.values() if v.get("vote") == "no"]

            message = f"{label}\n\n"
            message += f"✅ Будуть ({len(yes_list)}):\n"
            message += "\n".join(yes_list) if yes_list else "Ніхто"
            message += f"\n\n❌ Не будуть ({len(no_list)}):\n"
            message += "\n".join(no_list) if no_list else "Ніхто"

        elif vote_type == "general":
            vote_data = vote_item["data"]
            message = f"{label}\n\n"

            if vote_data["type"] == "yes_no":
                yes_list = [v["name"] for v in votes_data.values() if v["response"] == "Так"]
                no_list = [v["name"] for v in votes_data.values() if v["response"] == "Ні"]

                message += f"✅ Так ({len(yes_list)}):\n"
                message += "\n".join(yes_list) if yes_list else "Ніхто"
                message += f"\n\n❌ Ні ({len(no_list)}):\n"
                message += "\n".join(no_list) if no_list else "Ніхто"

            elif vote_data["type"] in ["multiple_choice_single", "multiple_choice_multi"]:
                option_counts = {}
                for option in vote_data["options"]:
                    option_counts[option] = []

                for response in votes_data.values():
                    if vote_data["type"] == "multiple_choice_multi":
                        selected_options = [opt.strip() for opt in response["response"].split(",")]
                        for opt in selected_options:
                            if opt in option_counts:
                                option_counts[opt].append(response["name"])
                    else:
                        if response["response"] in option_counts:
                            option_counts[response["response"]].append(response["name"])

                for option, names in option_counts.items():
                    message += f"• {option} ({len(names)}):\n"
                    if names:
                        message += "  " + ", ".join(names) + "\n"
                    else:
                        message += "  Ніхто\n"
                    message += "\n"

            else:  # text_response
                message += "Відповіді:\n\n"
                for i, response in enumerate(votes_data.values(), 1):
                    message += f"{i}. {response['name']}: {response['response']}\n\n"

        return message


unified_view_manager = UnifiedViewManager()


async def unified_view_votes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = load_data("users")

    if user_id not in user_data or "team" not in user_data[user_id]:
        await update.message.reply_text("Будь ласка, завершіть реєстрацію.")
        return

    all_votes = unified_view_manager.get_all_active_votes()

    if not all_votes:
        await update.message.reply_text("Наразі немає активних голосувань з результатами.")
        return

    keyboard = []
    context.user_data["view_votes_options"] = all_votes

    for idx, vote in enumerate(all_votes):
        keyboard.append([InlineKeyboardButton(vote["label"], callback_data=f"view_unified_{idx}")])

    await update.message.reply_text(
        "📊 Результати голосувань:\n\nОберіть голосування для перегляду результатів:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_unified_view_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("view_unified_", ""))
    vote_options = context.user_data.get("view_votes_options", [])

    if idx >= len(vote_options):
        await query.edit_message_text("⚠️ Помилка: вибране голосування більше не доступне.")
        return

    selected_vote = vote_options[idx]

    results_message = unified_view_manager.format_vote_results(selected_vote)

    if len(results_message) > 4000:
        parts = [results_message[i:i + 4000] for i in range(0, len(results_message), 4000)]
        for part in parts:
            await query.message.reply_text(part)
        await query.delete_message()
    else:
        await query.edit_message_text(results_message)


def create_general_vote_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("add_vote", add_vote)],
        states={
            VOTE_TYPE: [CallbackQueryHandler(handle_vote_type, pattern=r"^vote_type_")],
            VOTE_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vote_question)],
            VOTE_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vote_options)],
            VOTE_TEAM: [CallbackQueryHandler(handle_vote_team, pattern=r"^general_vote_team_")]
        },
        fallbacks=[CommandHandler("cancel", cancel_vote_creation)]
    )


def create_vot_for_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("vote_for", vote_for)],
        states={
            VOTE_OTHER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, vote_other_name)],
            VOTE_OTHER_SELECT: [CallbackQueryHandler(handle_vote_other_selection, pattern=r"^vote_other_\d+")]
        },
        fallbacks=[],
        allow_reentry=True
    )


def setup_voting_handlers(app):
    # /vote
    app.add_handler(CommandHandler("vote", unified_vote_command))
    # /view_votesd
    app.add_handler(CommandHandler("view_votes", unified_view_votes))
    # Admin: /close_vote
    app.add_handler(CommandHandler("close_vote", close_vote))
    # Admin: /unlock_training
    app.add_handler(CommandHandler("unlock_training", unlock_training))
    # Admin: /vote_for
    app.add_handler(create_vot_for_handler())

    # Admin: /add_vote
    app.add_handler(create_general_vote_handler())

    # Other
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_vote_input))
    app.add_handler(CallbackQueryHandler(handle_unified_vote_selection, pattern=r"^unified_vote_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_vote, pattern=r"^vote_(yes|no)_"))
    app.add_handler(CallbackQueryHandler(handle_unified_view_selection, pattern=r"^view_unified_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_view_votes_selection, pattern=r"^view_votes_\d+"))
    app.add_handler(CallbackQueryHandler(handle_vote_other_cast, pattern=r"^vote_other_cast_"))
    app.add_handler(CallbackQueryHandler(handle_general_vote_response, pattern=r"^general_vote_"))
    app.add_handler(CallbackQueryHandler(handle_unlock_selection, pattern=r"^unlock_training_\d+"))
