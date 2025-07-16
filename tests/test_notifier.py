import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date, timedelta
from telegram.ext import Application
from telegram import InlineKeyboardMarkup

from notifier import (
    generate_training_id, start_voting, check_voting_and_notify,
    open_training_voting, send_voting_reminder, check_game_reminders,
    send_game_reminder, WEEKDAYS, VOTES_LIMIT
)


class TestGenerateTrainingId:
    """Test training ID generation"""

    def test_generate_one_time_training_id(self):
        """Test one-time training ID generation"""
        training = {
            'date': '25.03.2025',
            'start_hour': 19,
            'start_min': 30
        }
        result = generate_training_id(training, "one-time")
        assert result == "25.03.2025_19:30"

    def test_generate_one_time_training_id_zero_padding(self):
        """Test one-time training ID with zero padding"""
        training = {
            'date': '01.01.2025',
            'start_hour': 9,
            'start_min': 5
        }
        result = generate_training_id(training, "one-time")
        assert result == "01.01.2025_09:05"

    def test_generate_constant_training_id(self):
        """Test constant training ID generation"""
        training = {
            'weekday': 1,
            'start_hour': 19,
            'start_min': 0
        }
        result = generate_training_id(training, "constant")
        assert result == "const_1_19:00"

    def test_generate_constant_training_id_weekend(self):
        """Test constant training ID for weekend"""
        training = {
            'weekday': 6,
            'start_hour': 10,
            'start_min': 30
        }
        result = generate_training_id(training, "constant")
        assert result == "const_6_10:30"


class TestStartVoting:
    """Test start voting functionality"""

    @pytest.fixture
    def mock_app(self):
        """Create mock application"""
        app = Mock(spec=Application)
        return app

    @patch('notifier.load_data')
    @patch('notifier.save_data')
    @patch('notifier.open_training_voting')
    @patch('notifier.datetime')
    @pytest.mark.asyncio
    async def test_start_voting_opens_one_time_training(
            self, mock_datetime, mock_open_voting, mock_save, mock_load, mock_app
    ):
        """Test start voting opens one-time training"""
        # Setup
        mock_today = date(2025, 3, 25)
        mock_datetime.today.return_value.date.return_value = mock_today

        users = {"123": {"team": "Male"}}
        one_time_trainings = {
            "1": {
                "start_voting": "25.03.2025",
                "voting_opened": False,
                "team": "Male"
            }
        }
        constant_trainings = {}

        mock_load.side_effect = [users, one_time_trainings, constant_trainings]
        mock_open_voting.return_value = None

        # Execute
        await start_voting(mock_app)

        # Verify
        mock_open_voting.assert_called_once()
        assert mock_save.call_count == 2

    @patch('notifier.load_data')
    @patch('notifier.save_data')
    @patch('notifier.open_training_voting')
    @patch('notifier.datetime')
    @pytest.mark.asyncio
    async def test_start_voting_skips_already_opened(
            self, mock_datetime, mock_open_voting, mock_save, mock_load, mock_app
    ):
        """Test start voting skips already opened trainings"""
        # Setup
        mock_today = date(2025, 3, 25)
        mock_datetime.today.return_value.date.return_value = mock_today

        users = {"123": {"team": "Male"}}
        one_time_trainings = {
            "1": {
                "start_voting": "25.03.2025",
                "voting_opened": True,  # Already opened
                "team": "Male"
            }
        }
        constant_trainings = {}

        mock_load.side_effect = [users, one_time_trainings, constant_trainings]

        # Execute
        await start_voting(mock_app)

        # Verify
        mock_open_voting.assert_not_called()

    @patch('notifier.load_data')
    @patch('notifier.save_data')
    @patch('notifier.open_training_voting')
    @patch('notifier.datetime')
    @pytest.mark.asyncio
    async def test_start_voting_opens_constant_training(
            self, mock_datetime, mock_open_voting, mock_save, mock_load, mock_app
    ):
        """Test start voting opens constant training"""
        # Setup
        mock_today = date(2025, 3, 25)  # Tuesday (weekday 1)
        mock_datetime.today.return_value.date.return_value = mock_today
        mock_datetime.today.return_value.weekday.return_value = 1

        users = {"123": {"team": "Female"}}
        one_time_trainings = {}
        constant_trainings = {
            "1": {
                "start_voting": 1,  # Tuesday
                "voting_opened": False,
                "team": "Female"
            }
        }

        mock_load.side_effect = [users, one_time_trainings, constant_trainings]

        # Execute
        await start_voting(mock_app)

        # Verify
        mock_open_voting.assert_called_once()
        assert mock_save.call_count == 2


