import json
import os

json_file = "user_data.json"


def validate_user_data(user_data):
    """Validate the structure of user data"""
    if not isinstance(user_data, dict):
        return False

    # Check each user's data format
    for user_id, data in user_data.items():
        if not isinstance(data, dict):
            return False

    return True


def load_user_data():
    """Load user data from JSON file with validation and error handling"""
    try:
        # Check if file exists
        if not os.path.exists(json_file):
            return {}

        # Check if file is empty
        if os.path.getsize(json_file) == 0:
            return {}

        # Read and parse JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                user_data = json.load(f)

                # Validate data structure
                if validate_user_data(user_data):
                    return user_data
                else:
                    # Create backup of corrupt file
                    backup_file = f"{json_file}.bak"
                    with open(backup_file, 'w', encoding='utf-8') as backup:
                        backup.write(open(json_file, 'r', encoding='utf-8').read())
                    return {}
            except json.JSONDecodeError:
                # Create backup of corrupt file
                backup_file = f"{json_file}.bak"
                with open(backup_file, 'w', encoding='utf-8') as backup:
                    backup.write(open(json_file, 'r', encoding='utf-8').read())
                return {}
    except Exception:
        return {}


def save_user_data(user_data):
    """Save user data to JSON file with validation and error handling"""
    try:
        # Validate data before saving
        if not validate_user_data(user_data):
            return False

        # Create directory if it doesn't exist
        directory = os.path.dirname(json_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        # Write to file
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False


def get_user_info(user_id):
    """Get specific user information"""
    user_data = load_user_data()
    return user_data.get(str(user_id), None)


def update_user_field(user_id, field, value):
    """Update a specific field for a user"""
    user_data = load_user_data()
    user_id_str = str(user_id)

    if user_id_str not in user_data:
        user_data[user_id_str] = {}

    user_data[user_id_str][field] = value
    return save_user_data(user_data)