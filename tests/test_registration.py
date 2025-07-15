import pytest
from unittest.mock import Mock, patch, MagicMock,AsyncMock
from telegram import Update, User, Message, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler

from registration import (
    UserProfile, Team, RegistrationManager, RegistrationState,
    create_registration_handler, Messages
)


class TestUserProfile:
    def test_user_profile_default_initialization(self):
        profile = UserProfile(telegram_id="123", telegram_username="test_user")

        assert profile.telegram_id == "123"
        assert profile.telegram_username == "test_user"
        assert profile.name is None
        assert profile.team is None
        assert profile.mvp == 0
        assert profile.training_attendance == {"attended": 0, "total": 0}
        assert profile.game_attendance == {"attended": 0, "total": 0}

    def test_user_profile_with_custom_values(self):
        profile = UserProfile(
            telegram_id="456",
            telegram_username="custom_user",
            name="John Doe",
            team=Team.MALE,
            mvp=5
        )

        assert profile.name == "John Doe"
        assert profile.team == Team.MALE
        assert profile.mvp == 5

    def test_is_registered_incomplete_profile(self):
        profile1 = UserProfile(telegram_id="123", telegram_username="test", team=Team.MALE)
        assert not profile1.is_registered()

        profile2 = UserProfile(telegram_id="123", telegram_username="test", name="John")
        assert not profile2.is_registered()

        profile3 = UserProfile(telegram_id="123", telegram_username="test")
        assert not profile3.is_registered()

    def test_is_registered_complete_profile(self):
        profile = UserProfile(
            telegram_id="123",
            telegram_username="test",
            name="John Doe",
            team=Team.FEMALE
        )
        assert profile.is_registered()

    def test_to_dict_serialization(self):
        profile = UserProfile(
            telegram_id="123",
            telegram_username="test_user",
            name="Jane Smith",
            team=Team.FEMALE,
            mvp=3
        )

        result = profile.to_dict()
        expected = {
            "telegram_username": "test_user",
            "name": "Jane Smith",
            "team": "Female",
            "mvp": 3,
            "training_attendance": {"attended": 0, "total": 0},
            "game_attendance": {"attended": 0, "total": 0}
        }

        assert result == expected

    def test_to_dict_with_none_team(self):
        profile = UserProfile(telegram_id="123", telegram_username="test")
        result = profile.to_dict()
        assert result["team"] is None


class TestStartCommand:
    @pytest.fixture
    def mock_update(self):
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.from_user = Mock(spec=User)
        update.message.from_user.id = 12345
        update.message.from_user.username = "test_user"
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @pytest.fixture
    def registration_manager(self):
        return RegistrationManager("test_users")

    @patch('registration.load_data')
    @patch('registration.save_data')
    @pytest.mark.asyncio
    async def test_start_new_user(self, mock_save, mock_load, registration_manager, mock_update, mock_context):
        mock_load.return_value = {}

        result = await registration_manager.handle_start(mock_update, mock_context)

        # Verify welcome message sent
        mock_update.message.reply_text.assert_called_once_with(Messages.WELCOME)

        # Verify user profile created and saved
        mock_save.assert_called_once()

        # Verify conversation continues to NAME state
        assert result == RegistrationState.NAME.value

    @patch('registration.load_data')
    @pytest.mark.asyncio
    async def test_start_already_registered_user(self, mock_load, registration_manager, mock_update, mock_context):
        """Test /start with fully registered user"""
        # Setup: existing complete user data
        mock_load.return_value = {
            "12345": {
                "telegram_username": "test_user",
                "name": "John Doe",
                "team": "Male",
                "mvp": 0,
                "training_attendance": {"attended": 0, "total": 0},
                "game_attendance": {"attended": 0, "total": 0}
            }
        }

        result = await registration_manager.handle_start(mock_update, mock_context)

        # Verify "already registered" message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "команди з меню" in call_args

        # Verify conversation ends
        assert result == ConversationHandler.END

    @patch('registration.load_data')
    @patch('registration.save_data')
    @pytest.mark.asyncio
    async def test_start_partially_registered_user(self, mock_save, mock_load, registration_manager, mock_update,
                                                   mock_context):
        """Test /start with user missing name or team"""
        # Setup: user exists but incomplete
        mock_load.return_value = {
            "12345": {
                "telegram_username": "test_user",
                "name": None,
                "team": None,
                "mvp": 0,
                "training_attendance": {"attended": 0, "total": 0},
                "game_attendance": {"attended": 0, "total": 0}
            }
        }

        result = await registration_manager.handle_start(mock_update, mock_context)

        # Verify welcome message sent (should continue registration)
        mock_update.message.reply_text.assert_called_once_with(Messages.WELCOME)

        # Verify conversation continues to NAME state
        assert result == RegistrationState.NAME.value


