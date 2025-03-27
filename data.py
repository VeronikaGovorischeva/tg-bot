import json


def load_data(file, *args):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return args[0] if args else {}


def save_data(data, file):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

