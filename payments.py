from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, \
    CommandHandler
from training_archive import archive_training_after_charge
from data import load_data, save_data,log_command_usage
from validation import ADMIN_IDS, is_authorized

CHARGE_SELECT_TRAINING, CHARGE_ENTER_AMOUNT, CHARGE_ENTER_CARD = range(100, 103)
CARD_NUMBER = "5457 0825 2151 6794"


async def charge_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    log_command_usage(user_id, "/charge_all")
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

    text = (update.message.text or "").strip()
    try:
        amount = int(text)
        if amount <= 0:
            await update.message.reply_text("⚠️ Сума повинна бути більше 0. Спробуйте ще раз:")
            return CHARGE_ENTER_AMOUNT
    except ValueError:
        await update.message.reply_text("⚠️ Будь ласка, введіть число. Спробуйте ще раз:")
        return CHARGE_ENTER_AMOUNT

    # Save and ask for card number
    context.user_data["charge_amount"] = amount

    await update.message.reply_text(
        "Введіть номер картки для оплати (можна з пробілами, IBAN також підійде):"
    )
    return CHARGE_ENTER_CARD

async def handle_charge_card_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Validate presence of required context
    if "selected_training" not in context.user_data or "charge_amount" not in context.user_data:
        await update.message.reply_text("⚠️ Помилка: дані втрачено. Спробуйте /charge_all знову.")
        return ConversationHandler.END

    card = (update.message.text or "").strip()
    if not card:
        await update.message.reply_text("⚠️ Порожній номер картки. Введіть номер картки ще раз:")
        return CHARGE_ENTER_CARD

    tid, ttype, label = context.user_data["selected_training"]
    amount = int(context.user_data["charge_amount"])

    # Load training
    trainings_file = "one_time_trainings" if ttype == "one_time" else "constant_trainings"
    trainings = load_data(trainings_file, {})
    training = trainings.get(tid)
    if not training:
        await update.message.reply_text("⚠️ Тренування не знайдено.")
        return ConversationHandler.END

    # Build training_id like before
    if ttype == "one_time":
        training_id = f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"
        training_datetime = f"{training['date']} {training['start_hour']:02d}:{training['start_min']:02d}"
    else:
        training_id = f"const_{training['weekday']}_{training['start_hour']:02d}:{training['start_min']:02d}"
        training_datetime = label  # already like "Понеділок о 19:00"

    # Get voters
    votes = load_data("votes", {"votes": {}}).get("votes", {})
    if training_id not in votes or not votes[training_id]:
        await update.message.reply_text("Ніхто не голосував за це тренування.")
        return ConversationHandler.END

    voters = votes[training_id]
    yes_voters = [uid for uid, v in voters.items() if v.get("vote") == "yes"]
    if not yes_voters:
        await update.message.reply_text("Ніхто не проголосував 'так' за це тренування.")
        return ConversationHandler.END

    per_person = round(amount / len(yes_voters))

    payments = load_data("payments", {})
    success_count = 0

    # Create & send payments
    for uid in yes_voters:
        payment_key = f"{training_id}_{uid}"
        payments[payment_key] = {
            "user_id": uid,
            "training_id": training_id,
            "amount": per_person,
            "total_training_cost": amount,
            "training_datetime": training_datetime,
            "card": card,
            "paid": False
        }

        keyboard = [[InlineKeyboardButton("✅ Я оплатив(ла)", callback_data=f"paid_yes_{training_id}_{uid}")]]
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(f"💳 Ти відвідав(-ла) тренування {training_datetime}.\n"
                      f"Сума до сплати: {per_person} грн\n"
                      f"Карта для оплати: `{card}`\n\n"
                      f"Натисни кнопку нижче, коли оплатиш:"),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            print(f"❌ Помилка надсилання повідомлення для {uid}: {e}")

    save_data(payments, "payments")

    # Update training status and close voting flag
    trainings[tid]["status"] = "charged"
    trainings[tid]["voting_opened"] = False
    save_data(trainings, trainings_file)

    # Archive after charge (existing logic preserved)
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
        f"💳 Картка: {card}\n"
        f"📤 Повідомлення надіслано {success_count} учасникам"
    )

    return ConversationHandler.END



