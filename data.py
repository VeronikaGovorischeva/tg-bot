import json


def load_user_data(file):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_user_data(user_data, file):
    with open(file, 'w') as f:
        json.dump(user_data, f, indent=4)
