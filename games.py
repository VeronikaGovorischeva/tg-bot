import datetime
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, \
    filters

from data import load_data, save_data
from validation import is_authorized

GAME_TYPE, GAME_TEAM, GAME_DATE, GAME_TIME, GAME_OPPONENT, GAME_LOCATION, GAME_ARRIVAL = range(300, 307)
EDIT_GAME_SELECT, EDIT_GAME_FIELD, EDIT_GAME_VALUE = range(320, 323)
CLOSE_GAME_SELECT, CLOSE_GAME_RESULTS, CLOSE_GAME_MVP, CLOSE_GAME_PAYMENT = range(400, 404)

GAMES_FILE = "games"
GAME_VOTES_FILE = "game_votes"
CARD_NUMBER = "5457 0825 2151 6794"


class GameType(Enum):
    FRIENDLY = "friendly"
    STOLICHKA = "stolichka"
    UNIVERSIAD = "universiad"


class Team(Enum):
    MALE = "Male"
    FEMALE = "Female"
    BOTH = "Both"


GAME_MESSAGES = {
    "unauthorized": "У вас немає дозволу на управління іграми.",
    "select_type": "Виберіть тип гри:",
    "select_team": "Для якої команди ця гра?",
    "enter_date": "Введіть дату гри у форматі ДД.ММ.РРРР (наприклад, 25.03.2025)",
    "enter_time": "Введіть час початку гри у форматі ГГ:ХХ (наприклад, 19:00)",
    "enter_opponent": "Введіть назву команди суперника:",
    "enter_location": "Введіть місце проведення гри (адреса або назва спорткомплексу):",
    "enter_arrival": "Введіть час прибуття у форматі ГГ:ХХ (рекомендований час до початку гри):",
    "enter_transport": "Введіть інформацію про транспорт або надішліть '-' якщо немає:",
    "enter_notes": "Введіть додаткові примітки або надішліть '-' якщо немає:",
    "game_saved": "Інформацію про гру успішно збережено!",
    "invalid_date": "Неправильний формат дати. Будь ласка, використовуйте формат ДД.ММ.РРРР",
    "invalid_time": "Неправильний формат часу. Будь ласка, використовуйте формат ГГ:ХХ"
}


class GameManager:
    def __init__(self):
        self.game_types = {
            GameType.FRIENDLY: "Товариська гра",
            GameType.STOLICHKA: "Столична ліга",
            GameType.UNIVERSIAD: "Універсіада"
        }

    def create_game_type_keyboard(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Товариська гра", callback_data=f"game_type_{GameType.FRIENDLY.value}")],
            [InlineKeyboardButton("Столична ліга", callback_data=f"game_type_{GameType.STOLICHKA.value}")],
            [InlineKeyboardButton("Універсіада", callback_data=f"game_type_{GameType.UNIVERSIAD.value}")]
        ])

    def create_team_keyboard(self):
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Чоловіча", callback_data="game_team_Male"),
                InlineKeyboardButton("Жіноча", callback_data="game_team_Female")
            ],
            [InlineKeyboardButton("Обидві команди", callback_data="game_team_Both")]
        ])

    def validate_date(self, date_text: str):
        try:
            return True, datetime.datetime.strptime(date_text, "%d.%m.%Y").date()
        except ValueError:
            return False, None

    def validate_time(self, time_text: str):
        try:
            time_obj = datetime.datetime.strptime(time_text, "%H:%M").time()
            return True, (time_obj.hour, time_obj.minute)
        except ValueError:
            return False, None


game_manager = GameManager()


async def add_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text(GAME_MESSAGES["unauthorized"])
        return ConversationHandler.END

    await update.message.reply_text(
        GAME_MESSAGES["select_type"],
        reply_markup=game_manager.create_game_type_keyboard()
    )
    return GAME_TYPE


async def game_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    game_type = query.data.replace("game_type_", "")
    context.user_data['game_type'] = game_type

    type_name = game_manager.game_types[GameType(game_type)]
    await query.edit_message_text(
        f"✅ Тип гри: {type_name}\n\n{GAME_MESSAGES['select_team']}",
        reply_markup=game_manager.create_team_keyboard()
    )
    return GAME_TEAM


async def game_team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    team = query.data.replace("game_team_", "")
    context.user_data['game_team'] = team

    team_names = {"Male": "чоловічої команди", "Female": "жіночої команди", "Both": "обох команд"}
    await query.edit_message_text(
        f"✅ Команда: {team_names[team]}\n\n{GAME_MESSAGES['enter_date']}"
    )
    return GAME_DATE


async def game_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    is_valid, date_obj = game_manager.validate_date(update.message.text)
    if not is_valid:
        await update.message.reply_text(GAME_MESSAGES["invalid_date"])
        return GAME_DATE

    context.user_data['game_date'] = date_obj.strftime("%d.%m.%Y")
    await update.message.reply_text(GAME_MESSAGES["enter_time"])
    return GAME_TIME


async def game_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    is_valid, time_tuple = game_manager.validate_time(update.message.text)
    if not is_valid:
        await update.message.reply_text(GAME_MESSAGES["invalid_time"])
        return GAME_TIME

    context.user_data['game_hour'], context.user_data['game_minute'] = time_tuple
    await update.message.reply_text(GAME_MESSAGES["enter_opponent"])
    return GAME_OPPONENT


async def game_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['game_opponent'] = update.message.text
    await update.message.reply_text(GAME_MESSAGES["enter_location"])
    return GAME_LOCATION


