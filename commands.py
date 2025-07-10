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


async def mvp_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="mvp_stats_Male"),
            InlineKeyboardButton("Жіноча команда", callback_data="mvp_stats_Female")
        ],
        [InlineKeyboardButton("Всі команди", callback_data="mvp_stats_Both")]
    ])

    await update.message.reply_text(
        "🏆 MVP Статистика\n\nОберіть команду для перегляду:",
        reply_markup=keyboard
    )


async def handle_mvp_stats_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    team_filter = query.data.replace("mvp_stats_", "")
    users = load_data("users", {})

    mvp_data = []
    for user_data in users.values():
        mvp_count = int(user_data.get("mvp", 0))
        if mvp_count > 0:
            name = user_data.get("name", "Невідомий")
            team = user_data.get("team")

            if team_filter == "Both" or team == team_filter:
                mvp_data.append((name, team, mvp_count))

    mvp_data.sort(key=lambda x: x[2], reverse=True)

    if team_filter == "Both":
        message = "🏆 MVP Статистика (всі команди):\n\n"

        male_players = [(name, count) for name, team, count in mvp_data if team == "Male"]
        female_players = [(name, count) for name, team, count in mvp_data if team == "Female"]

        if male_players:
            message += "Чоловіча команда:\n"
            for name, count in male_players:
                message += f"• {name}: {count} MVP\n"
            message += "\n"

        if female_players:
            message += "Жіноча команда:\n"
            for name, count in female_players:
                message += f"• {name}: {count} MVP\n"

    else:
        team_name = "чоловічої" if team_filter == "Male" else "жіночої"
        team_emoji = "👨" if team_filter == "Male" else "👩"
        message = f"🏆 MVP Статистика {team_emoji} {team_name} команди:\n\n"

        if mvp_data:
            for name, team, count in mvp_data:
                message += f"• {name}: {count} MVP\n"
        else:
            message += f"Поки що немає MVP нагород у {team_name} команди."

    if not mvp_data:
        message = "🏆 MVP Статистика:\n\nПоки що немає MVP нагород."

    await query.edit_message_text(message)


async def attendance_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="attendance_stats_Male"),
            InlineKeyboardButton("Жіноча команда", callback_data="attendance_stats_Female")
        ],
        [InlineKeyboardButton("Всі команди", callback_data="attendance_stats_Both")]
    ])

    await update.message.reply_text(
        "📊 Статистика відвідуваності\n\nОберіть команду для перегляду:",
        reply_markup=keyboard
    )


async def handle_attendance_stats_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    team_filter = query.data.replace("attendance_stats_", "")
    users = load_data("users", {})

    attendance_data = []
    for user_data in users.values():
        team = user_data.get("team")

        if team_filter == "Both" or team == team_filter:
            name = user_data.get("name", "Невідомий")
            training_att = user_data.get("training_attendance", {"attended": 0, "total": 0, "percentage": 0.0})
            game_att = user_data.get("game_attendance", {"attended": 0, "total": 0, "percentage": 0.0})

            attendance_data.append((name, team, training_att, game_att))

    attendance_data.sort(key=lambda x: x[0])

    if team_filter == "Both":
        message = "📊 Статистика відвідуваності (всі команди):\n\n"
    else:
        team_name = "чоловічої" if team_filter == "Male" else "жіночої"
        message = f"📊 Статистика відвідуваності {team_name} команди:\n\n"

    if attendance_data:
        for name, team, training_att, game_att in attendance_data:
            team_emoji = "👨" if team == "Male" else "👩"
            message += f"{team_emoji} {name}:\n"
            message += f"  🏐 Тренування: {training_att['attended']}/{training_att['total']} ({training_att['percentage']}%)\n"
            message += f"  🏆 Ігри: {game_att['attended']}/{game_att['total']} ({game_att['percentage']}%)\n\n"
    else:
        message += "Немає даних про відвідуваність."

    await query.edit_message_text(message)


async def training_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="training_stats_Male"),
            InlineKeyboardButton("Жіноча команда", callback_data="training_stats_Female")
        ],
        [InlineKeyboardButton("Всі команди", callback_data="training_stats_Both")]
    ])

    await update.message.reply_text(
        "🏐 Статистика відвідуваності тренувань\n\nОберіть команду для перегляду:",
        reply_markup=keyboard
    )


