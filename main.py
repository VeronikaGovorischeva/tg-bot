from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from trainings import *
from commands import *
from registration import *
from voting import view_votes, vote_training, handle_vote

chillnttestbot_token = "7640419427:AAHUciixP3FyY6PLahICwer6ybFLwQRqucg"
idontknownamesbot_token = "8010698609:AAGZhl3Cfqh_YRaV1u9ROm0xySNUgLIzIC0"
megachillguybot_token = "8158067169:AAGQaLETvllC5HR4byyadJqQeEwsOQN0IyE"
bot_username = "ChillNtTestBot"


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Update {update} caused error {context.error}")


if __name__ == "__main__":
    app = Application.builder().token(idontknownamesbot_token).build()
    registration = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            TEAM: [CallbackQueryHandler(team)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    training_add_handler = ConversationHandler(
        entry_points=[CommandHandler("add_training", add_training)],
        states={
            TYPE: [CallbackQueryHandler(training_type)],
            TEAM: [CallbackQueryHandler(training_team)],
            COACH: [CallbackQueryHandler(training_coach)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, training_date)],
            START: [MessageHandler(filters.TEXT & ~filters.COMMAND, training_start)],
            END: [MessageHandler(filters.TEXT & ~filters.COMMAND, training_end)],
            WEEKDAY: [CallbackQueryHandler(training_weekday)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    # game_add_handler = ConversationHandler(
    #     entry_points=[CommandHandler('add_game', add_game_command)],
    #     states={
    #         GAME_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_date)],
    #         GAME_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_time)],
    #         GAME_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_location)],
    #         GAME_OPPONENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_opponent)],
    #         GAME_TEAM: [CallbackQueryHandler(game_team, pattern=r"^add_")]
    #     },
    #     fallbacks=[CommandHandler('cancel', cancel)]
    # )
    # edit_game_handler = ConversationHandler(
    #     entry_points=[CommandHandler('edit_game', edit_game_command)],
    #     states={
    #         EDIT_GAME_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_game_field)],
    #         EDIT_GAME_NEW_VALUE: [
    #             MessageHandler(filters.TEXT & ~filters.COMMAND, edit_game_value),
    #             CallbackQueryHandler(edit_game_value, pattern=r"^edit_")
    #         ]
    #     },
    #     fallbacks=[CommandHandler('cancel', cancel)]
    # )

    app.add_handler(registration)
    app.add_handler(training_add_handler)
    # app.add_handler(game_add_handler)
    # app.add_handler(edit_game_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_training", add_training))
    app.add_handler(CommandHandler("next_training", next_training))
    app.add_handler(CommandHandler("next_training", next_training))
    app.add_handler(CommandHandler("vote_training", vote_training))
    app.add_handler(CommandHandler("view_votes", view_votes))
    app.add_handler(CallbackQueryHandler(handle_vote, pattern=r"^vote_"))
    app.add_handler(CommandHandler("last_training", last_training))
    # app.add_handler(CommandHandler("next_game", next_game))
    # app.add_handler(CommandHandler("check_debt", check_debt))
    #
    # app.add_handler(CommandHandler("list_games", list_games))
    # app.add_handler(CommandHandler("delete_game", delete_game_command))
    # app.add_handler(CallbackQueryHandler(delete_game_callback, pattern=r"^delete_"))
    # app.add_handler(CallbackQueryHandler(list_games_callback, pattern=r"^list_"))

    app.add_error_handler(error)
    app.run_polling(poll_interval=0.1)
