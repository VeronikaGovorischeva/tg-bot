import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Configuration for the Telegram bot."""

    # Conversation states
    NAME = 0
    TEAM = 1
    GAME_DATE = 10
    GAME_TIME = 11
    GAME_LOCATION = 12
    GAME_OPPONENT = 13
    GAME_ARRIVAL = 14
    GAME_TEAM = 15
    GAME_DELETE_CONFIRM = 20
    EDIT_GAME_SELECT = 30
    EDIT_GAME_FIELD = 31
    EDIT_GAME_NEW_VALUE = 32

    # File paths - use os.path to ensure cross-platform compatibility
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    JSON_FILE = "data.user_data.json"
    GAMES_FILE = "data.games_data.json"

    # Get Telegram token from environment variables
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

    # Admin configurations - read from environment variables with fallback to hardcoded values
    # Format in .env: ADMIN_IDS=786580423,1028639864
    _default_admins = "786580423,1028639864"  # danya_id, nika_id as fallback
    ADMIN_IDS = [int(id) for id in os.environ.get("ADMIN_IDS", _default_admins).split(",") if id]

    # Training schedule (day of week, start hour, start minute, end hour, end minute)
    # day of week: 0 - Monday, 4 - Friday, 5 - Saturday
    TRAINING_SCHEDULE = [
        (0, 19, 30, 21, 0),  # Monday 19:30-21:00
        (4, 18, 0, 19, 30),  # Friday 18:00-19:30
        (5, 17, 0, 19, 0)  # Saturday 17:00-19:00
    ]

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all required directories exist."""
        os.makedirs(cls.DATA_DIR, exist_ok=True)

    @classmethod
    def get_default_games_data(cls) -> Dict[str, Any]:
        """Get default structure for games data."""
        return {
            "upcoming_games": [],
            "authorized_users": cls.ADMIN_IDS
        }
