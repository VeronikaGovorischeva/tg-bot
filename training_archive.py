import datetime
from typing import Dict, Any, Optional
from data import load_data, save_data
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

TRAINING_VOTES_ARCHIVE_FILE = "training_votes_archive"
TRAINING_VOTES_FILE = "votes"
USERS_FILE = "users"


class TrainingVotesArchiver:
    def __init__(self):
        self.archive_file = TRAINING_VOTES_ARCHIVE_FILE
        self.votes_file = TRAINING_VOTES_FILE
        self.users_file = USERS_FILE

    def archive_training_vote(self, training_id: str, training_data: Dict[str, Any],
                              force_archive: bool = False) -> bool:
        try:
            votes_data = load_data(self.votes_file, {"votes": {}})

            if training_id not in votes_data["votes"]:
                print(f"⚠️ No votes found for training {training_id}")
                return False

            actual_date = self._get_actual_training_date(training_id, training_data)

            if not force_archive and not self._should_archive_today(training_id, actual_date):
                print(f"⚠️ Training {training_id} should not be archived today")
                return False
            archive_entry = self._create_archive_entry(
                training_id,
                training_data,
                votes_data["votes"][training_id],
                actual_date
            )

            archive_data = load_data(self.archive_file, {})
            archive_id = self._generate_archive_id(archive_data)
            archive_data[archive_id] = archive_entry
            save_data(archive_data, self.archive_file)

            self._update_user_statistics(
                votes_data["votes"][training_id],
                training_data.get("team", "Both")
            )

            del votes_data["votes"][training_id]
            save_data(votes_data, self.votes_file)

            print(f"✅ Archived training {training_id} with {len(archive_entry['votes'])} votes")
            return True

        except Exception as e:
            print(f"❌ Error archiving training {training_id}: {e}")
            return False

    def _get_actual_training_date(self, training_id: str, training_data: Dict[str, Any]) -> str:
        if training_id.startswith("const_"):
            today = datetime.datetime.now().date()
            weekday = training_data.get("weekday")

            if weekday is not None:
                days_ago = (today.weekday() - weekday) % 7
                if days_ago == 0:
                    training_time = datetime.time(
                        hour=training_data.get("end_hour", 21),
                        minute=training_data.get("end_min", 0)
                    )
                    now = datetime.datetime.now().time()
                    if now < training_time:
                        days_ago = 7

                training_date = today - datetime.timedelta(days=days_ago)
                return training_date.strftime("%d.%m.%Y")

            return today.strftime("%d.%m.%Y")
        else:
            return training_id.split("_")[0]

    def _should_archive_today(self, training_id: str, actual_date: str) -> bool:
        try:
            training_date = datetime.datetime.strptime(actual_date, "%d.%m.%Y").date()
            today = datetime.datetime.now().date()
            return training_date < today
        except:
            return False

    def _create_archive_entry(self, training_id: str, training_data: Dict[str, Any],
                              votes: Dict[str, Any], actual_date: str) -> Dict[str, Any]:
        return {
            "training_id": training_id,
            "date": actual_date,
            "team": training_data.get("team", "Both"),
            "with_coach": training_data.get("with_coach", False),
            "location": training_data.get("location", "НаУКМА"),
            "description": training_data.get("description", ""),
            "start_time": f"{training_data.get('start_hour', 19):02d}:{training_data.get('start_min', 0):02d}",
            "end_time": f"{training_data.get('end_hour', 21):02d}:{training_data.get('end_min', 0):02d}",
            "votes": votes.copy(),
        }

    def _generate_archive_id(self, archive_data: Dict[str, Any]) -> str:
        if not archive_data:
            return "1"
        return str(max(int(k) for k in archive_data.keys()) + 1)

    def _update_user_statistics(self, votes: Dict[str, Any], training_team: str) -> None:
        users_data = load_data(self.users_file, {})
        updated_count = 0

        for user_id, vote_info in votes.items():
            if user_id not in users_data:
                continue

            user_data = users_data[user_id]
            user_team = user_data.get("team")

            if not self._should_update_user_stats(user_team, training_team):
                continue

            if "training_attendance" not in user_data:
                user_data["training_attendance"] = {"attended": 0, "total": 0, "percentage": 0.0}

            attendance = user_data["training_attendance"]

            if vote_info.get("vote") == "yes":
                attendance["attended"] += 1

            attendance["total"] += 1

            updated_count += 1

        save_data(users_data, self.users_file)
        print(f"✅ Updated statistics for {updated_count} users")

    def _should_update_user_stats(self, user_team: str, training_team: str) -> bool:
        if training_team == "Both":
            return True
        return user_team == training_team

    def get_user_training_history(self, user_id: str, limit: int = 10) -> list:
        archive_data = load_data(self.archive_file, {})
        user_history = []

        for archive_id, entry in archive_data.items():
            if user_id in entry.get("votes", {}):
                vote_info = entry["votes"][user_id]
                user_history.append({
                    "date": entry["date"],
                    "training_id": entry["training_id"],
                    "vote": vote_info.get("vote"),
                    "with_coach": entry.get("with_coach", False),
                    "location": entry.get("location", ""),
                    "description": entry.get("description", "")
                })

        user_history.sort(key=lambda x: datetime.datetime.strptime(x["date"], "%d.%m.%Y"), reverse=True)

        return user_history[:limit]

    def get_training_statistics(self, team: str = "Both", days: int = 30) -> Dict[str, Any]:
        archive_data = load_data(self.archive_file, {})
        cutoff_date = datetime.datetime.now().date() - datetime.timedelta(days=days)

        stats = {
            "total_trainings": 0,
            "with_coach": 0,
            "average_attendance": 0.0,
            "most_active_users": [],
            "attendance_by_date": {}
        }

        user_attendance = {}

        for entry in archive_data.values():
            try:
                entry_date = datetime.datetime.strptime(entry["date"], "%d.%m.%Y").date()
                if entry_date < cutoff_date:
                    continue

                if team != "Both" and entry.get("team") not in [team, "Both"]:
                    continue

                stats["total_trainings"] += 1

                if entry.get("with_coach"):
                    stats["with_coach"] += 1

                yes_votes = 0
                total_votes = 0

                for user_id, vote_info in entry.get("votes", {}).items():
                    total_votes += 1
                    if vote_info.get("vote") == "yes":
                        yes_votes += 1

                        if user_id not in user_attendance:
                            user_attendance[user_id] = {"name": vote_info.get("name", "Unknown"), "attended": 0,
                                                        "total": 0}
                        user_attendance[user_id]["attended"] += 1

                    if user_id in user_attendance:
                        user_attendance[user_id]["total"] += 1

                if total_votes > 0:
                    attendance_rate = (yes_votes / total_votes) * 100
                    stats["attendance_by_date"][entry["date"]] = {
                        "attended": yes_votes,
                        "total": total_votes,
                        "percentage": round(attendance_rate, 1)
                    }

            except Exception as e:
                print(f"Error processing archive entry: {e}")
                continue

        if stats["attendance_by_date"]:
            total_percentage = sum(data["percentage"] for data in stats["attendance_by_date"].values())
            stats["average_attendance"] = round(total_percentage / len(stats["attendance_by_date"]), 1)

        most_active = []
        for user_id, data in user_attendance.items():
            if data["total"] > 0:
                percentage = (data["attended"] / data["total"]) * 100
                most_active.append({
                    "name": data["name"],
                    "attended": data["attended"],
                    "total": data["total"],
                    "percentage": round(percentage, 1)
                })

        most_active.sort(key=lambda x: (x["percentage"], x["attended"]), reverse=True)
        stats["most_active_users"] = most_active[:10]

        return stats


