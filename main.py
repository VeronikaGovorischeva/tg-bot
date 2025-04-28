from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from modules.commands import CommandsHandler
from modules.games import GamesManager
from config import Config

telegram_api_token = "8158067169:AAGQaLETvllC5HR4byyadJqQeEwsOQN0IyE"
bot_username = "megachillguybot"


async def error_handler(update, context):
    """Handle errors in the dispatcher."""
    print(f"Error: {context.error} in update {update}")


if __name__ == "__main__":
    app = Application.builder().token(telegram_api_token).build()
    commands = CommandsHandler(Config)
    games = GamesManager(Config.GAMES_FILE, Config.ADMIN_IDS)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', commands.start)],
        states={
            commands.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, commands.name)],
            commands.TEAM: [CallbackQueryHandler(commands.team, pattern=r"^team_")]
        },
        fallbacks=[CommandHandler('cancel', commands.cancel)],
    )
    game_add_handler = ConversationHandler(
        entry_points=[CommandHandler('add_game', commands.add_game_command)],
        states={
            Config.GAME_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, commands.game_date)],
            Config.GAME_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, commands.game_time)],
            Config.GAME_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, commands.game_location)],
            Config.GAME_OPPONENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, commands.game_opponent)],
            Config.GAME_TEAM: [CallbackQueryHandler(commands.game_team, pattern=r"^add_")]
        },
        fallbacks=[CommandHandler('cancel', commands.cancel)]
    )
    edit_game_handler = ConversationHandler(
        entry_points=[CommandHandler('edit_game', commands.edit_game_command)],
        states={
            Config.EDIT_GAME_SELECT: [CallbackQueryHandler(commands.edit_game_command, pattern=r"^select_")],
            Config.EDIT_GAME_FIELD: [CallbackQueryHandler(commands.edit_game_field, pattern=r"^field_")],
            Config.EDIT_GAME_NEW_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, commands.edit_game_value),
                CallbackQueryHandler(commands.edit_game_value, pattern=r"^edit_")
            ]
        },
        fallbacks=[CommandHandler('cancel', commands.cancel)]
    )

    app.add_handler(CommandHandler("next_training", commands.next_training))
    app.add_handler(CommandHandler("next_game", commands.next_game))
    app.add_handler(CommandHandler("check_debt", commands.check_debt))

    # Game management commands
    app.add_handler(CommandHandler("list_games", commands.list_games))
    app.add_handler(CommandHandler("delete_game", commands.delete_game_command))

    # Callback query handlers
    app.add_handler(CallbackQueryHandler(commands.list_games_callback, pattern=r"^list_"))
    app.add_handler(CallbackQueryHandler(commands.delete_game_callback, pattern=r"^delete_"))

    # Register error handler
    app.add_error_handler(error_handler)

    app.run_polling(poll_interval=0.1)
    print("Bot is running")
