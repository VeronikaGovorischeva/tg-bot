from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from commands import start, next_training, next_game, name, team, error, cancel, NAME, TEAM

# Your token should be kept secret and not hardcoded
telegram_api_token = "7640419427:AAHUciixP3FyY6PLahICwer6ybFLwQRqucg"
bot_username = "ChillNtTestBot"

if __name__ == "__main__":
    try:
        # Build the application
        app = Application.builder().token(telegram_api_token).build()

        # Create conversation handler with the states NAME and TEAM
        # Added per_message=True to fix the warning
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
                TEAM: [CallbackQueryHandler(team)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            per_message=True
        )

        # Add handlers
        app.add_handler(conv_handler)
        app.add_handler(CommandHandler("next_training", next_training))
        app.add_handler(CommandHandler("next_game", next_game))
        app.add_error_handler(error)

        # Start the bot
        print("Starting bot...")
        app.run_polling(poll_interval=0.1)
    except Exception as e:
        print(f"Error starting bot: {str(e)}")