class TestRegistrationFlow:
    """Test name and team selection flow"""

    @pytest.fixture
    def mock_update(self):
        """Create mock update object"""
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.from_user = Mock(spec=User)
        update.message.from_user.id = 12345
        update.message.text = "John Doe"
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
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @pytest.fixture
    def registration_manager(self):
        """Create RegistrationManager instance"""
        return RegistrationManager("test_users")

    @patch('registration.load_data')
    @patch('registration.save_data')
    @pytest.mark.asyncio
    async def test_handle_name_input(self, mock_save, mock_load, registration_manager, mock_update, mock_context):
        """Test name input handling"""
        # Setup: existing user without name
        mock_load.return_value = {
            "12345": {
                "telegram_username": "test_user",
                "name": None,
                "team": None,
                "mvp": 0,
                "training_attendance": {"attended": 0, "total": 0},
                "game_attendance": {"attended": 0, "total": 0}
            }
        }

        result = await registration_manager.handle_name(mock_update, mock_context)

        # Verify team selection message sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert Messages.TEAM_SELECTION in call_args

        # Verify profile saved with name
        mock_save.assert_called_once()

        # Verify conversation continues to TEAM state
        assert result == RegistrationState.TEAM.value

    @patch('registration.load_data')
    @pytest.mark.asyncio
    async def test_handle_name_no_profile(self, mock_load, registration_manager, mock_update, mock_context):
        """Test name input when no profile exists"""
        mock_load.return_value = {}

        result = await registration_manager.handle_name(mock_update, mock_context)

        # Verify conversation ends
        assert result == ConversationHandler.END

    @patch('registration.load_data')
    @patch('registration.save_data')
    @pytest.mark.asyncio
    async def test_handle_team_male_selection(self, mock_save, mock_load, registration_manager,
                                              mock_callback_query_update, mock_context):
        """Test male team selection"""
        # Setup callback data for male selection
        mock_callback_query_update.callback_query.data = "team_male"

        # Setup: existing user with name but no team
        mock_load.return_value = {
            "12345": {
                "telegram_username": "test_user",
                "name": "John Doe",
                "team": None,
                "mvp": 0,
                "training_attendance": {"attended": 0, "total": 0},
                "game_attendance": {"attended": 0, "total": 0}
            }
        }

        result = await registration_manager.handle_team(mock_callback_query_update, mock_context)

        # Verify completion message sent
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once_with(
            Messages.REGISTRATION_COMPLETE)

        # Verify profile saved
        mock_save.assert_called_once()

        # Verify conversation ends
        assert result == ConversationHandler.END

    @patch('registration.load_data')
    @patch('registration.save_data')
    @pytest.mark.asyncio
    async def test_handle_team_female_selection(self, mock_save, mock_load, registration_manager,
                                                mock_callback_query_update, mock_context):
        """Test female team selection"""
        # Setup callback data for female selection
        mock_callback_query_update.callback_query.data = "team_female"

        # Setup: existing user with name but no team
        mock_load.return_value = {
            "12345": {
                "telegram_username": "test_user",
                "name": "Jane Doe",
                "team": None,
                "mvp": 0,
                "training_attendance": {"attended": 0, "total": 0},
                "game_attendance": {"attended": 0, "total": 0}
            }
        }

        result = await registration_manager.handle_team(mock_callback_query_update, mock_context)

        # Verify completion message sent
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once_with(
            Messages.REGISTRATION_COMPLETE)

        # Verify conversation ends
        assert result == ConversationHandler.END

    @patch('registration.load_data')
    @pytest.mark.asyncio
    async def test_handle_team_no_profile(self, mock_load, registration_manager, mock_callback_query_update,
                                          mock_context):
        """Test team selection when no profile exists"""
        mock_load.return_value = {}

        result = await registration_manager.handle_team(mock_callback_query_update, mock_context)

        # Verify conversation ends
        assert result == ConversationHandler.END


