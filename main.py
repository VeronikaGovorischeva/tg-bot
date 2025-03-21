from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, Updater, \
    filters, CallbackQueryHandler
from commands import *

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
    game_add_handler = ConversationHandler(
        entry_points=[CommandHandler('add_game', add_game_command)],
        states={
            GAME_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_date)],
            GAME_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_time)],
            GAME_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_location)],
            GAME_OPPONENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_opponent)],
            GAME_ARRIVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_arrival)],
            GAME_TEAM: [CallbackQueryHandler(game_team, pattern=r"^add_")]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    edit_game_handler = ConversationHandler(
        entry_points=[CommandHandler('edit_game', edit_game_command)],
        states={
            EDIT_GAME_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_game_field)],
            EDIT_GAME_NEW_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_game_value),
                CallbackQueryHandler(edit_game_value, pattern=r"^edit_")
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(game_add_handler)
    app.add_handler(edit_game_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next_training", next_training))
    app.add_handler(CommandHandler("next_game", next_game))
    app.add_handler(CommandHandler("check_debt", check_debt))

    app.add_handler(CommandHandler("list_games", list_games))
    app.add_handler(CommandHandler("delete_game", delete_game_command))
    app.add_handler(CallbackQueryHandler(delete_game_callback, pattern=r"^delete_"))
    app.add_handler(CallbackQueryHandler(game_team_selection, pattern=r"^view_"))
    app.add_handler(CallbackQueryHandler(list_games_callback, pattern=r"^list_"))

    app.add_error_handler(error)
    app.run_polling(poll_interval=0.1)
