from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from next_training import get_next_training
from data import load_user_data, save_user_data

NAME = 0  # не розумію для чого воно тут


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_id = user.id

    # Load existing user data
    user_data = load_user_data()

    # Check if user is already registered
    if str(user_id) in user_data:
        return ConversationHandler.END

    # Store basic user info
    else:
        user_data[str(user_id)] = {
            "telegram_username": user.username
        }
        save_user_data(user_data)

    # Ask for the user's name
    await update.message.reply_text(
        "Привіт! Введи своє прізвище та ім'я АНГЛІЙСЬКОЮ"
    )

    return NAME


# Handle the user's name input
async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_id = str(user.id)
    user_input_name = update.message.text

    # Load existing user data
    user_data = load_user_data()
    user_data[user_id]["name"] = user_input_name
    save_user_data(user_data)

    await update.message.reply_text(
        f"Дякую!\n"
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
