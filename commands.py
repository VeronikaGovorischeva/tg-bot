import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters, \
    ConversationHandler
from data import load_data
from validation import ADMIN_IDS

SEND_MESSAGE_STATE = {}

GAME_RESULTS_TEAM, GAME_RESULTS_SEASON, GAME_RESULTS_TYPE = range(500, 503)


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
                "\n\nБудь ласка, використай команду /pay_debt щоб підтвердити оплату або оплатити."
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
        message = f"🏆 MVP Статистика {team_name} команди:\n\n"

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
            training_att = user_data.get("training_attendance", {"attended": 0, "total": 0})
            game_att = user_data.get("game_attendance", {"attended": 0, "total": 0})

            attendance_data.append((name, team, training_att, game_att))

    attendance_data.sort(key=lambda x: x[0])

    if team_filter == "Both":
        message = "📊 Статистика відвідуваності (всі команди):\n\n"
    else:
        team_name = "чоловічої" if team_filter == "Male" else "жіночої"
        message = f"📊 Статистика відвідуваності {team_name} команди:\n\n"

    if attendance_data:
        for name, team, training_att, game_att in attendance_data:
            message += f"{name}:\n"
            message += f"  🏐 Тренування: {training_att['attended']}/{training_att['total']} ({round(training_att['attended'] / training_att['total'] * 100) if training_att['total'] > 0 else 0}%)\n"
            message += f"  🏆 Ігри: {game_att['attended']}/{game_att['total']} ({round(game_att['attended'] / game_att['total'] * 100) if game_att['total'] > 0 else 0}%)\n\n"
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
            training_att = user_data.get("training_attendance", {"attended": 0, "total": 0})

            if training_att["total"] > 0:
                training_data.append((name, team, training_att))

    training_data.sort(key=lambda x: (x[2]["attended"] / x[2]["total"]) if x[2]["total"] > 0 else 0, reverse=True)

    if team_filter == "Both":
        message = "🏐 Статистика відвідуваності тренувань (всі команди):\n\n"
    else:
        team_name = "чоловічої" if team_filter == "Male" else "жіночої"
        message = f"🏐 Статистика відвідуваності тренувань {team_name} команди:\n\n"

    if training_data:
        for i, (name, team, training_att) in enumerate(training_data, 1):
            message += f"{i}. {name}: {training_att['attended']}/{training_att['total']} ({round(training_att['attended'] / training_att['total'] * 100) if training_att['total'] > 0 else 0}%)\n"
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
            game_att = user_data.get("game_attendance", {"attended": 0, "total": 0})

            if game_att["total"] > 0:
                game_data.append((name, team, game_att))

    game_data.sort(key=lambda x: (x[2]["attended"] / x[2]["total"]) if x[2]["total"] > 0 else 0, reverse=True)

    if team_filter == "Both":
        message = "🏆 Статистика відвідуваності ігор (всі команди):\n\n"
    else:
        team_name = "чоловічої" if team_filter == "Male" else "жіночої"
        message = f"🏆 Статистика відвідуваності ігор {team_name} команди:\n\n"

    if game_data:
        for i, (name, team, game_att) in enumerate(game_data, 1):
            message += f"{i}. {name}: {game_att['attended']}/{game_att['total']} ({round(game_att['attended'] / game_att['total'] * 100) if game_att['total'] > 0 else 0}%)\n"
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

    default_attendance = {"attended": 0, "total": 0}
    training_att = user_data.get("training_attendance", default_attendance)
    game_att = user_data.get("game_attendance", default_attendance)

    team_name = "чоловічої" if team == "Male" else "жіночої" if team == "Female" else "змішаної"

    message = f"📊 Моя статистика\n\n"
    message += f"{name} ({team_name} команда)\n\n"

    training_percentage = round(training_att['attended'] / training_att['total'] * 100) if training_att[
                                                                                               'total'] > 0 else 0
    game_percentage = round(game_att['attended'] / game_att['total'] * 100) if game_att['total'] > 0 else 0

    message += f"🏐 Тренування:\n"
    message += f"   Відвідав: {training_att['attended']}/{training_att['total']}\n"
    message += f"   Відсоток: {training_percentage}%\n\n"

    message += f"🏆 Ігри:\n"
    message += f"   Відвідав: {game_att['attended']}/{game_att['total']}\n"
    message += f"   Відсоток: {game_percentage}%\n\n"

    message += f"🎖️ MVP нагороди: {mvp}\n"

    if mvp > 0:
        games = load_data("games", {})
        mvp_games = []

        for game in games.values():
            if game.get("mvp") == name:
                mvp_games.append(game)

        if mvp_games:
            for game in mvp_games:
                type_names = {
                    "friendly": "Товариська",
                    "stolichka": "Столичка",
                    "universiad": "Універсіада"
                }
                type_name = type_names.get(game.get('type'), game.get('type'))
                message += f"   {type_name} - {game['date']} проти *{game['opponent']}*\n"

    message += "\n"

    # МОЖНА ДОДАТИ, АЛЕ ВПАДЛУ
    # if training_att["total"] > 0 and training_percentage >= 90:
    #     message += "🔥 Відмінна відвідуваність тренувань!"
    # elif training_att["total"] > 0 and training_percentage >= 70:
    #     message += "💪 Гарна відвідуваність тренувань!"
    # elif training_att["total"] > 0:
    #     message += "📈 Треба частіше ходити на тренування!"

    await update.message.reply_text(message, parse_mode='markdown')