async def game_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['game_location'] = update.message.text
    await update.message.reply_text(GAME_MESSAGES["enter_arrival"])
    return GAME_ARRIVAL


def generate_unique_game_id(games_data: dict, user_data: dict) -> str:
    try:
        game_date = datetime.datetime.strptime(user_data['game_date'], "%d.%m.%Y")
    except:
        game_date = datetime.datetime.now()

    if game_date.month >= 9:
        season_start = game_date.year
        season_end = game_date.year + 1
    else:
        season_start = game_date.year - 1
        season_end = game_date.year

    season = f"{season_start}_{season_end}"

    game_type = user_data['game_type']
    team = user_data['game_team'].lower()
    existing_count = 0
    season_prefix = f"{game_type}_{team}_{season}"

    for game_id in games_data.keys():
        if game_id.startswith(season_prefix):
            existing_count += 1

    return f"{game_type}_{team}_{season}_{existing_count + 1}"


async def game_arrival(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    is_valid, time_tuple = game_manager.validate_time(update.message.text)
    if not is_valid:
        await update.message.reply_text(GAME_MESSAGES["invalid_time"])
        return GAME_ARRIVAL

    context.user_data['arrival_hour'], context.user_data['arrival_minute'] = time_tuple

    games = load_data(GAMES_FILE, {})
    game_id = generate_unique_game_id(games, context.user_data)
    context.user_data['game_id'] = game_id

    await save_game_and_notify(update, context)
    return ConversationHandler.END


async def save_game_and_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    games = load_data(GAMES_FILE, {})
    game_id = context.user_data['game_id']

    game_data = {
        "id": game_id,
        "type": context.user_data['game_type'],
        "team": context.user_data['game_team'],
        "date": context.user_data['game_date'],
        "time": f"{context.user_data['game_hour']:02d}:{context.user_data['game_minute']:02d}",
        "opponent": context.user_data['game_opponent'],
        "location": context.user_data['game_location'],
        "arrival_time": f"{context.user_data['arrival_hour']:02d}:{context.user_data['arrival_minute']:02d}",
        "result": {
            "our_score": 0,
            "opponent_score": 0,
            "sets": [
                {"our": 0, "opponent": 0}
            ],
            "status": None  # "win", "loss", "draw"
        },
        "mvp": None
    }

    games[game_id] = game_data
    save_data(games, GAMES_FILE)

    type_name = game_manager.game_types[GameType(game_data['type'])]
    team_names = {"Male": "чоловічої команди", "Female": "жіночої команди", "Both": "обох команд"}

    message = f"Гру успішно створено!\n\n"
    message += f"Тип: {type_name}\n"
    message += f"Команда: {team_names[game_data['team']]}\n"
    message += f"Дата: {game_data['date']} о {game_data['time']}\n"
    message += f"Проти: {game_data['opponent']}\n"
    message += f"Місце: {game_data['location']}\n"
    message += f"Прибуття: {game_data['arrival_time']}"

    await update.message.reply_text(message)

    try:
        game_datetime = datetime.datetime.strptime(f"{game_data['date']} {game_data['time']}", "%d.%m.%Y %H:%M")
        now = datetime.datetime.now()

        if game_datetime > now:
            await send_game_voting_to_team(context, game_data)

    except ValueError as e:
        print(f"Помилка парсингу дати для гри {game_id}: {e}")


async def send_game_voting_to_team(context: ContextTypes.DEFAULT_TYPE, game_data: dict):
    users = load_data("users", {})
    type_name = game_manager.game_types[GameType(game_data['type'])]

    message = f"Нова гра!\n\n"
    message += f"{type_name}\n"
    message += f"Дата: {game_data['date']} о {game_data['time']}\n"
    message += f"Проти: {game_data['opponent']}\n"
    message += f"Місце: {game_data['location']}\n"
    message += f"Прибуття до: {game_data['arrival_time']}\n\n"
    message += "Чи будете брати участь?"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Буду", callback_data=f"game_vote_yes_{game_data['id']}"),
            InlineKeyboardButton("Не буду", callback_data=f"game_vote_no_{game_data['id']}")
        ]
    ])

    count = 0
    for uid, user_info in users.items():
        if game_data["team"] in [user_info.get("team"), "Both"]:
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=message,
                    reply_markup=keyboard
                )
                count += 1
            except Exception as e:
                print(f"Помилка надсилання голосування до {uid}: {e}")


async def next_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    users = load_data("users", {})

    if user_id not in users or "team" not in users[user_id]:
        await update.message.reply_text("Будь ласка, завершіть реєстрацію.")
        return

    user_team = users[user_id]["team"]
    games = load_data(GAMES_FILE, {})

    now = datetime.datetime.now()
    upcoming_games = []

    for game in games.values():
        if game.get("team") not in [user_team, "Both"]:
            continue

        try:
            game_datetime = datetime.datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
            if game_datetime > now:
                upcoming_games.append((game, game_datetime))
        except ValueError:
            continue

    if not upcoming_games:
        await update.message.reply_text("Немає запланованих ігор.")
        return

    upcoming_games.sort(key=lambda x: x[1])
    next_game_data, next_game_datetime = upcoming_games[0]

    days_until = (next_game_datetime.date() - now.date()).days

    if days_until == 0:
        day_text = "сьогодні"
    elif days_until == 1:
        day_text = "завтра"
    else:
        day_text = f"через {days_until} дні(в)"

    type_name = game_manager.game_types.get(GameType(next_game_data['type']), next_game_data['type'])
    team_names = {"Male": "для чоловічої команди", "Female": "для жіночої команди", "Both": "для обох команд"}

    message = f"🏐 Наступна гра {day_text}\n\n"
    message += f"🎮 {type_name} {team_names.get(next_game_data['team'], '')}\n"
    message += f"📅 {next_game_data['date']} о {next_game_data['time']}\n"
    message += f"🏆 Проти: {next_game_data['opponent']}\n"
    message += f"📍 Місце: {next_game_data['location']}\n"
    message += f"⏰ Прибуття до: {next_game_data['arrival_time']}\n"

    if next_game_data.get('transport'):
        message += f"🚌 Транспорт: {next_game_data['transport']}\n"
    if next_game_data.get('notes'):
        message += f"📝 Примітки: {next_game_data['notes']}\n"

    await update.message.reply_text(message)


