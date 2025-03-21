import json
from datetime import datetime

GAMES_FILE = "games_data.json"
danya_id, nika_id = 786580423, 1028639864
ADMIN_IDS = [danya_id, nika_id]  # Replace with actual admin user IDs


def load_games_data():
    try:
        with open(GAMES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"upcoming_games": [], "authorized_users": ADMIN_IDS}


def save_games_data(games_data):
    with open(GAMES_FILE, 'w') as f:
        json.dump(games_data, f, indent=4)


def add_game(date, time, location, opponent, arrival_time, team):
    games_data = load_games_data()

    max_id = 0
    for game in games_data["upcoming_games"]:
        if "id" in game and int(game["id"]) > max_id:
            max_id = int(game["id"])
    game_id = str(max_id + 1)

    new_game = {
        "id": game_id,  # Add the ID
        "date": date,
        "time": time,
        "location": location,
        "opponent": opponent,
        "arrival_time": arrival_time,
        "team": team,
    }

    games_data["upcoming_games"].append(new_game)
    save_games_data(games_data)
    return True


def get_next_game(team=None):
    games_data = load_games_data()
    upcoming = games_data.get("upcoming_games", [])

    if not upcoming:
        return "Немає запланованих ігор."

    now = datetime.now()

    # Filter games by team if specified
    if team:
        team_games = [game for game in upcoming if game.get('team') == team]
        if not team_games:
            return f"Немає запланованих ігор для {team} команди."
        upcoming = team_games

    future_games = []
    for game in upcoming:
        try:
            game_datetime = datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
            if game_datetime > now:
                future_games.append((game, game_datetime))
        except Exception as e:
            print(f"Error parsing date: {e}")

    if not future_games:
        return "Немає майбутніх ігор."

    # Sort by date and time
    future_games.sort(key=lambda x: x[1])

    # Get the next game
    game = future_games[0][0]
    game_datetime = future_games[0][1]

    # Calculate days until the game
    days_diff = (game_datetime.date() - now.date()).days

    # Format the message
    team_str = f"Команда: {game['team']}\n" if 'team' in game else ""
    day_text = "сьогодні" if days_diff == 0 else "завтра" if days_diff == 1 else f"через {days_diff} дні(в)"

    return (f"Наступна гра {day_text}, {game['date']} о {game['time']}\n"
            f"{team_str}"
            f"Проти: {game['opponent']}\n"
            f"Місце: {game['location']}\n"
            f"Прибути до: {game['arrival_time']}")


def is_authorized(user_id):
    games_data = load_games_data()
    return user_id in games_data.get("authorized_users", [])


def list_all_games():
    games_data = load_games_data()
    all_games = games_data.get("upcoming_games", [])

    if not all_games:
        return []

    # Filter for future games if requested
    now = datetime.now()
    filtered_games = []
    for game in all_games:
        try:
            game_datetime = datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
            if game_datetime > now:
                filtered_games.append(game)
        except Exception as e:
            print(f"Error parsing date: {e}")
            filtered_games.append(game)  # Keep games with parsing errors just to be safe
    games = filtered_games

    # Sort games by date and time
    try:
        games.sort(key=lambda x: datetime.strptime(f"{x['date']} {x['time']}", "%d.%m.%Y %H:%M"))
    except Exception as e:
        print(f"Error sorting games: {e}")

    return games


def delete_game(game_id):
    """Delete a game by its ID"""
    games_data = load_games_data()
    upcoming = games_data.get("upcoming_games", [])

    # Find the game with the given ID
    game_index = None
    for i, game in enumerate(upcoming):
        if game.get('id') == game_id:
            game_index = i
            break

    # If game found, remove it
    if game_index is not None:
        removed_game = upcoming.pop(game_index)
        games_data["upcoming_games"] = upcoming
        save_games_data(games_data)
        return True, removed_game

    return False, None


def edit_game(game_id, field, new_value):
    """Edit a specific field of a game"""
    games_data = load_games_data()
    upcoming = games_data.get("upcoming_games", [])

    # Find the game with the given ID
    for game in upcoming:
        if game.get('id') == game_id:
            game[field] = new_value
            save_games_data(games_data)
            return True, game

    return False, None


def get_game(game_id):
    """Get a game by its ID"""
    games_data = load_games_data()
    upcoming = games_data.get("upcoming_games", [])

    for game in upcoming:
        if game.get('id') == game_id:
            return game

    return None
