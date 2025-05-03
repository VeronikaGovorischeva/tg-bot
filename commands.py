from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from data import load_data

SEND_MESSAGE_STATE = {}

async def send_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="send_team_Male"),
            InlineKeyboardButton("Жіноча команда", callback_data="send_team_Female"),
        ],
        [InlineKeyboardButton("Обидві команди", callback_data="send_team_Both")]
    ])
    await update.message.reply_text("Оберіть команду, якій хочете надіслати повідомлення:", reply_markup=keyboard)


async def handle_send_message_team_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    team = query.data.replace("send_team_", "")
    SEND_MESSAGE_STATE[query.from_user.id] = team

    await query.edit_message_text(f"Ви обрали: {team} команда.\n\nТепер надішліть текст повідомлення у наступному повідомленні.")


async def handle_send_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in SEND_MESSAGE_STATE:
        return  # Not in send_message flow

    team = SEND_MESSAGE_STATE.pop(user_id)
    message_text = update.message.text
    users = load_data("data/user_data.json")

    count = 0
    for uid, info in users.items():
        if team in [info.get("team"), "Both"]:
            try:
                await context.bot.send_message(chat_id=int(uid), text=message_text)
                count += 1
            except Exception as e:
                print(f"❌ Не вдалося надіслати повідомлення {uid}: {e}")

    await update.message.reply_text(f"✅ Повідомлення надіслано {count} користувачам.")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from trainings import get_next_training
from games import *
from config import *
from data import *

