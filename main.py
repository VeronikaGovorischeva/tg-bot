from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext, \
    ContextTypes
from telegram import Update
import asyncio

from payments import charge_all, handle_payment_confirmation, collect_debts, handle_debt_check, pay_debt, \
    handle_pay_debt_selection, handle_pay_debt_confirmation
from trainings import create_training_add_handler, add_training, next_training, last_training, week_trainings
from registration import create_registration_handler
from notifier import check_voting_and_notify, start_voting
from voting import view_votes, vote_training, handle_vote, handle_training_vote_selection, handle_view_votes_selection

from apscheduler.schedulers.background import BackgroundScheduler

chillnttestbot_token = "7640419427:AAHUciixP3FyY6PLahICwer6ybFLwQRqucg"
idontknownamesbot_token = "8010698609:AAGZhl3Cfqh_YRaV1u9ROm0xySNUgLIzIC0"
megachillguybot_token = "8158067169:AAGQaLETvllC5HR4byyadJqQeEwsOQN0IyE"
bot_username = "ChillNtTestBot"


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Update {update} caused error {context.error}")


if __name__ == "__main__":
    app = Application.builder().token(chillnttestbot_token).build()
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

    # Registration
    app.add_handler(create_registration_handler())

    # Add training(only for admins)
    app.add_handler(create_training_add_handler())
    app.add_handler(CommandHandler("add_training", add_training))

    # Next training
    app.add_handler(CommandHandler("next_training", next_training))

    # Next week trainings
    app.add_handler(CommandHandler("week_trainings", week_trainings))

    # Last training(only for admins)
    app.add_handler(CommandHandler("last_training", last_training))

    # app.add_handler(game_add_handler)
    # app.add_handler(edit_game_handler)

    # Voting
    app.add_handler(CommandHandler("vote_training", vote_training))
    app.add_handler(CommandHandler("view_votes", view_votes))
    app.add_handler(CallbackQueryHandler(handle_vote, pattern=r"^vote_(yes|no)_"))
    app.add_handler(CallbackQueryHandler(handle_view_votes_selection, pattern=r"^view_votes_\d+"))
    app.add_handler(CallbackQueryHandler(handle_training_vote_selection, pattern=r"^training_vote_\d+"))

    app.add_handler(CommandHandler("charge_all", charge_all))
    app.add_handler(CallbackQueryHandler(handle_payment_confirmation, pattern=r"^paid_(yes|no)_\d+"))
    app.add_handler(CommandHandler("collect_debts", collect_debts))
    app.add_handler(CallbackQueryHandler(handle_debt_check, pattern=r"^debt_check_\d+"))
    app.add_handler(CommandHandler("pay_debt", pay_debt))
    app.add_handler(CallbackQueryHandler(handle_pay_debt_selection, pattern=r"^paydebt_select_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_pay_debt_confirmation, pattern=r"^paydebt_confirm_(yes|no)$"))

    # app.add_handler(CommandHandler("next_game", next_game))
    # app.add_handler(CommandHandler("check_debt", check_debt))
    #
    # app.add_handler(CommandHandler("list_games", list_games))
    # app.add_handler(CommandHandler("delete_game", delete_game_command))
    # app.add_handler(CallbackQueryHandler(delete_game_callback, pattern=r"^delete_"))
    # app.add_handler(CallbackQueryHandler(list_games_callback, pattern=r"^list_"))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: asyncio.run(start_voting(app)), 'cron', hour=18, minute=28)
    scheduler.add_job(lambda: asyncio.run(check_voting_and_notify(app)), 'cron', hour=17, minute=20)
    scheduler.start()

    app.add_error_handler(error)
    app.run_polling(poll_interval=0.1)