async def handle_training_stats_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    team_filter = query.data.replace("training_stats_", "")
    users = load_data("users", {})

    training_data = []
    for user_data in users.values():
        team = user_data.get("team")

        if team_filter == "Both" or team == team_filter:
            name = user_data.get("name", "Невідомий")
            training_att = user_data.get("training_attendance", {"attended": 0, "total": 0, "percentage": 0.0})

            if training_att["total"] > 0:
                training_data.append((name, team, training_att))

    training_data.sort(key=lambda x: x[2]["percentage"], reverse=True)

    if team_filter == "Both":
        message = "🏐 Статистика відвідуваності тренувань (всі команди):\n\n"
    else:
        team_name = "чоловічої" if team_filter == "Male" else "жіночої"
        message = f"🏐 Статистика відвідуваності тренувань {team_name} команди:\n\n"

    if training_data:
        for i, (name, team, training_att) in enumerate(training_data, 1):
            message += f"{i}. {name}: {training_att['attended']}/{training_att['total']} ({training_att['percentage']}%)\n"
    else:
        message += "Немає даних про відвідуваність тренувань."

    await query.edit_message_text(message)


async def game_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="game_stats_Male"),
            InlineKeyboardButton("Жіноча команда", callback_data="game_stats_Female")
        ],
        [InlineKeyboardButton("Всі команди", callback_data="game_stats_Both")]
    ])

    await update.message.reply_text(
        "🏆 Статистика відвідуваності ігор\n\nОберіть команду для перегляду:",
        reply_markup=keyboard
    )


async def handle_game_stats_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    team_filter = query.data.replace("game_stats_", "")
    users = load_data("users", {})

    game_data = []
    for user_data in users.values():
        team = user_data.get("team")

        if team_filter == "Both" or team == team_filter:
            name = user_data.get("name", "Невідомий")
            game_att = user_data.get("game_attendance", {"attended": 0, "total": 0, "percentage": 0.0})

            if game_att["total"] > 0:
                game_data.append((name, team, game_att))

    game_data.sort(key=lambda x: x[2]["percentage"], reverse=True)

    if team_filter == "Both":
        message = "🏆 Статистика відвідуваності ігор (всі команди):\n\n"
    else:
        team_name = "чоловічої" if team_filter == "Male" else "жіночої"
        message = f"🏆 Статистика відвідуваності ігор {team_name} команди:\n\n"

    if game_data:
        for i, (name, team, game_att) in enumerate(game_data, 1):
            message += f"{i}. {name}: {game_att['attended']}/{game_att['total']} ({game_att['percentage']}%)\n"
    else:
        message += "Немає даних про відвідуваність ігор."

    await query.edit_message_text(message)


async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    users = load_data("users", {})

    if user_id not in users:
        await update.message.reply_text("Будь ласка, завершіть реєстрацію спочатку.")
        return

    user_data = users[user_id]
    name = user_data.get("name", "Невідомий")
    team = user_data.get("team", "Невідомо")
    mvp = user_data.get("mvp", 0)

    default_attendance = {"attended": 0, "total": 0, "percentage": 0.0}
    training_att = user_data.get("training_attendance", default_attendance)
    game_att = user_data.get("game_attendance", default_attendance)

    team_name = "чоловічої" if team == "Male" else "жіночої" if team == "Female" else "змішаної"

    message = f"📊 Моя статистика\n\n"
    message += f"{name} ({team_name} команда)\n\n"

    message += f"🏐 Тренування:\n"
    message += f"   Відвідав: {training_att['attended']}/{training_att['total']}\n"
    message += f"   Відсоток: {training_att['percentage']}%\n\n"

    message += f"🏆 Ігри:\n"
    message += f"   Відвідав: {game_att['attended']}/{game_att['total']}\n"
    message += f"   Відсоток: {game_att['percentage']}%\n\n"

    message += f"🎖️ MVP нагороди: {mvp}\n\n"

    if training_att["total"] > 0 and training_att["percentage"] >= 90:
        message += "🔥 Відмінна відвідуваність тренувань!"
    elif training_att["total"] > 0 and training_att["percentage"] >= 70:
        message += "💪 Гарна відвідуваність тренувань!"
    elif training_att["total"] > 0:
        message += "📈 Треба частіше ходити на тренування!"

    await update.message.reply_text(message)


def setup_admin_handlers(app):
    # /mvp_stats
    app.add_handler(CommandHandler("mvp_stats", mvp_stats))
    # /my_stats
    app.add_handler(CommandHandler("my_stats", my_stats))
    # /training_stats
    app.add_handler(CommandHandler("training_stats", training_stats))
    # /game_stats
    app.add_handler(CommandHandler("game_stats", game_stats))
    # Buttons
    app.add_handler(CallbackQueryHandler(handle_training_stats_selection, pattern=r"^training_stats_"))
    app.add_handler(CallbackQueryHandler(handle_game_stats_selection, pattern=r"^game_stats_"))
    app.add_handler(CallbackQueryHandler(handle_mvp_stats_selection, pattern=r"^mvp_stats_"))
    # Admin: /send_message
    app.add_handler(CommandHandler("send_message", send_message_command))
    app.add_handler(CallbackQueryHandler(handle_send_message_team_selection, pattern=r"^send_team_"))
    # Admin: /notify_debtors
    app.add_handler(CommandHandler("notify_debtors", notify_debtors))
    # Handle message input (must be last text handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_send_message_input))
