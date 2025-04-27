from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import JSON_FILE
from data import load_data, save_data
from trainings import get_last_training
from voting import load_votes
from datetime import datetime, timedelta

PAYMENTS_FILE = "payments.json"
TRAINING_COST = 1750
CARD_NUMBER = "5375 4141 0273 8014"
DEBTS_FILE = "debts.json"

def load_debts():
    data = load_data(DEBTS_FILE, [])
    if not isinstance(data, list):
        data = []
    return data

def save_debt(debt):
    data = load_debts()
    data.append(debt)
    save_data(data, DEBTS_FILE)


def load_payments():
    data = load_data(PAYMENTS_FILE, [])
    if not isinstance(data, list):
        data = []
    return data


def save_payment(payment):
    data = load_payments()
    data.append(payment)
    save_data(data, PAYMENTS_FILE)


async def charge_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = load_data(JSON_FILE)
    votes = load_votes()["votes"]
    date_str, training_id = get_last_training()

    if not training_id:
        await update.message.reply_text("Немає останнього тренування для нарахування.")
        return

    one_time_trainings = load_data("one_time_trainings.json", {})
    constant_trainings = load_data("constant_trainings.json", {})

    training_key = None
    training = None

    if str(training_id) in one_time_trainings:
        training = one_time_trainings[str(training_id)]
        date = training["date"]
        hour = training["start_hour"]
        minute = training["start_min"]
        training_key = f"{date}_{hour:02d}:{minute:02d}"
    elif str(training_id) in constant_trainings:
        training = constant_trainings[str(training_id)]
        weekday = training["weekday"]
        hour = training["start_hour"]
        minute = training["start_min"]
        training_key = f"const_{weekday}_{hour:02d}:{minute:02d}"

    if not training_key or training_key not in votes:
        await update.message.reply_text("Ніхто не проголосував 'так' за останнє тренування.")
        return

    voters = votes[training_key]
    yes_voters = [uid for uid, v in voters.items() if v["vote"] == "yes"]

    if not yes_voters:
        await update.message.reply_text("Ніхто не проголосував 'так' за останнє тренування.")
        return

    per_person = round(TRAINING_COST / len(yes_voters)) if training.get("with_coach") else 0
    training_datetime = (
        f"{training['date']} {training['start_hour']:02d}:{training['start_min']:02d}"
        if 'date' in training else f"{date_str} {hour:02d}:{minute:02d}"
    )

    for uid in yes_voters:
        uid_str = str(uid)
        if uid_str not in user_data:
            continue

        context.bot_data[f"charge_{uid_str}"] = {
            "training_id": training_key,
            "amount": per_person,
            "training_datetime": training_datetime,
            "card": CARD_NUMBER
        }

        keyboard = [
            [
                InlineKeyboardButton("✅ Я оплатив(ла)", callback_data=f"paid_yes_{uid_str}"),
                InlineKeyboardButton("❌ Ще не оплатив(ла)", callback_data=f"paid_no_{uid_str}")
            ]
        ]

        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(
                    f"💳 Ти відвідав(-ла) останнє тренування {training_datetime}.\n"
                    f"Сума до сплати: {per_person} грн\n"
                    f"Карта для оплати: {CARD_NUMBER}\n\n"
                    f"Натисни, якщо ти вже оплатив:"
                ),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"❌ Помилка надсилання повідомлення для {uid}: {e}")

    await update.message.reply_text("✅ Повідомлення з інструкцією надіслано всім, хто голосував 'так'.")

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
    votes = load_votes()["votes"]

    two_weeks_ago = datetime.today().date() - timedelta(days=14)
    options = []

    for tid, training_votes in votes.items():
        if tid.startswith("const_"):
            continue  # optional: skip constant trainings if you want

        try:
            date_part, time_part = tid.split("_")
            training_date = datetime.strptime(date_part, "%d.%m.%Y").date()
            if training_date >= two_weeks_ago:
                options.append((tid, training_date, time_part))
        except:
            continue

    if not options:
        await update.message.reply_text("Немає тренувань за останні 2 тижні.")
        return

    context.user_data["debt_training_options"] = options

    keyboard = [
        [InlineKeyboardButton(f"{d.strftime('%d.%m.%Y')} о {t}", callback_data=f"debt_check_{i}")]
        for i, (tid, d, t) in enumerate(options)
    ]

    await update.message.reply_text(
        "Оберіть тренування для перевірки оплати:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_debt_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("debt_check_", ""))
    options = context.user_data.get("debt_training_options")
    if not options or idx >= len(options):
        await query.edit_message_text("Помилка: тренування не знайдено.")
        return

    training_id, date_obj, time_str = options[idx]
    training_datetime = f"{date_obj.strftime('%d.%m.%Y')} {time_str}"

    votes = load_votes()["votes"].get(training_id, {})
    payments = load_payments()
    paid_ids = {p["user_id"] for p in payments if p["training_id"] == training_id}

    yes_voters = [uid for uid, v in votes.items() if v["vote"] == "yes" and uid not in paid_ids]
    all_yes = [uid for uid, v in votes.items() if v["vote"] == "yes"]

    if not yes_voters:
        await query.edit_message_text("Усі, хто проголосував 'так', вже оплатили тренування.")
        return

    per_person = round(TRAINING_COST / len(all_yes))
    debts_before = load_debts()

    for uid in yes_voters:
        debt_entry = {
            "user_id": uid,
            "training_id": training_id,
            "amount": per_person,
            "training_datetime": training_datetime,
            "card": CARD_NUMBER
        }
        save_debt(debt_entry)

        # Calculate total debt
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

    await query.edit_message_text(f"📬 Повідомлення про борг надіслано {len(yes_voters)} учасникам.")


async def pay_debt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    debts = load_data(DEBTS_FILE, [])

    user_debts = [d for d in debts if d["user_id"] == user_id]

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

    # Save payment
    payments = load_data(PAYMENTS_FILE, [])
    payments.append({
        "user_id": selected_debt["user_id"],
        "training_id": selected_debt["training_id"],
        "amount": selected_debt["amount"],
        "training_datetime": selected_debt["training_datetime"],
        "card": selected_debt["card"]
    })
    save_data(payments, PAYMENTS_FILE)

    # Remove debt
    debts = load_data(DEBTS_FILE, [])
    debts = [d for d in debts if not (d["user_id"] == selected_debt["user_id"] and d["training_id"] == selected_debt["training_id"])]
    save_data(debts, DEBTS_FILE)

    await query.edit_message_text("✅ Дякуємо! Оплату зареєстровано і борг видалено.")




