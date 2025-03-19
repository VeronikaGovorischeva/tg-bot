from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from next_training import get_next_training
from data import load_user_data, save_user_data

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from next_training import get_next_training
from data import load_user_data, save_user_data

# Conversation states
NAME = 0
TEAM = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_id = user.id

    # Load existing user data
    user_data = load_user_data()

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
        save_user_data(user_data)

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
    user_data = load_user_data()
    user_data[user_id]["name"] = user_input_name
    user_data[user_id]["debt"] = 0
    save_user_data(user_data)

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
    user_data = load_user_data()
    user_data[user_id]["team"] = team_choice
    save_user_data(user_data)

    await query.edit_message_text(
        f"Чудово! Тебе зареєстровано в {team_choice.lower()} команді.\n"
        f"Використовуй команди /next_training для інформації про тренування "
        f"та /next_game для інформації про ігри."
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
    await update.message.reply_text("Наступне гра 19.03(середа) о 19:00")

async def check_debt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = load_user_data()
    user = update.message.from_user
    user_id = str(user.id)
    await update.message.reply_text("Твій борг: " + str(user_data[user_id]["debt"]))