import datetime
from typing import Dict, Any
from data import load_data, save_data
from validation import is_excluded_from_stats

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

        for user_id, user_data in users_data.items():
            if is_excluded_from_stats(user_id):
                continue
            user_team = user_data.get("team")

            if not self._should_update_user_stats(user_team, training_team):
                continue

            if "training_attendance" not in user_data:
                user_data["training_attendance"] = {"attended": 0, "total": 0}

            user_data["training_attendance"]["total"] += 1

        for user_id, vote_info in votes.items():
            if user_id not in users_data:
                continue

            user_data = users_data[user_id]
            user_team = user_data.get("team")

            if not self._should_update_user_stats(user_team, training_team):
                continue

            if vote_info.get("vote") == "yes":
                user_data["training_attendance"]["attended"] += 1

        save_data(users_data, self.users_file)

    def _should_update_user_stats(self, user_team: str, training_team: str) -> bool:
        if training_team == "Both":
            return True
        return user_team == training_team


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


async def enhanced_reset_today_constant_trainings_status():
    now = datetime.datetime.now()
    today = now.date()

    archiver = TrainingVotesArchiver()
    one_time_trainings = load_data("one_time_trainings", {})
    constant_trainings = load_data("constant_trainings", {})
    updated = False

    for tid, training in one_time_trainings.items():
        if training.get("status") != "not charged":
            continue

        try:
            training_date = datetime.datetime.strptime(training['date'], "%d.%m.%Y").date()
            if training_date < today:
                training_id = f"{training['date']}_{training['start_hour']:02d}:{training['start_min']:02d}"

                archive_success = archiver.archive_training_vote(training_id, training, force_archive=True)
                if archive_success:
                    print(f"✅ Archived one-time training {training_id}")

                training["status"] = "charged"
                training["voting_opened"] = False
                updated = True
                print(f"✅ Auto-charged one-time training {training_id} (no payment required)")

        except Exception as e:
            print(f"❌ Error processing one-time training {tid}: {e}")
            continue

    for tid, training in constant_trainings.items():
        if training.get("status") != "not charged" or not training.get("with_coach"):
            continue

        weekday = training.get("weekday")
        if weekday is None:
            continue

        yesterday = today - datetime.timedelta(days=1)
        days_ago = (yesterday.weekday() - weekday) % 7
        training_date = yesterday - datetime.timedelta(days=days_ago)

        if training_date == yesterday:
            training_id = f"const_{weekday}_{training['start_hour']:02d}:{training['start_min']:02d}"

            archive_success = archiver.archive_training_vote(training_id, training, force_archive=True)
            if archive_success:
                print(f"✅ Archived constant training {training_id}")

            training["status"] = "charged"
            training["voting_opened"] = False
            updated = True
            print(f"✅ Auto-charged constant training {training_id} (no payment required)")

    if updated:
        save_data(one_time_trainings, "one_time_trainings")
        save_data(constant_trainings, "constant_trainings")

        votes = load_data("votes", {"votes": {}})
        save_data(votes, "votes")

        print("✅ Auto-charged all completed trainings with coach (no payments created)")
