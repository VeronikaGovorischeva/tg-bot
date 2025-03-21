from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from next_training import get_next_training
from data import load_user_data, save_user_data
from games import *

# Conversation states
NAME = 0
TEAM = 1
GAME_DATE = 10
GAME_TIME = 11
GAME_LOCATION = 12
GAME_OPPONENT = 13
GAME_ARRIVAL = 14
GAME_TEAM=15
GAME_DELETE_CONFIRM = 20
EDIT_GAME_SELECT = 30
EDIT_GAME_FIELD = 31
EDIT_GAME_NEW_VALUE = 32
json_file = "user_data.json"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_id = user.id

    # Load existing user data
    user_data = load_user_data(json_file)

    # Check if user is already registered
    if str(user_id) in user_data and "name" in user_data[str(user_id)] and "team" in user_data[str(user_id)]:
        await update.message.reply_text(
            f"Вітаю, {user_data[str(user_id)]['name']}! Ти вже зареєстрований.\n"
            f"Твоя команда: {user_data[str(user_id)]['team']}\n"
            f"Використовуй команди /next_training для інформації про тренування "
            f"та /next_game для інформації про ігри."
        )
        return ConversationHandler.END

    # Store basic user info
    else:
        user_data[str(user_id)] = {
            "telegram_username": user.username or "No username"
        }
        save_user_data(user_data, json_file)

    # Ask for the user's name
    await update.message.reply_text(
        "Привіт! Введи своє прізвище та ім'я АНГЛІЙСЬКОЮ"
    )

    return NAME