async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    PREFIX = "paid_yes_"
    if not data.startswith(PREFIX):
        await query.edit_message_text("⚠️ Некоректні дані підтвердження.")
        return

    # payload examples:
    #  - "25.09.2025_19:00_123456789"          (training)
    #  - "const_2_19:00_123456789"             (constant training)
    #  - "game_friendly_male_2025_2026_1_123"  (game)
    payload = data[len(PREFIX):]

    if "_" not in payload:
        await query.edit_message_text("⚠️ Некоректні дані підтвердження.")
        return

    # Always split from the right: everything before last "_" is training_id; last piece is user_id
    training_id, user_id = payload.rsplit("_", 1)
    is_game = training_id.startswith("game_")

    payments = load_data("payments", {})
    key = f"{training_id}_{user_id}"

    rec = payments.get(key)
    if not rec:
        # Defensive fallback if someone saved numeric user ids in a different type
        alt_key = f"{training_id}_{str(int(user_id))}" if user_id.isdigit() else None
        rec = payments.get(alt_key) if alt_key else None
        if not rec:
            await query.edit_message_text(
                "⚠️ Помилка: запис про платіж не знайдено. Використай команду /pay_debt для підтвердження."
            )
            return
        key = alt_key

    # Mark as paid
    rec["paid"] = True
    save_data(payments, "payments")

    debt_type = "гру" if is_game else "тренування"
    await query.edit_message_text(f"✅ Дякуємо! Оплату за {debt_type} зареєстровано.")

    # Check if everyone paid within this group (by training_id)
    group_id = rec.get("training_id", training_id)
    all_paid = all(p.get("paid") for p in payments.values() if p.get("training_id") == group_id)

    if is_game:
        if all_paid:
            games = load_data("games", {})
            game_id = group_id[len("game_"):]  # strip "game_"
            if game_id in games:
                games[game_id]["payment_status"] = "collected"
                save_data(games, "games")
                for admin in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=int(admin),
                            text=f"✅ Всі гравці гри {games[game_id].get('date','')} проти {games[game_id].get('opponent','')} оплатили. Статус оновлено на 'collected'."
                        )
                    except Exception as e:
                        print(f"❌ Не вдалося надіслати повідомлення адміну {admin}: {e}")
    else:
        if all_paid:
            one_time_trainings = load_data("one_time_trainings", {})
            constant_trainings = load_data("constant_trainings", {})
            for bucket in (one_time_trainings, constant_trainings):
                for tid, tr in bucket.items():
                    tr_id = (
                        f"{tr['date']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                        if "date" in tr
                        else f"const_{tr['weekday']}_{tr['start_hour']:02d}:{tr['start_min']:02d}"
                    )
                    if tr_id == group_id:
                        tr["status"] = "collected"
                        save_data(bucket, "one_time_trainings" if "date" in tr else "constant_trainings")
                        for admin in ADMIN_IDS:
                            try:
                                await context.bot.send_message(
                                    chat_id=int(admin),
                                    text=f"✅ Всі учасники тренування {group_id} оплатили. Статус оновлено на 'collected'."
                                )
                            except Exception as e:
                                print(f"❌ Не вдалося надіслати повідомлення адміну {admin}: {e}")
                        return







async def cancel_charge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Нарахування скасовано.")
    return ConversationHandler.END


async def pay_debt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    log_command_usage(user_id, "/pay_debt")
    payments = load_data("payments", {})

    # both trainings and games
    user_debts = [p for p in payments.values() if p["user_id"] == user_id and not p.get("paid", False)]

    if not user_debts:
        await update.message.reply_text("🎉 У тебе немає неоплачених тренувань чи ігор!")
        return

    context.user_data["pay_debt_options"] = user_debts

    keyboard = [
        [InlineKeyboardButton(
            f"{'[Гра]' if p['training_id'].startswith('game_') else '[Тренування]'} "
            f"{p['training_datetime']} - {p['amount']} грн",
            callback_data=f"paydebt_select_{i}"
        )] for i, p in enumerate(user_debts)
    ]

    await update.message.reply_text(
        f"Оберіть для перегляду карти та підтвердження оплати:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )



async def handle_pay_debt_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("paydebt_select_", ""))
    options = context.user_data.get("pay_debt_options", [])

    if not options or idx >= len(options):
        await query.edit_message_text("⚠️ Помилка: запис не знайдено.")
        return

    selected = options[idx]
    context.user_data["selected_debt"] = selected

    debt_type = "гру" if selected["training_id"].startswith("game_") else "тренування"

    keyboard = [
        [InlineKeyboardButton("✅ Оплатив(ла)", callback_data="paydebt_confirm_yes")]
    ]

    await query.edit_message_text(
        f"Карта: `{selected['card']}`\n\n"
        f"Ти точно оплатив(-ла) {selected['amount']} грн за {debt_type} {selected['training_datetime']}?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
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
    user_id = str(update.message.from_user.id)
    log_command_usage(user_id, "/view_payments")
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ У вас немає доступу до перегляду платежів.")
        return

    payments = load_data("payments", {})
    if not payments:
        await update.message.reply_text("Немає записаних платежів.")
        return

    # build labels only for groups with at least one unpaid
    by_tid = {}
    for p in payments.values():
        tid = p["training_id"]
        if tid not in by_tid:
            by_tid[tid] = {"any_unpaid": False, "label": f"{'[Гра]' if tid.startswith('game_') else '[Тренування]'} {p['training_datetime']}"}
        if not p.get("paid"):
            by_tid[tid]["any_unpaid"] = True

    # filter out fully paid (collected)
    filtered = [(tid, info["label"]) for tid, info in by_tid.items() if info["any_unpaid"]]

    if not filtered:
        await update.message.reply_text("🎉 Усі платежі зібрані — немає боржників.")
        return

    context.user_data["view_payment_options"] = [tid for tid, _ in filtered]
    keyboard = [[InlineKeyboardButton(label, callback_data=f"view_payment_{i}")]
                for i, (_, label) in enumerate(filtered)]

    await update.message.reply_text(
        "Оберіть оплату для перегляду:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )





async def handle_view_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    idx = int(query.data.replace("view_payment_", ""))
    keys = context.user_data.get("view_payment_options", [])
    if idx >= len(keys):
        await query.edit_message_text("⚠️ Помилка: не знайдено.")
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

    debt_type = "гра" if training_id.startswith("game_") else "тренування"

    message = f"💰 Платежі за {debt_type} {payments[next(k for k in payments if payments[k]['training_id'] == training_id)]['training_datetime']}:\n\n"
    message += f"✅ Оплатили:\n{chr(10).join(paid) if paid else 'Ніхто'}\n\n"
    message += f"❌ Не оплатили:\n{chr(10).join(unpaid) if unpaid else 'Немає боржників'}"

    await query.edit_message_text(message)


def create_charge_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("charge_all", charge_all)],
        states={
            CHARGE_SELECT_TRAINING: [CallbackQueryHandler(handle_charge_selection, pattern=r"^charge_select_\d+$")],
            CHARGE_ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_charge_amount_input)],
            CHARGE_ENTER_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_charge_card_input)],
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
