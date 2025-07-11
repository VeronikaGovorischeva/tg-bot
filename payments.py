from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, \
    CommandHandler
from training_archive import archive_training_after_charge
from data import load_data, save_data
from validation import ADMIN_IDS, is_authorized

CHARGE_SELECT_TRAINING, CHARGE_ENTER_AMOUNT = range(100, 102)
CARD_NUMBER = "5457 0825 2151 6794"


async def charge_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ У вас немає прав для цієї команди.")
        return ConversationHandler.END

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
            day = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"][weekday]
            label = f"{day} о {time}"
            options.append((tid, "constant", label))

    if not options:
        await update.message.reply_text("Немає тренувань, які потребують нарахування платежів.")
        return ConversationHandler.END

    context.user_data["charge_options"] = options
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"charge_select_{i}")]
        for i, (_, _, label) in enumerate(options)
    ]

    await update.message.reply_text(
        "Оберіть тренування для нарахування платежів:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return CHARGE_SELECT_TRAINING


async def handle_charge_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("charge_select_", ""))
    options = context.user_data.get("charge_options", [])

    if idx >= len(options):
        await query.edit_message_text("Помилка: тренування не знайдено.")
        return ConversationHandler.END

    tid, ttype, label = options[idx]
    context.user_data["selected_training"] = (tid, ttype, label)

    await query.edit_message_text(
        f"Ви обрали тренування: {label}\n\n"
        "Введіть суму для цього тренування:\n"
        "Наприклад: 150"
    )

    return CHARGE_ENTER_AMOUNT


async def handle_charge_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if "selected_training" not in context.user_data:
        await update.message.reply_text("⚠️ Помилка: дані про тренування втрачено. Спробуйте /charge_all знову.")
        return ConversationHandler.END

    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            await update.message.reply_text("⚠️ Сума повинна бути більше 0. Спробуйте ще раз:")
            return CHARGE_ENTER_AMOUNT
    except ValueError:
        await update.message.reply_text("⚠️ Будь ласка, введіть число. Спробуйте ще раз:")
        return CHARGE_ENTER_AMOUNT

    tid, ttype, label = context.user_data["selected_training"]

    trainings = load_data("one_time_trainings" if ttype == "one_time" else "constant_trainings")
    training = trainings.get(tid)
    if not training:
        await update.message.reply_text("Тренування не знайдено.")
        return ConversationHandler.END

    votes = load_data("votes", {"votes": {}})["votes"]
    training_id = (
        f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"
        if ttype == "one_time"
        else f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"
    )

    if training_id not in votes:
        await update.message.reply_text("Ніхто не голосував за це тренування.")
        return ConversationHandler.END

    voters = votes[training_id]
    yes_voters = [uid for uid, v in voters.items() if v["vote"] == "yes"]
    if not yes_voters:
        await update.message.reply_text("Ніхто не проголосував 'так' за це тренування.")
        return ConversationHandler.END

    per_person = round(amount / len(yes_voters))
    training_datetime = (
        f"{training['date']} {training['start_hour']:02d}:{training['start_min']:02d}"
        if ttype == "one_time"
        else f"{label}"
    )

    payments = load_data("payments", {})
    success_count = 0

    for uid in yes_voters:
        payment_key = f"{training_id}_{uid}"
        payments[payment_key] = {
            "user_id": uid,
            "training_id": training_id,
            "amount": per_person,
            "total_training_cost": amount,
            "training_datetime": training_datetime,
            "card": CARD_NUMBER,
            "paid": False
        }

        keyboard = [[InlineKeyboardButton("✅ Я оплатив(ла)", callback_data=f"paid_yes_{training_id}_{uid}")]]
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(f"💳 Ти відвідав(-ла) тренування {training_datetime}.\n"
                      f"Сума до сплати: {per_person} грн\n"
                      f"Карта для оплати: `{CARD_NUMBER}`\n\n"
                      f"Натисни кнопку нижче, коли оплатиш:"),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            print(f"❌ Помилка надсилання повідомлення для {uid}: {e}")

    save_data(payments, "payments")
    trainings[tid]["status"] = "charged"
    trainings[tid]["voting_opened"] = False
    save_data(trainings, "one_time_trainings" if ttype == "one_time" else "constant_trainings")

    try:
        archive_success = archive_training_after_charge(training_id, ttype)
        if archive_success:
            print(f"✅ Training {training_id} archived successfully")
        else:
            print(f"⚠️ Failed to archive training {training_id}")
    except Exception as e:
        print(f"❌ Error archiving training {training_id}: {e}")

    await update.message.reply_text(
        f"✅ Нарахування завершено!\n"
        f"💰 Загальна сума: {amount} грн\n"
        f"👥 Учасників: {len(yes_voters)}\n"
        f"💵 По {per_person} грн з особи\n"
        f"📤 Повідомлення надіслано {success_count} учасникам"
    )

    return ConversationHandler.END


