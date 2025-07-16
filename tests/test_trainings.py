import pytest
import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from telegram import Update, User, Message, CallbackQuery, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from trainings import (
    TrainingType, Team, TimeValidator, VotingType,
    add_training, training_type, training_team, training_coach,
    training_location, training_description, training_date,
    training_weekday, training_start, training_end, training_start_voting,
    save_training_data, open_onetime_training_voting_immediately,
    get_next_training, get_next_week_trainings, next_training, week_trainings,
    format_next_training_message, cancel,
    create_training_type_keyboard, create_team_keyboard, create_coach_keyboard,
    create_weekday_keyboard, create_voting_day_keyboard,
    create_training_add_handler, MESSAGES,
    TYPE, TEAM, COACH, LOCATION, DESCRIPTION, DATE, START, END, WEEKDAY, START_VOTING,
    ONE_TIME_TRAININGS_FILE, CONSTANT_TRAININGS_FILE
)


class TestTrainingCreation:
    """Test training creation workflow"""

    @pytest.fixture
    def mock_update(self):
        """Create mock update object"""
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.from_user = Mock(spec=User)
        update.message.from_user.id = 12345
        update.message.text = "Test input"
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_callback_query_update(self):
        """Create mock update with callback query"""
        update = Mock(spec=Update)
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.from_user = Mock(spec=User)
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "test_data"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Create mock context object"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context

    @patch('trainings.is_authorized')
    @pytest.mark.asyncio
    async def test_add_training_authorized_user(self, mock_is_authorized, mock_update, mock_context):
        """Test /add_training with authorized user"""
        mock_is_authorized.return_value = True

        result = await add_training(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert MESSAGES["select_type"] in call_args[0][0]
        assert isinstance(call_args[1]["reply_markup"], InlineKeyboardMarkup)
        assert result == TYPE

    @patch('trainings.is_authorized')
    @pytest.mark.asyncio
    async def test_add_training_unauthorized_user(self, mock_is_authorized, mock_update, mock_context):
        """Test /add_training with unauthorized user"""
        mock_is_authorized.return_value = False

        result = await add_training(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(MESSAGES["unauthorized"])
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_training_type_onetime(self, mock_callback_query_update, mock_context):
        """Test training type selection - one-time"""
        mock_callback_query_update.callback_query.data = TrainingType.ONE_TIME.value

        result = await training_type(mock_callback_query_update, mock_context)

        assert mock_context.user_data['training_type'] == TrainingType.ONE_TIME.value
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        assert result == TEAM

    @pytest.mark.asyncio
    async def test_training_type_recurring(self, mock_callback_query_update, mock_context):
        """Test training type selection - recurring"""
        mock_callback_query_update.callback_query.data = TrainingType.RECURRING.value

        result = await training_type(mock_callback_query_update, mock_context)

        assert mock_context.user_data['training_type'] == TrainingType.RECURRING.value
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        assert result == TEAM

    @pytest.mark.asyncio
    async def test_training_team_male(self, mock_callback_query_update, mock_context):
        """Test team selection - male"""
        mock_callback_query_update.callback_query.data = "training_team_male"

        result = await training_team(mock_callback_query_update, mock_context)

        assert mock_context.user_data['training_team'] == Team.MALE.value
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        assert result == COACH

    @pytest.mark.asyncio
    async def test_training_team_female(self, mock_callback_query_update, mock_context):
        """Test team selection - female"""
        mock_callback_query_update.callback_query.data = "training_team_female"

        result = await training_team(mock_callback_query_update, mock_context)

        assert mock_context.user_data['training_team'] == Team.FEMALE.value
        assert result == COACH

    @pytest.mark.asyncio
    async def test_training_team_both(self, mock_callback_query_update, mock_context):
        """Test team selection - both teams"""
        mock_callback_query_update.callback_query.data = "training_team_both"

        result = await training_team(mock_callback_query_update, mock_context)

        assert mock_context.user_data['training_team'] == Team.BOTH.value
        assert result == COACH

    @pytest.mark.asyncio
    async def test_training_coach_yes(self, mock_callback_query_update, mock_context):
        """Test coach selection - with coach"""
        mock_callback_query_update.callback_query.data = "training_coach_yes"

        result = await training_coach(mock_callback_query_update, mock_context)

        assert mock_context.user_data['with_coach'] == True
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once_with(MESSAGES["enter_location"])
        assert result == LOCATION

    @pytest.mark.asyncio
    async def test_training_coach_no(self, mock_callback_query_update, mock_context):
        """Test coach selection - without coach"""
        mock_callback_query_update.callback_query.data = "training_coach_no"

        result = await training_coach(mock_callback_query_update, mock_context)

        assert mock_context.user_data['with_coach'] == False
        assert result == LOCATION

    @pytest.mark.asyncio
    async def test_training_location_with_location(self, mock_update, mock_context):
        """Test location input with actual location"""
        mock_update.message.text = "Sport Complex"

        result = await training_location(mock_update, mock_context)

        assert mock_context.user_data['training_location'] == "Sport Complex"
        mock_update.message.reply_text.assert_called_once_with(MESSAGES["enter_description"])
        assert result == DESCRIPTION

    @pytest.mark.asyncio
    async def test_training_location_default(self, mock_update, mock_context):
        """Test location input with default (-)"""
        mock_update.message.text = "-"

        result = await training_location(mock_update, mock_context)

        assert mock_context.user_data['training_location'] is None
        assert result == DESCRIPTION

    @pytest.mark.asyncio
    async def test_training_description_with_description(self, mock_update, mock_context):
        """Test description input with actual description"""
        mock_context.user_data['training_type'] = TrainingType.ONE_TIME.value
        mock_update.message.text = "Training description"

        result = await training_description(mock_update, mock_context)

        assert mock_context.user_data['training_description'] == "Training description"
        mock_update.message.reply_text.assert_called_once_with(MESSAGES["enter_date"])
        assert result == DATE

    @pytest.mark.asyncio
    async def test_training_description_default_onetime(self, mock_update, mock_context):
        """Test description input with default (-) for one-time training"""
        mock_context.user_data['training_type'] = TrainingType.ONE_TIME.value
        mock_update.message.text = "-"

        result = await training_description(mock_update, mock_context)

        assert mock_context.user_data['training_description'] is None
        assert result == DATE

    @pytest.mark.asyncio
    async def test_training_description_recurring(self, mock_update, mock_context):
        """Test description input for recurring training"""
        mock_context.user_data['training_type'] = TrainingType.RECURRING.value
        mock_update.message.text = "Regular training"

        result = await training_description(mock_update, mock_context)

        assert mock_context.user_data['training_description'] == "Regular training"
        mock_update.message.reply_text.assert_called_once()
        assert result == WEEKDAY


class TestTimeValidation:
    """Test time validation functionality"""

    def test_validate_date_valid_format(self):
        """Test date validation with valid format"""
        valid, date_obj = TimeValidator.validate_date("25.03.2025")

        assert valid == True
        assert date_obj == datetime.date(2025, 3, 25)

    def test_validate_date_invalid_format(self):
        """Test date validation with invalid format"""
        valid, date_obj = TimeValidator.validate_date("25/03/2025")

        assert valid == False
        assert date_obj is None

    def test_validate_date_invalid_date(self):
        """Test date validation with invalid date"""
        valid, date_obj = TimeValidator.validate_date("32.13.2025")

        assert valid == False
        assert date_obj is None

    def test_validate_date_leap_year(self):
        """Test date validation with leap year"""
        valid, date_obj = TimeValidator.validate_date("29.02.2024")

        assert valid == True
        assert date_obj == datetime.date(2024, 2, 29)

    def test_validate_date_non_leap_year(self):
        """Test date validation with non-leap year"""
        valid, date_obj = TimeValidator.validate_date("29.02.2023")

        assert valid == False
        assert date_obj is None

    def test_validate_time_valid_format(self):
        """Test time validation with valid format"""
        valid, time_tuple = TimeValidator.validate_time("19:30")

        assert valid == True
        assert time_tuple == (19, 30)

    def test_validate_time_invalid_format(self):
        """Test time validation with invalid format"""
        valid, time_tuple = TimeValidator.validate_time("19-30")

        assert valid == False
        assert time_tuple is None

    def test_validate_time_invalid_hour(self):
        """Test time validation with invalid hour"""
        valid, time_tuple = TimeValidator.validate_time("25:30")

        assert valid == False
        assert time_tuple is None

    def test_validate_time_invalid_minute(self):
        """Test time validation with invalid minute"""
        valid, time_tuple = TimeValidator.validate_time("19:70")

        assert valid == False
        assert time_tuple is None


class TestTrainingDateTimeHandling:
    """Test date and time input handling"""

    @pytest.fixture
    def mock_update(self):
        """Create mock update object"""
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_callback_query_update(self):
        """Create mock update with callback query"""
        update = Mock(spec=Update)
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.from_user = Mock(spec=User)
        update.callback_query.from_user.id = 12345
        update.callback_query.data = "test_data"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Create mock context object"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_training_date_valid(self, mock_update, mock_context):
        """Test training date with valid date"""
        mock_update.message.text = "25.03.2025"

        result = await training_date(mock_update, mock_context)

        assert mock_context.user_data['training_date'] == "25.03.2025"
        mock_update.message.reply_text.assert_called_once_with(MESSAGES["enter_start_time"])
        assert result == START

    @pytest.mark.asyncio
    async def test_training_date_invalid(self, mock_update, mock_context):
        """Test training date with invalid date"""
        mock_update.message.text = "invalid_date"

        result = await training_date(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(MESSAGES["invalid_date"])
        assert result == DATE

    @pytest.mark.asyncio
    async def test_training_weekday_selection(self, mock_callback_query_update, mock_context):
        """Test weekday selection for recurring training"""
        mock_callback_query_update.callback_query.data = "weekday_1"  # Tuesday

        result = await training_weekday(mock_callback_query_update, mock_context)

        assert mock_context.user_data['training_weekday'] == 1
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once_with(
            MESSAGES["enter_start_time"])
        assert result == START

    @pytest.mark.asyncio
    async def test_training_start_time_valid(self, mock_update, mock_context):
        """Test start time with valid time"""
        mock_update.message.text = "19:00"

        result = await training_start(mock_update, mock_context)

        assert mock_context.user_data['start_hour'] == 19
        assert mock_context.user_data['start_min'] == 0
        mock_update.message.reply_text.assert_called_once_with(MESSAGES["enter_end_time"])
        assert result == END

    @pytest.mark.asyncio
    async def test_training_start_time_invalid(self, mock_update, mock_context):
        """Test start time with invalid time"""
        mock_update.message.text = "invalid_time"

        result = await training_start(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(MESSAGES["invalid_time"])
        assert result == START

    @pytest.mark.asyncio
    async def test_training_end_time_valid_onetime(self, mock_update, mock_context):
        """Test end time with valid time for one-time training"""
        mock_context.user_data['training_type'] = TrainingType.ONE_TIME.value
        mock_update.message.text = "21:00"

        result = await training_end(mock_update, mock_context)

        assert mock_context.user_data['end_hour'] == 21
        assert mock_context.user_data['end_min'] == 0
        mock_update.message.reply_text.assert_called_once_with(MESSAGES["enter_voting_start_date"])
        assert result == START_VOTING

    @pytest.mark.asyncio
    async def test_training_end_time_valid_recurring(self, mock_update, mock_context):
        """Test end time with valid time for recurring training"""
        mock_context.user_data['training_type'] = TrainingType.RECURRING.value
        mock_update.message.text = "21:00"

        result = await training_end(mock_update, mock_context)

        assert mock_context.user_data['end_hour'] == 21
        assert mock_context.user_data['end_min'] == 0
        mock_update.message.reply_text.assert_called_once()
        assert result == START_VOTING


class TestTrainingRetrieval:
    """Test training retrieval functionality"""

    def setup_method(self):
        """Set up test data"""
        self.male_one_time_training = {
            "date": "25.03.2025",
            "start_hour": 19,
            "start_min": 0,
            "end_hour": 21,
            "end_min": 0,
            "team": "Male",
            "with_coach": True,
            "location": "Sport Hall",
            "description": "Male training"
        }

        self.female_one_time_training = {
            "date": "26.03.2025",
            "start_hour": 18,
            "start_min": 0,
            "end_hour": 20,
            "end_min": 0,
            "team": "Female",
            "with_coach": False,
            "location": "Gym",
            "description": "Female training"
        }

        self.both_one_time_training = {
            "date": "27.03.2025",
            "start_hour": 19,
            "start_min": 30,
            "end_hour": 21,
            "end_min": 30,
            "team": "Both",
            "with_coach": True,
            "location": None,
            "description": "Mixed training"
        }

        self.male_constant_training = {
            "weekday": 1,  # Tuesday
            "start_hour": 19,
            "start_min": 0,
            "end_hour": 21,
            "end_min": 0,
            "team": "Male",
            "with_coach": False,
            "location": "Hall A",
            "description": None
        }

        self.female_constant_training = {
            "weekday": 3,  # Thursday
            "start_hour": 18,
            "start_min": 30,
            "end_hour": 20,
            "end_min": 30,
            "team": "Female",
            "with_coach": True,
            "location": None,
            "description": "Regular training"
        }

        self.both_constant_training = {
            "weekday": 5,  # Saturday
            "start_hour": 10,
            "start_min": 0,
            "end_hour": 12,
            "end_min": 0,
            "team": "Both",
            "with_coach": True,
            "location": "Main Hall",
            "description": "Weekend training"
        }

    @patch('trainings.load_data')
    @patch('trainings.datetime')
    def test_get_next_training_male_team_finds_male_training(self, mock_datetime, mock_load):
        """Test male user finds male-specific training"""
        mock_now = datetime.datetime(2025, 3, 24, 18, 0)  # Monday
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.time = datetime.time
        mock_datetime.timedelta = datetime.timedelta
        mock_datetime.datetime.strptime = datetime.datetime.strptime

        mock_load.side_effect = [
            {"1": self.male_one_time_training},  # one_time_trainings
            {}  # constant_trainings
        ]

        result = get_next_training("Male")

        assert result is not None
        assert result["team"] == "Male"
        assert result["type"] == "one-time"

    @patch('trainings.load_data')
    @patch('trainings.datetime')
    def test_get_next_training_male_team_finds_both_training(self, mock_datetime, mock_load):
        """Test male user finds 'Both' training when no male-specific available"""
        mock_now = datetime.datetime(2025, 3, 24, 18, 0)  # Monday
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.time = datetime.time
        mock_datetime.timedelta = datetime.timedelta
        mock_datetime.datetime.strptime = datetime.datetime.strptime

        mock_load.side_effect = [
            {"1": self.both_one_time_training},  # one_time_trainings
            {}  # constant_trainings
        ]

        result = get_next_training("Male")

        assert result is not None
        assert result["team"] == "Both"
        assert result["type"] == "one-time"

    @patch('trainings.load_data')
    @patch('trainings.datetime')
    def test_get_next_training_female_team_finds_female_training(self, mock_datetime, mock_load):
        """Test female user finds female-specific training"""
        mock_now = datetime.datetime(2025, 3, 24, 18, 0)  # Monday
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.time = datetime.time
        mock_datetime.timedelta = datetime.timedelta
        mock_datetime.datetime.strptime = datetime.datetime.strptime

        mock_load.side_effect = [
            {"1": self.female_one_time_training},  # one_time_trainings
            {}  # constant_trainings
        ]

        result = get_next_training("Female")

        assert result is not None
        assert result["team"] == "Female"
        assert result["type"] == "one-time"

    @patch('trainings.load_data')
    @patch('trainings.datetime')
    def test_get_next_training_female_team_finds_both_training(self, mock_datetime, mock_load):
        """Test female user finds 'Both' training when no female-specific available"""
        mock_now = datetime.datetime(2025, 3, 24, 18, 0)  # Monday
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.time = datetime.time
        mock_datetime.timedelta = datetime.timedelta
        mock_datetime.datetime.strptime = datetime.datetime.strptime

        mock_load.side_effect = [
            {"1": self.both_one_time_training},  # one_time_trainings
            {}  # constant_trainings
        ]

        result = get_next_training("Female")

        assert result is not None
        assert result["team"] == "Both"
        assert result["type"] == "one-time"

    @patch('trainings.load_data')
    @patch('trainings.datetime')
    def test_get_next_training_constant_male(self, mock_datetime, mock_load):
        """Test getting next constant training for male team"""
        mock_now = datetime.datetime(2025, 3, 24, 18, 0)  # Monday
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.time = datetime.time
        mock_datetime.timedelta = datetime.timedelta

        mock_load.side_effect = [
            {},  # one_time_trainings
            {"1": self.male_constant_training}  # constant_trainings (Tuesday)
        ]

        result = get_next_training("Male")

        assert result is not None
        assert result["team"] == "Male"
        assert result["type"] == "constant"
        assert result["days_until"] == 1  # Next day (Tuesday)

    @patch('trainings.load_data')
    @patch('trainings.datetime')
    def test_get_next_training_constant_female(self, mock_datetime, mock_load):
        """Test getting next constant training for female team"""
        mock_now = datetime.datetime(2025, 3, 24, 18, 0)  # Monday
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.time = datetime.time
        mock_datetime.timedelta = datetime.timedelta

        mock_load.side_effect = [
            {},  # one_time_trainings
            {"1": self.female_constant_training}  # constant_trainings (Thursday)
        ]

        result = get_next_training("Female")

        assert result is not None
        assert result["team"] == "Female"
        assert result["type"] == "constant"
        assert result["days_until"] == 3  # Monday to Thursday

    @patch('trainings.load_data')
    def test_get_next_training_no_trainings_male(self, mock_load):
        """Test getting next training when none exist for male team"""
        mock_load.side_effect = [{}, {}]  # Empty data

        result = get_next_training("Male")

        assert result is None

    @patch('trainings.load_data')
    def test_get_next_training_no_trainings_female(self, mock_load):
        """Test getting next training when none exist for female team"""
        mock_load.side_effect = [{}, {}]  # Empty data

        result = get_next_training("Female")

        assert result is None

    @patch('trainings.load_data')
    def test_get_next_week_trainings_male_team(self, mock_load):
        """Test getting trainings for next week for male team"""
        mock_load.side_effect = [
            {"1": self.male_one_time_training, "2": self.both_one_time_training},  # one_time_trainings
            {"1": self.male_constant_training, "2": self.both_constant_training}  # constant_trainings
        ]

        result = get_next_week_trainings("Male")

        # Should include trainings for Male and Both teams
        assert len(result) >= 1
        for training in result:
            assert training["team"] in ["Male", "Both"]

    @patch('trainings.load_data')
    def test_get_next_week_trainings_female_team(self, mock_load):
        """Test getting trainings for next week for female team"""
        mock_load.side_effect = [
            {"1": self.female_one_time_training, "2": self.both_one_time_training},  # one_time_trainings
            {"1": self.female_constant_training, "2": self.both_constant_training}  # constant_trainings
        ]

        result = get_next_week_trainings("Female")

        # Should include trainings for Female and Both teams
        assert len(result) >= 1
        for training in result:
            assert training["team"] in ["Female", "Both"]

    @patch('trainings.load_data')
    def test_get_next_week_trainings_excludes_other_team(self, mock_load):
        """Test that male user doesn't see female-only trainings"""
        mock_load.side_effect = [
            {"1": self.female_one_time_training},  # one_time_trainings (Female only)
            {"1": self.female_constant_training}  # constant_trainings (Female only)
        ]

        result = get_next_week_trainings("Male")

        # Should be empty since no Male or Both trainings
        assert len(result) == 0

    @pytest.fixture
    def mock_update(self):
        """Create mock update object"""
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.from_user = Mock(spec=User)
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Create mock context object"""
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @patch('trainings.load_data')
    @patch('trainings.format_next_training_message')
    @pytest.mark.asyncio
    async def test_next_training_command(self, mock_format, mock_load, mock_update, mock_context):
        """Test /next_training command"""
        mock_format.return_value = "Next training info"

        await next_training(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with("Next training info")

    @patch('trainings.load_data')
    @patch('trainings.get_next_week_trainings')
    @pytest.mark.asyncio
    async def test_week_trainings_command_male_user(self, mock_get_week, mock_load, mock_update, mock_context):
        """Test /week_trainings command for male user"""
        mock_load.return_value = {
            "12345": {"team": "Male"}
        }

        mock_training = {
            "date": datetime.date(2025, 3, 25),
            "start_hour": 19,
            "start_min": 0,
            "end_hour": 21,
            "end_min": 0,
            "with_coach": True,
            "team": "Male",
            "location": "Gym",
            "description": "Training"
        }
        mock_get_week.return_value = [mock_training]

        await week_trainings(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Тренування на тиждень" in call_args

    @patch('trainings.load_data')
    @patch('trainings.get_next_week_trainings')
    @pytest.mark.asyncio
    async def test_week_trainings_command_female_user(self, mock_get_week, mock_load, mock_update, mock_context):
        """Test /week_trainings command for female user"""
        mock_load.return_value = {
            "12345": {"team": "Female"}
        }

        mock_training = {
            "date": datetime.date(2025, 3, 26),
            "start_hour": 18,
            "start_min": 0,
            "end_hour": 20,
            "end_min": 0,
            "with_coach": False,
            "team": "Female",
            "location": "Hall B",
            "description": "Female training"
        }
        mock_get_week.return_value = [mock_training]

        await week_trainings(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Тренування на тиждень" in call_args

    @patch('trainings.load_data')
    @pytest.mark.asyncio
    async def test_week_trainings_command_not_registered(self, mock_load, mock_update, mock_context):
        """Test /week_trainings command for unregistered user"""
        mock_load.return_value = {}

        await week_trainings(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with("Будь ласка, завершіть реєстрацію.")


class TestKeyboardCreation:
    """Test keyboard creation functions"""

    def test_create_training_type_keyboard(self):
        """Test training type keyboard creation"""
        keyboard = create_training_type_keyboard()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Check that it has the expected buttons
        buttons = keyboard.inline_keyboard
        assert len(buttons) == 1
        assert len(buttons[0]) == 2

    def test_create_team_keyboard(self):
        """Test team selection keyboard creation"""
        keyboard = create_team_keyboard()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        buttons = keyboard.inline_keyboard
        assert len(buttons) == 2  # Two rows
        assert len(buttons[0]) == 2  # Male and Female
        assert len(buttons[1]) == 1  # Both teams

    def test_create_coach_keyboard(self):
        """Test coach selection keyboard creation"""
        keyboard = create_coach_keyboard()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        buttons = keyboard.inline_keyboard
        assert len(buttons) == 1
        assert len(buttons[0]) == 2  # Yes and No

    def test_create_weekday_keyboard(self):
        """Test weekday selection keyboard creation"""
        keyboard = create_weekday_keyboard()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        buttons = keyboard.inline_keyboard
        assert len(buttons) == 7  # 7 days of week
        for button_row in buttons:
            assert len(button_row) == 1

    def test_create_voting_day_keyboard(self):
        """Test voting day keyboard creation"""
        keyboard = create_voting_day_keyboard("prefix_")

        assert isinstance(keyboard, InlineKeyboardMarkup)
        buttons = keyboard.inline_keyboard
        assert len(buttons) == 7  # 7 days of week


class TestMessageFormatting:
    """Test message formatting functions"""

    @patch('trainings.load_data')
    @patch('trainings.get_next_training')
    def test_format_next_training_message_registered_user(self, mock_get_next, mock_load):
        """Test message formatting for registered user with training"""
        mock_load.return_value = {
            "12345": {"team": "Male"}
        }

        mock_training = {
            "date": datetime.date(2025, 3, 25),
            "start_hour": 19,
            "start_min": 0,
            "end_hour": 21,
            "end_min": 0,
            "team": "Male",
            "with_coach": True,
            "location": "Gym",
            "description": "Training session",
            "days_until": 1
        }
        mock_get_next.return_value = mock_training

        result = format_next_training_message("12345")

        assert "Наступне тренування" in result
        assert "25.03.2025" in result
        assert "19:00" in result
        assert "21:00" in result
        assert "З тренером" in result

    @patch('trainings.load_data')
    def test_format_next_training_message_unregistered_user(self, mock_load):
        """Test message formatting for unregistered user"""
        mock_load.return_value = {}

        result = format_next_training_message("12345")

        assert "завершіть реєстрацію" in result

    @patch('trainings.load_data')
    @patch('trainings.get_next_training')
    def test_format_next_training_message_no_trainings(self, mock_get_next, mock_load):
        """Test message formatting when no trainings available"""
        mock_load.return_value = {
            "12345": {"team": "Male"}
        }
        mock_get_next.return_value = None

        result = format_next_training_message("12345")

        assert "Немає запланованих тренувань" in result


class TestDataOperations:
    """Test training data operations"""

    @pytest.fixture
    def mock_context(self):
        """Create mock context with training data"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {
            'training_type': TrainingType.ONE_TIME.value,
            'training_team': Team.MALE.value,
            'with_coach': True,
            'training_location': "Sport Hall",
            'training_description': "Test training",
            'training_date': "25.03.2025",
            'start_hour': 19,
            'start_min': 0,
            'end_hour': 21,
            'end_min': 0,
            'start_voting': "24.03.2025"
        }
        return context

    @patch('trainings.load_data')
    @patch('trainings.save_data')
    @patch('trainings.open_onetime_training_voting_immediately')
    @pytest.mark.asyncio
    async def test_save_training_data_onetime(self, mock_open_voting, mock_save, mock_load, mock_context):
        """Test saving one-time training data"""
        mock_load.return_value = {}
        mock_update = Mock()

        await save_training_data(mock_update, mock_context)

        # Verify save_data was called twice (initial save + voting status update)
        assert mock_save.call_count == 2

        # Check the first call (initial training save)
        first_call = mock_save.call_args_list[0]
        saved_data = first_call[0][0]
        collection_name = first_call[0][1]

        assert collection_name == "one_time_trainings"
        assert "1" in saved_data  # First training gets ID "1"
        assert saved_data["1"]["team"] == Team.MALE.value
        assert saved_data["1"]["with_coach"] == True
        assert saved_data["1"]["date"] == "25.03.2025"
        assert saved_data["1"]["status"] == "not charged"

        # Check the second call (voting status update)
        second_call = mock_save.call_args_list[1]
        assert second_call[0][1] == "one_time_trainings"
        assert second_call[0][0]["1"]["voting_opened"] == True

    @patch('trainings.load_data')
    @patch('trainings.save_data')
    @pytest.mark.asyncio
    async def test_save_training_data_recurring(self, mock_save, mock_load, mock_context):
        """Test saving recurring training data"""
        mock_context.user_data['training_type'] = TrainingType.RECURRING.value
        mock_context.user_data['training_weekday'] = 1  # Tuesday
        mock_context.user_data['start_voting'] = 0  # Monday
        del mock_context.user_data['training_date']  # Remove date for recurring

        mock_load.return_value = {}
        mock_update = Mock()

        await save_training_data(mock_update, mock_context)

        # Verify save_data was called with constant_trainings
        mock_save.assert_called_once()
        call_args = mock_save.call_args[0]
        collection_name = call_args[1]

        assert collection_name == "constant_trainings"
        assert "1" in call_args[0]  # First training gets ID "1"
        assert call_args[0]["1"]["weekday"] == 1
        assert call_args[0]["1"]["team"] == Team.MALE.value


class TestTrainingVotingIntegration:
    """Test training voting integration"""

    @patch('trainings.load_data')
    @pytest.mark.asyncio
    async def test_open_onetime_training_voting_immediately(self, mock_load):
        """Test opening voting for one-time training immediately"""
        mock_load.return_value = {
            "12345": {"team": "Male"},
            "67890": {"team": "Female"}
        }

        mock_context = Mock()
        mock_context.bot.send_message = AsyncMock()

        training_data = {
            "date": "25.03.2025",
            "start_hour": 19,
            "start_min": 0,
            "end_hour": 21,
            "end_min": 0,
            "team": "Both",
            "with_coach": True,
            "location": "Gym",
            "description": "Test training"
        }

        await open_onetime_training_voting_immediately(mock_context, training_data, "1")

        # Verify messages were sent to users
        assert mock_context.bot.send_message.call_count >= 1


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.fixture
    def mock_update(self):
        """Create mock update object"""
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Create mock context object"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_cancel_training_creation(self, mock_update, mock_context):
        """Test canceling training creation"""
        result = await cancel(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "скасоване" in call_args
        assert result == ConversationHandler.END

    @patch('trainings.load_data')
    def test_get_next_training_corrupted_date(self, mock_load):
        """Test handling corrupted date in training data"""
        corrupted_training = {
            "date": "invalid_date",
            "start_hour": 19,
            "start_min": 0,
            "end_hour": 21,
            "end_min": 0,
            "team": "Both",
            "with_coach": True
        }

        mock_load.side_effect = [
            {"1": corrupted_training},  # one_time_trainings
            {}  # constant_trainings
        ]

        result = get_next_training("Both")

        # Should handle corrupted date gracefully
        assert result is None

    @patch('trainings.load_data')
    def test_get_next_training_missing_fields(self, mock_load):
        """Test handling missing fields in training data"""
        incomplete_training = {
            "date": "25.03.2025",
            # Missing other required fields
        }

        mock_load.side_effect = [
            {"1": incomplete_training},  # one_time_trainings
            {}  # constant_trainings
        ]

        result = get_next_training("Both")

        # Should handle missing fields gracefully
        assert result is None or result["start_hour"] == 0  # Default value

    @pytest.mark.asyncio
    async def test_training_start_voting_onetime_invalid_date(self, mock_update, mock_context):
        """Test voting start with invalid date for one-time training"""
        mock_context.user_data['training_type'] = TrainingType.ONE_TIME.value
        mock_update.message.text = "invalid_date"

        with patch('trainings.save_training_data') as mock_save:
            mock_save.side_effect = Exception("Date parsing error")

            # Should raise the exception since there's no error handling
            with pytest.raises(Exception, match="Date parsing error"):
                await training_start_voting(mock_update, mock_context)


class TestConversationHandlers:
    """Test conversation handler setup"""

    def test_create_training_add_handler(self):
        """Test training add conversation handler creation"""
        handler = create_training_add_handler()

        assert isinstance(handler, ConversationHandler)

        # Verify entry points
        assert len(handler.entry_points) > 0

        # Verify states exist
        expected_states = [TYPE, TEAM, COACH, LOCATION, DESCRIPTION, DATE, START, END, WEEKDAY, START_VOTING]
        for state in expected_states:
            assert state in handler.states

        # Verify fallbacks exist
        assert len(handler.fallbacks) > 0

    def test_conversation_states_constants(self):
        """Test conversation state constants"""
        assert isinstance(TYPE, int)
        assert isinstance(TEAM, int)
        assert isinstance(COACH, int)
        assert isinstance(LOCATION, int)
        assert isinstance(DESCRIPTION, int)
        assert isinstance(DATE, int)
        assert isinstance(START, int)
        assert isinstance(END, int)
        assert isinstance(WEEKDAY, int)
        assert isinstance(START_VOTING, int)

        # Verify they are unique
        states = [TYPE, TEAM, COACH, LOCATION, DESCRIPTION, DATE, START, END, WEEKDAY, START_VOTING]
        assert len(set(states)) == len(states)


class TestEnumsAndConstants:
    """Test enums and constants"""

    def test_training_type_enum(self):
        """Test TrainingType enum values"""
        assert TrainingType.ONE_TIME.value == "training_onetime"
        assert TrainingType.RECURRING.value == "training_recurring"

    def test_team_enum(self):
        """Test Team enum values"""
        assert Team.MALE.value == "Male"
        assert Team.FEMALE.value == "Female"
        assert Team.BOTH.value == "Both"

        # Test to_json method
        assert Team.MALE.to_json() == "Male"
        assert Team.FEMALE.to_json() == "Female"
        assert Team.BOTH.to_json() == "Both"

    def test_voting_type_enum(self):
        """Test VotingType enum values"""
        assert VotingType.ONE_TIME.value == "one_time"
        assert VotingType.RECURRING.value == "recurring"

    def test_messages_constants(self):
        """Test MESSAGES dictionary"""
        required_keys = [
            "unauthorized", "select_type", "select_team", "with_coach",
            "enter_location", "enter_description", "enter_date",
            "enter_start_time", "enter_end_time", "select_weekday",
            "invalid_date", "invalid_time", "training_saved"
        ]

        for key in required_keys:
            assert key in MESSAGES
            assert isinstance(MESSAGES[key], str)
            assert len(MESSAGES[key]) > 0

    def test_file_constants(self):
        """Test file name constants"""
        assert ONE_TIME_TRAININGS_FILE == "one_time_trainings"
        assert CONSTANT_TRAININGS_FILE == "constant_trainings"


class TestSchedulingLogic:
    """Test advanced scheduling logic"""

    @patch('trainings.datetime')
    def test_weekday_calculation_next_week(self, mock_datetime):
        """Test weekday calculation when training is next week"""
        # Current time: Friday
        mock_now = datetime.datetime(2025, 3, 28, 18, 0)  # Friday
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.time = datetime.time
        mock_datetime.timedelta = datetime.timedelta

        with patch('trainings.load_data') as mock_load:
            # Training on Monday (weekday=0)
            monday_training = {
                "weekday": 0,  # Monday
                "start_hour": 19,
                "start_min": 0,
                "end_hour": 21,
                "end_min": 0,
                "team": "Both",
                "with_coach": True
            }

            mock_load.side_effect = [
                {},  # one_time_trainings
                {"1": monday_training}  # constant_trainings
            ]

            result = get_next_training("Both")

            assert result is not None
            assert result["days_until"] == 3  # Friday to Monday

    @patch('trainings.datetime')
    def test_training_time_comparison_same_day(self, mock_datetime):
        """Test training time comparison on same day"""
        # Current time: Monday 18:00
        mock_now = datetime.datetime(2025, 3, 24, 18, 0)  # Monday 6 PM
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.time = datetime.time
        mock_datetime.timedelta = datetime.timedelta

        with patch('trainings.load_data') as mock_load:
            # Training on Monday 19:00 (1 hour later)
            monday_training = {
                "weekday": 0,  # Monday
                "start_hour": 19,
                "start_min": 0,
                "end_hour": 21,
                "end_min": 0,
                "team": "Both",
                "with_coach": True
            }

            mock_load.side_effect = [
                {},  # one_time_trainings
                {"1": monday_training}  # constant_trainings
            ]

            result = get_next_training("Both")

            assert result is not None
            assert result["days_until"] == 0  # Same day

    @patch('trainings.datetime')
    def test_past_training_same_day_skipped(self, mock_datetime):
        """Test that past training on same day is skipped"""
        # Current time: Monday 20:00
        mock_now = datetime.datetime(2025, 3, 24, 20, 0)  # Monday 8 PM
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date = datetime.date
        mock_datetime.time = datetime.time
        mock_datetime.timedelta = datetime.timedelta

        with patch('trainings.load_data') as mock_load:
            # Training on Monday 19:00 (1 hour ago)
            monday_training = {
                "weekday": 0,  # Monday
                "start_hour": 19,
                "start_min": 0,
                "end_hour": 21,
                "end_min": 0,
                "team": "Both",
                "with_coach": True
            }

            mock_load.side_effect = [
                {},  # one_time_trainings
                {"1": monday_training}  # constant_trainings
            ]

            result = get_next_training("Both")

            # Should get next week's Monday training
            assert result is not None
            assert result["days_until"] == 7  # Next Monday


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios"""

    @pytest.fixture
    def mock_update(self):
        """Create mock update object"""
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.from_user = Mock(spec=User)
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_callback_query_update(self):
        """Create mock update with callback query"""
        update = Mock(spec=Update)
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.from_user = Mock(spec=User)
        update.callback_query.from_user.id = 12345
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Create mock context object"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context

    @patch('trainings.is_authorized')
    @patch('trainings.load_data')
    @patch('trainings.save_data')
    @pytest.mark.asyncio
    async def test_complete_onetime_training_creation_flow(self, mock_save, mock_load, mock_is_authorized,
                                                           mock_update, mock_callback_query_update, mock_context):
        """Test complete one-time training creation workflow"""
        mock_is_authorized.return_value = True
        mock_load.return_value = {}

        # Step 1: Start training creation
        result1 = await add_training(mock_update, mock_context)
        assert result1 == TYPE

        # Step 2: Select one-time training
        mock_callback_query_update.callback_query.data = TrainingType.ONE_TIME.value
        result2 = await training_type(mock_callback_query_update, mock_context)
        assert result2 == TEAM

        # Step 3: Select team
        mock_callback_query_update.callback_query.data = "training_team_both"
        result3 = await training_team(mock_callback_query_update, mock_context)
        assert result3 == COACH

        # Step 4: Select with coach
        mock_callback_query_update.callback_query.data = "training_coach_yes"
        result4 = await training_coach(mock_callback_query_update, mock_context)
        assert result4 == LOCATION

        # Step 5: Enter location
        mock_update.message.text = "Sport Hall"
        result5 = await training_location(mock_update, mock_context)
        assert result5 == DESCRIPTION

        # Step 6: Enter description
        mock_update.message.text = "Training session"
        result6 = await training_description(mock_update, mock_context)
        assert result6 == DATE

        # Step 7: Enter date
        mock_update.message.text = "25.03.2025"
        result7 = await training_date(mock_update, mock_context)
        assert result7 == START

        # Step 8: Enter start time
        mock_update.message.text = "19:00"
        result8 = await training_start(mock_update, mock_context)
        assert result8 == END

        # Step 9: Enter end time
        mock_update.message.text = "21:00"
        result9 = await training_end(mock_update, mock_context)
        assert result9 == START_VOTING

        # Verify all data was collected correctly
        assert mock_context.user_data['training_type'] == TrainingType.ONE_TIME.value
        assert mock_context.user_data['training_team'] == Team.BOTH.value
        assert mock_context.user_data['with_coach'] == True
        assert mock_context.user_data['training_location'] == "Sport Hall"
        assert mock_context.user_data['training_description'] == "Training session"
        assert mock_context.user_data['training_date'] == "25.03.2025"
        assert mock_context.user_data['start_hour'] == 19
        assert mock_context.user_data['start_min'] == 0
        assert mock_context.user_data['end_hour'] == 21
        assert mock_context.user_data['end_min'] == 0

    @patch('trainings.is_authorized')
    @patch('trainings.load_data')
    @patch('trainings.save_data')
    @pytest.mark.asyncio
    async def test_complete_recurring_training_creation_flow(self, mock_save, mock_load, mock_is_authorized,
                                                             mock_update, mock_callback_query_update, mock_context):
        """Test complete recurring training creation workflow"""
        mock_is_authorized.return_value = True
        mock_load.return_value = {}

        # Similar to above but for recurring training
        # Step 1-5: Same as above until description

        # Step 6: Enter description for recurring
        mock_context.user_data['training_type'] = TrainingType.RECURRING.value
        mock_update.message.text = "Weekly training"
        result6 = await training_description(mock_update, mock_context)
        assert result6 == WEEKDAY

        # Step 7: Select weekday
        mock_callback_query_update.callback_query.data = "weekday_1"  # Tuesday
        result7 = await training_weekday(mock_callback_query_update, mock_context)
        assert result7 == START

        # Verify weekday was saved
        assert mock_context.user_data['training_weekday'] == 1
