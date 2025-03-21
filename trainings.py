import datetime
from datetime import timedelta
import pytz


def get_next_training():
    # Розклад тренувань (день тижня, години, хвилини)
    # день тижня: 0 - понеділок, 4 - п'ятниця, 5 - субота
    schedule = [
        (0, 19, 30, 21, 00),  # Понеділок 19:30-21:00
        (4, 18, 00, 19, 30),  # П'ятниця 18:00-19:30
        (5, 17, 00, 19, 00)  # Субота 17:00-19:00
    ]  # Якщо з'являється якесь інше тренування, просто додати тут цю інфу і все

    # Отримуємо поточний час в Україні (Київ)
    kyiv_tz = pytz.timezone('Europe/Kiev')
    now = datetime.datetime.now(kyiv_tz)

    # Визначаємо поточний день тижня (0 - понеділок, 6 - неділя)
    current_weekday = now.weekday()

    # Знаходимо найближче тренування
    next_training = None
    days_until_next = 7  # Максимальна кількість днів до наступного тренування

    for training in schedule:
        weekday, start_hour, start_min, end_hour, end_min = training

        # Розрахуємо різницю в днях до цього тренування
        days_diff = (weekday - current_weekday) % 7

        # Створюємо datetime для цього тренування
        training_date = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
        if days_diff == 0:  # Якщо тренування сьогодні
            if now.time() < training_date.time():  # Якщо тренування ще не почалося
                if days_diff < days_until_next:
                    next_training = (days_diff, weekday, start_hour, start_min, end_hour, end_min)
                    days_until_next = days_diff
        else:  # Якщо тренування в інший день
            if days_diff < days_until_next:
                next_training = (days_diff, weekday, start_hour, start_min, end_hour, end_min)
                days_until_next = days_diff

    # Формуємо повідомлення
    if next_training:
        days_diff, weekday, start_hour, start_min, end_hour, end_min = next_training

        # Визначаємо назву дня тижня
        weekday_names = ['понеділок', 'вівторок', 'середу', 'четвер', "п'ятницю", 'суботу', 'неділю']
        weekday_name = weekday_names[weekday]

        # Дата наступного тренування
        next_date = now + timedelta(days=days_diff)
        date_str = next_date.strftime("%d.%m.%Y")

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
