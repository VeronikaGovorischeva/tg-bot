import json


def load_data(file, *args):
    try:
        with open(f"{file}", 'r',encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return args[0] if args else {}


def save_data(data, file):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)