async def list_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="list_games_Male"),
            InlineKeyboardButton("Жіноча команда", callback_data="list_games_Female")
        ],
        [InlineKeyboardButton("Всі ігри", callback_data="list_games_Both")]
    ])

    await update.message.reply_text(
        "Оберіть команду для перегляду ігор:",
        reply_markup=keyboard
    )


async def handle_list_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    team_filter = query.data.replace("list_games_", "")
    games = load_data(GAMES_FILE, {})
    if team_filter == "Both":
        filtered_games = list(games.values())
    else:
        filtered_games = [game for game in games.values() if game.get("team") in [team_filter, "Both"]]

    now = datetime.datetime.now()
    upcoming_games = []

    for game in filtered_games:
        try:
            game_datetime = datetime.datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
            if game_datetime > now:
                upcoming_games.append((game, game_datetime))
        except ValueError:
            continue

    if not upcoming_games:
        await query.edit_message_text("Немає запланованих ігор для обраної команди.")
        return

    upcoming_games.sort(key=lambda x: x[1])

    team_names = {"Male": "чоловічої команди", "Female": "жіночої команди", "Both": "всіх команд"}
    message = f"🏐 Список ігор {team_names.get(team_filter, '')}:\n\n"

    for i, (game, game_datetime) in enumerate(upcoming_games, 1):
        type_name = game_manager.game_types.get(GameType(game['type']), game['type'])

        message += f"{i}. {type_name}\n"
        message += f"   📅 {game['date']} о {game['time']}\n"
        message += f"   🏆 Проти: {game['opponent']}\n"
        message += f"   📍 {game['location']}\n"

        if game.get('team') != "Both":
            team_name = "чоловіча" if game['team'] == "Male" else "жіноча"
            message += f"   👥 Команда: {team_name}\n"

    if len(message) > 4000:
        parts = [message[i:i + 4000] for i in range(0, len(message), 4000)]
        for part in parts:
            await query.message.reply_text(part)
        await query.delete_message()
    else:
        await query.edit_message_text(message)


async def delete_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ У вас немає прав для видалення ігор.")
        return

    games = load_data(GAMES_FILE, {})
    now = datetime.datetime.now()

    available_games = []
    for game_id, game in games.items():
        try:
            game_datetime = datetime.datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
            if game_datetime >= now:
                available_games.append((game_id, game))
        except ValueError:
            available_games.append((game_id, game))

    if not available_games:
        await update.message.reply_text("Немає ігор для видалення.")
        return

    context.user_data["delete_game_options"] = available_games

    keyboard = []
    for i, (game_id, game) in enumerate(available_games):
        type_names = {
            "friendly": "Товариська",
            "stolichka": "Столичка",
            "universiad": "Універсіада"
        }
        type_name = type_names.get(game.get('type'), game.get('type'))
        team_name = "чоловіча" if game['team'] == "Male" else "жіноча" if game['team'] == "Female" else "змішана"

        label = f"{type_name} ({team_name}) - {game['date']} проти {game['opponent']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"delete_game_select_{i}")])

    await update.message.reply_text(
        "Оберіть гру для видалення:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_delete_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("delete_game_select_", ""))
    options = context.user_data.get("delete_game_options", [])

    if idx >= len(options):
        await query.edit_message_text("⚠️ Помилка: гру не знайдено.")
        return

    game_id, game = options[idx]

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Так, видалити", callback_data=f"delete_game_confirm_{idx}"),
            InlineKeyboardButton("❌ Скасувати", callback_data="delete_game_cancel")
        ]
    ])

    type_names = {
        "friendly": "Товариська",
        "stolichka": "Столичка",
        "universiad": "Універсіада"
    }
    type_name = type_names.get(game.get('type'), game.get('type'))

    message = f"Ви впевнені, що хочете видалити гру?\n\n"
    message += f"🎮 {type_name}\n"
    message += f"📅 {game['date']} о {game['time']}\n"
    message += f"🏆 Проти: {game['opponent']}\n"

    await query.edit_message_text(message, reply_markup=keyboard)


async def handle_delete_game_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "delete_game_cancel":
        await query.edit_message_text("❌ Видалення гри скасовано.")
        return

    idx = int(query.data.replace("delete_game_confirm_", ""))
    options = context.user_data.get("delete_game_options", [])

    if idx >= len(options):
        await query.edit_message_text("⚠️ Помилка: гру не знайдено.")
        return

    game_id, game = options[idx]
    games = load_data(GAMES_FILE, {})

    if game_id not in games:
        await query.edit_message_text("⚠️ Гру не знайдено.")
        return

    del games[game_id]
    save_data(games, GAMES_FILE)

    game_votes = load_data(GAME_VOTES_FILE, {"votes": {}})
    if game_id in game_votes["votes"]:
        del game_votes["votes"][game_id]
        save_data(game_votes, GAME_VOTES_FILE)
        print(f"✅ Видалено голосування за гру {game_id}")

    type_names = {
        "friendly": "Товариська",
        "stolichka": "Столичка",
        "universiad": "Універсіада"
    }
    type_name = type_names.get(game.get('type'), game.get('type'))

    await query.edit_message_text(
        f"✅ Гру видалено:\n\n"
        f"🎮 {type_name}\n"
        f"📅 {game['date']} о {game['time']}\n"
        f"🏆 Проти: {game['opponent']}"
    )


