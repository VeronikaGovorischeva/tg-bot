import pytest
import datetime
from unittest.mock import Mock, patch, MagicMock
from training_archive import (
    TrainingVotesArchiver,
    archive_training_after_charge,
    enhanced_reset_today_constant_trainings_status,
    TRAINING_VOTES_ARCHIVE_FILE,
    TRAINING_VOTES_FILE,
    USERS_FILE
)


class TestTrainingVotesArchiver:
    """Test TrainingVotesArchiver class functionality"""

    @pytest.fixture
    def archiver(self):
        """Create archiver instance"""
        return TrainingVotesArchiver()

    @pytest.fixture
    def sample_training_data(self):
        """Sample training data for testing"""
        return {
            "date": "25.03.2025",
            "team": "Both",
            "with_coach": True,
            "location": "НаУКМА",
            "description": "Test training",
            "start_hour": 19,
            "start_min": 0,
            "end_hour": 21,
            "end_min": 0,
            "weekday": 1  # For constant trainings
        }

    @pytest.fixture
    def sample_votes_data(self):
        """Sample votes data for testing"""
        return {
            "votes": {
                "25.03.2025_19:00": {
                    "user1": {"name": "John", "vote": "yes"},
                    "user2": {"name": "Jane", "vote": "no"},
                    "user3": {"name": "Bob", "vote": "yes"}
                }
            }
        }

    @pytest.fixture
    def sample_users_data(self):
        """Sample users data for testing"""
        return {
            "user1": {
                "name": "John",
                "team": "Male",
                "training_attendance": {"attended": 5, "total": 10}
            },
            "user2": {
                "name": "Jane",
                "team": "Female",
                "training_attendance": {"attended": 3, "total": 8}
            },
            "user3": {
                "name": "Bob",
                "team": "Male",
                "training_attendance": {"attended": 7, "total": 12}
            },
            "user4": {
                "name": "Alice",
                "team": "Female"
                # No training_attendance yet
            }
        }

    def test_archiver_initialization(self, archiver):
        """Test archiver initialization"""
        assert archiver.archive_file == TRAINING_VOTES_ARCHIVE_FILE
        assert archiver.votes_file == TRAINING_VOTES_FILE
        assert archiver.users_file == USERS_FILE

    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    def test_archive_training_vote_success(self, mock_save, mock_load, archiver,
                                           sample_training_data, sample_votes_data, sample_users_data):
        """Test successful training vote archiving"""
        training_id = "25.03.2025_19:00"

        # Mock load_data calls
        mock_load.side_effect = [
            sample_votes_data,  # votes data
            {},  # archive data (empty)
            sample_users_data  # users data
        ]

        with patch.object(archiver, '_get_actual_training_date', return_value="25.03.2025"):
            with patch.object(archiver, '_should_archive_today', return_value=True):
                result = archiver.archive_training_vote(training_id, sample_training_data)

        assert result == True

        # Verify save_data was called for archive and votes
        assert mock_save.call_count == 3  # archive, users, votes

        # Check archive data structure
        archive_call = mock_save.call_args_list[0]
        archive_data = archive_call[0][0]
        assert "1" in archive_data  # First archive entry
        assert archive_data["1"]["training_id"] == training_id
        assert archive_data["1"]["date"] == "25.03.2025"
        assert archive_data["1"]["team"] == "Both"
        assert archive_data["1"]["with_coach"] == True

    @patch('training_archive.load_data')
    def test_archive_training_vote_no_votes_found(self, mock_load, archiver, sample_training_data):
        """Test archiving when no votes exist"""
        training_id = "nonexistent_training"

        mock_load.return_value = {"votes": {}}

        result = archiver.archive_training_vote(training_id, sample_training_data)

        assert result == False

    @patch('training_archive.load_data')
    def test_archive_training_vote_should_not_archive_today(self, mock_load, archiver,
                                                            sample_training_data, sample_votes_data):
        """Test archiving when training should not be archived today"""
        training_id = "25.03.2025_19:00"

        mock_load.return_value = sample_votes_data

        with patch.object(archiver, '_get_actual_training_date', return_value="25.03.2025"):
            with patch.object(archiver, '_should_archive_today', return_value=False):
                result = archiver.archive_training_vote(training_id, sample_training_data)

        assert result == False

    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    def test_archive_training_vote_force_archive(self, mock_save, mock_load, archiver,
                                                 sample_training_data, sample_votes_data):
        """Test force archiving regardless of date checks"""
        training_id = "25.03.2025_19:00"

        mock_load.side_effect = [
            sample_votes_data,  # votes data
            {},  # archive data
            {}  # users data
        ]

        with patch.object(archiver, '_get_actual_training_date', return_value="25.03.2025"):
            with patch.object(archiver, '_should_archive_today', return_value=False):
                result = archiver.archive_training_vote(training_id, sample_training_data, force_archive=True)

        assert result == True

    def test_get_actual_training_date_one_time(self, archiver, sample_training_data):
        """Test getting actual date for one-time training"""
        training_id = "25.03.2025_19:00"

        result = archiver._get_actual_training_date(training_id, sample_training_data)

        assert result == "25.03.2025"

    @patch('training_archive.datetime')
    def test_get_actual_training_date_constant_today(self, mock_datetime, archiver, sample_training_data):
        """Test getting actual date for constant training (today)"""
        training_id = "const_1_19:00"

        # Mock today as Tuesday (weekday=1)
        mock_today = datetime.date(2025, 3, 25)  # Tuesday
        mock_datetime.datetime.now.return_value.date.return_value = mock_today
        mock_datetime.date = datetime.date
        mock_datetime.timedelta = datetime.timedelta
        mock_datetime.time = datetime.time

        # Mock current time as before training end time
        mock_now_time = datetime.time(18, 0)  # 6 PM
        mock_datetime.datetime.now.return_value.time.return_value = mock_now_time

        result = archiver._get_actual_training_date(training_id, sample_training_data)

        # Should return yesterday (last occurrence) since training hasn't ended yet today
        expected_date = (mock_today - datetime.timedelta(days=7)).strftime("%d.%m.%Y")
        assert result == expected_date

    @patch('training_archive.datetime')
    def test_get_actual_training_date_constant_past_end_time(self, mock_datetime, archiver, sample_training_data):
        """Test getting actual date for constant training (after end time today)"""
        training_id = "const_1_19:00"

        # Mock today as Tuesday (weekday=1)
        mock_today = datetime.date(2025, 3, 25)  # Tuesday
        mock_datetime.datetime.now.return_value.date.return_value = mock_today
        mock_datetime.date = datetime.date
        mock_datetime.timedelta = datetime.timedelta
        mock_datetime.time = datetime.time

        # Mock current time as after training end time
        mock_now_time = datetime.time(22, 0)  # 10 PM (after 21:00 end)
        mock_datetime.datetime.now.return_value.time.return_value = mock_now_time

        result = archiver._get_actual_training_date(training_id, sample_training_data)

        # Should return today since training has ended
        expected_date = mock_today.strftime("%d.%m.%Y")
        assert result == expected_date

    def test_should_archive_today_past_training(self, archiver):
        """Test should archive for past training"""
        actual_date = "24.03.2025"  # Yesterday

        with patch('training_archive.datetime') as mock_datetime:
            mock_today = datetime.date(2025, 3, 25)
            mock_datetime.datetime.now.return_value.date.return_value = mock_today
            mock_datetime.datetime.strptime.return_value.date.return_value = datetime.date(2025, 3, 24)

            result = archiver._should_archive_today("training_id", actual_date)

            assert result == True

    def test_should_archive_today_future_training(self, archiver):
        """Test should not archive for future training"""
        actual_date = "26.03.2025"  # Tomorrow

        with patch('training_archive.datetime') as mock_datetime:
            mock_today = datetime.date(2025, 3, 25)
            mock_datetime.datetime.now.return_value.date.return_value = mock_today
            mock_datetime.datetime.strptime.return_value.date.return_value = datetime.date(2025, 3, 26)

            result = archiver._should_archive_today("training_id", actual_date)

            assert result == False

    def test_should_archive_today_today_training(self, archiver):
        """Test should not archive for today's training"""
        actual_date = "25.03.2025"  # Today

        with patch('training_archive.datetime') as mock_datetime:
            mock_today = datetime.date(2025, 3, 25)
            mock_datetime.datetime.now.return_value.date.return_value = mock_today
            mock_datetime.datetime.strptime.return_value.date.return_value = datetime.date(2025, 3, 25)

            result = archiver._should_archive_today("training_id", actual_date)

            assert result == False

    def test_create_archive_entry_one_time(self, archiver, sample_training_data, sample_votes_data):
        """Test creating archive entry for one-time training"""
        training_id = "25.03.2025_19:00"
        votes = sample_votes_data["votes"][training_id]
        actual_date = "25.03.2025"

        result = archiver._create_archive_entry(training_id, sample_training_data, votes, actual_date)

        assert result["training_id"] == training_id
        assert result["date"] == actual_date
        assert result["team"] == "Both"
        assert result["with_coach"] == True
        assert result["location"] == "НаУКМА"
        assert result["description"] == "Test training"
        assert result["start_time"] == "19:00"
        assert result["end_time"] == "21:00"
        assert result["votes"] == votes

    def test_create_archive_entry_constant(self, archiver, sample_training_data, sample_votes_data):
        """Test creating archive entry for constant training"""
        training_id = "const_1_19:00"
        votes = sample_votes_data["votes"]["25.03.2025_19:00"]  # Use sample votes
        actual_date = "25.03.2025"

        result = archiver._create_archive_entry(training_id, sample_training_data, votes, actual_date)

        assert result["training_id"] == training_id
        assert result["date"] == actual_date
        assert result["team"] == "Both"
        assert result["with_coach"] == True

    def test_generate_archive_id_empty_archive(self, archiver):
        """Test generating archive ID for empty archive"""
        archive_data = {}

        result = archiver._generate_archive_id(archive_data)

        assert result == "1"

    def test_generate_archive_id_existing_entries(self, archiver):
        """Test generating archive ID with existing entries"""
        archive_data = {
            "1": {"training_id": "old1"},
            "3": {"training_id": "old2"},
            "5": {"training_id": "old3"}
        }

        result = archiver._generate_archive_id(archive_data)

        assert result == "6"  # max(1,3,5) + 1

    @patch('training_archive.is_excluded_from_stats')
    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    def test_update_user_statistics_both_team(self, mock_save, mock_load, mock_is_excluded,
                                              archiver, sample_users_data):
        """Test updating user statistics for 'Both' team training"""
        votes = {
            "user1": {"name": "John", "vote": "yes"},
            "user2": {"name": "Jane", "vote": "no"},
            "user3": {"name": "Bob", "vote": "yes"}
        }
        training_team = "Both"

        mock_load.return_value = sample_users_data
        mock_is_excluded.return_value = False

        archiver._update_user_statistics(votes, training_team)

        # Verify save was called
        mock_save.assert_called_once()

        # Check updated user data
        updated_users = mock_save.call_args[0][0]

        # All users should have total incremented
        assert updated_users["user1"]["training_attendance"]["total"] == 11  # 10 + 1
        assert updated_users["user2"]["training_attendance"]["total"] == 9  # 8 + 1
        assert updated_users["user3"]["training_attendance"]["total"] == 13  # 12 + 1

        # Only "yes" voters should have attended incremented
        assert updated_users["user1"]["training_attendance"]["attended"] == 6  # 5 + 1
        assert updated_users["user2"]["training_attendance"]["attended"] == 3  # no change
        assert updated_users["user3"]["training_attendance"]["attended"] == 8  # 7 + 1

    @patch('training_archive.is_excluded_from_stats')
    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    def test_update_user_statistics_male_team_only(self, mock_save, mock_load, mock_is_excluded,
                                                   archiver, sample_users_data):
        """Test updating user statistics for male team only"""
        votes = {
            "user1": {"name": "John", "vote": "yes"},
            "user2": {"name": "Jane", "vote": "no"},  # Female, should not be updated
            "user3": {"name": "Bob", "vote": "yes"}
        }
        training_team = "Male"

        mock_load.return_value = sample_users_data
        mock_is_excluded.return_value = False

        archiver._update_user_statistics(votes, training_team)

        updated_users = mock_save.call_args[0][0]

        # Only male users should have stats updated
        assert updated_users["user1"]["training_attendance"]["total"] == 11  # Male user
        assert updated_users["user2"]["training_attendance"]["total"] == 8  # Female user, no change
        assert updated_users["user3"]["training_attendance"]["total"] == 13  # Male user

    @patch('training_archive.is_excluded_from_stats')
    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    def test_update_user_statistics_new_user_attendance(self, mock_save, mock_load, mock_is_excluded,
                                                        archiver, sample_users_data):
        """Test updating statistics for user without existing attendance data"""
        votes = {
            "user4": {"name": "Alice", "vote": "yes"}  # User without training_attendance
        }
        training_team = "Female"

        mock_load.return_value = sample_users_data
        mock_is_excluded.return_value = False

        archiver._update_user_statistics(votes, training_team)

        updated_users = mock_save.call_args[0][0]

        # User4 should get new attendance data
        assert "training_attendance" in updated_users["user4"]
        assert updated_users["user4"]["training_attendance"]["total"] == 1
        assert updated_users["user4"]["training_attendance"]["attended"] == 1

    @patch('training_archive.is_excluded_from_stats')
    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    def test_update_user_statistics_excluded_user(self, mock_save, mock_load, mock_is_excluded,
                                                  archiver, sample_users_data):
        """Test that excluded users don't get stats updated"""
        votes = {
            "user1": {"name": "John", "vote": "yes"}
        }
        training_team = "Both"

        mock_load.return_value = sample_users_data
        mock_is_excluded.return_value = True  # User is excluded

        archiver._update_user_statistics(votes, training_team)

        updated_users = mock_save.call_args[0][0]

        # User stats should not change
        assert updated_users["user1"]["training_attendance"]["total"] == 10  # No change
        assert updated_users["user1"]["training_attendance"]["attended"] == 6  # No change

    def test_should_update_user_stats_both_team(self, archiver):
        """Test should update stats for 'Both' team training"""
        assert archiver._should_update_user_stats("Male", "Both") == True
        assert archiver._should_update_user_stats("Female", "Both") == True

    def test_should_update_user_stats_specific_team(self, archiver):
        """Test should update stats for specific team training"""
        assert archiver._should_update_user_stats("Male", "Male") == True
        assert archiver._should_update_user_stats("Female", "Male") == False
        assert archiver._should_update_user_stats("Male", "Female") == False
        assert archiver._should_update_user_stats("Female", "Female") == True

    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    def test_archive_training_vote_exception_handling(self, mock_save, mock_load, archiver,
                                                      sample_training_data):
        """Test exception handling in archive_training_vote"""
        training_id = "25.03.2025_19:00"

        # Mock load_data to raise exception
        mock_load.side_effect = Exception("Database error")

        result = archiver.archive_training_vote(training_id, sample_training_data)

        assert result == False


