from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from data import load_data, save_data
from validation import ADMIN_IDS, is_authorized

ENTER_COST = range(1)
TRAINING_COST = 1400
CARD_NUMBER = "5457 0825 2151 6794"

async def charge_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    one_time = load_data("one_time_trainings", {})
    constant = load_data("constant_trainings", {})

    options = []
    keyboard = []

    for tid, t in one_time.items():
        if t.get("with_coach") and t.get("status") == "not charged":
            label = f"{t['date']} о {t['start_hour']:02d}:{t['start_min']:02d}"
            index = len(options)
            options.append((tid, "one_time", label))  # or "constant"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"charge_select_{index}")])

    for tid, t in constant.items():
        if t.get("with_coach") and t.get("status") == "not charged":
            day = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"][t["weekday"]]
            label = f"{day} о {t['start_hour']:02d}:{t['start_min']:02d}"
            index = len(options)
            options.append((tid, "constant", label))  # or "constant"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"charge_select_{index}")])

    if not options:
        await update.message.reply_text("Немає тренувань для нарахування.")
        return

    context.user_data["charge_options"] = options
    await update.message.reply_text("Оберіть тренування:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_charge_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    options = context.user_data.get("charge_options", [])
    if not options:
        await query.edit_message_text(
            "⚠️ Помилка: не вдалося знайти варіанти. Можливо, сесія закінчилась. Спробуй /charge_all ще раз.")
        return ConversationHandler.END

    try:
        idx = int(query.data.replace("charge_select_", ""))
        opt = options[idx]
    except (ValueError, IndexError):
        await query.edit_message_text("⚠️ Некоректний вибір. Спробуй /charge_all ще раз.")
        return ConversationHandler.END

    opt = options[idx]
    if not isinstance(opt, (tuple, list)) or len(opt) != 3:
        await query.edit_message_text("⚠️ Дані про тренування пошкоджені.")
        return

    tid, ttype, label = opt
    context.user_data["selected_training"] = (tid, ttype, label)

    await query.edit_message_text(
        f"Ви обрали: {label}\n\nВведіть загальну вартість тренування в гривнях:"
    )
    return ENTER_COST



async def handle_enter_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cost = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Будь ласка, введіть число.")
        return ENTER_COST

    tid, ttype, label = context.user_data.get("selected_training")
    data = load_data("one_time_trainings" if ttype == "one_time" else "constant_trainings")
    training = data.get(tid)
    if not training:
        await update.message.reply_text("⚠️ Тренування не знайдено.")
        return ConversationHandler.END

    votes = load_data("votes", {"votes": {}})["votes"]
    training_id = (
        f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"
        if ttype == "one_time"
        else f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"
    )

    yes_voters = [uid for uid, v in votes.get(training_id, {}).items() if v.get("vote") == "yes"]
    if not yes_voters:
        await update.message.reply_text("⚠️ Немає голосів 'так' за це тренування.")
        return ConversationHandler.END

    amount = round(cost / len(yes_voters))
    payments = load_data("payments", {})

    for uid in yes_voters:
        key = f"{training_id}_{uid}"
        payments[key] = {
            "user_id": uid,
            "training_id": training_id,
            "training_datetime": label,
            "amount": amount,
            "card": CARD_NUMBER,
            "paid": False
        }
        keyboard = [[InlineKeyboardButton("✅ Я оплатив(ла)", callback_data=f"paid_yes_{training_id}_{uid}")]]
        try:
            await update.message.bot.send_message(
                chat_id=int(uid),
                text=(f"💳 Ти відвідав(-ла) тренування {label}.\n"
                      f"Сума до сплати: {amount} грн\n"
                      f"Карта: {CARD_NUMBER}\n\nНатисни кнопку після оплати."),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"❌ Не вдалося надіслати повідомлення {uid}: {e}")

    data[tid]["status"] = "charged"
    save_data("payments", payments)
    save_data("one_time_trainings" if ttype == "one_time" else "constant_trainings", data)

    await update.message.reply_text("✅ Повідомлення надіслано всім, хто проголосував 'так'.")
    return ConversationHandler.END


async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payload = query.data[len("paid_yes_"):]
    training_id, user_id = payload.rsplit("_", 1)

    payments = load_data("payments", {})
    key = f"{training_id}_{user_id}"

    if key not in payments:
        await query.edit_message_text("⚠️ Помилка: запис про платіж не знайдено. Використай команду /pay_debt для підтвердження")
        return

    payments[key]["paid"] = True
    save_data(payments, "payments")
    await query.edit_message_text("✅ Дякуємо! Оплату зареєстровано.")

    all_paid = all(p["paid"] for p in payments.values() if p["training_id"] == training_id)
    if all_paid:
        for coll_name in ("one_time_trainings", "constant_trainings"):
            trainings = load_data(coll_name, {})
            for tid, tr in trainings.items():
                tr_id = (
                    f"{tr['date']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                    if "date" in tr
                    else f"const_{tr['weekday']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                )
                if tr_id == training_id:
                    tr["status"] = "collected"
                    save_data(trainings, coll_name)
                    for admin in ADMIN_IDS:
                        try:
                            await context.bot.send_message(
                                chat_id=int(admin),
                                text=f"✅ Всі учасники тренування {training_id} оплатили. Статус оновлено на 'collected'."
                            )
                        except Exception as e:
                            print(f"❌ Не вдалося надіслати повідомлення адміну {admin}: {e}")
                    return

async def pay_debt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    payments = load_data("payments", {})

    user_debts = [p for p in payments.values() if p["user_id"] == user_id and not p.get("paid", False)]

    if not user_debts:
        await update.message.reply_text("🎉 У тебе немає неоплачених тренувань!")
        return

    context.user_data["pay_debt_options"] = user_debts

    keyboard = [[InlineKeyboardButton(f"{p['training_datetime']} - {p['amount']} грн", callback_data=f"paydebt_select_{i}")]
                for i, p in enumerate(user_debts)]

    await update.message.reply_text("Оберіть тренування для підтвердження оплати:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_pay_debt_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("paydebt_select_", ""))
    options = context.user_data.get("pay_debt_options", [])

    if not options or idx >= len(options):
        await query.edit_message_text("⚠️ Помилка: тренування не знайдено.")
        return

    selected = options[idx]
    context.user_data["selected_debt"] = selected

    keyboard = [[InlineKeyboardButton("✅ Так, оплатив(ла)", callback_data="paydebt_confirm_yes")]]
    await query.edit_message_text(f"Ти точно оплатив(-ла) {selected['amount']} грн за тренування {selected['training_datetime']}?",
                                  reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_pay_debt_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    selected = context.user_data.get("selected_debt")
    if not selected:
        await query.edit_message_text("⚠️ Помилка: тренування не знайдено.")
        return

    payments = load_data("payments", {})
    key = f"{selected['training_id']}_{selected['user_id']}"

    if key not in payments:
        await query.edit_message_text("⚠️ Помилка: запис про платіж не знайдено.")
        return

    payments[key]["paid"] = True
    save_data(payments, "payments")
    await query.edit_message_text("✅ Дякуємо! Оплату зареєстровано.")

    training_id = selected["training_id"]
    all_paid = all(p["paid"] for p in payments.values() if p["training_id"] == training_id)
    if all_paid:
        for coll_name in ("one_time_trainings", "constant_trainings"):
            trainings = load_data(coll_name, {})
            for tid, tr in trainings.items():
                tr_id = (
                    f"{tr['date']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                    if "date" in tr
                    else f"const_{tr['weekday']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                )
                if tr_id == training_id:
                    tr["status"] = "collected"
                    save_data(trainings, coll_name)
                    for admin in ADMIN_IDS:
                        try:
                            await context.bot.send_message(
                                chat_id=int(admin),
                                text=f"✅ Всі учасники тренування {training_id} оплатили. Статус оновлено на 'collected'."
                            )
                        except Exception as e:
                            print(f"❌ Не вдалося надіслати повідомлення адміну {admin}: {e}")
                    return
async def view_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("У вас немає доступу до перегляду платежів.")
        return

    payments = load_data("payments", {})
    if not payments:
        await update.message.reply_text("Немає записаних платежів.")
        return

    training_map = {}
    for p in payments.values():
        tid = p["training_id"]
        if tid not in training_map:
            training_map[tid] = p["training_datetime"]

    context.user_data["view_payment_options"] = list(training_map.keys())

    keyboard = [
        [InlineKeyboardButton(training_map[tid], callback_data=f"view_payment_{i}")]
        for i, tid in enumerate(training_map.keys())
    ]

    await update.message.reply_text(
        "Оберіть тренування для перегляду платежів:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_view_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("view_payment_", ""))
    keys = context.user_data.get("view_payment_options", [])
    if idx >= len(keys):
        await query.edit_message_text("⚠️ Помилка: тренування не знайдено.")
        return

    training_id = keys[idx]
    payments = load_data("payments", {})
    users = load_data("users", {})

    paid = []
    unpaid = []

    for p in payments.values():
        if p["training_id"] != training_id:
            continue
        name = users.get(p["user_id"], {}).get("name", p["user_id"])
        if p.get("paid"):
            paid.append(name)
        else:
            unpaid.append(name)

    message = f"💰 Платежі за тренування {payments[next(k for k in payments if payments[k]['training_id'] == training_id)]['training_datetime']}\n\n"
    message += f"✅ Оплатили:\n{chr(10).join(paid) if paid else 'Ніхто'}\n\n"
    message += f"❌ Не оплатили:\n{chr(10).join(unpaid) if unpaid else 'Немає боржників'}"

    await query.edit_message_text(message)