async def handle_game_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split("_")
    vote = data_parts[2]
    game_id = "_".join(data_parts[3:])

    user_id = str(query.from_user.id)
    users = load_data("users", {})
    user_name = users.get(user_id, {}).get("name", "Невідомий")

    game_votes = load_data(GAME_VOTES_FILE, {"votes": {}})
    if game_id not in game_votes["votes"]:
        game_votes["votes"][game_id] = {}

    game_votes["votes"][game_id][user_id] = {
        "name": user_name,
        "vote": vote
    }
    save_data(game_votes, GAME_VOTES_FILE)

    vote_text = "БУДУ" if vote == "yes" else "НЕ БУДУ"
    await query.edit_message_text(f"✅ Ваш голос '{vote_text}' збережено!")


async def week_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    users = load_data("users", {})

    if user_id not in users or "team" not in users[user_id]:
        await update.message.reply_text("Будь ласка, завершіть реєстрацію.")
        return

    user_team = users[user_id]["team"]
    games = load_data(GAMES_FILE, {})

    now = datetime.datetime.now()
    week_end = now + datetime.timedelta(days=7)
    week_games = []

    for game in games.values():
        if game.get("team") not in [user_team, "Both"]:
            continue

        try:
            game_datetime = datetime.datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
            if now <= game_datetime <= week_end:
                week_games.append((game, game_datetime))
        except ValueError:
            continue

    if not week_games:
        await update.message.reply_text("Немає ігор на наступний тиждень.")
        return

    week_games.sort(key=lambda x: x[1])

    weekday_names = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', "П'ятниця", 'Субота', 'Неділя']
    message = "🏐 Ігри на тиждень:\n\n"

    for game, game_datetime in week_games:
        weekday = weekday_names[game_datetime.weekday()]
        type_name = game_manager.game_types.get(GameType(game['type']), game['type'])

        message += f"• {weekday} {game['date']} о {game['time']}\n"
        message += f"  {type_name} проти {game['opponent']}\n"
        message += f"  📍 {game['location']}\n"
        message += f"  ⏰ Прибуття: {game['arrival_time']}\n"

        if game.get('transport'):
            message += f"  🚌 {game['transport']}\n"

    await update.message.reply_text(message)


async def cancel_game_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Додавання гри скасовано.")
    return ConversationHandler.END


async def close_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ У вас немає прав для закриття ігор.")
        return ConversationHandler.END

    games = load_data(GAMES_FILE, {})

    uncompleted_games = []
    for game_id, game in games.items():
        result = game.get("result", {})
        if result.get("status") is None:
            uncompleted_games.append((game_id, game))

    if not uncompleted_games:
        await update.message.reply_text("Немає ігор, які потребують закриття.")
        return ConversationHandler.END

    context.user_data["uncompleted_games"] = uncompleted_games

    keyboard = []
    for i, (game_id, game) in enumerate(uncompleted_games):
        type_names = {
            "friendly": "Товариська",
            "stolichka": "Столичка",
            "universiad": "Універсіада"
        }
        type_name = type_names.get(game.get('type'), game.get('type'))
        team_name = "чоловіча" if game['team'] == "Male" else "жіноча" if game['team'] == "Female" else "змішана"

        label = f"{type_name} ({team_name}) - {game['date']} проти {game['opponent']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"close_game_{i}")])

    await update.message.reply_text(
        "Оберіть гру для закриття:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return CLOSE_GAME_SELECT


async def handle_close_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("close_game_", ""))
    uncompleted_games = context.user_data.get("uncompleted_games", [])

    if idx >= len(uncompleted_games):
        await query.edit_message_text("⚠️ Помилка: гру не знайдено.")
        return ConversationHandler.END

    game_id, game = uncompleted_games[idx]
    context.user_data["selected_game_id"] = game_id
    context.user_data["selected_game"] = game

    type_names = {
        "friendly": "Товариська",
        "stolichka": "Столичка",
        "universiad": "Універсіада"
    }
    type_name = type_names.get(game.get('type'), game.get('type'))

    await query.edit_message_text(
        f"🏆 Закриття гри: {type_name}\n"
        f"📅 {game['date']} проти {game['opponent']}\n\n"
        f"Введіть результати гри у форматі:\n"
        f"1 рядок: загальний рахунок (наприклад: 3:1)\n"
        f"2 рядок: рахунок 1-го сету (наприклад: 25:20)\n"
        f"3 рядок: рахунок 2-го сету (наприклад: 23:25)\n"
        f"І так далі для кожного сету...\n\n"
        f"Приклад:\n"
        f"3:1\n"
        f"25:20\n"
        f"23:25\n"
        f"25:18\n"
        f"25:22"
    )

    return CLOSE_GAME_RESULTS


