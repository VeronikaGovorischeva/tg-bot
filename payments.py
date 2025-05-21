from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from data import load_data, save_data
from trainings import get_last_training
from datetime import datetime, timedelta

DATA_FILE = "users"
PAYMENTS_FILE = "payments"
DEBTS_FILE = "debts"

TRAINING_COST = 1750
CARD_NUMBER = "5375 4141 0273 8014"


def load_debts():
    data = load_data('debts', default=[])
    if isinstance(data, dict) and data:
        return list(data.values())
    return []


def save_debt(debt):
    debts = load_debts()
    debts.append(debt)
    debts_dict = {str(i): debt for i, debt in enumerate(debts)}
    save_data(debts_dict, 'debts')


def load_payments():
    data = load_data('payments', default=[])
    if isinstance(data, dict) and data:
        return list(data.values())
    return []


def save_payment(payment):
    payments = load_payments()
    payments.append(payment)
    payments_dict = {str(i): payment for i, payment in enumerate(payments)}
    save_data(payments_dict, 'payments')


async def charge_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    one_time_trainings = load_data("one_time_trainings", {})
    constant_trainings = load_data("constant_trainings", {})

    options = []

    for tid, t in one_time_trainings.items():
        if t.get("status") == "not charged":
            date = t["date"]
            time = f"{t['start_hour']:02d}:{t['start_min']:02d}"
            label = f"{date} о {time}"
            options.append((tid, "one_time", label))

    for tid, t in constant_trainings.items():
        if t.get("status") == "not charged":
            weekday = t["weekday"]
            time = f"{t['start_hour']:02d}:{t['start_min']:02d}"
            day = ["Понеділок","Вівторок","Середа","Четвер","П'ятниця","Субота","Неділя"][weekday]
            label = f"{day} о {time}"
            options.append((tid, "constant", label))

    if not options:
        await update.message.reply_text("Немає тренувань зі статусом 'not charged'.")
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

    per_person = round(TRAINING_COST / len(yes_voters)) if training.get("with_coach") else 0
    training_datetime = (
        f"{training['date']} {training['start_hour']:02d}:{training['start_min']:02d}"
        if ttype == "one_time"
        else f"{datetime.today().strftime('%d.%m.%Y')} {training['start_hour']:02d}:{training['start_min']:02d}"
    )

    user_data = load_data("users")

    for uid in yes_voters:
        if str(uid) not in user_data:
            continue

        context.bot_data[f"charge_{uid}"] = {
            "training_id": training_id,
            "amount": per_person,
            "training_datetime": training_datetime,
            "card": CARD_NUMBER
        }

        keyboard = [
            [
                InlineKeyboardButton("✅ Я оплатив(ла)", callback_data=f"paid_yes_{uid}"),
                InlineKeyboardButton("❌ Ще не оплатив(ла)", callback_data=f"paid_no_{uid}")
            ]
        ]

        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(
                    f"💳 Ти відвідав(-ла) тренування {training_datetime}.\n"
                    f"Сума до сплати: {per_person} грн\n"
                    f"Карта для оплати: {CARD_NUMBER}\n\n"
                    f"Натисни, якщо ти вже оплатив:"
                ),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"❌ Помилка надсилання повідомлення для {uid}: {e}")

    # Update training status
    trainings[tid]["status"] = "charged"
    save_data(trainings, "one_time_trainings" if ttype == "one_time" else "constant_trainings")

    await query.edit_message_text("✅ Повідомлення з інструкцією надіслано всім, хто голосував 'так'.")



async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    user_id = data[2]
    confirmed = data[1] == "yes"

    info = context.bot_data.get(f"charge_{user_id}")
    if not info:
        await query.edit_message_text("⚠️ Помилка: інформацію про платіж не знайдено.")
        return

    if confirmed:
        save_payment({
            "user_id": user_id,
            "training_id": info["training_id"],
            "amount": info["amount"],
            "training_datetime": info["training_datetime"],
            "card": info["card"]
        })
        await query.edit_message_text("✅ Дякуємо! Оплату зареєстровано.")
    else:
        await query.edit_message_text("⏳ Добре! Нагадай, як тільки оплатиш.")


