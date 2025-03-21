NAME = 0
TEAM = 1
GAME_DATE = 10
GAME_TIME = 11
GAME_LOCATION = 12
GAME_OPPONENT = 13
GAME_ARRIVAL = 14
GAME_TEAM = 15
GAME_DELETE_CONFIRM = 20
EDIT_GAME_SELECT = 30
EDIT_GAME_FIELD = 31
EDIT_GAME_NEW_VALUE = 32
JSON_FILE = "user_data.json"
GAMES_FILE = "games_data.json"
danya_id, nika_id = 786580423, 1028639864
ADMIN_IDS = [danya_id, nika_id]
GAMES_DICT = {"upcoming_games": [], "authorized_users": ADMIN_IDS}
# Розклад тренувань (день тижня, години, хвилини)
# день тижня: 0 - понеділок, 4 - п'ятниця, 5 - субота
TRAINING_SCHEDULE = [
    (0, 19, 30, 21, 00),  # Понеділок 19:30-21:00
    (4, 18, 00, 19, 30),  # П'ятниця 18:00-19:30
    (5, 17, 00, 19, 00)  # Субота 17:00-19:00
]
