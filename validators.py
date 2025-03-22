import re
from datetime import datetime
from typing import Tuple, Optional


class InputValidator:

    @staticmethod
    def validate_date(date_str: str) -> Tuple[bool, Optional[str]]:
        pattern = r"^\d{2}\.\d{2}\.\d{4}$"
        if not re.match(pattern, date_str):
            return False, "Неправильний формат дати. Використовуйте ДД.ММ.РРРР (наприклад, 25.03.2025)"

        try:
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            # Check if date is not in the past
            if date_obj.date() < datetime.now().date():
                return False, "Дата не може бути в минулому"
            return True, None
        except ValueError:
            return False, "Неіснуюча дата. Перевірте правильність дня та місяця"

    @staticmethod
    def validate_time(time_str: str) -> Tuple[bool, Optional[str]]:
        pattern = r"^\d{1,2}:\d{2}$"
        if not re.match(pattern, time_str):
            return False, "Неправильний формат часу. Використовуйте ГГ:ХХ (наприклад, 19:00)"

        try:
            time_parts = time_str.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1])

            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                return False, "Неправильний час. Години мають бути від 0 до 23, хвилини - від 0 до 59"

            return True, None
        except (ValueError, IndexError):
            return False, "Неправильний формат часу"

    @staticmethod
    def validate_datetime_combination(date_str: str, time_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a date and time combination is in the future.

        Args:
            date_str: Date string in DD.MM.YYYY format
            time_str: Time string in HH:MM format

        Returns:
            Tuple of (is_valid, error_message)
        """
        date_valid, date_error = InputValidator.validate_date(date_str)
        time_valid, time_error = InputValidator.validate_time(time_str)

        if not date_valid:
            return False, date_error
        if not time_valid:
            return False, time_error

        try:
            datetime_obj = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
            if datetime_obj < datetime.now():
                return False, "Дата та час не можуть бути в минулому"
            return True, None
        except ValueError:
            return False, "Неправильна комбінація дати та часу"