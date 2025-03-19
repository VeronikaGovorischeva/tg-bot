from datetime import datetime
import pytz

# Kiev timezone
KYIV_TZ = pytz.timezone('Europe/Kiev')


def get_current_kyiv_time():
    """Get the current time in Kyiv timezone"""
    return datetime.now(KYIV_TZ)


def format_date(date):
    """Format date as DD.MM.YYYY"""
    return date.strftime("%d.%m.%Y")


def format_time(hour, minute):
    """Format time as HH:MM"""
    return f"{hour:02d}:{minute:02d}"


def days_until_next_weekday(current_weekday, target_weekday):
    """Calculate days until the next occurrence of a specific weekday"""
    return (target_weekday - current_weekday) % 7


def get_team_specific_message(team):
    """Get team-specific messages"""
    if team == "Чоловіча":
        return {
            "welcome": "Вітаємо у чоловічій команді!",
            "training_info": "Тренування чоловічої команди відбуваються по понеділках, п'ятницях та суботах."
        }
    else:  # Жіноча
        return {
            "welcome": "Вітаємо у жіночій команді!",
            "training_info": "Тренування жіночої команди відбуваються по середах, п'ятницях та неділях."
        }