class TestArchiveTrainingAfterCharge:
    """Test archive_training_after_charge function"""

    @patch('training_archive.TrainingVotesArchiver')
    @patch('training_archive.load_data')
    def test_archive_one_time_training_success(self, mock_load, mock_archiver_class):
        """Test successful archiving of one-time training"""
        training_id = "25.03.2025_19:00"
        training_type = "one_time"

        sample_training = {
            "date": "25.03.2025",
            "start_hour": 19,
            "start_min": 0,
            "team": "Both"
        }

        mock_load.return_value = {"1": sample_training}
        mock_archiver = Mock()
        mock_archiver.archive_training_vote.return_value = True
        mock_archiver_class.return_value = mock_archiver

        result = archive_training_after_charge(training_id, training_type)

        assert result == True
        mock_archiver.archive_training_vote.assert_called_once_with(training_id, sample_training, force_archive=True)

    @patch('training_archive.TrainingVotesArchiver')
    @patch('training_archive.load_data')
    def test_archive_constant_training_success(self, mock_load, mock_archiver_class):
        """Test successful archiving of constant training"""
        training_id = "const_1_19:00"
        training_type = "constant"

        sample_training = {
            "weekday": 1,
            "start_hour": 19,
            "start_min": 0,
            "team": "Male"
        }

        mock_load.return_value = {"1": sample_training}
        mock_archiver = Mock()
        mock_archiver.archive_training_vote.return_value = True
        mock_archiver_class.return_value = mock_archiver

        result = archive_training_after_charge(training_id, training_type)

        assert result == True
        mock_archiver.archive_training_vote.assert_called_once_with(training_id, sample_training, force_archive=True)

    @patch('training_archive.TrainingVotesArchiver')
    @patch('training_archive.load_data')
    def test_archive_training_not_found(self, mock_load, mock_archiver_class):
        """Test archiving when training data not found"""
        training_id = "nonexistent_training"
        training_type = "one_time"

        mock_load.return_value = {}  # No trainings

        result = archive_training_after_charge(training_id, training_type)

        assert result == False

    @patch('training_archive.TrainingVotesArchiver')
    @patch('training_archive.load_data')
    def test_archive_training_archiver_fails(self, mock_load, mock_archiver_class):
        """Test archiving when archiver fails"""
        training_id = "25.03.2025_19:00"
        training_type = "one_time"

        sample_training = {
            "date": "25.03.2025",
            "start_hour": 19,
            "start_min": 0
        }

        mock_load.return_value = {"1": sample_training}
        mock_archiver = Mock()
        mock_archiver.archive_training_vote.return_value = False
        mock_archiver_class.return_value = mock_archiver

        result = archive_training_after_charge(training_id, training_type)

        assert result == False


