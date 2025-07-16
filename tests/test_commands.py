import pytest
import datetime
from unittest.mock import Mock, patch, AsyncMock
from telegram import Update, User, Message, CallbackQuery, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from commands import (
    send_message_command, handle_send_message_team_selection, handle_send_message_input,
    notify_debtors, mvp_stats, handle_mvp_stats_selection, attendance_stats,
    handle_attendance_stats_selection, training_stats, handle_training_stats_selection,
    game_stats, handle_game_stats_selection, my_stats, game_results,
    handle_game_results_team_selection, handle_game_results_season_selection,
    handle_game_results_type_selection, get_available_seasons_from_ids,
    filter_games_by_season_id, create_game_results_handler,
    SEND_MESSAGE_STATE, GAME_RESULTS_TEAM, GAME_RESULTS_SEASON, GAME_RESULTS_TYPE
)


class TestSendMessageCommand:
    """Test send message functionality"""

    @pytest.fixture
    def mock_update(self):
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.from_user = Mock(spec=User)
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_callback_query_update(self):
        update = Mock(spec=Update)
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.from_user = Mock(spec=User)
        update.callback_query.from_user.id = 12345
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        context.bot.send_chat_action = AsyncMock()
        context.bot.send_dice = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_send_message_command_shows_team_selection(self, mock_update, mock_context):
        """Test that send message command shows team selection keyboard"""
        await send_message_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Оберіть команду" in call_args[0][0]
        assert isinstance(call_args[1]["reply_markup"], InlineKeyboardMarkup)

    @pytest.mark.asyncio
    async def test_handle_send_message_team_selection_male(self, mock_callback_query_update, mock_context):
        """Test team selection for male team"""
        mock_callback_query_update.callback_query.data = "send_team_Male"

        await handle_send_message_team_selection(mock_callback_query_update, mock_context)

        # Verify team was stored in SEND_MESSAGE_STATE
        assert SEND_MESSAGE_STATE[12345] == "Male"

        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args[0][0]
        assert "Male команда" in call_args

    @pytest.mark.asyncio
    async def test_handle_send_message_team_selection_female(self, mock_callback_query_update, mock_context):
        """Test team selection for female team"""
        mock_callback_query_update.callback_query.data = "send_team_Female"

        await handle_send_message_team_selection(mock_callback_query_update, mock_context)

        assert SEND_MESSAGE_STATE[12345] == "Female"

    @pytest.mark.asyncio
    async def test_handle_send_message_team_selection_both(self, mock_callback_query_update, mock_context):
        """Test team selection for both teams"""
        mock_callback_query_update.callback_query.data = "send_team_Both"

        await handle_send_message_team_selection(mock_callback_query_update, mock_context)

        assert SEND_MESSAGE_STATE[12345] == "Both"

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_send_message_input_normal_message(self, mock_load, mock_update, mock_context):
        """Test handling normal message input"""
        # Setup state
        SEND_MESSAGE_STATE[12345] = "Male"

        mock_update.message.text = "Test message"
        mock_update.message.from_user.username = "testuser"
        mock_update.message.from_user.first_name = "Test"

        # Mock users data with numeric user IDs (as strings)
        mock_load.return_value = {
            "11111": {"team": "Male"},
            "22222": {"team": "Female"},
            "33333": {"team": "Male"}
        }

        await handle_send_message_input(mock_update, mock_context)

        # Verify messages sent to correct users (Male team)
        assert mock_context.bot.send_message.call_count == 2  # 2 male users

        # Verify success message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "надіслано 2 користувачам" in call_args

        # Verify user removed from state
        assert 12345 not in SEND_MESSAGE_STATE

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_send_message_input_clown_emoji(self, mock_load, mock_update, mock_context):
        """Test special handling for clown emoji"""
        SEND_MESSAGE_STATE[12345] = "Both"
        mock_update.message.text = "Test message 🤡"
        mock_update.message.from_user.username = "testuser"
        mock_load.return_value = {"user1": {"team": "Male"}}

        await handle_send_message_input(mock_update, mock_context)

        # Verify special actions were triggered
        mock_context.bot.send_chat_action.assert_called()

        # Verify "Ти Клоун" message was sent
        reply_calls = mock_update.message.reply_text.call_args_list
        clown_message_sent = any("Ти Клоун" in str(call) for call in reply_calls)
        assert clown_message_sent

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_send_message_input_middle_finger_emoji(self, mock_load, mock_update, mock_context):
        """Test special handling for middle finger emoji"""
        SEND_MESSAGE_STATE[12345] = "Both"
        mock_update.message.text = "Test message 🖕"
        mock_update.message.from_user.username = "testuser"
        mock_load.return_value = {"user1": {"team": "Male"}}

        await handle_send_message_input(mock_update, mock_context)

        # Verify dice was sent
        mock_context.bot.send_dice.assert_called_once_with(12345, emoji='🎲')

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_send_message_input_no_state(self, mock_load, mock_update, mock_context):
        """Test handling message input when user not in state"""
        # Ensure user not in state
        if 12345 in SEND_MESSAGE_STATE:
            del SEND_MESSAGE_STATE[12345]

        mock_update.message.text = "Test message"
        mock_load.return_value = {}

        await handle_send_message_input(mock_update, mock_context)

        # Should not send any messages
        mock_context.bot.send_message.assert_not_called()
        mock_update.message.reply_text.assert_not_called()

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_send_message_input_message_send_failure(self, mock_load, mock_update, mock_context):
        """Test handling when sending message fails"""
        SEND_MESSAGE_STATE[12345] = "Male"
        mock_update.message.text = "Test message"
        mock_update.message.from_user.username = "testuser"

        mock_load.return_value = {
            "11111": {"team": "Male"},
            "22222": {"team": "Male"}
        }

        # Make one message send fail
        mock_context.bot.send_message.side_effect = [Exception("Send failed"), None]

        await handle_send_message_input(mock_update, mock_context)

        # Should still report partial success
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "надіслано 1 користувачам" in call_args