async def handle_close_game_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lines = update.message.text.strip().split('\n')

    if len(lines) < 2:
        await update.message.reply_text(
            "⚠️ Некоректний формат. Потрібно мінімум 2 рядки:\n"
            "1 рядок: загальний рахунок\n"
            "2+ рядки: рахунки сетів"
        )
        return CLOSE_GAME_RESULTS

    try:
        main_score = lines[0].split(':')
        if len(main_score) != 2:
            raise ValueError("Неправильний формат загального рахунку")

        our_score = int(main_score[0])
        opponent_score = int(main_score[1])
        total_sets = our_score + opponent_score

        if len(lines) - 1 != total_sets:
            await update.message.reply_text(
                f"⚠️ Помилка: загальний рахунок {our_score}:{opponent_score} означає {total_sets} сетів,\n"
                f"але ви ввели {len(lines) - 1} сетів."
            )
            return CLOSE_GAME_RESULTS

        sets = []
        for i in range(1, len(lines)):
            set_score = lines[i].split(':')
            if len(set_score) != 2:
                raise ValueError(f"Неправильний формат сету {i}")

            set_our = int(set_score[0])
            set_opponent = int(set_score[1])
            sets.append({"our": set_our, "opponent": set_opponent})

        if our_score > opponent_score:
            game_status = "win"
        elif our_score < opponent_score:
            game_status = "loss"
        else:
            game_status = "draw"

        context.user_data["game_results"] = {
            "our_score": our_score,
            "opponent_score": opponent_score,
            "sets": sets,
            "status": game_status
        }

        game = context.user_data["selected_game"]
        users = load_data("users", {})

        team_players = []
        for uid, user_data in users.items():
            user_team = user_data.get("team")
            if game.get("team") in [user_team, "Both"]:
                team_players.append((uid, user_data.get("name", "Невідомий")))

        if not team_players:
            await update.message.reply_text("⚠️ Не знайдено гравців команди.")
            return ConversationHandler.END

        context.user_data["team_players"] = team_players

        keyboard = []
        for uid, name in team_players:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"mvp_{uid}")])

        keyboard.append([InlineKeyboardButton("❌ Немає MVP", callback_data="mvp_none")])

        status_emoji = "🟢" if game_status == "win" else "🔴" if game_status == "loss" else "🟡"

        sets_text = ', '.join([f"{s['our']}:{s['opponent']}" for s in sets])

        await update.message.reply_text(
            f"✅ Результат збережено!\n\n"
            f"{status_emoji} Рахунок: {our_score}:{opponent_score}\n"
            f"Сети: {sets_text}\n\n"
            f"Оберіть MVP гри:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return CLOSE_GAME_MVP

    except (ValueError, IndexError) as e:
        await update.message.reply_text(
            f"⚠️ Помилка формату: {str(e)}\n\n"
            f"Використовуйте формат:\n"
            f"3:1\n"
            f"25:20\n"
            f"23:25\n"
            f"25:18\n"
            f"25:22"
        )
        return CLOSE_GAME_RESULTS


async def handle_close_game_mvp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    game_id = context.user_data["selected_game_id"]
    game_results = context.user_data["game_results"]

    mvp_name = None
    if query.data != "mvp_none":
        mvp_uid = query.data.replace("mvp_", "")
        team_players = context.user_data["team_players"]

        for uid, name in team_players:
            if uid == mvp_uid:
                mvp_name = name

                users = load_data("users", {})
                if uid in users:
                    users[uid]["mvp"] = users[uid].get("mvp", 0) + 1
                    save_data(users, "users")
                break

    context.user_data["selected_mvp"] = mvp_name

    status_emoji = "🟢" if game_results["status"] == "win" else "🔴" if game_results["status"] == "loss" else "🟡"

    await query.edit_message_text(
        f"✅ Результат та MVP збережено!\n\n"
        f"{status_emoji} Рахунок: {game_results['our_score']}:{game_results['opponent_score']}\n"
        f"🏆 MVP: {mvp_name if mvp_name else 'Не призначено'}\n\n"
        f"💰 Введіть суму для оплати за гру (в гривнях):\n"
        f"Наприклад: 200\n"
        f"Або 0 якщо гра безкоштовна"
    )

    return CLOSE_GAME_PAYMENT


async def handle_close_game_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = int(update.message.text.strip())
        if amount < 0:
            await update.message.reply_text("⚠️ Сума не може бути від'ємною. Спробуйте ще раз:")
            return CLOSE_GAME_PAYMENT
    except ValueError:
        await update.message.reply_text("⚠️ Будь ласка, введіть число. Спробуйте ще раз:")
        return CLOSE_GAME_PAYMENT

    game_id = context.user_data["selected_game_id"]
    game_results = context.user_data["game_results"]
    mvp_name = context.user_data.get("selected_mvp")
    game = context.user_data["selected_game"]

    games = load_data(GAMES_FILE, {})
    if game_id in games:
        games[game_id]["result"] = game_results
        games[game_id]["mvp"] = mvp_name
        save_data(games, GAMES_FILE)

    if amount > 0:
        game_votes = load_data(GAME_VOTES_FILE, {"votes": {}})
        game_voters = game_votes.get("votes", {}).get(game_id, {})

        yes_voters = [uid for uid, vote_info in game_voters.items() if vote_info.get("vote") == "yes"]

        if yes_voters:
            per_person = round(amount / len(yes_voters))

            payments = load_data("payments", {})

            for uid in yes_voters:
                payment_key = f"game_{game_id}_{uid}"
                payments[payment_key] = {
                    "user_id": uid,
                    "game_id": game_id,
                    "amount": per_person,
                    "total_game_cost": amount,
                    "game_info": f"{game['date']} проти {game['opponent']}",
                    "card": f"*{CARD_NUMBER}*",
                    "paid": False
                }

            save_data(payments, "payments")

            await send_game_payment_notifications(context, game, yes_voters, per_person, amount, game_id)

            status_emoji = "🟢" if game_results["status"] == "win" else "🔴" if game_results["status"] == "loss" else "🟡"
            status_text = "Перемога" if game_results["status"] == "win" else "Поразка" if game_results[
                                                                                              "status"] == "loss" else "Нічия"

            message = f"✅ Гру успішно закрито!\n\n"
            message += f"{status_emoji} {status_text}: {game_results['our_score']}:{game_results['opponent_score']}\n"
            message += f"📅 {game['date']} проти {game['opponent']}\n"

            if mvp_name:
                message += f"🏆 MVP: {mvp_name}\n"

            message += f"\n💰 Оплата:\n"
            message += f"💵 Загальна сума: {amount} грн\n"
            message += f"👥 Учасників: {len(yes_voters)}\n"
            message += f"💳 По {per_person} грн з особи\n"
            message += f"📤 Повідомлення надіслано учасникам"

        else:
            message = f"✅ Гру закрито, але ніхто не проголосував 'так', тому платежі не створено."

    else:
        status_emoji = "🟢" if game_results["status"] == "win" else "🔴" if game_results["status"] == "loss" else "🟡"
        status_text = "Перемога" if game_results["status"] == "win" else "Поразка" if game_results[
                                                                                          "status"] == "loss" else "Нічия"

        message = f"✅ Гру успішно закрито!\n\n"
        message += f"{status_emoji} {status_text}: {game_results['our_score']}:{game_results['opponent_score']}\n"
        message += f"📅 {game['date']} проти {game['opponent']}\n"

        if mvp_name:
            message += f"🏆 MVP: {mvp_name}\n"

        message += f"\n🆓 Гра була безкоштовною"

    await update.message.reply_text(message)
    return ConversationHandler.END


async def send_game_payment_notifications(context: ContextTypes.DEFAULT_TYPE, game, yes_voters, per_person,
                                          total_amount, game_id):
    type_names = {
        "friendly": "Товариська гра",
        "stolichka": "Столична ліга",
        "universiad": "Універсіада"
    }
    type_name = type_names.get(game.get('type'), game.get('type', 'Гра'))

    count = 0
    for uid in yes_voters:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатив(ла)", callback_data=f"paid_yes_game_{game_id}_{uid}")]
        ])

        message = (
            f"💳 Ти брав(-ла) участь у грі!\n\n"
            f"🎮 {type_name}\n"
            f"📅 {game['date']} проти {game['opponent']}\n"
            f"💰 Сума до сплати: {per_person} грн\n"
            f"💳 Карта для оплати: `5457 0825 2151 6794`\n\n"
            f"Натисни кнопку нижче, коли оплатиш:"
        )

        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            count += 1
        except Exception as e:
            print(f"❌ Помилка надсилання повідомлення про оплату до {uid}: {e}")

    return count