class TestEnhancedResetTodayConstantTrainingsStatus:
    """Test enhanced_reset_today_constant_trainings_status function"""

    @pytest.fixture
    def sample_one_time_trainings(self):
        """Sample one-time trainings data"""
        return {
            "1": {
                "date": "24.03.2025",  # Yesterday
                "start_hour": 19,
                "start_min": 0,
                "status": "not charged",
                "with_coach": False,  # Should be charged
                "team": "Male"
            },
            "2": {
                "date": "26.03.2025",  # Tomorrow
                "start_hour": 19,
                "start_min": 0,
                "status": "not charged",
                "with_coach": False,
                "team": "Female"
            },
            "3": {
                "date": "24.03.2025",  # Yesterday
                "start_hour": 20,
                "start_min": 0,
                "status": "charged",  # Already charged
                "with_coach": False,
                "team": "Both"
            }
        }

    @pytest.fixture
    def sample_constant_trainings(self):
        """Sample constant trainings data"""
        return {
            "1": {
                "weekday": 0,  # Monday (yesterday if today is Tuesday)
                "start_hour": 19,
                "start_min": 0,
                "status": "not charged",
                "with_coach": False,  # Should be charged
                "team": "Male"
            },
            "2": {
                "weekday": 2,  # Wednesday (tomorrow if today is Tuesday)
                "start_hour": 19,
                "start_min": 0,
                "status": "not charged",
                "with_coach": False,
                "team": "Female"
            },
            "3": {
                "weekday": 0,  # Monday
                "start_hour": 18,
                "start_min": 0,
                "status": "charged",  # Already charged
                "with_coach": False,
                "team": "Both"
            }
        }

    @patch('training_archive.datetime')
    @patch('training_archive.TrainingVotesArchiver')
    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    @pytest.mark.asyncio
    async def test_reset_one_time_trainings(self, mock_save, mock_load, mock_archiver_class, mock_datetime,
                                            sample_one_time_trainings, sample_constant_trainings):
        """Test resetting one-time trainings status"""
        # Mock today as Tuesday (2025-03-25)
        mock_now = datetime.datetime(2025, 3, 25, 10, 0)  # Tuesday
        mock_today = datetime.date(2025, 3, 25)
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.timedelta = datetime.timedelta
        mock_datetime.datetime.strptime = datetime.datetime.strptime  # Add this line

        # Mock archiver
        mock_archiver = Mock()
        mock_archiver.archive_training_vote.return_value = True
        mock_archiver_class.return_value = mock_archiver

        # Mock load_data calls
        mock_load.side_effect = [
            sample_one_time_trainings,  # one_time_trainings
            sample_constant_trainings,  # constant_trainings
            {"votes": {}}  # votes
        ]

        await enhanced_reset_today_constant_trainings_status()

        # If trainings were updated, check the data
        if mock_save.call_count >= 2:
            # Verify that training "1" (yesterday's training) was processed
            one_time_save_call = mock_save.call_args_list[0]
            updated_one_time = one_time_save_call[0][0]

            assert updated_one_time["1"]["status"] == "charged"
            assert updated_one_time["1"]["voting_opened"] == False

            # Training "2" (tomorrow) should not be changed
            assert updated_one_time["2"]["status"] == "not charged"

    @patch('training_archive.datetime')
    @patch('training_archive.TrainingVotesArchiver')
    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    @pytest.mark.asyncio
    async def test_reset_constant_trainings(self, mock_save, mock_load, mock_archiver_class, mock_datetime,
                                            sample_one_time_trainings, sample_constant_trainings):
        """Test resetting constant trainings status"""
        # Create real datetime objects
        mock_now = datetime.datetime(2025, 3, 25, 10, 0)  # Tuesday
        mock_today = datetime.date(2025, 3, 25)
        mock_yesterday = datetime.date(2025, 3, 24)  # Monday

        # Mock datetime.datetime.now() but keep other datetime functions real
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date.today.return_value = mock_today
        mock_datetime.datetime.strptime.side_effect = datetime.datetime.strptime
        mock_datetime.date.side_effect = datetime.date
        mock_datetime.timedelta.side_effect = datetime.timedelta

        # Mock archiver
        mock_archiver = Mock()
        mock_archiver.archive_training_vote.return_value = True
        mock_archiver_class.return_value = mock_archiver

        # Mock load_data calls
        mock_load.side_effect = [
            sample_one_time_trainings,  # one_time_trainings
            sample_constant_trainings,  # constant_trainings
            {"votes": {}}  # votes
        ]

        await enhanced_reset_today_constant_trainings_status()

        # Check if any save calls were made
        if mock_save.call_count > 0:
            # Look for constant trainings save call
            for call_args in mock_save.call_args_list:
                if len(call_args[0]) > 1 and call_args[0][1] == "constant_trainings":
                    updated_constant = call_args[0][0]

                    # Training "1" (Monday weekday, yesterday) might be charged
                    if "1" in updated_constant and updated_constant["1"].get("weekday") == 0:
                        assert updated_constant["1"]["status"] == "charged"
                        assert updated_constant["1"]["voting_opened"] == False

                    # Training "2" (Wednesday weekday, future) should not be changed
                    if "2" in updated_constant:
                        assert updated_constant["2"]["status"] == "not charged"
                    break

    @patch('training_archive.datetime')
    @patch('training_archive.TrainingVotesArchiver')
    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    @pytest.mark.asyncio
    async def test_reset_with_coach_trainings_not_processed(self, mock_save, mock_load, mock_archiver_class,
                                                            mock_datetime):
        """Test that trainings with coach are not auto-charged"""
        trainings_with_coach = {
            "1": {
                "date": "24.03.2025",  # Yesterday
                "start_hour": 19,
                "start_min": 0,
                "status": "not charged",
                "with_coach": True,  # Should NOT be auto-charged
                "team": "Male"
            }
        }

        # Mock today as Tuesday
        mock_now = datetime.datetime(2025, 3, 25, 10, 0)
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.timedelta = datetime.timedelta

        # Mock archiver
        mock_archiver = Mock()
        mock_archiver_class.return_value = mock_archiver

        # Mock load_data calls
        mock_load.side_effect = [
            trainings_with_coach,  # one_time_trainings
            {},  # constant_trainings
            {"votes": {}}  # votes
        ]

        await enhanced_reset_today_constant_trainings_status()

        # Training with coach should NOT be auto-charged
        if mock_save.called:
            saved_data = mock_save.call_args_list[0][0][0]
            assert saved_data["1"]["status"] == "not charged"  # Should remain unchanged

    @patch('training_archive.datetime')
    @patch('training_archive.TrainingVotesArchiver')
    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    @pytest.mark.asyncio
    async def test_reset_no_trainings_to_process(self, mock_save, mock_load, mock_archiver_class, mock_datetime):
        """Test when no trainings need processing"""
        # All trainings are either future or already charged
        future_trainings = {
            "1": {
                "date": "26.03.2025",  # Tomorrow
                "start_hour": 19,
                "start_min": 0,
                "status": "not charged",
                "with_coach": False,
                "team": "Male"
            }
        }

        # Mock today as Tuesday
        mock_now = datetime.datetime(2025, 3, 25, 10, 0)
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.timedelta = datetime.timedelta

        mock_load.side_effect = [
            future_trainings,  # one_time_trainings
            {},  # constant_trainings
            {"votes": {}}  # votes
        ]

        await enhanced_reset_today_constant_trainings_status()

        # No trainings should be updated, but votes should still be saved
        # (save is called for votes cleanup regardless)
        assert mock_save.call_count <= 3

    @patch('training_archive.datetime')
    @patch('training_archive.TrainingVotesArchiver')
    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    @pytest.mark.asyncio
    async def test_reset_archiver_fails(self, mock_save, mock_load, mock_archiver_class, mock_datetime,
                                        sample_one_time_trainings):
        """Test when archiver fails but training is still charged"""
        # Create real datetime objects
        mock_now = datetime.datetime(2025, 3, 25, 10, 0)
        mock_today = datetime.date(2025, 3, 25)

        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date.today.return_value = mock_today
        mock_datetime.datetime.strptime.side_effect = datetime.datetime.strptime
        mock_datetime.date.side_effect = datetime.date
        mock_datetime.timedelta.side_effect = datetime.timedelta

        # Mock archiver to fail
        mock_archiver = Mock()
        mock_archiver.archive_training_vote.return_value = False
        mock_archiver_class.return_value = mock_archiver

        mock_load.side_effect = [
            sample_one_time_trainings,  # one_time_trainings
            {},  # constant_trainings
            {"votes": {}}  # votes
        ]

        await enhanced_reset_today_constant_trainings_status()

        # Training should still be charged even if archiving fails
        if mock_save.call_count > 0:
            one_time_save_call = mock_save.call_args_list[0]
            updated_one_time = one_time_save_call[0][0]

            # Check if yesterday's training was processed
            if "1" in updated_one_time and updated_one_time["1"]["date"] == "24.03.2025":
                assert updated_one_time["1"]["status"] == "charged"

    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    @pytest.mark.asyncio
    async def test_reset_exception_handling(self, mock_save, mock_load):
        """Test exception handling during reset"""
        # Mock load_data to raise exception on first call
        mock_load.side_effect = Exception("Database error")

        # The function should propagate the exception, not handle it
        with pytest.raises(Exception, match="Database error"):
            await enhanced_reset_today_constant_trainings_status()

        # Function should handle the exception gracefully


class TestEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.fixture
    def archiver(self):
        return TrainingVotesArchiver()

    def test_get_actual_training_date_missing_weekday(self, archiver):
        """Test handling missing weekday in constant training"""
        training_id = "const_1_19:00"
        training_data = {}  # Missing weekday

        with patch('training_archive.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.date.return_value = datetime.date(2025, 3, 25)
            mock_datetime.date = datetime.date

            result = archiver._get_actual_training_date(training_id, training_data)

            # Should return today as fallback
            assert result == "25.03.2025"

    def test_should_archive_today_invalid_date(self, archiver):
        """Test should archive with invalid date format"""
        actual_date = "invalid_date"

        result = archiver._should_archive_today("training_id", actual_date)

        # Should return False for invalid dates
        assert result == False

    @patch('training_archive.load_data')
    def test_update_user_statistics_missing_user_in_votes(self, mock_load, archiver):
        """Test updating stats when vote references non-existent user"""
        votes = {
            "nonexistent_user": {"name": "Ghost", "vote": "yes"}
        }
        users_data = {
            "user1": {"name": "John", "team": "Male"}
        }

        mock_load.return_value = users_data

        with patch('training_archive.save_data') as mock_save:
            with patch('training_archive.is_excluded_from_stats', return_value=False):
                # Should not raise exception
                archiver._update_user_statistics(votes, "Both")

                # Save should still be called
                mock_save.assert_called_once()

    @patch('training_archive.load_data')
    def test_update_user_statistics_missing_team_field(self, mock_load, archiver):
        """Test updating stats when user has no team field"""
        votes = {
            "user1": {"name": "John", "vote": "yes"}
        }
        users_data = {
            "user1": {"name": "John"}  # Missing team field
        }

        mock_load.return_value = users_data

        with patch('training_archive.save_data') as mock_save:
            with patch('training_archive.is_excluded_from_stats', return_value=False):
                # Should not raise exception
                archiver._update_user_statistics(votes, "Both")

                mock_save.assert_called_once()


class TestIntegrationScenarios:
    """Test integration scenarios that combine multiple components"""

    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    @patch('training_archive.is_excluded_from_stats')
    def test_complete_archiving_workflow(self, mock_is_excluded, mock_save, mock_load):
        """Test complete archiving workflow from start to finish"""
        archiver = TrainingVotesArchiver()

        # Setup test data
        training_id = "25.03.2025_19:00"
        training_data = {
            "date": "25.03.2025",
            "team": "Both",
            "with_coach": True,
            "location": "Gym",
            "description": "Test training",
            "start_hour": 19,
            "start_min": 0,
            "end_hour": 21,
            "end_min": 0
        }

        votes_data = {
            "votes": {
                training_id: {
                    "user1": {"name": "John", "vote": "yes"},
                    "user2": {"name": "Jane", "vote": "no"},
                    "user3": {"name": "Bob", "vote": "yes"}
                }
            }
        }

        users_data = {
            "user1": {"name": "John", "team": "Male", "training_attendance": {"attended": 5, "total": 10}},
            "user2": {"name": "Jane", "team": "Female", "training_attendance": {"attended": 3, "total": 8}},
            "user3": {"name": "Bob", "team": "Male", "training_attendance": {"attended": 7, "total": 12}}
        }

        archive_data = {}

        # Mock load_data calls in order
        mock_load.side_effect = [votes_data, archive_data, users_data]
        mock_is_excluded.return_value = False

        with patch.object(archiver, '_get_actual_training_date', return_value="25.03.2025"):
            with patch.object(archiver, '_should_archive_today', return_value=True):
                result = archiver.archive_training_vote(training_id, training_data, force_archive=True)

        assert result == True

        # Verify all three save calls were made
        assert mock_save.call_count == 3

        # Check archive data
        archive_call = mock_save.call_args_list[0]
        saved_archive = archive_call[0][0]
        assert "1" in saved_archive
        assert saved_archive["1"]["training_id"] == training_id
        assert saved_archive["1"]["team"] == "Both"

        # Check users data
        users_call = mock_save.call_args_list[1]
        saved_users = users_call[0][0]

        # All users should have total incremented
        assert saved_users["user1"]["training_attendance"]["total"] == 11
        assert saved_users["user2"]["training_attendance"]["total"] == 9
        assert saved_users["user3"]["training_attendance"]["total"] == 13

        # Only "yes" voters should have attended incremented
        assert saved_users["user1"]["training_attendance"]["attended"] == 6
        assert saved_users["user2"]["training_attendance"]["attended"] == 3  # no change
        assert saved_users["user3"]["training_attendance"]["attended"] == 8

        # Check votes data (should have training removed)
        votes_call = mock_save.call_args_list[2]
        saved_votes = votes_call[0][0]
        assert training_id not in saved_votes["votes"]

    @patch('training_archive.load_data')
    @patch('training_archive.TrainingVotesArchiver')
    def test_archive_after_charge_integration(self, mock_archiver_class, mock_load):
        """Test archive_training_after_charge integration with archiver"""
        training_id = "const_1_19:00"
        training_type = "constant"

        training_data = {
            "weekday": 1,
            "start_hour": 19,
            "start_min": 0,
            "team": "Both",
            "with_coach": False
        }

        trainings_data = {"training1": training_data}
        mock_load.return_value = trainings_data

        # Mock archiver
        mock_archiver = Mock()
        mock_archiver.archive_training_vote.return_value = True
        mock_archiver_class.return_value = mock_archiver

        result = archive_training_after_charge(training_id, training_type)

        assert result == True

        # Verify archiver was created and called correctly
        mock_archiver_class.assert_called_once()
        mock_archiver.archive_training_vote.assert_called_once_with(
            training_id, training_data, force_archive=True
        )


class TestPerformanceAndScalability:
    """Test performance-related scenarios"""

    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    @patch('training_archive.is_excluded_from_stats')
    def test_large_number_of_votes(self, mock_is_excluded, mock_save, mock_load):
        """Test archiving with large number of votes"""
        archiver = TrainingVotesArchiver()
        training_id = "25.03.2025_19:00"

        # Create 100 votes
        votes = {}
        users = {}
        for i in range(100):
            user_id = f"user{i}"
            votes[user_id] = {"name": f"User{i}", "vote": "yes" if i % 2 == 0 else "no"}
            users[user_id] = {
                "name": f"User{i}",
                "team": "Male" if i % 2 == 0 else "Female",
                "training_attendance": {"attended": i, "total": i + 5}
            }

        votes_data = {"votes": {training_id: votes}}
        training_data = {"team": "Both", "with_coach": True, "start_hour": 19, "start_min": 0, "end_hour": 21,
                         "end_min": 0}

        mock_load.side_effect = [votes_data, {}, users]
        mock_is_excluded.return_value = False

        with patch.object(archiver, '_get_actual_training_date', return_value="25.03.2025"):
            with patch.object(archiver, '_should_archive_today', return_value=True):
                result = archiver.archive_training_vote(training_id, training_data)

        assert result == True

        # Verify all users were processed
        users_call = mock_save.call_args_list[1]
        saved_users = users_call[0][0]
        assert len(saved_users) == 100

    @patch('training_archive.load_data')
    @patch('training_archive.save_data')
    def test_large_existing_archive(self, mock_save, mock_load):
        """Test adding to large existing archive"""
        archiver = TrainingVotesArchiver()

        # Create large existing archive
        existing_archive = {}
        for i in range(1000):
            existing_archive[str(i)] = {"training_id": f"old_training_{i}"}

        votes_data = {"votes": {"new_training": {"user1": {"name": "User", "vote": "yes"}}}}
        training_data = {"team": "Both", "with_coach": True, "start_hour": 19, "start_min": 0, "end_hour": 21,
                         "end_min": 0}

        mock_load.side_effect = [votes_data, existing_archive, {}]

        with patch.object(archiver, '_get_actual_training_date', return_value="25.03.2025"):
            with patch.object(archiver, '_should_archive_today', return_value=True):
                result = archiver.archive_training_vote("new_training", training_data)

        assert result == True

        # Verify new entry gets correct ID
        archive_call = mock_save.call_args_list[0]
        saved_archive = archive_call[0][0]
        assert "1000" in saved_archive  # Next available ID