from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from commands import start, next_training, next_game

telegram_api_token = "7640419427:AAHUciixP3FyY6PLahICwer6ybFLwQRqucg"
bot_username = "ChillNtTestBot"


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Update {update} caused error {context.error}")


if __name__ == "__main__":
    app = Application.builder().token(telegram_api_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next_training", next_training))
    app.add_handler(CommandHandler("next_game", next_game))
    app.add_error_handler(error)
    app.run_polling(poll_interval=0.1)