async def collect_debts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    one_time_trainings = load_data("one_time_trainings", {})
    constant_trainings = load_data("constant_trainings", {})

    options = []

    for tid, t in one_time_trainings.items():
        if t.get("status") == "charged":
            date = t["date"]
            time = f"{t['start_hour']:02d}:{t['start_min']:02d}"
            options.append((tid, "one_time", f"{date} о {time}"))

    for tid, t in constant_trainings.items():
        if t.get("status") == "charged":
            weekday = t["weekday"]
            time = f"{t['start_hour']:02d}:{t['start_min']:02d}"
            day = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"][weekday]
            options.append((tid, "constant", f"{day} о {time}"))

    if not options:
        await update.message.reply_text("Немає тренувань зі статусом 'charged'.")
        return

    context.bot_data[f"debt_training_options_{update.effective_user.id}"] = options
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"debt_check_{i}")]
        for i, (_, _, label) in enumerate(options)
    ]

    await update.message.reply_text(
        "Оберіть тренування для перевірки боргів:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_debt_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("debt_check_", ""))
    user_id = str(update.effective_user.id)
    options = context.bot_data.get(f"debt_training_options_{user_id}", [])
    if idx >= len(options):
        await query.edit_message_text("Помилка: тренування не знайдено.")
        return

    tid, ttype, label = options[idx]

    trainings = load_data("one_time_trainings" if ttype == "one_time" else "constant_trainings")
    training = trainings.get(tid)
    if not training:
        await query.edit_message_text("Тренування не знайдено.")
        return

    training_id = (
        f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"
        if ttype == "one_time"
        else f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"
    )
    training_datetime = (
        f"{training['date']} {training['start_hour']:02d}:{training['start_min']:02d}"
        if ttype == "one_time"
        else f"{datetime.today().strftime('%d.%m.%Y')} {training['start_hour']:02d}:{training['start_min']:02d}"
    )

    votes = load_data("votes", {"votes": {}}).get("votes", {}).get(training_id, {})
    payments = load_data("payments", [])
    paid_ids = {p["user_id"] for p in payments if p["training_id"] == training_id}
    all_yes = [uid for uid, v in votes.items() if v["vote"] == "yes"]
    debtors = [uid for uid in all_yes if uid not in paid_ids]

    if not debtors:
        await query.edit_message_text("Усі, хто проголосував 'так', вже оплатили тренування.")
        return

    per_person = round(TRAINING_COST / len(all_yes)) if training.get("with_coach") else 0
    debts_before = load_debts()

    for uid in debtors:
        debt_entry = {
            "user_id": uid,
            "training_id": training_id,
            "amount": per_person,
            "training_datetime": training_datetime,
            "card": CARD_NUMBER
        }
        save_debt(debt_entry)

        total_debt = sum(
            d["amount"] for d in debts_before + [debt_entry] if d["user_id"] == uid
        )

        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(
                    f"🚨 Ти не оплатив(-ла) тренування {training_datetime}.\n"
                    f"➕ Додано до боргу: {per_person} грн\n"
                    f"💰 Загальний борг: {total_debt} грн\n"
                    f"Карта для оплати: {CARD_NUMBER}"
                )
            )
        except Exception as e:
            print(f"❌ Не вдалося надіслати повідомлення {uid}: {e}")

    # Update training status
    trainings[tid]["status"] = "collected"
    save_data(trainings, "one_time_trainings" if ttype == "one_time" else "constant_trainings")

    await query.edit_message_text(f"📬 Повідомлення про борг надіслано {len(debtors)} учасникам.")

async def pay_debt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    debts = load_data(DEBTS_FILE, {})

    user_debts = [d for d in debts.values() if d["user_id"] == user_id]

    if not user_debts:
        await update.message.reply_text("У тебе немає боргів! 🎉")
        return

    context.user_data["pay_debt_options"] = user_debts

    keyboard = [
        [InlineKeyboardButton(
            f"{d['training_datetime']} - {d['amount']} грн",
            callback_data=f"paydebt_select_{i}"
        )] for i, d in enumerate(user_debts)
    ]

    await update.message.reply_text(
        "Оберіть борг, який хочете оплатити:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )



async def handle_pay_debt_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("paydebt_select_", ""))
    options = context.user_data.get("pay_debt_options", [])

    if not options or idx >= len(options):
        await query.edit_message_text("Помилка: не знайдено боргу.")
        return

    selected_debt = options[idx]
    context.user_data["selected_debt"] = selected_debt

    keyboard = [
        [
            InlineKeyboardButton("✅ Так, оплатив(ла)", callback_data="paydebt_confirm_yes"),
            InlineKeyboardButton("❌ Ні, ще не оплатив(ла)", callback_data="paydebt_confirm_no")
        ]
    ]

    await query.edit_message_text(
        f"Ти точно оплатив(-ла) {selected_debt['amount']} грн за тренування {selected_debt['training_datetime']}?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_pay_debt_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "paydebt_confirm_no":
        await query.edit_message_text("⏳ Добре! Натисни знову /pay_debt, коли оплатиш.")
        return

    selected_debt = context.user_data.get("selected_debt")
    if not selected_debt:
        await query.edit_message_text("Помилка: борг не знайдено для підтвердження.")
        return

    payments = load_data(PAYMENTS_FILE, [])
    payments.append({
        "user_id": selected_debt["user_id"],
        "training_id": selected_debt["training_id"],
        "amount": selected_debt["amount"],
        "training_datetime": selected_debt["training_datetime"],
        "card": selected_debt["card"]
    })
    payments_dict = {str(i): payment for i, payment in enumerate(payments)}
    save_data(payments_dict, PAYMENTS_FILE)

    # Remove debt
    debts = load_data(DEBTS_FILE, {})
    debts = {
        k: v for k, v in debts.items()
        if not (v["user_id"] == selected_debt["user_id"] and v["training_id"] == selected_debt["training_id"])
    }
    save_data(debts, DEBTS_FILE)

    await query.edit_message_text("✅ Дякуємо! Оплату зареєстровано і борг видалено.")

