from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from data import load_data, save_data
from validation import ADMIN_IDS

TRAINING_COST = 1750
CARD_NUMBER = "5375 4141 0273 8014"

async def charge_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    one_time_trainings = load_data("one_time_trainings", {})
    constant_trainings = load_data("constant_trainings", {})

    options = []
    for tid, t in one_time_trainings.items():
        if t.get("status") == "not charged" and t.get("with_coach"):
            date = t["date"]
            time = f"{t['start_hour']:02d}:{t['start_min']:02d}"
            label = f"{date} о {time}"
            options.append((tid, "one_time", label))

    for tid, t in constant_trainings.items():
        if t.get("status") == "not charged" and t.get("with_coach"):
            weekday = t["weekday"]
            time = f"{t['start_hour']:02d}:{t['start_min']:02d}"
            day = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"][weekday]
            label = f"{day} о {time}"
            options.append((tid, "constant", label))

    if not options:
        await update.message.reply_text("Немає тренувань, які потребують нарахування платежів.")
        return

    context.user_data["charge_options"] = options
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"charge_select_{i}")]
        for i, (_, _, label) in enumerate(options)
    ]

    await update.message.reply_text(
        "Оберіть тренування для нарахування платежів:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_charge_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("charge_select_", ""))
    options = context.user_data.get("charge_options", [])
    if idx >= len(options):
        await query.edit_message_text("Помилка: тренування не знайдено.")
        return

    tid, ttype, label = options[idx]
    trainings = load_data("one_time_trainings" if ttype == "one_time" else "constant_trainings")
    training = trainings.get(tid)
    if not training:
        await query.edit_message_text("Тренування не знайдено.")
        return

    votes = load_data("votes", {"votes": {}})["votes"]
    training_id = (
        f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"
        if ttype == "one_time"
        else f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"
    )

    if training_id not in votes:
        await query.edit_message_text("Ніхто не голосував за це тренування.")
        return

    voters = votes[training_id]
    yes_voters = [uid for uid, v in voters.items() if v["vote"] == "yes"]
    if not yes_voters:
        await query.edit_message_text("Ніхто не проголосував 'так' за це тренування.")
        return

    per_person = round(TRAINING_COST / len(yes_voters))
    training_datetime = (
        f"{training['date']} {training['start_hour']:02d}:{training['start_min']:02d}"
        if ttype == "one_time"
        else f"{label}"
    )

    payments = load_data("payments", {})
    new_payments = []

    for uid in yes_voters:
        new_entry = {
            "user_id": uid,
            "training_id": training_id,
            "amount": per_person,
            "training_datetime": training_datetime,
            "card": CARD_NUMBER,
            "paid": False
        }
        payments[f"{training_id}_{uid}"] = new_entry

        keyboard = [
            [InlineKeyboardButton("✅ Я оплатив(ла)", callback_data=f"paid_yes_{training_id}_{uid}")]
        ]

        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(f"💳 Ти відвідав(-ла) тренування {training_datetime}.\n"
                      f"Сума до сплати: {per_person} грн\n"
                      f"Карта для оплати: {CARD_NUMBER}\n\n"
                      f"Натисни кнопку нижче, коли оплатиш:"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"❌ Помилка надсилання повідомлення для {uid}: {e}")

    save_data(payments, "payments")
    trainings[tid]["status"] = "charged"
    save_data(trainings, "one_time_trainings" if ttype == "one_time" else "constant_trainings")

    await query.edit_message_text("✅ Повідомлення з інструкцією надіслано всім, хто голосував 'так'.")

async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    training_id, user_id = parts[2], parts[3]

    payments = load_data("payments", {})
    key = f"{training_id}_{user_id}"

    if key not in payments:
        await query.edit_message_text("⚠️ Помилка: запис про платіж не знайдено.")
        return

    payments[key]["paid"] = True
    save_data(payments, "payments")
    await query.edit_message_text("✅ Дякуємо! Оплату зареєстровано.")

    # Перевіряємо, чи всі вже оплатили
    all_paid = all(p["paid"] for p in payments.values() if p["training_id"] == training_id)
    if all_paid:
        one_time_trainings = load_data("one_time_trainings", {})
        constant_trainings = load_data("constant_trainings", {})

        for t in (one_time_trainings, constant_trainings):
            for tid, tr in t.items():
                tr_id = (
                    f"{tr['date']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                    if "date" in tr
                    else f"const_{tr['weekday']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                )
                if tr_id == training_id:
                    tr["status"] = "collected"
                    save_data(t, "one_time_trainings" if "date" in tr else "constant_trainings")
                    for admin in ADMIN_IDS:
                        try:
                            await context.bot.send_message(
                                chat_id=int(admin),
                                text=f"✅ Всі учасники тренування {training_id} оплатили. Статус оновлено на 'collected'."
                            )
                        except Exception as e:
                            print(f"❌ Не вдалося надіслати повідомлення адміну {admin}: {e}")
                    return


