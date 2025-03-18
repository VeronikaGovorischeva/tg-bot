from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

telegram_api_token = "7640419427:AAHUciixP3FyY6PLahICwer6ybFLwQRqucg"
bot_username = "ChillNtTestBot"

# Create a simple start command with buttons
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Button 1", callback_data='button1')],
        [InlineKeyboardButton("Button 2", callback_data='button2')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Hello! Choose a button:", reply_markup=reply_markup)

# Handle button presses
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # Acknowledge the button press
    if query.data == 'button1':
        await query.edit_message_text("You pressed Button 1!")
    elif query.data == 'button2':
        await query.edit_message_text("You pressed Button 2!")

# Main function to set up the bot
if __name__ == "__main__":
    app = Application.builder().token(telegram_api_token).build()
    app.add_handler(CommandHandler("start", start))  # /start command
    app.add_handler(CallbackQueryHandler(button))    # Handler for button presses
    app.run_polling(poll_interval=0.1)
