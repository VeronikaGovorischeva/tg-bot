import asyncio
from datetime import datetime
from data import load_data
from config import JSON_FILE
from telegram.ext import Application

ONE_TIME_TRAININGS_FILE = "data/one_time_trainings.json"
CONSTANT_TRAININGS_FILE = "data/constant_trainings.json"

async def check_voting_and_notify(app: Application):
    users = load_data(JSON_FILE)
    today = datetime.today().date()
    weekday = today.weekday()
    weekday_names = ['понеділок', 'вівторок', 'середу', 'четвер', "п'ятницю", 'суботу', 'неділю']

    one_time_trainings = load_data(ONE_TIME_TRAININGS_FILE, {})
    constant_trainings = load_data(CONSTANT_TRAININGS_FILE, {})

    # Notify for one-time trainings
    for training in one_time_trainings.values():
        if training.get("start_voting") != today.strftime("%d.%m.%Y"):
            continue

        for uid, info in users.items():
            if info.get("team") in [training.get("team"), "Both"]:
                try:
                    await app.bot.send_message(
                        chat_id=int(uid),
                        text=f"🗳 Голосування відкрите на тренування {training['date']} з {training['start_hour']:02d}:{training['start_min']:02d}. Використай /vote_training"
                    )
                except Exception as e:
                    print(f"❌ Помилка надсилання для {uid}: {e}")

    # Notify for constant trainings
    for training in constant_trainings.values():
        if weekday_names[int(training.get("start_voting"))] != weekday:
            continue

        for uid, info in users.items():
            if info.get("team") in [training.get("team"), "Both"]:
                try:
                    print("📤 надсилаю повідомлення для {uid}")
                    await app.bot.send_message(...)
                except Exception as e:
                    print("❌ Помилка надсилання: {e}")


async def schedule_notifications(app: Application):
    while True:
        await check_voting_and_notify(app)
        await asyncio.sleep(24 * 3600)  # раз на добу


async def check_time(update, context):
    await check_voting_and_notify(context.application)
    await update.message.reply_text("✅ Час перевірено. Якщо настав момент голосування — користувачі сповіщені.")