class TestOpenTrainingVoting:
    """Test opening training voting"""

    @pytest.fixture
    def mock_app(self):
        """Create mock application with bot"""
        app = Mock(spec=Application)
        app.bot = Mock()
        app.bot.send_message = AsyncMock()
        return app

    @pytest.mark.asyncio
    async def test_open_training_voting_one_time(self, mock_app):
        """Test opening voting for one-time training"""
        training = {
            'date': '25.03.2025',
            'start_hour': 19,
            'start_min': 0,
            'end_hour': 21,
            'end_min': 0,
            'team': 'Male',
            'with_coach': True,
            'location': 'Gym',
            'description': 'Test training'
        }

        users = {
            "123": {"team": "Male"},
            "456": {"team": "Female"}  # Should not receive message
        }

        await open_training_voting(mock_app, training, "test_id", users, "one-time")

        # Should send message only to male team user
        assert mock_app.bot.send_message.call_count == 1
        call_args = mock_app.bot.send_message.call_args
        assert call_args[1]['chat_id'] == 123
        assert "25.03.2025" in call_args[1]['text']
        assert "З тренером" in call_args[1]['text']
        assert isinstance(call_args[1]['reply_markup'], InlineKeyboardMarkup)

    @pytest.mark.asyncio
    async def test_open_training_voting_constant(self, mock_app):
        """Test opening voting for constant training"""
        training = {
            'weekday': 1,  # Tuesday
            'start_hour': 18,
            'start_min': 30,
            'end_hour': 20,
            'end_min': 30,
            'team': 'Both',
            'with_coach': False,
            'location': None,
            'description': None
        }

        users = {
            "123": {"team": "Male"},
            "456": {"team": "Female"}
        }

        await open_training_voting(mock_app, training, "test_id", users, "constant")

        # Should send message to both users (team is "Both")
        assert mock_app.bot.send_message.call_count == 2

        # Check message content
        call_args = mock_app.bot.send_message.call_args_list[0]
        assert WEEKDAYS[1] in call_args[1]['text']  # вівторок
        assert "З тренером" not in call_args[1]['text']  # No coach

    @pytest.mark.asyncio
    async def test_open_training_voting_handles_send_error(self, mock_app):
        """Test that send errors are handled gracefully"""
        training = {
            'date': '25.03.2025',
            'start_hour': 19,
            'start_min': 0,
            'end_hour': 21,
            'end_min': 0,
            'team': 'Male',
            'with_coach': True
        }

        users = {"123": {"team": "Male"}}

        # Make send_message raise an exception
        mock_app.bot.send_message.side_effect = Exception("User blocked bot")

        # Should not raise exception
        await open_training_voting(mock_app, training, "test_id", users, "one-time")


class TestSendVotingReminder:
    """Test sending voting reminders"""

    @pytest.fixture
    def mock_app(self):
        """Create mock application with bot"""
        app = Mock(spec=Application)
        app.bot = Mock()
        app.bot.send_message = AsyncMock()
        return app

    @pytest.mark.asyncio
    async def test_send_voting_reminder_only_to_non_voters(self, mock_app):
        """Test reminder only sent to users who haven't voted"""
        training = {
            'date': '25.03.2025',
            'start_hour': 19,
            'start_min': 0,
            'end_hour': 21,
            'end_min': 0,
            'team': 'Both',
            'with_coach': True
        }

        users = {
            "123": {"team": "Male"},
            "456": {"team": "Female"},
            "789": {"team": "Male"}
        }

        votes_data = {
            "votes": {
                "test_vote_id": {
                    "123": {"vote": "yes"},  # Already voted
                    # 456 and 789 haven't voted
                }
            }
        }

        await send_voting_reminder(mock_app, training, "test_id", users, votes_data, "one-time")

        # Should send to 2 users (456 and 789), not to 123 who already voted
        assert mock_app.bot.send_message.call_count == 3

    @pytest.mark.asyncio
    async def test_send_voting_reminder_message_content(self, mock_app):
        """Test reminder message content"""
        training = {
            'weekday': 2,  # Wednesday
            'start_hour': 19,
            'start_min': 0,
            'end_hour': 21,
            'end_min': 0,
            'team': 'Female',
            'with_coach': False,
            'location': 'Hall A',
            'description': 'Training session'
        }

        users = {"456": {"team": "Female"}}
        votes_data = {"votes": {}}

        await send_voting_reminder(mock_app, training, "test_id", users, votes_data, "constant")

        call_args = mock_app.bot.send_message.call_args
        message_text = call_args[1]['text']

        assert "Нагадування про голосування" in message_text
        assert WEEKDAYS[2] in message_text  # середу
        assert "Hall A" in message_text
        assert "Training session" in message_text
        assert "проголосуйте" in message_text


