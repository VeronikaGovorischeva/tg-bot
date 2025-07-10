from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from data import load_data
from validation import ADMIN_IDS

SEND_MESSAGE_STATE = {}


async def send_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="send_team_Male"),
            InlineKeyboardButton("Жіноча команда", callback_data="send_team_Female"),
        ],
        [InlineKeyboardButton("Обидві команди", callback_data="send_team_Both")]
    ])
    await update.message.reply_text("Оберіть команду, якій хочете надіслати повідомлення:", reply_markup=keyboard)


async def handle_send_message_team_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    team = query.data.replace("send_team_", "")
    SEND_MESSAGE_STATE[query.from_user.id] = team

    await query.edit_message_text(
        f"Ви обрали: {team} команда.\n\nТепер надішліть текст повідомлення у наступному повідомленні.")


async def handle_send_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if update.message.text == "🤡" or update.message.text == "🖕":
        await update.message.reply_text("🤡")
        return
    if user_id not in SEND_MESSAGE_STATE:
        return

    team = SEND_MESSAGE_STATE.pop(user_id)
    message_text = update.message.text
    users = load_data("users")

    sender_username = update.message.from_user.username
    if sender_username:
        footer = f"\n\n👤 Повідомлення надіслав(ла): @{sender_username}"
    else:
        footer = f"\n\n👤 Повідомлення надіслав(ла): {update.message.from_user.first_name}"

    full_message = f"{message_text}{footer}"

    count = 0
    for uid, info in users.items():
        if team in [info.get("team"), "Both"]:
            try:
                await context.bot.send_message(chat_id=int(uid), text=full_message)
                count += 1
            except Exception as e:
                print(f"❌ Не вдалося надіслати повідомлення {uid}: {e}")

    await update.message.reply_text(f"✅ Повідомлення надіслано {count} користувачам.")


async def notify_debtors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас немає прав для надсилання повідомлень боржникам.")
        return

    payments = load_data("payments", {})

    debts_by_user = {}
    for p in payments.values():
        if not p.get("paid", False):
            uid = p["user_id"]
            debts_by_user.setdefault(uid, []).append(p)

    notified_count = 0

    for uid, debts in debts_by_user.items():
        lines = []
        for d in debts:
            lines.append(f"• {d['training_datetime']}: {d['amount']} грн")

        message = (
                "📢 У тебе є неоплачені тренування:\n\n" +
                "\n".join(lines) +
                "\n\nБудь ласка, використай команду /pay_debt щоб підтвердити оплату або оплатити через Telegram."
        )

        try:
            await context.bot.send_message(chat_id=int(uid), text=message)
            notified_count += 1
        except Exception as e:
            print(f"❌ Не вдалося надіслати повідомлення до {uid}: {e}")

    await update.message.reply_text(f"✅ Сповіщення надіслано {notified_count} боржникам.")


def setup_admin_handlers(app):
    # Admin: /send_message
    app.add_handler(CommandHandler("send_message", send_message_command))
    app.add_handler(CallbackQueryHandler(handle_send_message_team_selection, pattern=r"^send_team_"))
    # Admin: /notify_debtors
    app.add_handler(CommandHandler("notify_debtors", notify_debtors))
    # Handle message input (must be last text handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_send_message_input))
