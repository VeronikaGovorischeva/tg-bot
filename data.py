from pymongo import MongoClient
from typing import Any, Dict, Optional

client = MongoClient('mongodb://localhost:27017/')
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
