from enum import Enum, auto
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, \
    filters

from data import load_data, save_data

REGISTRATION_FILE = "data/user_data.json"


class RegistrationState(Enum):
    NAME = auto()
    TEAM = auto()


class Team(Enum):
    MALE = "Male"
    FEMALE = "Female"


class UserMessages:
    WELCOME = "Привіт! Введи своє прізвище та ім'я Українською"
    TEAM_SELECTION = "Дякую! Тепер обери свою команду:"
    REGISTRATION_COMPLETE = ("Реєстрацію завершено.\n"
                             "Використовуй команди /next_training для інформації про тренування "
                             "та /next_game для інформації про ігри.")
    ALREADY_REGISTERED = ("Використовуй команди /next_training /next_game та /list_games "
                          "щоб дізнатися інфу про наступне тренування та наступну гру.")
    REGISTRATION_CANCELLED = "Реєстрація скасована. Використовуй /start щоб спробувати знову."


def create_team_keyboard() -> InlineKeyboardMarkup:
    """Creates keyboard markup for team selection."""
    keyboard = [
        [
            InlineKeyboardButton("Чоловіча", callback_data="team_male"),
            InlineKeyboardButton("Жіноча", callback_data="team_female"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def is_user_registered(user_data: Dict[str, Any], user_id: str) -> bool:
    """Checks if user is already registered."""
    return (str(user_id) in user_data and
            "name" in user_data[str(user_id)] and
            "team" in user_data[str(user_id)])


def initialize_user_data(user_id: str, username: Optional[str]) -> Dict[str, Any]:
    """Initialize basic user data structure."""
    return {str(user_id): {"telegram_username": username, "debt": [0]}}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the start command and begins registration process."""
    user = update.message.from_user
    user_id = str(user.id)
    user_data = load_data(REGISTRATION_FILE)

    if is_user_registered(user_data, user_id):
        await update.message.reply_text(UserMessages.ALREADY_REGISTERED)
        return ConversationHandler.END

    user_data.update(initialize_user_data(user_id, user.username))
    save_data(user_data, REGISTRATION_FILE)

    await update.message.reply_text(UserMessages.WELCOME)
    return RegistrationState.NAME.value


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles user's name input and proceeds to team selection."""
    user_id = str(update.message.from_user.id)
    user_input_name = update.message.text

    user_data = load_data(REGISTRATION_FILE)
    user_data[user_id]["name"] = user_input_name
    save_data(user_data, REGISTRATION_FILE)

    await update.message.reply_text(
        UserMessages.TEAM_SELECTION,
        reply_markup=create_team_keyboard()
    )
    return RegistrationState.TEAM.value


async def handle_team_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles team selection and completes registration."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    team_choice = Team.MALE if query.data == "team_male" else Team.FEMALE

    user_data = load_data(REGISTRATION_FILE)
    user_data[user_id]["team"] = team_choice.value
    save_data(user_data, REGISTRATION_FILE)

    await query.edit_message_text(UserMessages.REGISTRATION_COMPLETE)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles registration cancellation."""
    await update.message.reply_text(UserMessages.REGISTRATION_CANCELLED)
    return ConversationHandler.END


def create_registration_handler() -> ConversationHandler:
    """Creates and configures the registration conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            RegistrationState.NAME.value: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            RegistrationState.TEAM.value: [CallbackQueryHandler(handle_team_selection)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

# FUTURE OOP CODE
# from typing import Dict, Optional
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
# from dataclasses import dataclass
# from enum import Enum, auto
# from data import load_data, save_data
#
# class RegistrationState(Enum):
#     NAME = auto()
#     TEAM = auto()
#
# @dataclass
# class UserProfile:
#     telegram_id: str
#     telegram_username: Optional[str]
#     name: Optional[str] = None
#     team: Optional[str] = None
#     debt: list[int] = None
#
#     def is_registered(self) -> bool:
#         return all([self.name, self.team])
#
#     def to_dict(self) -> Dict:
#         return {
#             "telegram_username": self.telegram_username,
#             "name": self.name,
#             "team": self.team,
#             "debt": self.debt or [0]
#         }
#
#
# class RegistrationManager:
#     def __init__(self, registration_file: str):
#         self.registration_file = registration_file
#         self.messages = {
#             "welcome": "Привіт! Введи своє прізвище та ім'я АНГЛІЙСЬКОЮ",
#             "team_selection": "Дякую! Тепер обери свою команду:",
#             "registration_complete": ("Реєстрацію завершено.\n"
#                                       "Використовуй команди /next_training для інформації про тренування "
#                                       "та /next_game для інформації про ігри."),
#             "registration_cancelled": "Реєстрація скасована. Використовуй /start щоб спробувати знову.",
#         }
#         self.commands = {
#             "next_training": "інформації про тренування",
#             "next_game": "інформації про ігри",
#             "list_games": "список ігор"
#         }
#
#     def _create_team_keyboard(self) -> InlineKeyboardMarkup:
#         """Create keyboard markup for team selection."""
#         keyboard = [
#             [
#                 InlineKeyboardButton("Чоловіча", callback_data="team_male"),
#                 InlineKeyboardButton("Жіноча", callback_data="team_female"),
#             ]
#         ]
#         return InlineKeyboardMarkup(keyboard)
#     #Змінив би якось
#     def _get_commands_message(self) -> str:
#         """Generate message with available commands."""
#         commands = [f"/{cmd}" for cmd in self.commands.keys()]
#         return f"Використовуй команди {' '.join(commands)} щоб дізнатися інфу про наступне тренування та наступну гру."
#
#     def _load_user_profile(self, user_id: str) -> UserProfile|None:
#         """Load user profile from storage."""
#         user_data = load_data(self.registration_file)
#         if user_id in user_data:
#             data = user_data[user_id]
#             return UserProfile(
#                 telegram_id=user_id,
#                 telegram_username=data.get("telegram_username"),
#                 name=data.get("name"),
#                 team=data.get("team"),
#                 debt=data.get("debt", [0])
#             )
#         return None
#
#     def _save_user_profile(self, profile: UserProfile) -> None:
#         """Save user profile to storage."""
#         user_data = load_data(self.registration_file)
#         user_data[profile.telegram_id] = profile.to_dict()
#         save_data(user_data, self.registration_file)
#
#     async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#         """Handle the start command and begin registration process."""
#         user = update.message.from_user
#         profile = self._load_user_profile(str(user.id))
#
#         if profile and profile.is_registered():
#             await update.message.reply_text(self._get_commands_message())
#             return ConversationHandler.END
#
#         profile = UserProfile(
#             telegram_id=str(user.id),
#             telegram_username=user.username
#         )
#         self._save_user_profile(profile)
#
#         await update.message.reply_text(self.messages["welcome"])
#         return RegistrationState.NAME.value
#
#     async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#         """Handle name input and proceed to team selection."""
#         user_id = str(update.message.from_user.id)
#         profile = self._load_user_profile(user_id)
#
#         if not profile:
#             return ConversationHandler.END
#
#         profile.name = update.message.text
#         self._save_user_profile(profile)
#
#         await update.message.reply_text(
#             self.messages["team_selection"],
#             reply_markup=self._create_team_keyboard()
#         )
#         return RegistrationState.TEAM.value
#
#     async def handle_team(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#         """Handle team selection and complete registration."""
#         query = update.callback_query
#         await query.answer()
#
#         user_id = str(query.from_user.id)
#         profile = self._load_user_profile(user_id)
#
#         if not profile:
#             return ConversationHandler.END
#
#         profile.team = "Male" if query.data == "team_male" else "Female"
#         self._save_user_profile(profile)
#
#         await query.edit_message_text(self.messages["registration_complete"])
#         return ConversationHandler.END
#
#     async def handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#         """Handle registration cancellation."""
#         await update.message.reply_text(self.messages["registration_cancelled"])
#         return ConversationHandler.END
#
#
# def create_registration_handler() -> ConversationHandler:
#     """Create and configure the registration conversation handler."""
#     registration_manager = RegistrationManager("data/registration.json")
#
#     return ConversationHandler(
#         entry_points=[CommandHandler("start", registration_manager.handle_start)],
#         states={
#             RegistrationState.NAME.value: [
#                 MessageHandler(filters.TEXT & ~filters.COMMAND, registration_manager.handle_name)
#             ],
#             RegistrationState.TEAM.value: [
#                 CallbackQueryHandler(registration_manager.handle_team, pattern="^team_")
#             ],
#         },
#         fallbacks=[CommandHandler("cancel", registration_manager.handle_cancel)]
#     )