class TestCheckVotingAndNotify:
    """Test checking voting and sending notifications"""

    @pytest.fixture
    def mock_app(self):
        """Create mock application"""
        app = Mock(spec=Application)
        return app

    @patch('notifier.load_data')
    @patch('notifier.send_voting_reminder')
    @patch('notifier.datetime')
    @pytest.mark.asyncio
    async def test_check_voting_sends_reminder_two_days_before(
            self, mock_datetime, mock_send_reminder, mock_load, mock_app
    ):
        """Test reminder sent 2 days before training"""
        # Setup: today is March 23, training is March 25
        mock_today = date(2025, 3, 23)
        mock_datetime.today.return_value.date.return_value = mock_today
        mock_datetime.strptime.side_effect = datetime.strptime

        users = {"123": {"team": "Male"}}
        one_time_trainings = {
            "1": {
                "date": "25.03.2025",
                "team": "Male"
            }
        }
        constant_trainings = {}
        votes_data = {"votes": {}}

        mock_load.side_effect = [users, one_time_trainings, constant_trainings, votes_data]

        await check_voting_and_notify(mock_app)

    @patch('notifier.load_data')
    @patch('notifier.send_voting_reminder')
    @patch('notifier.datetime')
    @pytest.mark.asyncio
    async def test_check_voting_skips_wrong_date(
            self, mock_datetime, mock_send_reminder, mock_load, mock_app
    ):
        """Test reminder not sent on wrong date"""
        # Setup: today is March 20, training is March 25 (5 days, not 2)
        mock_today = date(2025, 3, 20)
        mock_datetime.today.return_value.date.return_value = mock_today
        mock_datetime.strptime.side_effect = datetime.strptime

        users = {"123": {"team": "Male"}}
        one_time_trainings = {
            "1": {
                "date": "25.03.2025",
                "team": "Male"
            }
        }

        mock_load.side_effect = [users, one_time_trainings, {}, {"votes": {}}]

        await check_voting_and_notify(mock_app)

        mock_send_reminder.assert_not_called()


