from datetime import datetime
import json
from typing import Dict, List, Tuple, Optional, Any


class GamesManager:
    def __init__(self, games_file: str, admin_ids: List[int]) -> None:
        self.games_file = games_file
        self.default_data = {"upcoming_games": [], "authorized_users": admin_ids}

    def load_data(self) -> Dict[str, Any]:
        try:
            with open(self.games_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.default_data.copy()

    def save_data(self, data: Dict[str, Any]) -> None:
        with open(self.games_file, 'w') as f:
            json.dump(data, f, indent=4)

    def add_game(self, date: str, time: str, location: str, opponent: str, team: str) -> bool:
        games_data = self.load_data()

        # Generate new game ID
        max_id = 0
        for game in games_data["upcoming_games"]:
            if "id" in game and int(game["id"]) > max_id:
                max_id = int(game["id"])
        game_id = str(max_id + 1)

        new_game = {
            "id": game_id,
            "team": team,
            "date": date,
            "time": time,
            "location": location,
            "opponent": opponent,
        }

        games_data["upcoming_games"].append(new_game)
        self.save_data(games_data)
        return True

    def get_next_game(self, team: Optional[str] = None) -> str:
        games_data = self.load_data()
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

        future_games.sort(key=lambda x: x[1])
        game = future_games[0][0]
        game_datetime = future_games[0][1]
        days_diff = (game_datetime.date() - now.date()).days
        team_str = f"Команда: {game['team']}\n" if 'team' in game else ""
        day_text = "сьогодні" if days_diff == 0 else "завтра" if days_diff == 1 else f"через {days_diff} дні(в)"

        return (f"Наступна гра {day_text}, {game['date']} о {game['time']}\n"
                f"{team_str}"
                f"Проти: {game['opponent']}\n"
                f"Місце: {game['location']}")

    def is_authorized(self, user_id: int) -> bool:
        games_data = self.load_data()
        return user_id in games_data.get("authorized_users", [])

    def list_all_games(self) -> List[Dict[str, Any]]:
        games_data = self.load_data()
        all_games = games_data.get("upcoming_games", [])

        if not all_games:
            return []

        # Filter for future games
        now = datetime.now()
        filtered_games = []
        for game in all_games:
            try:
                game_datetime = datetime.strptime(f"{game['date']} {game['time']}", "%d.%m.%Y %H:%M")
                if game_datetime > now:
                    filtered_games.append(game)
            except Exception as e:
                print(f"Error parsing date: {e}")
                filtered_games.append(game)

        try:
            filtered_games.sort(key=lambda x: datetime.strptime(f"{x['date']} {x['time']}", "%d.%m.%Y %H:%M"))
        except Exception as e:
            print(f"Error sorting games: {e}")

        return filtered_games

    def delete_game(self, game_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        games_data = self.load_data()
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
            self.save_data(games_data)
            return True, removed_game

        return False, None

    def edit_game(self, game_id: str, field: str, new_value: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        games_data = self.load_data()
        upcoming = games_data.get("upcoming_games", [])

        # Find the game with the given ID
        for game in upcoming:
            if game.get('id') == game_id:
                game[field] = new_value
                self.save_data(games_data)
                return True, game

        return False, None

    def get_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        games_data = self.load_data()
        upcoming = games_data.get("upcoming_games", [])

        for game in upcoming:
            if game.get('id') == game_id:
                return game

        return None
