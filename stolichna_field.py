# stolichna_field.py
from data import load_data, save_data

users = load_data("users")

for user_id, data in users.items():
    if "stolichna" not in data:
        data["stolichna"] = False  # default value

save_data(users, "users")
print("✅ Field 'stolichna' added to all users.")