def archive_training_after_charge(training_id: str, training_type: str) -> bool:
    archiver = TrainingVotesArchiver()

    if training_type == "one_time":
        trainings = load_data("one_time_trainings", {})
    else:
        trainings = load_data("constant_trainings", {})

    training_data = None
    for tid, data in trainings.items():
        if training_type == "one_time":
            check_id = f"{data['date']}_{data['start_hour']:02d}:{data['start_min']:02d}"
        else:
            check_id = f"const_{data['weekday']}_{data['start_hour']:02d}:{data['start_min']:02d}"

        if check_id == training_id:
            training_data = data
            break

    if not training_data:
        print(f"❌ Training data not found for {training_id}")
        return False

    return archiver.archive_training_vote(training_id, training_data, force_archive=True)


def enhanced_reset_today_constant_trainings_status():
    now = datetime.datetime.now()
    today = now.date()
    current_time = now.time()

    archiver = TrainingVotesArchiver()
    constant_trainings = load_data("constant_trainings", {})
    votes = load_data("votes", {"votes": {}})
    updated = False

    for tid, training in constant_trainings.items():
        weekday = training.get("weekday")
        if weekday is None:
            continue

        days_ago = (now.weekday() - weekday) % 7
        training_date = today - datetime.timedelta(days=days_ago)

        if training_date > today:
            continue

        training_end_time = datetime.time(hour=training["end_hour"], minute=training["end_min"])
        vote_id = f"const_{weekday}_{training['start_hour']:02d}:{training['start_min']:02d}"

        if training_date == today and current_time >= training_end_time:
            if vote_id in votes["votes"]:
                archiver.archive_training_vote(vote_id, training)

            if training.get("status") != "not charged":
                training["status"] = "not charged"
                updated = True

        if training_date < today:
            if vote_id in votes["votes"]:
                archiver.archive_training_vote(vote_id, training)
                updated = True

    if updated:
        save_data(constant_trainings, "constant_trainings")
        votes = load_data("votes", {"votes": {}})
        save_data(votes, "votes")
        print("✅ Reset statuses and archived finished trainings.")


