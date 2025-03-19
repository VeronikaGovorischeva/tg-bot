# Bot configuration
BOT_USERNAME = "ChillNtTestBot"

# File paths
USER_DATA_FILE = "user_data.json"

# Team configurations
TEAMS = {
    "male": {
        "name": "Чоловіча",
        "callback_data": "team_male",
        "training_days": [0, 4, 5],  # Monday, Friday, Saturday
        "next_game": "19.03(середа) о 19:00"
    },
    "female": {
        "name": "Жіноча",
        "callback_data": "team_female",
        "training_days": [2, 4, 6],  # Wednesday, Friday, Sunday
        "next_game": "20.03(четвер) о 18:00"
    }
}

# Conversation states
CONVERSATION_STATES = {
    "NAME": 0,
    "TEAM": 1
}

# Messages
MESSAGES = {
    "welcome": "Привіт! Введи своє прізвище та ім'я АНГЛІЙСЬКОЮ",
    "team_selection": "Дякую! Тепер обери свою команду:",
    "registration_complete": "Чудово! Тебе зареєстровано в {team} команді.\n"
                            "Використовуй команди /next_training для інформації про тренування "
                            "та /next_game для інформації про ігри.",
    "already_registered": "Вітаю, {name}! Ти вже зареєстрований.\n"
                         "Твоя команда: {team}\n"
                         "Використовуй команди /next_training для інформації про тренування "
                         "та /next_game для інформації про ігри.",
    "registration_canceled": "Реєстрація скасована. Використовуй /start щоб спробувати знову.",
    "please_register": "Будь ласка, зареєструйся спочатку використовуючи команду /start"
}