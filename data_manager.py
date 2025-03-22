import json
import os
from typing import Dict, Any, Optional


class DataManager:

    def __init__(self, default_data: Optional[Dict[str, Any]] = None):
        self.default_data = default_data or {}

    def load_data(self, file_path: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(file_path):
                self.save_data(self.default_data, file_path)
                return self.default_data.copy()

            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {file_path}")
            return self.default_data.copy()
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")
            return self.default_data.copy()

    def save_data(self, data: Dict[str, Any], file_path: str) -> bool:
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving data to {file_path}: {e}")
            return False

    def update_user_data(self, file_path: str, user_id: str, data: Dict[str, Any]) -> bool:
        try:
            all_data = self.load_data(file_path)

            # If user exists, update their data
            if user_id in all_data:
                all_data[user_id].update(data)
            else:
                all_data[user_id] = data

            return self.save_data(all_data, file_path)
        except Exception as e:
            print(f"Error updating user data: {e}")
            return False
