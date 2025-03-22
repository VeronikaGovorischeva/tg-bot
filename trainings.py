import datetime
from datetime import timedelta
import pytz
from typing import List, Tuple, Dict, Optional


class TrainingManager:
    """Manager for training schedules and information."""

    def __init__(self):
        """Initialize with default training schedule."""
        # Format: (weekday, start_hour, start_min, end_hour, end_min)
        # weekday: 0 = Monday, 6 = Sunday
        self.schedule = [
            (0, 19, 30, 21, 0),  # Monday 19:30-21:00
            (4, 18, 0, 19, 30),  # Friday 18:00-19:30
            (5, 17, 0, 19, 0)  # Saturday 17:00-19:00
        ]
        self.timezone = pytz.timezone('Europe/Kiev')

    def get_current_time(self) -> datetime.datetime:
        """Get current time in the configured timezone."""
        return datetime.datetime.now(self.timezone)

    def get_next_training(self) -> str:
        """Get information about the next training session."""
        now = self.get_current_time()
        current_weekday = now.weekday()

        # Find the next training
        next_training = None
        days_until_next = 7  # Maximum days until next training

        for training in self.schedule:
            weekday, start_hour, start_min, end_hour, end_min = training

            # Calculate days difference to this training
            days_diff = (weekday - current_weekday) % 7

            # Create datetime for this training
            training_date = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)

            if days_diff == 0:  # If training is today
                if now.time() < training_date.time():  # If training hasn't started yet
                    if days_diff < days_until_next:
                        next_training = (days_diff, weekday, start_hour, start_min, end_hour, end_min)
                        days_until_next = days_diff
            else:  # If training is on another day
                if days_diff < days_until_next:
                    next_training = (days_diff, weekday, start_hour, start_min, end_hour, end_min)
                    days_until_next = days_diff

        # Format message
        if next_training:
            days_diff, weekday, start_hour, start_min, end_hour, end_min = next_training

            # Get weekday name
            weekday_names = ['понеділок', 'вівторок', 'середу', 'четвер', "п'ятницю", 'суботу', 'неділю']
            weekday_name = weekday_names[weekday]

            # Get date for next training
            next_date = now + timedelta(days=days_diff)
            date_str = next_date.strftime("%d.%m.%Y")

            # Format day text
            if days_diff == 0:
                day_text = "сьогодні"
            elif days_diff == 1:
                day_text = "завтра"
            else:
                day_text = f"через {days_diff} дні(в)"

            message = (f"Наступне тренування {day_text} ({weekday_name}), {date_str} "
                       f"з {start_hour:02d}:{start_min:02d} до {end_hour:02d}:{end_min:02d}")
        else:
            message = "Не вдалося визначити наступне тренування."

        return message

    def add_special_training(self, date: datetime.date,
                             start_time: Tuple[int, int],
                             end_time: Tuple[int, int],
                             location: Optional[str] = None) -> bool:
        """
        Add a special training session outside regular schedule.
        This would require additional implementation to store special trainings.
        """
        # Implementation would depend on how you want to store special trainings
        # For example, you might add them to a file or database
        pass

    def modify_schedule(self, new_schedule: List[Tuple[int, int, int, int, int]]) -> None:
        """Update the regular training schedule."""
        self.schedule = new_schedule