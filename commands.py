from telegram import Update
from telegram.ext import ContextTypes
from next_training import get_next_training
from data import load_user_data, save_user_data


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user  # Getting user info
    user_id = user.id
    first_name = user.first_name
    last_name = user.last_name
    username = user.username

    # Load existing user data
    user_data = load_user_data()

    # Store user info if not already saved
    if user_id not in user_data:
        user_data[user_id] = {
            "first_name": first_name,
            "last_name": last_name,
            "username": username
        }
        # Save updated user data to JSON
        save_user_data(user_data)
        print(f"New user saved: {user_id}, {first_name} {last_name}")

    # Send a welcome message
    await update.message.reply_text(f"Hello, {first_name}! Welcome to the bot!")


# command to get info about next training
async def next_training(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_next_training())
    print(update.message.from_user.id)
    print(update.message.from_user.first_name)
    print(update.message.from_user.last_name)
    print(update.message.from_user.username)


# command to get info about next game
async def next_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Наступне гра 19.03(середа) о 19:00")
