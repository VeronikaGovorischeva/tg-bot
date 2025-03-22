from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import *
from data import *


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_id = user.id

    # Load existing user data
    user_data = load_data(JSON_FILE)

    # Check if user is already registered
    if str(user_id) in user_data and "name" in user_data[str(user_id)] and "team" in user_data[str(user_id)]:
        await update.message.reply_text(
            f"Використовуй команди /next_training /next_game та /list_games щоб дізнатися інфу про наступне тренування та наступну гру."
        )
        return ConversationHandler.END

    # Store basic user info
    else:
        user_data[str(user_id)] = {
            "telegram_username": user.username
        }
        save_data(user_data, JSON_FILE)

    # Ask for the user's name
    await update.message.reply_text(
        "Привіт! Введи своє прізвище та ім'я АНГЛІЙСЬКОЮ"
    )  # Залежить від того як ми будемо зберігати

    return NAME


# Поки не зрозуміло як краще зберігати дебт, а інше нормально
async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    user_input_name = update.message.text

    # Load existing user data
    user_data = load_data(JSON_FILE)
    user_data[user_id]["name"] = user_input_name
    user_data[user_id]["debt"] = [
        0]  # Треба подумати як краще оце зберігати( або масив масивів або дікт діктів) але загалом можна просто в масив і чілити
    save_data(user_data, JSON_FILE)

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


# Просто змінити текст після завершення реєстрації
async def team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    team_choice = "Male" if query.data == "team_male" else "Female"

    # Load existing user data
    user_data = load_data(JSON_FILE)
    user_data[user_id]["team"] = team_choice
    save_data(user_data, JSON_FILE)

    await query.edit_message_text(
        f"Реєстрацію завершено.\n"
        f"Використовуй команди /next_training для інформації про тренування "
        f"та /next_game для інформації про ігри."
    )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Реєстрація скасована. Використовуй /start щоб спробувати знову."
    )
    return ConversationHandler.END
