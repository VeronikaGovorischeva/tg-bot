import asyncio
import os
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import Application, ContextTypes

from trainings import setup_training_handlers, reset_today_constant_trainings_status
from registration import setup_registration_handlers
from games import setup_game_handlers
from voting import setup_voting_handlers
from payments import setup_payment_handlers
from commands import setup_admin_handlers
from notifier import check_voting_and_notify, start_voting, check_game_reminders

BOT_TOKEN = os.getenv("NEW_TOKEN")


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Update {update} caused error {context.error}")


def setup_scheduler(app):
    scheduler = BackgroundScheduler()
    loop = asyncio.get_event_loop()

    # Start voting daily at 18:00
    scheduler.add_job(
        lambda: loop.call_soon_threadsafe(
            lambda: asyncio.create_task(start_voting(app))
        ),
        'cron', hour=19, minute=12
    )

    # Send voting reminders daily at 19:00
    scheduler.add_job(
        lambda: loop.call_soon_threadsafe(
            lambda: asyncio.create_task(check_voting_and_notify(app))
        ),
        'cron', hour=16, minute=0
    )

    # Send game reminders daily at 19:00
    scheduler.add_job(
        lambda: loop.call_soon_threadsafe(
            lambda: asyncio.create_task(check_game_reminders(app))
        ),
        'cron', hour=16, minute=0
    )

    # Reset training statuses daily at 22:00
    scheduler.add_job(
        lambda: loop.call_soon_threadsafe(
            lambda: asyncio.create_task(reset_today_constant_trainings_status())
        ),
        'cron', hour=19, minute=0
    )

    scheduler.start()
    return scheduler


if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()

    setup_registration_handlers(app)
    setup_training_handlers(app)
    setup_game_handlers(app)
    setup_voting_handlers(app)
    setup_payment_handlers(app)
    setup_admin_handlers(app)  # Must be last

    scheduler = setup_scheduler(app)

    app.add_error_handler(error)

    app.run_polling(poll_interval=0.1)