# async def next_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     user_id = str(update.message.from_user.id)
#     user_data = load_data(JSON_FILE)
#
#     # If user is registered, show games for their team
#     if user_id in user_data and "team" in user_data[user_id]:
#         await update.message.reply_text(get_next_game(user_data[user_id]["team"]))
#     else:
#         print("Заверши реєстрацію, щоб побачити інформацію про наступну гру")
#
#
# async def add_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     # Check if user is authorized
#     if not is_authorized(update.message.from_user.id):
#         await update.message.reply_text("У вас немає дозволу на додавання інформації про ігри.")
#         return ConversationHandler.END
#
#     await update.message.reply_text(
#         "Додавання нової гри:\n"
#         "Введіть дату гри у форматі ДД.ММ.РРРР (наприклад, 25.03.2025)"
#     )
#
#     return GAME_DATE
#
#
# # Треба додати перевірку на правильність введених данних
# async def game_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     context.user_data['game_date'] = update.message.text
#
#     await update.message.reply_text(
#         "Введіть час початку гри у форматі ГГ:ХХ (наприклад, 19:00)"
#     )
#
#     return GAME_TIME
#
#
# # Треба додати перевірку на правильність введених данних
# async def game_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     context.user_data['game_time'] = update.message.text
#
#     await update.message.reply_text(
#         "Введіть місце проведення гри (адресу або назву спортзалу)"
#     )
#
#     return GAME_LOCATION
#
#
# async def game_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     context.user_data['game_location'] = update.message.text
#
#     await update.message.reply_text(
#         "Введіть проти якої команди буде гра"
#     )
#
#     return GAME_OPPONENT
#
#
# async def game_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     context.user_data['game_opponent'] = update.message.text
#
#     keyboard = [
#         [
#             InlineKeyboardButton("Чоловіча команда", callback_data="add_male"),
#             InlineKeyboardButton("Жіноча команда", callback_data="add_female"),
#         ]
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#
#     await update.message.reply_text(
#         "Виберіть команду, для якої додається гра:",
#         reply_markup=reply_markup
#     )
#
#     return GAME_TEAM
#
#
# async def game_team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     query = update.callback_query
#     await query.answer()
#
#     team_choice = "Male" if query.data == "add_male" else "Female"
#     context.user_data['game_team'] = team_choice
#
#     # Save the game data
#     add_game(
#         date=context.user_data['game_date'],
#         time=context.user_data['game_time'],
#         location=context.user_data['game_location'],
#         opponent=context.user_data['game_opponent'],
#         team=team_choice
#     )
#
#     await query.edit_message_text(
#         f"Інформацію про гру успішно додано для {team_choice} команди!\n"
#         f"Гравці можуть переглянути її за допомогою команди /next_game"
#     )
#
#     return ConversationHandler.END
#
#
# # Не знаю чи достатньо цього функціоналу чи ще щось треба
# async def list_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     # Create team selection keyboard
#     keyboard = [
#         [
#             InlineKeyboardButton("Чоловіча команда", callback_data="list_male"),
#             InlineKeyboardButton("Жіноча команда", callback_data="list_female"),
#         ],
#         [
#             InlineKeyboardButton("Всі ігри", callback_data="list_all"),
#         ]
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#
#     await update.message.reply_text(
#         "Виберіть команду для перегляду ігор:",
#         reply_markup=reply_markup
#     )
#
#
# # Наче норм але думаю можна трошки змінити
# async def list_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = update.callback_query
#     await query.answer()
#     data = query.data
#     games = list_all_games()
#
#     # Filter by team if needed
#     if data == "list_male":
#         games = [game for game in games if game.get('team') == "Male"]
#     elif data == "list_female":
#         games = [game for game in games if game.get('team') == "Female"]
#
#     if not games:
#         await query.edit_message_text("Немає запланованих ігор.")
#         return
#
#     # Create a message with information about each game
#     message = "📅 Список ігор:\n\n"
#
#     for i, game in enumerate(games, 1):
#         team_str = f"Команда: {game.get('team', 'Не вказано')}\n"
#         message += (f"{i}. Дата: {game['date']} о {game['time']}\n"
#                     f"   {team_str}"
#                     f"   Проти: {game['opponent']}\n"
#                     f"   Місце: {game['location']}\n"
#                     f"   ID гри: {game['id']}\n\n")
#
#     await query.edit_message_text(message)
#
#
# # Теж наче норм
# async def delete_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     # Check if user is authorized
#     if not is_authorized(update.message.from_user.id):
#         await update.message.reply_text("У вас немає дозволу на видалення ігор.")
#         return
#
#     # Check if game ID is provided
#     if not context.args:
#         await update.message.reply_text(
#             "Використання: /delete_game ID_гри\n"
#             "Щоб побачити ID ігор, використайте /list_games"
#         )
#         return
#     game_id = context.args[0]
#
#     # Create confirmation keyboard
#     keyboard = [
#         [
#             InlineKeyboardButton("Так, видалити", callback_data=f"delete_confirm_{game_id}"),
#             InlineKeyboardButton("Ні, скасувати", callback_data="delete_cancel"),
#         ]
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#
#     await update.message.reply_text(
#         f"Ви впевнені, що хочете видалити гру з ID {game_id}?",
#         reply_markup=reply_markup
#     )
#
#
# async def delete_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = update.callback_query
#     await query.answer()
#
#     callback_data = query.data
#
#     if callback_data == "delete_cancel":
#         await query.edit_message_text("Видалення гри скасовано.")
#         return
#
#     if callback_data.startswith("delete_confirm_"):
#         game_id = callback_data.replace("delete_confirm_", "")
#         success, game = delete_game(game_id)
#
#         if success:
#             team_str = f"Команда: {game.get('team', 'Не вказано')}\n"
#             await query.edit_message_text(
#                 f"Гру успішно видалено:\n"
#                 f"Дата: {game['date']} о {game['time']}\n"
#                 f"{team_str}"
#                 f"Проти: {game['opponent']}"
#             )
#         else:
#             await query.edit_message_text(f"Не вдалося знайти гру з ID {game_id}.")
#
#
# async def edit_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     if not is_authorized(update.message.from_user.id):
#         await update.message.reply_text("У вас немає дозволу на редагування ігор.")
#         return ConversationHandler.END
#
#     # Check if game ID is provided
#     if not context.args:
#         await update.message.reply_text(
#             "Використання: /edit_game ID_гри\n"
#             "Щоб побачити ID ігор, використайте /list_games"
#         )
#         return ConversationHandler.END
#
#     game_id = context.args[0]
#     game = get_game(game_id)
#
#     if not game:
#         await update.message.reply_text(f"Не вдалося знайти гру з ID {game_id}.")
#         return ConversationHandler.END
#
#     context.user_data['edit_game_id'] = game_id
#
#     # Display current game information
#     team_str = f"Команда: {game.get('team', 'Не вказано')}\n"
#     await update.message.reply_text(
#         f"Редагування гри з ID {game_id}:\n\n"
#         f"Поточна інформація:\n"
#         f"1. Дата: {game['date']}\n"
#         f"2. Час: {game['time']}\n"
#         f"3. Місце: {game['location']}\n"
#         f"4. Суперник: {game['opponent']}\n"
#         f"5. Час прибуття: {game['arrival_time']}\n"
#         f"6. {team_str}\n"
#         f"\nВиберіть, що саме ви хочете змінити (введіть номер):"
#     )
#
#     return EDIT_GAME_FIELD
#
#
# async def edit_game_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     field_num = update.message.text.strip()
#     field_mapping = {
#         "1": "date",
#         "2": "time",
#         "3": "location",
#         "4": "opponent",
#         "5": "arrival_time",
#         "6": "team",
#     }
#
#     if field_num not in field_mapping:
#         await update.message.reply_text(
#             "Невірний номер поля. Введіть номер від 1 до 6."
#         )
#         return EDIT_GAME_FIELD
#
#     field = field_mapping[field_num]
#     context.user_data['edit_field'] = field
#
#     # Handle team field separately with buttons
#     if field == "team":
#         keyboard = [
#             [
#                 InlineKeyboardButton("Чоловіча команда", callback_data="edit_male"),
#                 InlineKeyboardButton("Жіноча команда", callback_data="edit_female"),
#             ]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
#
#         await update.message.reply_text(
#             "Виберіть нову команду:",
#             reply_markup=reply_markup
#         )
#         return EDIT_GAME_NEW_VALUE
#
#     # For other fields, ask for text input
#     field_names = {
#         "date": "дату (ДД.ММ.РРРР)",
#         "time": "час (ГГ:ХХ)",
#         "location": "місце проведення",
#         "opponent": "назву команди суперника",
#         "arrival_time": "час прибуття (ГГ:ХХ)",
#     }
#
#     await update.message.reply_text(f"Введіть нове значення для поля '{field_names[field]}':")
#     return EDIT_GAME_NEW_VALUE
#
#
# async def edit_game_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     # This handles text input
#     if hasattr(update, 'message') and update.message:
#         new_value = update.message.text.strip()
#         field = context.user_data['edit_field']
#         game_id = context.user_data['edit_game_id']
#
#         success, updated_game = edit_game(game_id, field, new_value)
#
#         if success:
#             await update.message.reply_text(
#                 f"Інформацію про гру успішно оновлено!\n"
#                 f"Поле '{field}' змінено на '{new_value}'."
#             )
#         else:
#             await update.message.reply_text(f"Не вдалося оновити гру з ID {game_id}.")
#
#     # This handles callback for team selection
#     elif hasattr(update, 'callback_query') and update.callback_query:
#         query = update.callback_query
#         await query.answer()
#
#         new_value = "Male" if query.data == "edit_male" else "Female"
#         field = context.user_data['edit_field']
#         game_id = context.user_data['edit_game_id']
#
#         success, updated_game = edit_game(game_id, field, new_value)
#
#         if success:
#             await query.edit_message_text(
#                 f"Інформацію про гру успішно оновлено!\n"
#                 f"Команду змінено на '{new_value}'."
#             )
#         else:
#             await query.edit_message_text(f"Не вдалося оновити гру з ID {game_id}.")
#
#     return ConversationHandler.END
#
#
# # Потім змінити або додати щось в разі потреби
# async def check_debt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     user_data = load_data(JSON_FILE)
#     await update.message.reply_text(f"Твій борг: {str(user_data[str(update.message.from_user.id)]["debt"][0])} гривень")