async def handle_game_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split("_")
    game_id = data_parts[3]
    user_id = data_parts[4]

    payments = load_data("payments", {})
    payment_key = f"game_{game_id}_{user_id}"

    if payment_key not in payments:
        await query.edit_message_text("⚠️ Помилка: запис про платіж не знайдено.")
        return

    payments[payment_key]["paid"] = True
    save_data(payments, "payments")

    await query.edit_message_text("✅ Дякуємо! Оплату за гру зареєстровано.")


async def edit_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ У вас немає прав для редагування ігор.")
        return ConversationHandler.END

    games = load_data(GAMES_FILE, {})

    if not games:
        await update.message.reply_text("Немає ігор для редагування.")
        return ConversationHandler.END

    context.user_data["all_games"] = list(games.items())

    keyboard = []
    for i, (game_id, game) in enumerate(games.items()):
        type_names = {
            "friendly": "Товариська",
            "stolichka": "Столичка",
            "universiad": "Універсіада"
        }
        type_name = type_names.get(game.get('type'), game.get('type'))
        team_name = "чоловіча" if game['team'] == "Male" else "жіноча" if game['team'] == "Female" else "змішана"

        label = f"{type_name} ({team_name}) - {game['date']} проти {game['opponent']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"edit_game_select_{i}")])

    await update.message.reply_text(
        "Оберіть гру для редагування:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return EDIT_GAME_SELECT


async def handle_edit_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("edit_game_select_", ""))
    all_games = context.user_data.get("all_games", [])

    if idx >= len(all_games):
        await query.edit_message_text("⚠️ Помилка: гру не знайдено.")
        return ConversationHandler.END

    game_id, game = all_games[idx]
    context.user_data["edit_game_id"] = game_id
    context.user_data["edit_game_data"] = game.copy()
    context.user_data["edit_changes"] = {}

    keyboard = [
        [InlineKeyboardButton("📅 Дата", callback_data="edit_field_date")],
        [InlineKeyboardButton("⏰ Час", callback_data="edit_field_time")],
        [InlineKeyboardButton("🏆 Суперник", callback_data="edit_field_opponent")],
        [InlineKeyboardButton("📍 Місце", callback_data="edit_field_location")],
        [InlineKeyboardButton("⏰ Час прибуття", callback_data="edit_field_arrival")],
        [InlineKeyboardButton("👥 Команда", callback_data="edit_field_team")],
        [InlineKeyboardButton("✅ Зберегти зміни", callback_data="edit_save_changes")],
        [InlineKeyboardButton("❌ Скасувати", callback_data="edit_cancel")]
    ]

    type_names = {
        "friendly": "Товариська",
        "stolichka": "Столичка",
        "universiad": "Універсіада"
    }
    type_name = type_names.get(game.get('type'), game.get('type'))

    message = f"🎮 Редагування гри: {type_name}\n\n"
    message += f"📅 Дата: {game['date']}\n"
    message += f"⏰ Час: {game['time']}\n"
    message += f"🏆 Суперник: {game['opponent']}\n"
    message += f"📍 Місце: {game['location']}\n"
    message += f"⏰ Прибуття: {game['arrival_time']}\n"
    message += f"👥 Команда: {'чоловіча' if game['team'] == 'Male' else 'жіноча' if game['team'] == 'Female' else 'обидві'}\n\n"
    message += "Оберіть що хочете змінити:"

    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    return EDIT_GAME_FIELD