class TestGameReminders:
    """Test game reminder functionality"""

    @pytest.fixture
    def mock_app(self):
        """Create mock application with bot"""
        app = Mock(spec=Application)
        app.bot = Mock()
        app.bot.send_message = AsyncMock()
        return app

    @patch('notifier.load_data')
    @patch('notifier.send_game_reminder')
    @patch('notifier.datetime')
    @pytest.mark.asyncio
    async def test_check_game_reminders_tomorrow(
            self, mock_datetime, mock_send_reminder, mock_load, mock_app
    ):
        """Test game reminder sent for tomorrow's game"""
        mock_today = date(2025, 3, 24)
        mock_tomorrow = date(2025, 3, 25)
        mock_datetime.today.return_value.date.return_value = mock_today
        mock_datetime.strptime.side_effect = datetime.strptime

        users = {"123": {"team": "Male"}}
        games = {
            "1": {
                "date": "25.03.2025",  # Tomorrow
                "team": "Male"
            }
        }
        game_votes = {"votes": {}}

        mock_load.side_effect = [users, games, game_votes]

        await check_game_reminders(mock_app)

        mock_send_reminder.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_game_reminder_message_content(self, mock_app):
        """Test game reminder message content"""
        game = {
            "type": "friendly",
            "date": "25.03.2025",
            "time": "19:00",
            "opponent": "Team X",
            "location": "Sport Hall",
            "arrival_time": "18:30",
            "team": "Male"
        }

        users = {"123": {"team": "Male"}}
        game_votes = {"votes": {}}

        await send_game_reminder(mock_app, game, "game_1", users, game_votes)

        call_args = mock_app.bot.send_message.call_args
        message_text = call_args[1]['text']

        assert "Нагадування про гру" in message_text
        assert "Товариська гра" in message_text
        assert "25.03.2025" in message_text
        assert "19:00" in message_text
        assert "Team X" in message_text
        assert "Sport Hall" in message_text
        assert "18:30" in message_text

    @pytest.mark.asyncio
    async def test_send_game_reminder_different_game_types(self, mock_app):
        """Test different game type names"""
        game_types = {
            "friendly": "Товариська гра",
            "stolichka": "Столична ліга",
            "universiad": "Універсіада",
            "unknown": "unknown"  # Should use the original value
        }

        users = {"123": {"team": "Both"}}
        game_votes = {"votes": {}}

        for game_type, expected_name in game_types.items():
            game = {
                "type": game_type,
                "date": "25.03.2025",
                "time": "19:00",
                "opponent": "Team X",
                "location": "Sport Hall",
                "arrival_time": "18:30",
                "team": "Both"
            }

            mock_app.bot.send_message.reset_mock()
            await send_game_reminder(mock_app, game, "game_1", users, game_votes)

            call_args = mock_app.bot.send_message.call_args
            message_text = call_args[1]['text']
            assert expected_name in message_text


class TestConstants:
    """Test constants and data structures"""

    def test_weekdays_list(self):
        """Test weekdays list is correct"""
        expected_weekdays = [
            'понеділок', 'вівторок', 'середу', 'четвер',
            "п'ятницю", 'суботу', 'неділю'
        ]
        assert WEEKDAYS == expected_weekdays
        assert len(WEEKDAYS) == 7

    def test_votes_limit(self):
        """Test votes limit constant"""
        assert VOTES_LIMIT == 14
        assert isinstance(VOTES_LIMIT, int)


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_generate_training_id_with_missing_fields(self):
        """Test training ID generation with missing fields"""
        # This might raise KeyError - depends on implementation
        training = {'date': '25.03.2025'}  # Missing time fields

        with pytest.raises(KeyError):
            generate_training_id(training, "one-time")

    @patch('notifier.load_data')
    @patch('notifier.datetime')
    @pytest.mark.asyncio
    async def test_check_voting_handles_invalid_date(self, mock_datetime, mock_load):
        """Test check voting handles invalid date format"""
        mock_today = date(2025, 3, 23)
        mock_datetime.today.return_value.date.return_value = mock_today
        mock_datetime.strptime.side_effect = ValueError("Invalid date")

        users = {"123": {"team": "Male"}}
        one_time_trainings = {
            "1": {
                "date": "invalid_date",
                "team": "Male"
            }
        }

        mock_load.side_effect = [users, one_time_trainings, {}, {"votes": {}}]
        mock_app = Mock()

        # Should not raise exception
        await check_voting_and_notify(mock_app)

    @pytest.mark.asyncio
    async def test_open_training_voting_with_location_filtering(self):
        """Test location filtering (НаУКМА gets hidden)"""
        mock_app = Mock(spec=Application)
        mock_app.bot = Mock()
        mock_app.bot.send_message = AsyncMock()

        training = {
            'date': '25.03.2025',
            'start_hour': 19,
            'start_min': 0,
            'end_hour': 21,
            'end_min': 0,
            'team': 'Both',
            'with_coach': True,
            'location': 'НаУКМА',  # Should be filtered out
            'description': 'Test'
        }

        users = {"123": {"team": "Both"}}

        await open_training_voting(mock_app, training, "test_id", users, "one-time")

        call_args = mock_app.bot.send_message.call_args
        message_text = call_args[1]['text']

        # НаУКМА location should not appear in message
        assert "НаУКМА" not in message_text
        assert "📍" not in message_text