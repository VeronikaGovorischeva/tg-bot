from pymongo import MongoClient
from typing import Optional
from models import UserProfile, Team

client = MongoClient("mongodb://localhost:27017/")
db = client['TestBot']  # Change the name for better db
users = db['users']


class UserRepository:
    """
    Handles interaction with the user database for managing user information.

    This class provides methods to retrieve and save user profiles in a database
    based on their Telegram ID. It acts as a repository for UserProfile objects,
    allowing for the retrieval of user details and the updating or insertion of
    records into the database.
    """
    @staticmethod
    def get_by_telegram_id(telegram_id: int) -> Optional[UserProfile]:
        """
        Fetch a user profile from the database based on the provided Telegram ID.

        This method retrieves a user profile document from the database using the
        provided Telegram ID. If a matching document is found, it is converted to
        a UserProfile instance using the from_dict method. If no document is
        found, the method returns None.

        Args:
            telegram_id (int): The unique identifier of the Telegram user.

        Returns:
            Optional[UserProfile]: The user profile associated with the given
            Telegram ID, or None if no matching profile is found.
        """
        doc = users.find_one({"telegram_id": telegram_id})
        if doc:
            return UserProfile.from_dict(dict(doc))
        return None

    @staticmethod
    def save(user: UserProfile) -> None:
        """
        Save or update a user profile in the database. This method ensures that the user
        profile is stored in the 'users' collection. If a user profile with the specified
        telegram_id already exists, it updates the profile with the new data. Otherwise,
        it inserts a new user profile. The operation is performed as an upsert.

        Args:
            user (UserProfile): An instance of UserProfile representing the user's
                profile information to be saved in the database.

        Returns:
            None
        """
        users.update_one(
            {"telegram_id": user.telegram_id},
            {"$set": user.to_dict()},
            upsert=True
        )
