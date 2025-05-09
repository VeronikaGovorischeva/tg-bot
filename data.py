from pymongo import MongoClient
from typing import Any, Dict, Optional

# MongoDB connection setup
client = MongoClient('mongodb://localhost:27017/')
db = client['TelegramBot']


def load_data(collection_name: str, default: Optional[Any] = None) -> Dict:
    """
    Load data from MongoDB collection.

    Args:
        collection_name (str): Name of the collection to load data from
        default (Any, optional): Default value if collection is empty

    Returns:
        Dict: Data from the collection or default value
    """
    try:
        # Get the collection
        collection = db[collection_name]

        # Get all documents from collection and combine into one dictionary
        data = {}
        for doc in collection.find():
            # Remove MongoDB's _id field
            doc_id = str(doc.pop('_id'))
            data[doc_id] = doc

        return data if data else (default if default is not None else {})
    except Exception as e:
        print(f"Error loading data from MongoDB: {e}")
        return default if default is not None else {}


def save_data(data: Dict, collection_name: str) -> None:
    """
    Save data to MongoDB collection.

    Args:
        data (Dict): Data to save
        collection_name (str): Name of the collection to save to
    """
    try:
        # Get the collection
        collection = db[collection_name]

        # Clear existing collection
        collection.delete_many({})

        # Insert new data
        for key, value in data.items():
            # Create document with ID
            document = value.copy() if isinstance(value, dict) else {'value': value}
            document['_id'] = key

            # Insert document
            collection.insert_one(document)
    except Exception as e:
        print(f"Error saving data to MongoDB: {e}")