async def training_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    archiver = TrainingVotesArchiver()

    history = archiver.get_user_training_history(user_id, limit=15)

    if not history:
        await update.message.reply_text("📝 У вас поки що немає історії тренувань.")
        return

    message = "📝 Моя історія тренувань (останні 15):\n\n"

    for entry in history:
        status_emoji = "✅" if entry["vote"] == "yes" else "❌"
        coach_text = " (З тренером)" if entry["with_coach"] else ""

        message += f"{status_emoji} {entry['date']}{coach_text}\n"

        if entry["description"]:
            message += f"   ℹ️ {entry['description']}\n"

        if entry["location"] and entry["location"].lower() != "наукма":
            message += f"   📍 {entry['location']}\n"

        message += "\n"

    await update.message.reply_text(message)


async def detailed_training_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Чоловіча команда", callback_data="detailed_stats_Male"),
            InlineKeyboardButton("Жіноча команда", callback_data="detailed_stats_Female")
        ],
        [InlineKeyboardButton("Всі команди", callback_data="detailed_stats_Both")]
    ])

    await update.message.reply_text(
        "📊 Детальна статистика тренувань (останні 30 днів)\n\nОберіть команду:",
        reply_markup=keyboard
    )


async def handle_detailed_stats_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    team = query.data.replace("detailed_stats_", "")
    archiver = TrainingVotesArchiver()

    stats = archiver.get_training_statistics(team=team, days=30)

    team_name = "чоловічої" if team == "Male" else "жіночої" if team == "Female" else "всіх команд"

    message = f"📊 Статистика тренувань {team_name} (30 днів):\n\n"
    message += f"🏐 Всього тренувань: {stats['total_trainings']}\n"
    message += f" З тренером: {stats['with_coach']}\n"
    message += f"📈 Середня відвідуваність: {stats['average_attendance']}%\n\n"

    if stats['most_active_users']:
        message += "🏆 Топ-5 за відвідуваністю:\n"
        for i, user in enumerate(stats['most_active_users'][:5], 1):
            message += f"{i}. {user['name']}: {user['attended']}/{user['total']} ({user['percentage']}%)\n"

    await query.edit_message_text(message)