async def handle_edit_game_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "edit_cancel":
        await query.edit_message_text("❌ Редагування скасовано.")
        return ConversationHandler.END

    if query.data == "edit_save_changes":
        changes = context.user_data.get("edit_changes", {})
        if not changes:
            await query.answer("⚠️ Немає змін для збереження!", show_alert=True)
            return EDIT_GAME_FIELD

        game_id = context.user_data["edit_game_id"]
        games = load_data(GAMES_FILE, {})

        old_game = games[game_id].copy()

        for field, new_value in changes.items():
            games[game_id][field] = new_value

        save_data(games, GAMES_FILE)

        await send_game_update_notification(context, old_game, games[game_id], changes)

        changes_text = "\n".join([f"• {field}: {value}" for field, value in changes.items()])
        await query.edit_message_text(
            f"✅ Зміни збережено!\n\n"
            f"Змінено:\n{changes_text}\n\n"
            f"Команду сповіщено про зміни."
        )
        return ConversationHandler.END

    field = query.data.replace("edit_field_", "")
    context.user_data["edit_current_field"] = field

    field_names = {
        "date": "дату (ДД.ММ.РРРР)",
        "time": "час (ГГ:ХХ)",
        "opponent": "назву команди суперника",
        "location": "місце проведення гри",
        "arrival": "час прибуття (ГГ:ХХ)",
        "team": "команду"
    }

    if field == "team":
        keyboard = [
            [InlineKeyboardButton("Чоловіча", callback_data="edit_value_Male")],
            [InlineKeyboardButton("Жіноча", callback_data="edit_value_Female")],
            [InlineKeyboardButton("Обидві", callback_data="edit_value_Both")]
        ]
        await query.edit_message_text(
            f"Оберіть нову команду:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDIT_GAME_VALUE
    else:
        await query.edit_message_text(f"Введіть нову {field_names[field]}:")
        return EDIT_GAME_VALUE


async def handle_edit_game_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.get("edit_current_field")

    if hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        await query.answer()
        new_value = query.data.replace("edit_value_", "")

        context.user_data["edit_changes"][field] = new_value

        team_names = {"Male": "чоловіча", "Female": "жіноча", "Both": "обидві"}
        await query.edit_message_text(f"✅ Команда змінена на: {team_names[new_value]}")

    else:
        new_value = update.message.text.strip()

        if field == "date":
            try:
                datetime.datetime.strptime(new_value, "%d.%m.%Y")
                context.user_data["edit_changes"][field] = new_value
            except ValueError:
                await update.message.reply_text("⚠️ Неправильний формат дати. Використовуйте ДД.ММ.РРРР")
                return EDIT_GAME_VALUE

        elif field in ["time", "arrival"]:
            try:
                datetime.datetime.strptime(new_value, "%H:%M")
            except ValueError:
                await update.message.reply_text("⚠️ Неправильний формат часу. Використовуйте ГГ:ХХ")
                return EDIT_GAME_VALUE

            if field == "arrival":
                context.user_data["edit_changes"]["arrival_time"] = new_value
            else:
                context.user_data["edit_changes"][field] = new_value
        else:
            context.user_data["edit_changes"][field] = new_value

        field_names = {
            "date": "дата",
            "time": "час",
            "opponent": "суперник",
            "location": "місце",
            "arrival": "час прибуття"
        }

        await update.message.reply_text(f"✅ {field_names[field].capitalize()} змінено на: {new_value}")

    game_data = context.user_data["edit_game_data"]
    changes = context.user_data.get("edit_changes", {})

    current_data = game_data.copy()
    current_data.update(changes)

    keyboard = [
        [InlineKeyboardButton("📅 Дата", callback_data="edit_field_date")],
        [InlineKeyboardButton("⏰ Час", callback_data="edit_field_time")],
        [InlineKeyboardButton("🏆 Суперник", callback_data="edit_field_opponent")],
        [InlineKeyboardButton("📍 Місце", callback_data="edit_field_location")],
        [InlineKeyboardButton("⏰ Час прибуття", callback_data="edit_field_arrival")],
        [InlineKeyboardButton("👥 Команда", callback_data="edit_field_team")],
        [InlineKeyboardButton("✅ Зберегти зміни", callback_data="edit_save_changes")],
        [InlineKeyboardButton("❌ Скасувати", callback_data="edit_cancel")]
    ]

    message = f"🎮 Редагування гри:\n\n"
    message += f"📅 Дата: {current_data.get('date', game_data['date'])}\n"
    message += f"⏰ Час: {current_data.get('time', game_data['time'])}\n"
    message += f"🏆 Суперник: {current_data.get('opponent', game_data['opponent'])}\n"
    message += f"📍 Місце: {current_data.get('location', game_data['location'])}\n"
    message += f"⏰ Прибуття: {current_data.get('arrival_time', game_data['arrival_time'])}\n"

    team_display = current_data.get('team', game_data['team'])
    team_text = 'чоловіча' if team_display == 'Male' else 'жіноча' if team_display == 'Female' else 'обидві'
    message += f"👥 Команда: {team_text}\n\n"

    if changes:
        message += "🔄 Зміни:\n"
        for field, value in changes.items():
            field_names = {
                "date": "Дата",
                "time": "Час",
                "opponent": "Суперник",
                "location": "Місце",
                "arrival_time": "Час прибуття",
                "team": "Команда"
            }
            if field == "team":
                value = 'чоловіча' if value == 'Male' else 'жіноча' if value == 'Female' else 'обидві'
            message += f"• {field_names.get(field, field)}: {value}\n"
        message += "\n"

    message += "Оберіть що ще хочете змінити або збережіть:"

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    return EDIT_GAME_FIELD


async def send_game_update_notification(context: ContextTypes.DEFAULT_TYPE, old_game, new_game, changes):
    users = load_data("users", {})

    type_names = {
        "friendly": "Товариська гра",
        "stolichka": "Столична ліга",
        "universiad": "Універсіада"
    }
    type_name = type_names.get(new_game.get('type'), new_game.get('type'))

    message = f"📢 Зміни в грі!\n\n"
    message += f"🎮 {type_name}\n"
    message += f"📅 {new_game['date']} о {new_game['time']}\n"
    message += f"🏆 Проти: {new_game['opponent']}\n\n"
    message += f"🔄 Що змінилося:\n"

    field_names = {
        "date": "Дата",
        "time": "Час",
        "opponent": "Суперник",
        "location": "Місце",
        "arrival_time": "Час прибуття",
        "team": "Команда"
    }

    for field, new_value in changes.items():
        old_value = old_game.get(field, "")
        if field == "team":
            old_value = 'чоловіча' if old_value == 'Male' else 'жіноча' if old_value == 'Female' else 'обидві'
            new_value = 'чоловіча' if new_value == 'Male' else 'жіноча' if new_value == 'Female' else 'обидві'

        message += f"• {field_names.get(field, field)}: {old_value} → {new_value}\n"

    count = 0
    for uid, user_info in users.items():
        if new_game.get("team") in [user_info.get("team"), "Both"]:
            try:
                await context.bot.send_message(chat_id=int(uid), text=message)
                count += 1
            except Exception as e:
                print(f"❌ Помилка надсилання сповіщення до {uid}: {e}")

    print(f"✅ Сповіщення про зміни в грі надіслано {count} користувачам")


def create_edit_game_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("edit_game", edit_game)],
        states={
            EDIT_GAME_SELECT: [CallbackQueryHandler(handle_edit_game_selection, pattern=r"^edit_game_select_\d+$")],
            EDIT_GAME_FIELD: [CallbackQueryHandler(handle_edit_game_field, pattern=r"^edit_")],
            EDIT_GAME_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_game_value),
                CallbackQueryHandler(handle_edit_game_value, pattern=r"^edit_value_")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_game_creation)],
        allow_reentry=True
    )


