from pymongo import MongoClient
from typing import Any, Dict, Optional
import os
from dotenv import load_dotenv
import logging
import datetime

load_dotenv()

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client['TelegramBot']


def load_data(collection_name: str, default: Optional[Any] = None) -> Dict:
    try:
        collection = db[collection_name]
        data = {}
        for doc in collection.find():
            doc_id = str(doc.pop('_id'))
            data[doc_id] = doc

        return data if data else (default if default is not None else {})
    except Exception as e:
        print(f"Error loading data from MongoDB: {e}")
        return default if default is not None else {}


def save_data(data: Dict, collection_name: str) -> None:
    try:
        collection = db[collection_name]

        collection.delete_many({})

        for key, value in data.items():
            document = value.copy() if isinstance(value, dict) else {'value': value}
            document['_id'] = key

            collection.insert_one(document)
    except Exception as e:
        print(f"Error saving data to MongoDB: {e}")

def log_command_usage(user_id: str, command_name: str):
    commands = load_data("commands", {})

    cmd = commands.get(command_name, {
        "amount": 0,
        "last_time": None,
        "last_user_id": None
    })

    cmd["amount"] += 1
    cmd["last_time"] = datetime.datetime.now().isoformat(timespec="seconds")
    cmd["last_user_id"] = user_id

    commands[command_name] = cmd
    save_data(commands, "commands")

    # 🔹 логінг замість print
    logger.info(f"Command {command_name} used by {user_id} (total {cmd['amount']})")