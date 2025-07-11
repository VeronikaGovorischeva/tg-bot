import datetime
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, \
    filters

from data import load_data, save_data
from validation import is_authorized

GAME_TYPE, GAME_TEAM, GAME_DATE, GAME_TIME, GAME_OPPONENT, GAME_LOCATION, GAME_ARRIVAL = range(300, 307)
EDIT_GAME_SELECT, EDIT_GAME_FIELD, EDIT_GAME_VALUE = range(320, 323)
CLOSE_GAME_SELECT, CLOSE_GAME_RESULTS, CLOSE_GAME_MVP = range(400, 403)

GAMES_FILE = "games"
GAME_VOTES_FILE = "game_votes"


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
        "status": None,
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

    if not context.args:
        await update.message.reply_text(
            "Використання: /delete_game [ID_гри]\n"
            "Щоб побачити ID ігор, використайте /list_games"
        )
        return

    game_id = context.args[0]
    games = load_data(GAMES_FILE, {})

    if game_id not in games:
        await update.message.reply_text(f"⚠️ Гру з ID {game_id} не знайдено.")
        return

    game = games[game_id]

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Так, видалити", callback_data=f"delete_game_confirm_{game_id}"),
            InlineKeyboardButton("❌ Скасувати", callback_data="delete_game_cancel")
        ]
    ])

    type_name = game_manager.game_types.get(GameType(game['type']), game['type'])
    message = f"Ви впевнені, що хочете видалити гру?\n\n"
    message += f"🎮 {type_name}\n"
    message += f"📅 {game['date']} о {game['time']}\n"
    message += f"🏆 Проти: {game['opponent']}\n"
    message += f"🆔 ID: {game_id}"

    await update.message.reply_text(message, reply_markup=keyboard)


async def handle_delete_game_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "delete_game_cancel":
        await query.edit_message_text("❌ Видалення гри скасовано.")
        return

    game_id = query.data.replace("delete_game_confirm_", "")
    games = load_data(GAMES_FILE, {})

    if game_id not in games:
        await query.edit_message_text("⚠️ Гру не знайдено.")
        return

    game = games[game_id]
    del games[game_id]
    save_data(games, GAMES_FILE)

    type_name = game_manager.game_types.get(GameType(game['type']), game['type'])
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

    games = load_data(GAMES_FILE, {})
    if game_id in games:
        games[game_id]["result"] = game_results
        games[game_id]["mvp"] = mvp_name
        save_data(games, GAMES_FILE)

    game = context.user_data["selected_game"]
    status_emoji = "🟢" if game_results["status"] == "win" else "🔴" if game_results["status"] == "loss" else "🟡"
    status_text = "Перемога" if game_results["status"] == "win" else "Поразка" if game_results[
                                                                                      "status"] == "loss" else "Нічия"

    sets_text = ', '.join([f"{s['our']}:{s['opponent']}" for s in game_results['sets']])

    message = f"✅ Гру успішно закрито!\n\n"
    message += f"{status_emoji} {status_text}: {game_results['our_score']}:{game_results['opponent_score']}\n"
    message += f"📅 {game['date']} проти {game['opponent']}\n"
    message += f"Сети: {sets_text}\n"

    if mvp_name:
        message += f"🏆 MVP: {mvp_name}"

    await query.edit_message_text(message)
    return ConversationHandler.END


async def cancel_close_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Закриття гри скасовано.")
    return ConversationHandler.END


def create_close_game_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("close_game", close_game)],
        states={
            CLOSE_GAME_SELECT: [CallbackQueryHandler(handle_close_game_selection, pattern=r"^close_game_\d+$")],
            CLOSE_GAME_RESULTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_close_game_results)],
            CLOSE_GAME_MVP: [CallbackQueryHandler(handle_close_game_mvp, pattern=r"^mvp_")]
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

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_list_games, pattern=r"^list_games_"))
    app.add_handler(CallbackQueryHandler(handle_delete_game_confirmation, pattern=r"^delete_game_"))
    app.add_handler(CallbackQueryHandler(handle_game_vote, pattern=r"^game_vote_(yes|no)_"))
