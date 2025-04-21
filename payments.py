from telegram import Update
from telegram.ext import ContextTypes
from config import JSON_FILE
from data import load_data, save_data
from trainings import get_last_training
from voting import load_votes
from datetime import datetime

TRAINING_COST = 1750
CARD_NUMBER = "5375 4141 0273 8014"

async def charge_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = load_data(JSON_FILE)
    votes = load_votes()["votes"]
    date_str, training_id = get_last_training()

    if not training_id:
        await update.message.reply_text("Немає останнього тренування для нарахування.")
        return

    one_time_trainings = load_data("one_time_trainings.json", {})
    constant_trainings = load_data("constant_trainings.json", {})

    # Determine key used in voting file
    if str(training_id) in one_time_trainings:
        date = one_time_trainings[str(training_id)]["date"]
        hour = one_time_trainings[str(training_id)]["start_hour"]
        minute = one_time_trainings[str(training_id)]["start_min"]
        training_key = f"{date}_{hour:02d}:{minute:02d}"
        training = one_time_trainings[str(training_id)]
    elif str(training_id) in constant_trainings:
        weekday = constant_trainings[str(training_id)]["weekday"]
        hour = constant_trainings[str(training_id)]["start_hour"]
        minute = constant_trainings[str(training_id)]["start_min"]
        training_key = f"const_{weekday}_{hour:02d}:{minute:02d}"
        training = constant_trainings[str(training_id)]
    else:
        await update.message.reply_text("Не вдалося знайти тренування для нарахування.")
        return

    voters = votes.get(training_key, {})

    yes_voters = [uid for uid, v in voters.items() if v["vote"] == "yes"]
    if not yes_voters:
        await update.message.reply_text("Ніхто не проголосував 'так' за останнє тренування.")
        return

    # Determine cost per person
    constant_trainings = load_data("constant_trainings.json", {})
    one_time_trainings = load_data("one_time_trainings.json", {})

    training = constant_trainings.get(str(training_id)) or one_time_trainings.get(str(training_id))
    if not training:
        await update.message.reply_text("Не вдалося знайти тренування для нарахування.")
        return

    per_person = round(TRAINING_COST / len(yes_voters)) if training.get("with_coach") else 0

    # Charge users
    for uid in yes_voters:
        uid_str = str(uid)
        if uid_str not in user_data:
            continue
        user_data[uid_str]["debt"] += per_person
        try:
            await update.get_bot().send_message(
                chat_id=int(uid),
                text=f"💳 Ти відвідав(-ла) останнє тренування {date_str}.\n"
                     f"Сума до сплати: {per_person} грн\n"
                     f"Карта: {CARD_NUMBER}"
            )
        except Exception as e:
            print(f"Помилка надсилання повідомлення для {uid}: {e}")

    save_data(user_data, JSON_FILE)
    await update.message.reply_text("Повідомлення про оплату надіслано всім, хто був на тренуванні.")
