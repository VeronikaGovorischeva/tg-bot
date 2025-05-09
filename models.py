from dataclasses import dataclass,field
from enum import Enum
from typing import Optional, Dict,List
from bson import ObjectId
from datetime import datetime


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


@dataclass
class DebtEntry:
    """
    Represents an entry of debt related to a specific training session.

    This class is used to encapsulate the details of a debt associated with a
    training session. It stores information such as the training identifier,
    training date, amount owed, payment card used, and the current status of
    the debt. This representation allows for easier manipulation and tracking
    of debt-related data.

    Attributes:
        training_id (ObjectId): The unique identifier for the training session.
        training_date (datetime): The date associated with the training session.
        amount (float): The amount of debt owed.
        payment_card (str): The identifier of the payment card used.
        status (str): The current status of the debt.

    Methods:
        to_dict() -> Dict:
            Converts the DebtEntry instance into a dictionary for easier
            storage or transmission.
    """
    training_id: ObjectId
    training_date: datetime
    amount: float
    payment_card: str
    status: str

    def to_dict(self) -> Dict:
        return {
            "training_id": self.training_id,
            "training_date": self.training_date,
            "amount": self.amount,
            "payment_card": self.payment_card,
            "status": self.status
        }


@dataclass
class UserProfile:
    """
    Represents a user's profile with attributes and helper methods for data manipulation.

    Defines a class to manage user information including their Telegram ID, username, display name,
    team affiliation, debt details, and debt history. This class enables serialization and
    deserialization of user data to and from dictionaries, as well as conditional checks for
    registration status.

    Attributes:
        telegram_id: int
            A unique identifier for the user in Telegram.
        telegram_username: Optional[str]
            The Telegram username of the user, if available.
        display_name: Optional[str]
            The name displayed for the user. Defaults to None if not set.
        team: Optional[Team]
            The team the user belongs to, represented by the Team enum. Defaults to None if not set.
        debt: float
            The amount of debt the user owes. Defaults to 0.
        debt_history: List[DebtEntry]
            A list containing the user's history of debt changes and entries. Defaults to an empty
            list.

    """
    telegram_id: int
    telegram_username: Optional[str]
    name: Optional[str] = None
    team: Optional[Team] = None
    debt: float = 0
    debt_history: List[DebtEntry] = field(default_factory=list)

    def is_registered(self) -> bool:
        return self.name is not None and self.team is not None

    def to_dict(self) -> Dict:
        return {
            "telegram_id": self.telegram_id,
            "telegram_username": self.telegram_username,
            "name": self.name,
            "team": self.team.value if self.team else None,
            "debt": self.debt,
            "debt_history": [entry.to_dict() for entry in self.debt_history]
        }

    @staticmethod
    def from_dict(data: Dict) -> "UserProfile":
        return UserProfile(
            telegram_id=data["telegram_id"],
            telegram_username=data.get("telegram_username"),
            name=data.get("name"),
            team=Team(data["team"]) if data.get("team") else None,
            debt=data.get("debt", 0),
            debt_history=[
                DebtEntry(**entry) for entry in data.get("debt_history", [])
            ]
        )