class TestNotifyDebtors:
    """Test notify debtors functionality"""

    @pytest.fixture
    def mock_update(self):
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.from_user = Mock(spec=User)
        update.message.from_user.id = 786580423  # Admin ID from validation.py
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        return context

    @patch('commands.ADMIN_IDS', [786580423])
    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_notify_debtors_authorized_user(self, mock_load, mock_update, mock_context):
        """Test notify debtors with authorized user"""
        # Mock payments data with debtors - use numeric user IDs
        mock_load.return_value = {
            "payment1": {
                "user_id": "11111",
                "training_datetime": "Training 1",
                "amount": 100,
                "paid": False
            },
            "payment2": {
                "user_id": "11111",
                "training_datetime": "Training 2",
                "amount": 150,
                "paid": False
            },
            "payment3": {
                "user_id": "22222",
                "training_datetime": "Training 3",
                "amount": 200,
                "paid": True  # Paid
            }
        }

        await notify_debtors(mock_update, mock_context)

        # Should send message to user1 (has 2 unpaid)
        mock_context.bot.send_message.assert_called_once()

        # Verify success message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "надіслано 1 боржникам" in call_args

    @patch('commands.ADMIN_IDS', [999999])  # Different admin ID
    @pytest.mark.asyncio
    async def test_notify_debtors_unauthorized_user(self, mock_update, mock_context):
        """Test notify debtors with unauthorized user"""
        await notify_debtors(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "немає прав" in call_args

    @patch('commands.ADMIN_IDS', [786580423])
    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_notify_debtors_no_debtors(self, mock_load, mock_update, mock_context):
        """Test notify debtors when no debtors exist"""
        # All payments are paid
        mock_load.return_value = {
            "payment1": {
                "user_id": "11111",
                "training_datetime": "Training 1",
                "amount": 100,
                "paid": True
            }
        }

        await notify_debtors(mock_update, mock_context)

        # Should not send any messages
        mock_context.bot.send_message.assert_not_called()

        # Should report 0 debtors
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "надіслано 0 боржникам" in call_args


class TestMVPStats:
    """Test MVP statistics functionality"""

    @pytest.fixture
    def mock_update(self):
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_callback_query_update(self):
        update = Mock(spec=Update)
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @pytest.mark.asyncio
    async def test_mvp_stats_shows_team_selection(self, mock_update, mock_context):
        """Test that MVP stats command shows team selection"""
        await mvp_stats(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "MVP Статистика" in call_args[0][0]
        assert isinstance(call_args[1]["reply_markup"], InlineKeyboardMarkup)

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_mvp_stats_selection_male_team(self, mock_load, mock_callback_query_update, mock_context):
        """Test MVP stats for male team"""
        mock_callback_query_update.callback_query.data = "mvp_stats_Male"

        mock_load.return_value = {
            "user1": {"name": "John", "team": "Male", "mvp": 5},
            "user2": {"name": "Jane", "team": "Female", "mvp": 3},
            "user3": {"name": "Bob", "team": "Male", "mvp": 7},
            "user4": {"name": "Alice", "team": "Male", "mvp": 0}  # No MVPs
        }

        await handle_mvp_stats_selection(mock_callback_query_update, mock_context)

        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args[0][0]

        # Should show male team stats only, sorted by MVP count
        assert "чоловічої команди" in call_args
        assert "Bob: 7 MVP" in call_args
        assert "John: 5 MVP" in call_args
        assert "Jane" not in call_args  # Female player not included

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_mvp_stats_selection_both_teams(self, mock_load, mock_callback_query_update, mock_context):
        """Test MVP stats for both teams"""
        mock_callback_query_update.callback_query.data = "mvp_stats_Both"

        mock_load.return_value = {
            "user1": {"name": "John", "team": "Male", "mvp": 5},
            "user2": {"name": "Jane", "team": "Female", "mvp": 3}
        }

        await handle_mvp_stats_selection(mock_callback_query_update, mock_context)

        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args[0][0]

        # Should show both teams separated
        assert "Чоловіча команда:" in call_args
        assert "Жіноча команда:" in call_args
        assert "John: 5 MVP" in call_args
        assert "Jane: 3 MVP" in call_args

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_mvp_stats_selection_no_mvps(self, mock_load, mock_callback_query_update, mock_context):
        """Test MVP stats when no MVPs exist"""
        mock_callback_query_update.callback_query.data = "mvp_stats_Male"

        mock_load.return_value = {
            "user1": {"name": "John", "team": "Male", "mvp": 0},
            "user2": {"name": "Bob", "team": "Male"}  # No mvp field
        }

        await handle_mvp_stats_selection(mock_callback_query_update, mock_context)

        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args[0][0]
        assert "немає MVP нагород" in call_args


class TestAttendanceStats:
    """Test attendance statistics functionality"""

    @pytest.fixture
    def mock_update(self):
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_callback_query_update(self):
        update = Mock(spec=Update)
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @pytest.mark.asyncio
    async def test_attendance_stats_shows_team_selection(self, mock_update, mock_context):
        """Test that attendance stats command shows team selection"""
        await attendance_stats(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Статистика відвідуваності" in call_args[0][0]

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_attendance_stats_selection(self, mock_load, mock_callback_query_update, mock_context):
        """Test attendance stats display"""
        mock_callback_query_update.callback_query.data = "attendance_stats_Male"

        mock_load.return_value = {
            "user1": {
                "name": "John",
                "team": "Male",
                "training_attendance": {"attended": 8, "total": 10},
                "game_attendance": {"attended": 3, "total": 5}
            },
            "user2": {
                "name": "Bob",
                "team": "Male",
                "training_attendance": {"attended": 6, "total": 8},
                "game_attendance": {"attended": 2, "total": 4}
            }
        }

        await handle_attendance_stats_selection(mock_callback_query_update, mock_context)

        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args[0][0]

        # Should show attendance percentages
        assert "John:" in call_args
        assert "8/10 (80%)" in call_args
        assert "3/5 (60%)" in call_args
        assert "Bob:" in call_args


class TestTrainingStats:
    """Test training statistics functionality"""

    @pytest.fixture
    def mock_update(self):
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_callback_query_update(self):
        update = Mock(spec=Update)
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_training_stats_selection_sorted_by_percentage(self, mock_load, mock_callback_query_update,
                                                                        mock_context):
        """Test training stats are sorted by attendance percentage"""
        mock_callback_query_update.callback_query.data = "training_stats_Male"

        mock_load.return_value = {
            "user1": {
                "name": "John",
                "team": "Male",
                "training_attendance": {"attended": 8, "total": 10}  # 80%
            },
            "user2": {
                "name": "Bob",
                "team": "Male",
                "training_attendance": {"attended": 9, "total": 10}  # 90%
            },
            "user3": {
                "name": "Charlie",
                "team": "Male",
                "training_attendance": {"attended": 7, "total": 10}  # 70%
            }
        }

        await handle_training_stats_selection(mock_callback_query_update, mock_context)

        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args[0][0]

        # Should be sorted with Bob (90%) first, then John (80%), then Charlie (70%)
        lines = call_args.split('\n')
        stats_lines = [line for line in lines if ':' in line and '/' in line]

        assert "Bob" in stats_lines[0]
        assert "John" in stats_lines[1]
        assert "Charlie" in stats_lines[2]


class TestGameStats:
    """Test game statistics functionality"""

    @pytest.fixture
    def mock_callback_query_update(self):
        update = Mock(spec=Update)
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_game_stats_selection_with_games(self, mock_load, mock_callback_query_update, mock_context):
        """Test game stats display with game attendance data"""
        mock_callback_query_update.callback_query.data = "game_stats_Female"

        mock_load.return_value = {
            "user1": {
                "name": "Jane",
                "team": "Female",
                "game_attendance": {"attended": 4, "total": 6}  # 67%
            },
            "user2": {
                "name": "Alice",
                "team": "Female",
                "game_attendance": {"attended": 5, "total": 6}  # 83%
            }
        }

        await handle_game_stats_selection(mock_callback_query_update, mock_context)

        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args[0][0]

        # Should be sorted by percentage (Alice first)
        assert "Alice" in call_args
        assert "5/6 (83%)" in call_args
        assert "Jane" in call_args
        assert "4/6 (67%)" in call_args


class TestMyStats:
    """Test individual user statistics"""

    @pytest.fixture
    def mock_update(self):
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.from_user = Mock(spec=User)
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock(spec=ContextTypes.DEFAULT_TYPE)

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_my_stats_registered_user(self, mock_load, mock_update, mock_context):
        """Test my stats for registered user"""
        # Mock user data and games data
        mock_load.side_effect = [
            # First call - users data
            {
                "12345": {
                    "name": "John Doe",
                    "team": "Male",
                    "mvp": 3,
                    "training_attendance": {"attended": 15, "total": 20},
                    "game_attendance": {"attended": 8, "total": 10}
                }
            },
            # Second call - games data
            {
                "game1": {"mvp": "John Doe", "date": "01.01.2025", "opponent": "Team A", "type": "friendly"},
                "game2": {"mvp": "John Doe", "date": "15.01.2025", "opponent": "Team B", "type": "stolichka"},
                "game3": {"mvp": "Someone Else", "date": "20.01.2025", "opponent": "Team C", "type": "friendly"}
            }
        ]

        await my_stats(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]

        # Verify stats are displayed
        assert "John Doe (чоловічої команда)" in call_args
        assert "15/20" in call_args  # Training attendance
        assert "75%" in call_args  # Training percentage
        assert "8/10" in call_args  # Game attendance
        assert "80%" in call_args  # Game percentage
        assert "3" in call_args  # MVP count

        # Verify MVP games are listed
        assert "Team A" in call_args
        assert "Team B" in call_args
        assert "Team C" not in call_args  # Not his MVP

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_my_stats_unregistered_user(self, mock_load, mock_update, mock_context):
        """Test my stats for unregistered user"""
        mock_load.return_value = {}  # No user data

        await my_stats(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "завершіть реєстрацію" in call_args


class TestGameResults:
    """Test game results functionality"""

    @pytest.fixture
    def mock_update(self):
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_callback_query_update(self):
        update = Mock(spec=Update)
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message = Mock()
        update.callback_query.message.reply_text = AsyncMock()
        update.callback_query.delete_message = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_game_results_shows_team_selection(self, mock_update, mock_context):
        """Test game results command shows team selection"""
        result = await game_results(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Результати ігор" in call_args[0][0]
        assert isinstance(call_args[1]["reply_markup"], InlineKeyboardMarkup)
        assert result == GAME_RESULTS_TEAM

    @patch('commands.load_data')
    @patch('commands.get_available_seasons_from_ids')
    @pytest.mark.asyncio
    async def test_handle_game_results_team_selection_single_season(self, mock_get_seasons, mock_load,
                                                                    mock_callback_query_update, mock_context):
        """Test team selection when only one season exists"""
        mock_callback_query_update.callback_query.data = "game_results_team_Male"
        mock_get_seasons.return_value = ["2024_2025"]  # Only one season
        mock_load.return_value = {}

        result = await handle_game_results_team_selection(mock_callback_query_update, mock_context)

        # Should skip season selection and go directly to tournament type
        assert mock_context.user_data["selected_team"] == "Male"
        assert mock_context.user_data["selected_season"] == "2024_2025"
        assert result == GAME_RESULTS_TYPE

    @patch('commands.load_data')
    @patch('commands.get_available_seasons_from_ids')
    @pytest.mark.asyncio
    async def test_handle_game_results_team_selection_multiple_seasons(self, mock_get_seasons, mock_load,
                                                                       mock_callback_query_update, mock_context):
        """Test team selection when multiple seasons exist"""
        mock_callback_query_update.callback_query.data = "game_results_team_Female"
        mock_get_seasons.return_value = ["2023_2024", "2024_2025"]  # Multiple seasons
        mock_load.return_value = {}

        result = await handle_game_results_team_selection(mock_callback_query_update, mock_context)

        # Should show season selection
        assert mock_context.user_data["selected_team"] == "Female"
        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        assert result == GAME_RESULTS_SEASON

    @pytest.mark.asyncio
    async def test_handle_game_results_season_selection(self, mock_callback_query_update, mock_context):
        """Test season selection"""
        mock_callback_query_update.callback_query.data = "game_results_season_2024_2025"
        mock_context.user_data["selected_team"] = "Male"

        result = await handle_game_results_season_selection(mock_callback_query_update, mock_context)

        assert mock_context.user_data["selected_season"] == "2024_2025"
        assert result == GAME_RESULTS_TYPE

    @pytest.mark.asyncio
    async def test_handle_game_results_season_selection_all(self, mock_callback_query_update, mock_context):
        """Test season selection for all seasons"""
        mock_callback_query_update.callback_query.data = "game_results_season_all"
        mock_context.user_data["selected_team"] = "Female"

        result = await handle_game_results_season_selection(mock_callback_query_update, mock_context)

        assert mock_context.user_data["selected_season"] is None  # All seasons
        assert result == GAME_RESULTS_TYPE

    @patch('commands.load_data')
    @patch('commands.filter_games_by_season_id')
    @patch('commands.datetime')
    @pytest.mark.asyncio
    async def test_handle_game_results_type_selection_with_games(self, mock_datetime, mock_filter, mock_load,
                                                                 mock_callback_query_update, mock_context):
        """Test tournament type selection with completed games"""
        mock_callback_query_update.callback_query.data = "game_results_type_friendly"
        mock_context.user_data["selected_team"] = "Male"
        mock_context.user_data["selected_season"] = "2024_2025"

        # Mock current time to be after games
        mock_now = datetime.datetime(2025, 3, 1, 12, 0)
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.datetime.strptime = datetime.datetime.strptime

        # Mock games data
        mock_load.return_value = {
            "friendly_male_2024_2025_1": {
                "type": "friendly",
                "team": "Male",
                "date": "15.02.2025",
                "time": "19:00",
                "opponent": "Team A",
                "location": "Hall A",
                "result": {
                    "status": "win",
                    "our_score": 3,
                    "opponent_score": 1,
                    "sets": [
                        {"our": 25, "opponent": 20},
                        {"our": 23, "opponent": 25},
                        {"our": 25, "opponent": 18},
                        {"our": 25, "opponent": 22}
                    ]
                },
                "mvp": "John Doe"
            }
        }

        # Mock filter function
        mock_filter.return_value = [
            ("friendly_male_2024_2025_1", mock_load.return_value["friendly_male_2024_2025_1"],
             datetime.datetime(2025, 2, 15, 19, 0))
        ]

        result = await handle_game_results_type_selection(mock_callback_query_update, mock_context)

        mock_callback_query_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args[0][0]

        # Verify game results are displayed
        assert "Результати товариських матчів" in call_args
        assert "🟢 Товариська - 15.02.2025" in call_args
        assert "Team A" in call_args
        assert "3:1" in call_args
        assert "25:20, 23:25, 25:18, 25:22" in call_args
        assert "MVP: John Doe" in call_args
        assert "1 перемог, 0 поразок" in call_args

        assert result == ConversationHandler.END

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_game_results_type_selection_no_games(self, mock_load, mock_callback_query_update,
                                                               mock_context):
        """Test tournament type selection with no completed games"""
        mock_callback_query_update.callback_query.data = "game_results_type_stolichka"
        mock_context.user_data["selected_team"] = "Female"
        mock_context.user_data["selected_season"] = None

        mock_load.return_value = {}  # No games

        result = await handle_game_results_type_selection(mock_callback_query_update, mock_context)

        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args[0][0]
        assert "немає завершених ігор" in call_args
        assert result == ConversationHandler.END

    @patch('commands.load_data')
    @patch('commands.filter_games_by_season_id')
    @patch('commands.datetime')
    @pytest.mark.asyncio
    async def test_handle_game_results_type_selection_long_message(self, mock_datetime, mock_filter, mock_load,
                                                                   mock_callback_query_update, mock_context):
        """Test tournament type selection with long message (over 4000 chars)"""
        mock_callback_query_update.callback_query.data = "game_results_type_all"
        mock_context.user_data["selected_team"] = "Both"
        mock_context.user_data["selected_season"] = None

        mock_now = datetime.datetime(2025, 3, 1, 12, 0)
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.datetime.strptime = datetime.datetime.strptime

        # Create many games to make message long
        games = {}
        filtered_games = []
        for i in range(50):  # Many games to exceed 4000 chars
            game_id = f"game_{i}"
            game = {
                "type": "friendly",
                "team": "Both",
                "date": f"{15:02d}.02.2025",
                "time": "19:00",
                "opponent": f"Team {chr(65 + (i % 26))}",
                "result": {
                    "status": "win",
                    "our_score": 3,
                    "opponent_score": 1,
                    "sets": [{"our": 25, "opponent": 20}] * 3
                }
            }
            games[game_id] = game
            filtered_games.append((game_id, game, datetime.datetime(2025, 2, 15, 19, 0)))

        mock_load.return_value = games
        mock_filter.return_value = filtered_games

        result = await handle_game_results_type_selection(mock_callback_query_update, mock_context)

        # Should send multiple messages instead of edit
        mock_callback_query_update.callback_query.message.reply_text.assert_called()
        mock_callback_query_update.callback_query.delete_message.assert_called_once()

        assert result == ConversationHandler.END


class TestGameResultsHelperFunctions:
    """Test helper functions for game results"""

    def test_get_available_seasons_from_ids_multiple_seasons(self):
        """Test extracting seasons from game IDs"""
        games_data = {
            "friendly_male_2023_2024_1": {"team": "Male"},
            "stolichka_male_2024_2025_1": {"team": "Male"},
            "friendly_female_2023_2024_1": {"team": "Female"},
            "universiad_male_2024_2025_1": {"team": "Male"},
            "invalid_game_id": {"team": "Male"}  # Should be ignored
        }

        result = get_available_seasons_from_ids(games_data, "Male")

        # Should be sorted in reverse chronological order
        assert result == ["2024_2025", "2023_2024"]

    def test_get_available_seasons_from_ids_team_filter(self):
        """Test season extraction with team filtering"""
        games_data = {
            "friendly_male_2023_2024_1": {"team": "Male"},
            "friendly_female_2023_2024_1": {"team": "Female"},
            "friendly_both_2024_2025_1": {"team": "Both"}
        }

        male_result = get_available_seasons_from_ids(games_data, "Male")
        female_result = get_available_seasons_from_ids(games_data, "Female")

        # Male should see Male and Both games
        assert "2023_2024" in male_result
        assert "2024_2025" in male_result

        # Female should see Female and Both games
        assert "2023_2024" in female_result
        assert "2024_2025" in female_result

    def test_get_available_seasons_from_ids_no_valid_seasons(self):
        """Test when no valid seasons found"""
        games_data = {
            "invalid_game_1": {"team": "Male"},
            "also_invalid": {"team": "Male"}
        }

        result = get_available_seasons_from_ids(games_data, "Male")
        assert result == []

    def test_filter_games_by_season_id_with_season(self):
        """Test filtering games by specific season"""
        games = [
            ("friendly_male_2023_2024_1", {"team": "Male"}, datetime.datetime.now()),
            ("stolichka_male_2024_2025_1", {"team": "Male"}, datetime.datetime.now()),
            ("friendly_female_2024_2025_1", {"team": "Female"}, datetime.datetime.now())
        ]

        result = filter_games_by_season_id(games, "2024_2025")

        # Should only include 2024_2025 games
        assert len(result) == 2
        assert all("2024_2025" in game[0] for game in result)

    def test_filter_games_by_season_id_no_season(self):
        """Test filtering when no season filter provided"""
        games = [
            ("game1", {"team": "Male"}, datetime.datetime.now()),
            ("game2", {"team": "Female"}, datetime.datetime.now())
        ]

        result = filter_games_by_season_id(games, None)

        # Should return all games unchanged
        assert result == games

    def test_filter_games_by_season_id_no_matches(self):
        """Test filtering when season doesn't match any games"""
        games = [
            ("friendly_male_2023_2024_1", {"team": "Male"}, datetime.datetime.now())
        ]

        result = filter_games_by_season_id(games, "2025_2026")
        assert result == []


class TestConversationHandler:
    """Test conversation handler creation"""

    def test_create_game_results_handler(self):
        """Test game results conversation handler creation"""
        handler = create_game_results_handler()

        assert isinstance(handler, ConversationHandler)

        # Verify entry points
        assert len(handler.entry_points) > 0

        # Verify states exist
        expected_states = [GAME_RESULTS_TEAM, GAME_RESULTS_SEASON, GAME_RESULTS_TYPE]
        for state in expected_states:
            assert state in handler.states

        # Verify fallbacks exist (should be empty for this handler)
        assert len(handler.fallbacks) == 0


class TestConstants:
    """Test module constants"""

    def test_send_message_state_global(self):
        """Test SEND_MESSAGE_STATE is properly defined"""
        assert isinstance(SEND_MESSAGE_STATE, dict)

    def test_conversation_state_constants(self):
        """Test conversation state constants"""
        assert isinstance(GAME_RESULTS_TEAM, int)
        assert isinstance(GAME_RESULTS_SEASON, int)
        assert isinstance(GAME_RESULTS_TYPE, int)

        # Verify they are unique
        states = [GAME_RESULTS_TEAM, GAME_RESULTS_SEASON, GAME_RESULTS_TYPE]
        assert len(set(states)) == len(states)

        # Verify they are in expected range (500-502 from the file)
        assert 500 <= GAME_RESULTS_TEAM <= 502
        assert 500 <= GAME_RESULTS_SEASON <= 502
        assert 500 <= GAME_RESULTS_TYPE <= 502


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def mock_update(self):
        update = Mock(spec=Update)
        update.message = Mock(spec=Message)
        update.message.from_user = Mock(spec=User)
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_callback_query_update(self):
        update = Mock(spec=Update)
        update.callback_query = Mock(spec=CallbackQuery)
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        return context

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_handle_send_message_input_empty_user_data(self, mock_load, mock_update, mock_context):
        """Test send message with empty user data"""
        SEND_MESSAGE_STATE[12345] = "Both"
        mock_update.message.text = "Test message"
        mock_update.message.from_user.username = "testuser"
        mock_load.return_value = {}  # No users

        await handle_send_message_input(mock_update, mock_context)

        # Should report 0 messages sent
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "надіслано 0 користувачам" in call_args

    @patch('commands.load_data')
    @pytest.mark.asyncio
    async def test_my_stats_user_with_missing_data(self, mock_load, mock_update, mock_context):
        """Test my stats for user with incomplete data"""
        mock_load.side_effect = [
            {
                "12345": {
                    "name": "John",
                    "team": "Male"
                    # Missing mvp and attendance data
                }
            },
            {}  # No games
        ]

        await my_stats(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Should handle missing data gracefully with defaults
        assert "John (чоловічої команда)" in call_args
        assert "0/0" in call_args  # Default attendance
        assert "0%" in call_args  # Default percentage

    @patch('commands.datetime')
    def test_get_available_seasons_from_ids_exception_handling(self, mock_datetime):
        """Test season extraction with malformed game IDs"""
        mock_datetime.datetime.now.return_value = datetime.datetime(2025, 1, 1)

        games_data = {
            "friendly_male_2024_2025_1": {"team": "Male"},
            "malformed_id": {"team": "Male"},
            "": {"team": "Male"},  # Empty ID
            # None: {"team": "Male"}  # None ID removed as it would cause KeyError
        }

        # Should not raise exception
        result = get_available_seasons_from_ids(games_data, "Male")

        # Should still extract valid season
        assert "2024_2025" in result

    @patch('commands.load_data')
    @patch('commands.datetime')
    @pytest.mark.asyncio
    async def test_handle_game_results_type_selection_invalid_date(self, mock_datetime, mock_load,
                                                                   mock_callback_query_update, mock_context):
        """Test game results with invalid date format"""
        mock_callback_query_update.callback_query.data = "game_results_type_friendly"
        mock_context.user_data["selected_team"] = "Male"
        mock_context.user_data["selected_season"] = None

        mock_now = datetime.datetime(2025, 3, 1, 12, 0)
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.datetime.strptime.side_effect = ValueError("Invalid date")

        mock_load.return_value = {
            "game1": {
                "type": "friendly",
                "team": "Male",
                "date": "invalid_date",
                "time": "19:00",
                "opponent": "Team A",
                "result": {"status": "win", "our_score": 3, "opponent_score": 1, "sets": []}
            }
        }

        result = await handle_game_results_type_selection(mock_callback_query_update, mock_context)

        # Should handle gracefully and show no games
        call_args = mock_callback_query_update.callback_query.edit_message_text.call_args[0][0]
        assert "немає завершених ігор" in call_args
        assert result == ConversationHandler.END