async def cancel_close_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Закриття гри скасовано.")
    return ConversationHandler.END


def create_close_game_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("close_game", close_game)],
        states={
            CLOSE_GAME_SELECT: [CallbackQueryHandler(handle_close_game_selection, pattern=r"^close_game_\d+$")],
            CLOSE_GAME_RESULTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_close_game_results)],
            CLOSE_GAME_MVP: [CallbackQueryHandler(handle_close_game_mvp, pattern=r"^mvp_")],
            CLOSE_GAME_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_close_game_payment)]
        },
        fallbacks=[CommandHandler("cancel", cancel_close_game)],
        allow_reentry=True
    )


def create_game_add_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("add_game", add_game)],
        states={
            GAME_TYPE: [CallbackQueryHandler(game_type, pattern=r"^game_type_")],
            GAME_TEAM: [CallbackQueryHandler(game_team, pattern=r"^game_team_")],
            GAME_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_date)],
            GAME_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_time)],
            GAME_OPPONENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_opponent)],
            GAME_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_location)],
            GAME_ARRIVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_arrival)]
        },
        fallbacks=[CommandHandler("cancel", cancel_game_creation)]
    )


def setup_game_handlers(app):
    # /next_game
    app.add_handler(CommandHandler("next_game", next_game))
    # /list_games
    app.add_handler(CommandHandler("list_games", list_games))
    # /week_games
    app.add_handler(CommandHandler("week_games", week_games))
    # Admin: /add_game
    app.add_handler(create_game_add_handler())
    # Admin: /delete_game
    app.add_handler(CommandHandler("delete_game", delete_game))
    # Admin: /close_game
    app.add_handler(create_close_game_handler())
    # Admin: /edit_game
    app.add_handler(create_edit_game_handler())

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_list_games, pattern=r"^list_games_"))
    app.add_handler(CallbackQueryHandler(handle_delete_game_selection, pattern=r"^delete_game_select_\d+$"))
    app.add_handler(
        CallbackQueryHandler(handle_delete_game_confirmation, pattern=r"^delete_game_(confirm_\d+|cancel)$"))
    app.add_handler(CallbackQueryHandler(handle_game_vote, pattern=r"^game_vote_(yes|no)_"))
    app.add_handler(CallbackQueryHandler(handle_game_payment_confirmation, pattern=r"^paid_yes_game_"))