class TestDatabaseOperations:
    """Test database operations"""

    @pytest.fixture
    def registration_manager(self):
        """Create RegistrationManager instance"""
        return RegistrationManager("test_users")

    @patch('registration.load_data')
    def test_load_user_profile_existing_user(self, mock_load, registration_manager):
        """Test loading existing user profile"""
        mock_load.return_value = {
            "12345": {
                "telegram_username": "test_user",
                "name": "John Doe",
                "team": "Male",
                "mvp": 5,
                "training_attendance": {"attended": 10, "total": 15},
                "game_attendance": {"attended": 3, "total": 5}
            }
        }

        profile = registration_manager.load_user_profile("12345")

        assert profile is not None
        assert profile.telegram_id == "12345"
        assert profile.name == "John Doe"
        assert profile.team == Team.MALE
        assert profile.mvp == 5
        assert profile.training_attendance == {"attended": 10, "total": 15}
        assert profile.game_attendance == {"attended": 3, "total": 5}

    @patch('registration.load_data')
    def test_load_user_profile_nonexistent_user(self, mock_load, registration_manager):
        """Test loading nonexistent user profile"""
        mock_load.return_value = {}

        profile = registration_manager.load_user_profile("99999")

        assert profile is None

    @patch('registration.load_data')
    def test_load_user_profile_with_defaults(self, mock_load, registration_manager):
        """Test loading user profile applies default values"""
        mock_load.return_value = {
            "12345": {
                "telegram_username": "test_user",
                "name": "John Doe",
                "team": "Female"
                # Missing mvp and attendance data
            }
        }

        profile = registration_manager.load_user_profile("12345")

        assert profile.mvp == 0  # Default value
        assert profile.training_attendance == {"attended": 0, "total": 0}  # Default value
        assert profile.game_attendance == {"attended": 0, "total": 0}  # Default value

    @patch('registration.load_data')
    @patch('registration.save_data')
    def test_save_user_profile(self, mock_save, mock_load, registration_manager):
        """Test saving user profile"""
        mock_load.return_value = {}

        profile = UserProfile(
            telegram_id="12345",
            telegram_username="test_user",
            name="John Doe",
            team=Team.MALE
        )

        registration_manager.save_user_profile(profile)

        # Verify save_data was called
        mock_save.assert_called_once()

        # Verify correct data structure was saved
        call_args = mock_save.call_args[0]
        saved_data = call_args[0]
        collection_name = call_args[1]

        assert collection_name == "test_users"
        assert "12345" in saved_data
        assert saved_data["12345"]["name"] == "John Doe"
        assert saved_data["12345"]["team"] == "Male"


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
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @pytest.mark.asyncio
    async def test_handle_cancel(self, mock_update, mock_context):
        """Test cancel command during registration"""
        result = await RegistrationManager.handle_cancel(mock_update, mock_context)

        # Verify cancellation message sent
        mock_update.message.reply_text.assert_called_once_with(Messages.REGISTRATION_CANCELLED)

        # Verify conversation ends
        assert result == ConversationHandler.END

    @patch('registration.load_data')
    def test_load_user_profile_corrupted_team_data(self, mock_load):
        """Test handling corrupted team data"""
        mock_load.return_value = {
            "12345": {
                "telegram_username": "test_user",
                "name": "John Doe",
                "team": "",
                "mvp": 0,
                "training_attendance": {"attended": 0, "total": 0},
                "game_attendance": {"attended": 0, "total": 0}
            }
        }

        registration_manager = RegistrationManager("test_users")

        # Should handle ValueError gracefully and return None team
        profile = registration_manager.load_user_profile("12345")
        assert profile.team is None

    @patch('registration.load_data')
    def test_load_user_profile_missing_fields(self, mock_load):
        """Test handling missing fields in user data"""
        mock_load.return_value = {
            "12345": {
                "telegram_username": "test_user"
                # Missing all other fields
            }
        }

        registration_manager = RegistrationManager("test_users")
        profile = registration_manager.load_user_profile("12345")

        # Should apply defaults for missing fields
        assert profile.name is None
        assert profile.team is None
        assert profile.mvp == 0
        assert profile.training_attendance == {"attended": 0, "total": 0}
        assert profile.game_attendance == {"attended": 0, "total": 0}


class TestConversationStates:
    """Test conversation state management"""

    def test_registration_states_enum(self):
        """Test RegistrationState enum values"""
        assert RegistrationState.NAME.value == 1
        assert RegistrationState.TEAM.value == 2

    def test_team_enum_values(self):
        """Test Team enum values"""
        assert Team.MALE.value == "Male"
        assert Team.FEMALE.value == "Female"

    def test_messages_constants(self):
        """Test Messages class contains required constants"""
        assert hasattr(Messages, 'WELCOME')
        assert hasattr(Messages, 'TEAM_SELECTION')
        assert hasattr(Messages, 'REGISTRATION_COMPLETE')
        assert hasattr(Messages, 'REGISTRATION_CANCELLED')

        # Verify messages are strings
        assert isinstance(Messages.WELCOME, str)
        assert isinstance(Messages.TEAM_SELECTION, str)
        assert isinstance(Messages.REGISTRATION_COMPLETE, str)
        assert isinstance(Messages.REGISTRATION_CANCELLED, str)

    def test_create_registration_handler(self):
        """Test conversation handler creation"""
        handler = create_registration_handler()

        # Verify it returns a ConversationHandler
        assert isinstance(handler, ConversationHandler)

        # Verify it has the correct entry points and states
        assert len(handler.entry_points) > 0
        assert RegistrationState.NAME.value in handler.states
        assert RegistrationState.TEAM.value in handler.states