def get_available_seasons_from_ids(games_data, team_filter):
    seasons = set()

    for game_id, game in games_data.items():
        if game.get("team") not in [team_filter, "Both"]:
            continue
        try:
            parts = game_id.split("_")
            if len(parts) >= 4:
                for i in range(len(parts) - 1):
                    if (parts[i].isdigit() and parts[i + 1].isdigit() and
                            len(parts[i]) == 4 and len(parts[i + 1]) == 4):
                        season = f"{parts[i]}_{parts[i + 1]}"
                        seasons.add(season)
                        break
        except:
            continue

    return sorted(seasons, reverse=True)


async def show_tournament_selection(query, context, team_name):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Товариські матчі", callback_data="game_results_type_friendly"),
            InlineKeyboardButton("Столична ліга", callback_data="game_results_type_stolichka")
        ],
        [
            InlineKeyboardButton("Універсіада", callback_data="game_results_type_universiad"),
            InlineKeyboardButton("Всі матчі", callback_data="game_results_type_all")
        ]
    ])

    season_text = ""
    selected_season = context.user_data.get("selected_season")
    if selected_season:
        season_start, season_end = selected_season.split("_")
        season_text = f" сезону {season_start}/{season_end}"

    await query.edit_message_text(
        f"🏆 Результати ігор {team_name} команди{season_text}\n\nОберіть тип турніру:",
        reply_markup=keyboard
    )

    return GAME_RESULTS_TYPE


def filter_games_by_season_id(games, season_filter):
    if not season_filter:
        return games

    filtered_games = []

    for game_id, game, game_datetime in games:
        if season_filter in game_id:
            filtered_games.append((game_id, game, game_datetime))

    return filtered_games


async def game_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="game_results_team_Male"),
            InlineKeyboardButton("Жіноча команда", callback_data="game_results_team_Female")
        ]
    ])

    await update.message.reply_text(
        "🏆 Результати ігор\n\nОберіть команду:",
        reply_markup=keyboard
    )

    return GAME_RESULTS_TEAM


