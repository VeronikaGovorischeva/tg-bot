from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext, \
    ContextTypes
from telegram import Update
import asyncio

from payments import *
from trainings import create_training_add_handler, add_training, next_training, last_training, week_trainings, \
    reset_today_constant_trainings_status
from registration import create_registration_handler
from notifier import check_voting_and_notify, start_voting
from voting import *
from commands import send_message_command, handle_send_message_team_selection, handle_send_message_input
import os

states = {
    VOTE_OTHER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, vote_other_name)],
    VOTE_OTHER_SELECT: [CallbackQueryHandler(handle_vote_other_selection, pattern=r"^vote_other_\d+")],
},

from apscheduler.schedulers.background import BackgroundScheduler

chillnttestbot_token = "7640419427:AAHUciixP3FyY6PLahICwer6ybFLwQRqucg"
idontknownamesbot_token = "8010698609:AAGZhl3Cfqh_YRaV1u9ROm0xySNUgLIzIC0"
megachillguybot_token = "8158067169:AAGQaLETvllC5HR4byyadJqQeEwsOQN0IyE"
bot_username = "ChillNtTestBot"
BOT_TOKEN = os.getenv("NEW_TOKEN")

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Update {update} caused error {context.error}")


if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
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
    app.add_handler(CommandHandler("send_message", send_message_command))
    app.add_handler(CallbackQueryHandler(handle_send_message_team_selection, pattern=r"^send_team_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_send_message_input))

    app.add_handler(CommandHandler("charge_all", charge_all))
    app.add_handler(CallbackQueryHandler(handle_payment_confirmation, pattern=r"^paid_yes_.*"))
    app.add_handler(CallbackQueryHandler(handle_charge_selection, pattern=r"^charge_select_\d+"))
    app.add_handler(CommandHandler("pay_debt", pay_debt))
    app.add_handler(CallbackQueryHandler(handle_pay_debt_selection, pattern=r"^paydebt_select_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_pay_debt_confirmation, pattern=r"^paydebt_confirm_yes$"))
    app.add_handler(CommandHandler("view_payments", view_payments))
    app.add_handler(CallbackQueryHandler(handle_view_payment_selection, pattern=r"^view_payment_\d+"))
    app.add_handler(CallbackQueryHandler(handle_vote_other_cast, pattern=r"^vote_other_cast_(yes|no)$"))
    app.add_handler(CommandHandler("unlock_training", unlock_training))
    app.add_handler(CallbackQueryHandler(handle_unlock_selection, pattern=r"^unlock_training_\d+"))

    # app.add_handler(CommandHandler("next_game", next_game))
    # app.add_handler(CommandHandler("check_debt", check_debt))
    #
    # app.add_handler(CommandHandler("list_games", list_games))
    # app.add_handler(CommandHandler("delete_game", delete_game_command))
    # app.add_handler(CallbackQueryHandler(delete_game_callback, pattern=r"^delete_"))
    # app.add_handler(CallbackQueryHandler(list_games_callback, pattern=r"^list_"))

    scheduler = BackgroundScheduler()
    loop = asyncio.get_event_loop()
    scheduler.add_job(lambda: loop.call_soon_threadsafe(lambda: asyncio.create_task(start_voting(app))), 'cron', hour=15, minute=0)
    scheduler.add_job(lambda: loop.call_soon_threadsafe(lambda: asyncio.create_task(check_voting_and_notify(app))),'cron', hour=16, minute=0)
    scheduler.add_job(reset_today_constant_trainings_status, 'cron', hour=22, minute=0)

    scheduler.start()

    app.add_error_handler(error)
    app.run_polling(poll_interval=0.1)
