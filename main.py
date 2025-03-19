from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, Updater, \
    filters, CallbackQueryHandler
from commands import start, next_training, next_game, check_debt, name, error, cancel, team, TEAM, NAME

telegram_api_token = "8010698609:AAGZhl3Cfqh_YRaV1u9ROm0xySNUgLIzIC0"
bot_username = "ChillNtTestBot"

if __name__ == "__main__":
    app = Application.builder().token(telegram_api_token).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            TEAM: [CallbackQueryHandler(team)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next_training", next_training))
    app.add_handler(CommandHandler("next_game", next_game))
    app.add_handler(CommandHandler("check_debt", check_debt))
    app.add_error_handler(error)
    app.run_polling(poll_interval=0.1)