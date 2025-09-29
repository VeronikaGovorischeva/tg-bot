from enum import Enum, auto
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, \
    filters
from dataclasses import dataclass
from data import load_data, save_data


class RegistrationState(Enum):
    NAME = auto()
    TEAM = auto()


class Team(Enum):
    MALE = "Male"
    FEMALE = "Female"


class Messages:
    WELCOME = "Привіт! Введи своє прізвище та ім'я"
    TEAM_SELECTION = "Дякую! Тепер обери свою команду:"
    REGISTRATION_COMPLETE = ("Реєстрацію завершено.\n"
                             "Використовуй команди з меню для інформації про тренування, оплату та голосування")
    REGISTRATION_CANCELLED = "Реєстрація скасована. Використовуй /start щоб спробувати знову."


@dataclass
class UserProfile:
    telegram_id: str
    telegram_username: Optional[str]
    name: Optional[str] = None
    team: Optional[Team] = None
    mvp: int = 0
    stolichna: bool = False
    training_attendance: Dict = None
    game_attendance: Dict = None

    def __post_init__(self):
        if self.training_attendance is None:
            self.training_attendance = {"attended": 0, "total": 0}
        if self.game_attendance is None:
            self.game_attendance = {"attended": 0, "total": 0}

    def is_registered(self) -> bool:
        return all([self.name, self.team])

    def to_dict(self) -> Dict:
        return {
            "telegram_username": self.telegram_username,
            "name": self.name,
            "team": self.team.value if self.team else None,
            "mvp": self.mvp,
            "stolichna": self.stolichna,
            "training_attendance": self.training_attendance,
            "game_attendance": self.game_attendance
        }


class MessageHandlers:
    @staticmethod
    def create_team_keyboard() -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("Чоловіча", callback_data="team_male"),
                InlineKeyboardButton("Жіноча", callback_data="team_female"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)


class RegistrationManager:
    def __init__(self, registration_file: str):
        self.registration_file = registration_file
        self.message_handler = MessageHandlers()

    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        user_data = load_data(self.registration_file)
        if user_id in user_data:
            data = user_data[user_id]
            team = Team(data.get("team")) if data.get("team") else None

            default_attendance = {"attended": 0, "total": 0}

            return UserProfile(
                telegram_id=user_id,
                telegram_username=data.get("telegram_username"),
                name=data.get("name"),
                team=team,
                mvp=data.get("mvp", 0),
                stolichna=data.get("stolichna", True),
                training_attendance=data.get("training_attendance", default_attendance),
                game_attendance=data.get("game_attendance", default_attendance)
            )
        return None

    def save_user_profile(self, profile: UserProfile) -> None:
        user_data = load_data(self.registration_file)
        user_data[profile.telegram_id] = profile.to_dict()
        save_data(user_data, self.registration_file)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        profile = self.load_user_profile(str(user.id))

        if profile and profile.is_registered():
            await update.message.reply_text(
                f"Використовуй команди з меню щоб дізнатися інфу про наступне тренування та наступну гру.")
            return ConversationHandler.END

        profile = UserProfile(
            telegram_id=str(user.id),
            telegram_username=user.username
        )
        self.save_user_profile(profile)

        await update.message.reply_text(Messages.WELCOME)
        return RegistrationState.NAME.value

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = str(update.message.from_user.id)
        profile = self.load_user_profile(user_id)

        if not profile:
            return ConversationHandler.END

        profile.name = update.message.text
        self.save_user_profile(profile)

        await update.message.reply_text(
            Messages.TEAM_SELECTION,
            reply_markup=self.message_handler.create_team_keyboard()
        )
        return RegistrationState.TEAM.value

    async def handle_team(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()

        user_id = str(query.from_user.id)
        profile = self.load_user_profile(user_id)

        if not profile:
            return ConversationHandler.END

        profile.team = Team.MALE if query.data == "team_male" else Team.FEMALE
        self.save_user_profile(profile)

        await query.edit_message_text(Messages.REGISTRATION_COMPLETE)
        return ConversationHandler.END

    @staticmethod
    async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(Messages.REGISTRATION_CANCELLED)
        return ConversationHandler.END


def create_registration_handler() -> ConversationHandler:
    registration_manager = RegistrationManager("users")

    return ConversationHandler(
        entry_points=[CommandHandler("start", registration_manager.handle_start)],
        states={
            RegistrationState.NAME.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, registration_manager.handle_name)
            ],
            RegistrationState.TEAM.value: [
                CallbackQueryHandler(registration_manager.handle_team, pattern="^team_")
            ],
        },
        fallbacks=[CommandHandler("cancel", registration_manager.handle_cancel)]
    )


def setup_registration_handlers(app):
    # /start
    app.add_handler(create_registration_handler())
