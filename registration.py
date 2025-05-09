from enum import Enum, auto
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, \
    filters
from dataclasses import dataclass
from data import load_data, save_data


class RegistrationState(Enum):
    """
    Represents the possible states of a registration process.

    This enum class provides constants that define the different stages or states
    a registration process might involve. Each state is represented as a distinct
    enumerated value.

    Attributes:
        NAME: Represents the "name" state in the registration process.
        TEAM: Represents the "team" state in the registration process.
    """
    NAME = auto()
    TEAM = auto()


class Team(Enum):
    """
    Enumeration representing possible team categories.

    This enumeration defines two categories for teams, 'Male' and 'Female',
    which can be used to classify or differentiate between different teams
    based on gender.

    Attributes
    ----------
    MALE : str
        Represents the 'Male' team category.
    FEMALE : str
        Represents the 'Female' team category.
    """
    MALE = "Male"
    FEMALE = "Female"


class Messages:
    """
    Represents a collection of messages used for user interaction.

    This class provides a set of predefined constant messages that can be utilized for
    communicating with users during various stages of interaction such as registration,
    team selection, or cancellation processes. These messages are static and primarily
    intended for use in user interface or bot interactions.
    """
    WELCOME = "Привіт! Введи своє прізвище та ім'я АНГЛІЙСЬКОЮ"
    TEAM_SELECTION = "Дякую! Тепер обери свою команду:"
    REGISTRATION_COMPLETE = ("Реєстрацію завершено.\n"
                             "Використовуй команди /next_training для інформації про тренування "
                             "та /next_game для інформації про ігри.")
    REGISTRATION_CANCELLED = "Реєстрація скасована. Використовуй /start щоб спробувати знову."


@dataclass
class UserProfile:
    """
    Represents a user profile with details related to their Telegram account and additional attributes.

    The UserProfile class encapsulates user information such as Telegram ID, username, associated name,
    team membership, and debt list. This structure is particularly useful in applications where user
    details need to be managed or serialized.

    Attributes:
        telegram_id (str): The unique Telegram ID for the user.
        telegram_username (Optional[str]): The Telegram username of the user. Can be None.
        name (Optional[str]): The name of the user. Can be None.
        team (Optional[Team]): The team the user belongs to. Can be None.
        debt (list[int]): A list representing the user's debt or financial status. Defaults to None.

    Methods:
        is_registered:
            Determines if the user profile is considered registered. It checks whether the 'name' and 'team'
            attributes are present.

        to_dict:
            Converts the user profile into a dictionary format suitable for serialization or storage.
    """
    telegram_id: str
    telegram_username: Optional[str]
    name: Optional[str] = None
    team: Optional[Team] = None
    debt: list[int] = None

    def is_registered(self) -> bool:
        return all([self.name, self.team])

    def to_dict(self) -> Dict:
        return {
            "telegram_username": self.telegram_username,
            "name": self.name,
            "team": self.team.value if self.team else None,
            "debt": self.debt or [0]
        }


