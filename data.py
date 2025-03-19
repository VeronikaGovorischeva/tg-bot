import json

json_file = "user_data.json"


def load_user_data():
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_user_data(user_data):
    with open(json_file, 'w') as f:
        json.dump(user_data, f, indent=4)