# Handle the user's name input and ask for team selection
async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_id = str(user.id)
    user_input_name = update.message.text

    # Load existing user data
    user_data = load_user_data(json_file)
    user_data[user_id]["name"] = user_input_name
    user_data[user_id]["debt"] = [
        0]  # Треба подумати як краще оце зберігати( або масив масивів або дікт діктів) але загалом можна просто в масив і чілити
    save_user_data(user_data, json_file)

    # Create keyboard for team selection
    keyboard = [
        [
            InlineKeyboardButton("Чоловіча", callback_data="team_male"),
            InlineKeyboardButton("Жіноча", callback_data="team_female"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Дякую! Тепер обери свою команду:",
        reply_markup=reply_markup
    )

    return TEAM


# Handle team selection
async def team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    team_choice = "Male" if query.data == "team_male" else "Female"

    # Load existing user data
    user_data = load_user_data(json_file)
    user_data[user_id]["team"] = team_choice
    save_user_data(user_data, json_file)

    await query.edit_message_text(
        f"Реєстреацію завершено"
        f"Використовуй команди /next_training для інформації про тренування "
        f"та /next_game для інформації про ігри."  # Потім треба було б додати щоб знати що є
    )

    return ConversationHandler.END


# Cancel function to end conversation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Реєстрація скасована. Використовуй /start щоб спробувати знову."
    )
    return ConversationHandler.END


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Update {update} caused error {context.error}")


# command to get info about next training
async def next_training(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_next_training())


# command to get info about next game
async def next_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)

    # Load user data to check team
    user_data = load_user_data(json_file)

    # If user is registered, show games for their team
    if user_id in user_data and "team" in user_data[user_id]:
        team = user_data[user_id]["team"]
        await update.message.reply_text(get_next_game(team))
    else:
        # Let user select which team's games to view
        keyboard = [
            [
                InlineKeyboardButton("Чоловіча команда", callback_data="view_male"),
                InlineKeyboardButton("Жіноча команда", callback_data="view_female"),
            ],
            [
                InlineKeyboardButton("Всі ігри", callback_data="view_all"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Виберіть команду, щоб переглянути інформацію про наступну гру:",
            reply_markup=reply_markup
        )


async def game_team_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "view_male":
        await query.edit_message_text(get_next_game("Male"))
    elif data == "view_female":
        await query.edit_message_text(get_next_game("Female"))
    else:  # view_all
        await query.edit_message_text(get_next_game())


async def add_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id

    # Check if user is authorized
    if not is_authorized(user_id):
        await update.message.reply_text("У вас немає дозволу на додавання інформації про ігри.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Додавання нової гри:\n"
        "Введіть дату гри у форматі ДД.ММ.РРРР (наприклад, 25.03.2025)"
    )

    return GAME_DATE


async def game_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['game_date'] = update.message.text

    await update.message.reply_text(
        "Введіть час початку гри у форматі ГГ:ХХ (наприклад, 19:00)"
    )

    return GAME_TIME


async def game_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['game_time'] = update.message.text

    await update.message.reply_text(
        "Введіть місце проведення гри (адресу або назву спортзалу)"
    )

    return GAME_LOCATION


async def game_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['game_location'] = update.message.text

    await update.message.reply_text(
        "Введіть проти якої команди буде гра"
    )

    return GAME_OPPONENT


async def game_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['game_opponent'] = update.message.text

    await update.message.reply_text(
        "Введіть час, коли гравці повинні прибути на місце (наприклад, 18:30)"
    )

    return GAME_ARRIVAL


async def game_arrival(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['game_arrival'] = update.message.text

    # Create keyboard for team selection
    keyboard = [
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="add_male"),
            InlineKeyboardButton("Жіноча команда", callback_data="add_female"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Виберіть команду, для якої додається гра:",
        reply_markup=reply_markup
    )

    return GAME_TEAM


async def game_team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    team_choice = "Male" if query.data == "add_male" else "Female"
    context.user_data['game_team'] = team_choice
    user_id = query.from_user.id

    # Save the game data
    add_game(
        date=context.user_data['game_date'],
        time=context.user_data['game_time'],
        location=context.user_data['game_location'],
        opponent=context.user_data['game_opponent'],
        arrival_time=context.user_data['game_arrival'],
        team=team_choice
    )

    await query.edit_message_text(
        f"Інформацію про гру успішно додано для {team_choice} команди!\n"
        f"Гравці можуть переглянути її за допомогою команди /next_game"
    )

    return ConversationHandler.END


async def check_debt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = load_user_data(json_file)
    await update.message.reply_text(f"Твій борг: {str(user_data[str(update.message.from_user.id)]["debt"][0])} гривень")


async def list_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    # Check if user is authorized to manage games
    is_admin = is_authorized(user_id)

    # Load user data to check team
    user_data = load_user_data(json_file)
    user_id_str = str(user_id)

    # Create team selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="list_male"),
            InlineKeyboardButton("Жіноча команда", callback_data="list_female"),
        ],
        [
            InlineKeyboardButton("Всі ігри", callback_data="list_all"),
        ]
    ]

    # Add past games option for admins
    if is_admin:
        keyboard.append([
            InlineKeyboardButton("Включаючи минулі ігри", callback_data="list_past"),
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Default to user's team if registered
    default_team = None
    if user_id_str in user_data and "team" in user_data[user_id_str]:
        default_team = user_data[user_id_str]["team"]

    context.user_data['list_admin'] = is_admin

    await update.message.reply_text(
        "Виберіть команду для перегляду ігор:",
        reply_markup=reply_markup
    )


async def list_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    is_admin = context.user_data.get('list_admin', False)

    # Get games based on selection
    include_past = data == "list_past"
    games = list_all_games()

    # Filter by team if needed
    if data == "list_male":
        games = [game for game in games if game.get('team') == "Male"]
    elif data == "list_female":
        games = [game for game in games if game.get('team') == "Female"]

    if not games:
        await query.edit_message_text("Немає запланованих ігор.")
        return

    # Create a message with information about each game
    message = "📅 Список ігор:\n\n"

    for i, game in enumerate(games, 1):
        team_str = f"Команда: {game.get('team', 'Не вказано')}\n"
        message += (f"{i}. Дата: {game['date']} о {game['time']}\n"
                    f"   {team_str}"
                    f"   Проти: {game['opponent']}\n"
                    f"   Місце: {game['location']}\n"
                    f"   ID гри: {game['id']}\n\n")

    if is_admin:
        message += "📝 Керування іграми:\n"
        message += "• Щоб видалити гру: /delete_game ID_гри\n"
        message += "• Щоб редагувати гру: /edit_game ID_гри\n"

    await query.edit_message_text(message)


async def delete_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    # Check if user is authorized
    if not is_authorized(user_id):
        await update.message.reply_text("У вас немає дозволу на видалення ігор.")
        return

    # Check if game ID is provided
    if not context.args:
        await update.message.reply_text(
            "Використання: /delete_game ID_гри\n"
            "Щоб побачити ID ігор, використайте /list_games"
        )
        return

    game_id = context.args[0]

    # Create confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("Так, видалити", callback_data=f"delete_confirm_{game_id}"),
            InlineKeyboardButton("Ні, скасувати", callback_data="delete_cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Ви впевнені, що хочете видалити гру з ID {game_id}?",
        reply_markup=reply_markup
    )


async def delete_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data == "delete_cancel":
        await query.edit_message_text("Видалення гри скасовано.")
        return

    if callback_data.startswith("delete_confirm_"):
        game_id = callback_data.replace("delete_confirm_", "")
        success, game = delete_game(game_id)

        if success:
            team_str = f"Команда: {game.get('team', 'Не вказано')}\n"
            await query.edit_message_text(
                f"Гру успішно видалено:\n"
                f"Дата: {game['date']} о {game['time']}\n"
                f"{team_str}"
                f"Проти: {game['opponent']}"
            )
        else:
            await query.edit_message_text(f"Не вдалося знайти гру з ID {game_id}.")


async def edit_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id

    # Check if user is authorized
    if not is_authorized(user_id):
        await update.message.reply_text("У вас немає дозволу на редагування ігор.")
        return ConversationHandler.END

    # Check if game ID is provided
    if not context.args:
        await update.message.reply_text(
            "Використання: /edit_game ID_гри\n"
            "Щоб побачити ID ігор, використайте /list_games"
        )
        return ConversationHandler.END

    game_id = context.args[0]
    game = get_game(game_id)

    if not game:
        await update.message.reply_text(f"Не вдалося знайти гру з ID {game_id}.")
        return ConversationHandler.END

    context.user_data['edit_game_id'] = game_id

    # Display current game information
    team_str = f"Команда: {game.get('team', 'Не вказано')}\n"
    await update.message.reply_text(
        f"Редагування гри з ID {game_id}:\n\n"
        f"Поточна інформація:\n"
        f"1. Дата: {game['date']}\n"
        f"2. Час: {game['time']}\n"
        f"3. Місце: {game['location']}\n"
        f"4. Суперник: {game['opponent']}\n"
        f"5. Час прибуття: {game['arrival_time']}\n"
        f"6. {team_str}\n"
        f"\nВиберіть, що саме ви хочете змінити (введіть номер):"
    )

    return EDIT_GAME_FIELD


async def edit_game_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field_num = update.message.text.strip()
    field_mapping = {
        "1": "date",
        "2": "time",
        "3": "location",
        "4": "opponent",
        "5": "arrival_time",
        "6": "team",
    }

    if field_num not in field_mapping:
        await update.message.reply_text(
            "Невірний номер поля. Введіть номер від 1 до 6."
        )
        return EDIT_GAME_FIELD

    field = field_mapping[field_num]
    context.user_data['edit_field'] = field

    # Handle team field separately with buttons
    if field == "team":
        keyboard = [
            [
                InlineKeyboardButton("Чоловіча команда", callback_data="edit_male"),
                InlineKeyboardButton("Жіноча команда", callback_data="edit_female"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Виберіть нову команду:",
            reply_markup=reply_markup
        )
        return EDIT_GAME_NEW_VALUE

    # For other fields, ask for text input
    field_names = {
        "date": "дату (ДД.ММ.РРРР)",
        "time": "час (ГГ:ХХ)",
        "location": "місце проведення",
        "opponent": "назву команди суперника",
        "arrival_time": "час прибуття (ГГ:ХХ)",
    }

    await update.message.reply_text(f"Введіть нове значення для поля '{field_names[field]}':")
    return EDIT_GAME_NEW_VALUE


async def edit_game_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # This handles text input
    if hasattr(update, 'message') and update.message:
        new_value = update.message.text.strip()
        field = context.user_data['edit_field']
        game_id = context.user_data['edit_game_id']

        success, updated_game = edit_game(game_id, field, new_value)

        if success:
            await update.message.reply_text(
                f"Інформацію про гру успішно оновлено!\n"
                f"Поле '{field}' змінено на '{new_value}'."
            )
        else:
            await update.message.reply_text(f"Не вдалося оновити гру з ID {game_id}.")

    # This handles callback for team selection
    elif hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        await query.answer()

        new_value = "Male" if query.data == "edit_male" else "Female"
        field = context.user_data['edit_field']
        game_id = context.user_data['edit_game_id']

        success, updated_game = edit_game(game_id, field, new_value)

        if success:
            await query.edit_message_text(
                f"Інформацію про гру успішно оновлено!\n"
                f"Команду змінено на '{new_value}'."
            )
        else:
            await query.edit_message_text(f"Не вдалося оновити гру з ID {game_id}.")

    return ConversationHandler.END