class MessageHandlers:
    """
    Handles messages and related functionalities.

    This class provides methods for generating command-related
    messages and creating keyboards for team selection. It is
    intended for use in scenarios where a bot is required to
    respond to user interactions with structured commands and
    keyboards.

    Attributes:
        commands (Dict[str, str]): A dictionary mapping command
            names to their descriptions or purposes.
    """

    def __init__(self, commands: Dict[str, str]):
        self.commands = commands

    def get_commands_message(self) -> str:
        """
        Returns a message containing the available commands for the user.

        Commands are dynamically generated based on the keys available
        in the `self.commands` dictionary. Each command is prefixed with
        a forward slash ('/') and the resulting message encourages the
        user to use these commands for obtaining information about
        trainings and upcoming games.

        Returns:
            str: Message listing all available commands.
        """
        commands = [f"/{cmd}" for cmd in self.commands.keys()]
        return f"Використовуй команди {' '.join(commands)} щоб дізнатися інфу про наступне тренування та наступну гру."

    @staticmethod
    def create_team_keyboard() -> InlineKeyboardMarkup:
        """
        Create an inline keyboard for selecting team gender.

        This method generates an inline keyboard markup that provides options
        for selecting a male or female team. It is utilized in scenarios where
        gender-specific team selection is required.

        Returns:
            InlineKeyboardMarkup: The generated inline keyboard markup that
            allows the user to select between male and female teams.
        """
        keyboard = [
            [
                InlineKeyboardButton("Чоловіча", callback_data="team_male"),
                InlineKeyboardButton("Жіноча", callback_data="team_female"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)


class RegistrationManager:
    """
    Manages user registration, including loading, saving user profiles, handling commands,
    and collecting required user information.

    This class is designed for managing the process of user registration in a conversational
    bot application. It includes methods to handle various stages of registration, from
    starting the process to collecting user name, team preference, and storing user
    information persistently. Additionally, it manages bot commands and responses during
    registration and post-registration activities.
    """

    def __init__(self, registration_file: str):
        self.registration_file = registration_file
        self.commands = {
            "next_training": "інформації про тренування",
            "next_game": "інформації про ігри",
            "list_games": "список ігор"
        }
        self.message_handler = MessageHandlers(self.commands)

    def _get_commands_message(self) -> str:
        """
        Constructs and returns a message string containing a list of available commands for
        interaction, formatted as Telegram bot commands.

        Returns:
            str: A formatted string listing all available commands.
        """
        commands = [f"/{cmd}" for cmd in self.commands.keys()]
        return f"Використовуй команди {' '.join(commands)} щоб дізнатися інфу про наступне тренування та наступну гру."

    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Loads a user profile based on the provided user ID.

        This method retrieves user data from the registration file and returns a
        UserProfile object if the user is found. If the user does not exist in
        the data, it returns None. The method also manages optional fields such as
        the user's team and debt information.

        Arguments:
            user_id (str): The unique identifier of the user whose profile
                needs to be loaded.

        Returns:
            Optional[UserProfile]: A UserProfile object containing the user's
            information if the user exists in the registration file, otherwise None.
        """
        user_data = load_data(self.registration_file)
        if user_id in user_data:
            data = user_data[user_id]
            team = Team(data.get("team")) if data.get("team") else None
            return UserProfile(
                telegram_id=user_id,
                telegram_username=data.get("telegram_username"),
                name=data.get("name"),
                team=team,
                debt=data.get("debt", [0])
            )
        return None

    def save_user_profile(self, profile: UserProfile) -> None:
        """
        Save the user profile to the registration file.

        This method loads user data from a file, updates the data
        with the given user profile, and then saves the updated
        data back to the file. It ensures that a user's profile is
        stored and managed within the registration system.

        Args:
            profile (UserProfile): The user profile to be saved.

        """
        user_data = load_data(self.registration_file)
        user_data[profile.telegram_id] = profile.to_dict()
        save_data(user_data, self.registration_file)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Handles the /start command for initiating a conversation with the user, ensuring
        the user's registration status is checked and processed accordingly. If the user
        is already registered, it sends a list of available commands. Otherwise, it
        guides the user through the registration process by saving their initial profile
        information.

        Args:
            update (Update): The update object containing information about the incoming message.
            context (ContextTypes.DEFAULT_TYPE): The context object containing information about
                the current state and associated data.

        Returns:
            int: The next state of the conversation. Returns `ConversationHandler.END`
                if the user is already registered, or the next registration state value
                if the user is not registered.
        """
        user = update.message.from_user
        profile = self.load_user_profile(str(user.id))

        if profile and profile.is_registered():
            await update.message.reply_text(self._get_commands_message())
            return ConversationHandler.END

        profile = UserProfile(
            telegram_id=str(user.id),
            telegram_username=user.username
        )
        self.save_user_profile(profile)

        await update.message.reply_text(Messages.WELCOME)
        return RegistrationState.NAME.value

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Handles the user's input to set their name during the registration process. This function is
        part of an asynchronous conversational flow within a bot, ensuring that the user's name
        is stored and the user progresses to the next step of registration.

        Parameters
        ----------
        update : Update
            Incoming update object that contains user interaction data, including their message.
        context : ContextTypes.DEFAULT_TYPE
            Application context that allows passing relevant data throughout the conversation.

        Returns
        -------
        int
            The next state in the conversation, guiding the user to the team selection step. If the
            user profile is not loaded successfully, it ends the conversation.

        Raises
        ------
        None
        """
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
        """
        Handles the selection of a user's team in a conversation flow.

        This asynchronous method processes the user's team selection based on the
        callback query data during a bot conversation, updates the user's profile,
        and finalizes the registration process.

        Parameters:
            update (Update): The incoming update that includes the callback query.
            context (ContextTypes.DEFAULT_TYPE): The context from the bot framework
                providing contextual information about the conversation.

        Returns:
            int: Indicates the end of the conversation handler when the task is
                complete.

        """
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
        """
        Handles the cancellation of a conversation within a chat.

        This method is triggered when a user decides to cancel their ongoing
        conversation or interaction, particularly during the registration process.
        Upon cancellation, a predefined cancellation message is sent as a response
        to the user.

        Parameters:
        update (Update): The incoming update containing information such as the user
            and the message.
        context (ContextTypes.DEFAULT_TYPE): Provides contextual information about
            the ongoing conversation and allows interaction with the bot.

        Returns:
        int: Returns the END constant from ConversationHandler to indicate
            the termination of the conversation.
        """
        await update.message.reply_text(Messages.REGISTRATION_CANCELLED)
        return ConversationHandler.END


def create_registration_handler() -> ConversationHandler:
    """
    Creates a conversation handler for the user registration process.

    This function sets up the registration process by creating a
    ConversationHandler that guides the user through several states
    to gather necessary details such as their name and team preference.
    It uses a registration manager to handle user input and state transitions.

    Returns:
        ConversationHandler: The handler configured with the workflow
        for user registration, entry points, states, and fallback commands.
    """
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