async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payload = query.data[len("paid_yes_"):]
    training_id, user_id = payload.rsplit("_", 1)

    payments = load_data("payments", {})
    key = f"{training_id}_{user_id}"

    if key not in payments:
        await query.edit_message_text(
            "⚠️ Помилка: запис про платіж не знайдено. Використай команду /pay_debt для підтвердження")
        return

    payments[key]["paid"] = True
    save_data(payments, "payments")
    await query.edit_message_text("✅ Дякуємо! Оплату зареєстровано.")

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


async def cancel_charge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Нарахування скасовано.")
    return ConversationHandler.END


async def pay_debt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    payments = load_data("payments", {})

    user_debts = [p for p in payments.values() if p["user_id"] == user_id and not p.get("paid", False)]

    if not user_debts:
        await update.message.reply_text("🎉 У тебе немає неоплачених тренувань!")
        return

    context.user_data["pay_debt_options"] = user_debts

    keyboard = [
        [InlineKeyboardButton(
            f"{p['training_datetime']} - {p['amount']} грн",
            callback_data=f"paydebt_select_{i}"
        )] for i, p in enumerate(user_debts)
    ]

    await update.message.reply_text(
        f"Карта: `{CARD_NUMBER}`\nОберіть тренування для підтвердження оплати:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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

    keyboard = [
        [InlineKeyboardButton("✅ Так, оплатив(ла)", callback_data="paydebt_confirm_yes")]
    ]

    await query.edit_message_text(
        f"Ти точно оплатив(-ла) {selected['amount']} грн за тренування {selected['training_datetime']}?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


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

    # Optional: Check if all paid -> notify admins
    training_id = selected["training_id"]
    all_paid = all(p["paid"] for p in payments.values() if p["training_id"] == training_id)
    if all_paid:
        from validation import ADMIN_IDS
        from trainings import load_data as load_trainings, save_data as save_trainings
        one_time = load_trainings("one_time_trainings")
        constant = load_trainings("constant_trainings")
        for t in (one_time, constant):
            for tid, tr in t.items():
                tr_id = (
                    f"{tr['date']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                    if "date" in tr
                    else f"const_{tr['weekday']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                )
                if tr_id == training_id:
                    tr["status"] = "collected"
                    save_trainings(t, "one_time_trainings" if "date" in tr else "constant_trainings")
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

    message = f"💰 Платежі за тренування {payments[next(k for k in payments if payments[k]['training_id'] == training_id)]['training_datetime']}:\n\n"
    message += f"✅ Оплатили:\n{chr(10).join(paid) if paid else 'Ніхто'}\n\n"
    message += f"❌ Не оплатили:\n{chr(10).join(unpaid) if unpaid else 'Немає боржників'}"

    await query.edit_message_text(message)


def create_charge_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("charge_all", charge_all)],
        states={
            CHARGE_SELECT_TRAINING: [
                CallbackQueryHandler(handle_charge_selection, pattern=r"^charge_select_\d+$")
            ],
            CHARGE_ENTER_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_charge_amount_input)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_charge)
        ],
    )


def setup_payment_handlers(app):
    # /pay_debt
    app.add_handler(CommandHandler("pay_debt", pay_debt))
    # Admin: /charge_all
    app.add_handler(create_charge_conversation_handler())
    # Admin: /view_payments
    app.add_handler(CommandHandler("view_payments", view_payments))

    # Other
    app.add_handler(CallbackQueryHandler(handle_payment_confirmation, pattern=r"^paid_yes_.*"))
    app.add_handler(CallbackQueryHandler(handle_pay_debt_selection, pattern=r"^paydebt_select_\d+$"))
    app.add_handler(CallbackQueryHandler(handle_pay_debt_confirmation, pattern=r"^paydebt_confirm_yes$"))
    app.add_handler(CallbackQueryHandler(handle_view_payment_selection, pattern=r"^view_payment_\d+"))