async def handle_game_results_team_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    team_filter = query.data.replace("game_results_team_", "")
    context.user_data["selected_team"] = team_filter

    games = load_data("games", {})
    available_seasons = get_available_seasons_from_ids(games, team_filter)

    team_name = "чоловічої" if team_filter == "Male" else "жіночої"

    if len(available_seasons) <= 1:
        if available_seasons:
            context.user_data["selected_season"] = available_seasons[0]
        else:
            context.user_data["selected_season"] = None
        return await show_tournament_selection(query, context, team_name)

    keyboard = []
    for season in available_seasons:
        season_start, season_end = season.split("_")
        season_label = f"{season_start}/{season_end}"
        keyboard.append([InlineKeyboardButton(season_label, callback_data=f"game_results_season_{season}")])

    keyboard.append([InlineKeyboardButton("🗓️ Всі сезони", callback_data="game_results_season_all")])

    await query.edit_message_text(
        f"🏆 Результати ігор {team_name} команди\n\nОберіть сезон:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return GAME_RESULTS_SEASON


async def handle_game_results_season_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    season_filter = query.data.replace("game_results_season_", "")
    context.user_data["selected_season"] = season_filter if season_filter != "all" else None

    team_filter = context.user_data.get("selected_team")
    team_name = "чоловічої" if team_filter == "Male" else "жіночої"

    return await show_tournament_selection(query, context, team_name)


async def handle_game_results_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    team_filter = context.user_data.get("selected_team")
    season_filter = context.user_data.get("selected_season")
    type_filter = query.data.replace("game_results_type_", "")

    games = load_data("games", {})
    now = datetime.datetime.now()

    completed_games = []
    for game_id, game in games.items():
        if game.get("team") not in [team_filter, "Both"]:
            continue

        if type_filter != "all" and game.get("type") != type_filter:
            continue

        try:
            game_datetime = datetime.datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
            result = game.get("result", {})
            if game_datetime < now and result.get("status") is not None:
                completed_games.append((game_id, game, game_datetime))
        except ValueError:
            continue

    if season_filter:
        completed_games = filter_games_by_season_id(completed_games, season_filter)

    completed_games.sort(key=lambda x: x[2], reverse=True)

    team_name = "чоловічої" if team_filter == "Male" else "жіночої"

    season_text = ""
    if season_filter:
        season_start, season_end = season_filter.split("_")
        season_text = f" сезону {season_start}/{season_end}"

    type_names = {
        "friendly": "товариських матчів",
        "stolichka": "Столичної ліги",
        "universiad": "Універсіади",
        "all": "всіх матчів"
    }
    type_name = type_names.get(type_filter, "матчів")

    if not completed_games:
        await query.edit_message_text(
            f"🏆 Результати {type_name} {team_name} команди{season_text}:\n\n"
            f"Поки що немає завершених ігор з результатами."
        )
        return ConversationHandler.END

    message = f"🏆 Результати {type_name} {team_name} команди{season_text}:\n\n"

    game_type_names = {
        "friendly": "Товариська",
        "stolichka": "Столичка",
        "universiad": "Універсіада"
    }

    for game_id, game, game_datetime in completed_games:
        result = game["result"]
        type_name_short = game_type_names.get(game["type"], game["type"])

        if result["status"] == "win":
            result_emoji = "🟢"
        elif result["status"] == "loss":
            result_emoji = "🔴"
        else:
            result_emoji = "🟡"

        message += f"{result_emoji} {type_name_short} - {game['date']}\n"
        message += f"   Проти: **{game['opponent']}**\n"
        message += f"   Рахунок: {result['our_score']}:{result['opponent_score']}\n"

        if result.get("sets"):
            sets_text = ", ".join([f"{s['our']}:{s['opponent']}" for s in result["sets"]])
            message += f"   Сети: {sets_text}\n"

        if game.get("mvp"):
            message += f"   🏆 MVP: {game['mvp']}\n"

        message += "\n"

    wins = sum(1 for _, game, _ in completed_games if game["result"]["status"] == "win")
    losses = sum(1 for _, game, _ in completed_games if game["result"]["status"] == "loss")
    draws = sum(1 for _, game, _ in completed_games if game["result"]["status"] == "draw")

    message += f"📊 Статистика: {wins} перемог, {losses} поразок"
    if draws > 0:
        message += f", {draws} нічиїх"

    if len(message) > 4000:
        parts = [message[i:i + 4000] for i in range(0, len(message), 4000)]
        for part in parts:
            await query.message.reply_text(part, parse_mode='Markdown')
        await query.delete_message()
    else:
        await query.edit_message_text(message, parse_mode='Markdown')

    return ConversationHandler.END


def create_game_results_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("game_results", game_results)],
        states={
            GAME_RESULTS_TEAM: [
                CallbackQueryHandler(handle_game_results_team_selection, pattern=r"^game_results_team_")],
            GAME_RESULTS_SEASON: [
                CallbackQueryHandler(handle_game_results_season_selection, pattern=r"^game_results_season_")],
            GAME_RESULTS_TYPE: [
                CallbackQueryHandler(handle_game_results_type_selection, pattern=r"^game_results_type_")]
        },
        fallbacks=[]
    )


def setup_admin_handlers(app):
    # /mvp_stats
    app.add_handler(CommandHandler("mvp_stats", mvp_stats))
    # /my_stats
    app.add_handler(CommandHandler("my_stats", my_stats))
    # /training_stats
    app.add_handler(CommandHandler("training_stats", training_stats))
    # /game_stats
    app.add_handler(CommandHandler("game_stats", game_stats))
    # /game_results
    app.add_handler(create_game_results_handler())

    # Others
    app.add_handler(CallbackQueryHandler(handle_training_stats_selection, pattern=r"^training_stats_"))
    app.add_handler(CallbackQueryHandler(handle_game_stats_selection, pattern=r"^game_stats_"))
    app.add_handler(CallbackQueryHandler(handle_mvp_stats_selection, pattern=r"^mvp_stats_"))
    # Admin: /send_message
    app.add_handler(CallbackQueryHandler(handle_send_message_team_selection, pattern=r"^send_team_"))
    # Admin: /notify_debtors
    app.add_handler(CommandHandler("notify_debtors", notify_debtors))
    # Handle message input (must be last text handler)
    app.add_handler(CommandHandler("send_message", send_message_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_send_message_input))
