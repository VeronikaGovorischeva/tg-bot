from data import load_data, save_data

def add_universiada_field():
    users = load_data("users", {})

    for uid, user in users.items():
        # Add field only if missing
        if "universiada" not in user:
            user["universiada"] = False

    save_data(users, "users")
    print("universiada field added to all users")

if __name__ == "__main__":
    add_universiada_field()

