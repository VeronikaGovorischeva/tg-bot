from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, Updater, \
    filters
from commands import start, next_training, next_game, name, error, cancel

telegram_api_token = "7640419427:AAHUciixP3FyY6PLahICwer6ybFLwQRqucg"
bot_username = "ChillNtTestBot"
NAME = 0

if __name__ == "__main__":
    app = Application.builder().token(telegram_api_token).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next_training", next_training))
    app.add_handler(CommandHandler("next_game", next_game))
    app.add_error_handler(error)
    app.run_polling(poll_interval=0.1)
