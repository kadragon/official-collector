"""
Unit tests for console_interface module

Tests UI logic, menu systems, and user interaction patterns with mocked I/O.
These tests focus on the business logic without actual console interaction.
"""

import pytest
from unittest.mock import patch, MagicMock, call
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ui.console_interface import (
    ConsoleInterface,
    Colors,
    Symbols,
    SelectionResult,
    get_display_width,
    clear_screen,
    print_info,
    print_success,
    print_warning,
    print_error,
    get_valid_selection,
    confirm_choice,
    get_user_choice_from_list,
    print_final_result,
)
from tests.fixtures.mock_responses import MockUserInterface
from tests.fixtures.sample_documents import SampleDocuments


class TestColors:
    """Test color constants."""

    def test_color_codes_exist(self):
        """Test that all color codes are defined."""
        assert Colors.RESET == "\033[0m"
        assert Colors.BOLD == "\033[1m"
        assert Colors.RED == "\033[31m"
        assert Colors.GREEN == "\033[32m"
        assert Colors.YELLOW == "\033[33m"
        assert Colors.BLUE == "\033[34m"
        assert Colors.CYAN == "\033[36m"
        assert Colors.WHITE == "\033[37m"

    def test_symbols_exist(self):
        """Test that all symbols are defined."""
        assert Symbols.ARROW == "->"
        assert Symbols.INFO == "[INFO]"
        assert Symbols.WARNING == "[WARN]"
        assert Symbols.ERROR == "[ERROR]"
        assert Symbols.SUCCESS == "[OK]"


class TestDisplayWidth:
    """Test Korean text display width calculation."""

    @pytest.mark.parametrize(
        "text,expected_width",
        [
            ("hello", 5),  # 영문
            ("안녕하세요", 10),  # 한글 5자 = 10칸
            ("hello안녕", 9),  # 영문5 + 한글4 = 9칸
            ("", 0),  # 빈 문자열
            ("123", 3),  # 숫자
            ("!@#", 3),  # 특수문자
            ("한글English123", 15),  # 혼합 (한글4칸 + 영문7칸 + 숫자3칸 + 특수문자1칸)
        ],
    )
    def test_display_width_calculation(self, text, expected_width):
        """Test display width calculation for various text types."""
        assert get_display_width(text) == expected_width

    def test_unicode_characters(self):
        """Test Unicode character width calculation."""
        # 다양한 Unicode 문자들
        emoji_text = "😀🎉"  # 이모지
        width = get_display_width(emoji_text)
        assert width > 0  # 정확한 값보다는 처리되는지 확인

    def test_mixed_content_edge_cases(self):
        """Test edge cases with mixed content."""
        mixed = "Tab\t줄바꿈\n공백 "
        width = get_display_width(mixed)
        assert width > 0


class TestUtilityFunctions:
    """Test utility functions."""

    @patch("subprocess.run")
    def test_clear_screen_windows(self, mock_subprocess):
        """Test clear screen on Windows."""
        with patch("os.name", "nt"):
            clear_screen()
            mock_subprocess.assert_called_once_with(["cmd", "/c", "cls"], check=True)

    @patch("subprocess.run")
    def test_clear_screen_unix(self, mock_subprocess):
        """Test clear screen on Unix-like systems."""
        with patch("os.name", "posix"):
            clear_screen()
            mock_subprocess.assert_called_once_with(["clear"], check=True)

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_clear_screen_fallback(self, mock_print, mock_subprocess):
        """Test clear screen fallback when subprocess fails."""
        mock_subprocess.side_effect = Exception("Command failed")

        clear_screen()

        # Should print newlines as fallback
        assert mock_print.called
        print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
        assert "\n" * 50 in print_calls

    @patch("builtins.print")
    @patch("logging.getLogger")
    def test_print_functions(self, mock_logger, mock_print):
        """Test message printing functions."""
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance

        # Test each print function
        print_info("정보 메시지")
        print_success("성공 메시지")
        print_warning("경고 메시지")
        print_error("에러 메시지")

        # Verify logging was called
        assert mock_logger_instance.info.called
        assert mock_logger_instance.warning.called
        assert mock_logger_instance.error.called

        # Verify print was called with colored output
        assert mock_print.call_count >= 4


class TestInputValidation:
    """Test input validation functions."""

    def test_get_valid_selection_valid_input(self):
        """Test valid selection input."""
        options = ["옵션1", "옵션2", "옵션3"]

        # Valid selections
        assert get_valid_selection("1", options) == "옵션1"
        assert get_valid_selection("2", options) == "옵션2"
        assert get_valid_selection("3", options) == "옵션3"

    def test_get_valid_selection_invalid_input(self):
        """Test invalid selection input."""
        options = ["옵션1", "옵션2", "옵션3"]

        # Invalid selections should raise ValueError
        with pytest.raises(ValueError, match="유효하지 않은 번호입니다"):
            get_valid_selection("0", options)

        with pytest.raises(ValueError, match="유효하지 않은 번호입니다"):
            get_valid_selection("4", options)

        with pytest.raises(ValueError, match="유효하지 않은 입력입니다"):
            get_valid_selection("abc", options)

        with pytest.raises(ValueError, match="유효하지 않은 입력입니다"):
            get_valid_selection("", options)

    def test_get_valid_selection_edge_cases(self):
        """Test edge cases for selection validation."""
        options = ["단일옵션"]

        assert get_valid_selection("1", options) == "단일옵션"

        with pytest.raises(ValueError):
            get_valid_selection("2", options)

    @patch("builtins.input")
    def test_confirm_choice_yes_responses(self, mock_input):
        """Test confirm_choice with yes responses."""
        # Test various yes responses
        test_cases = [
            ("y", True),
            ("Y", True),
            ("", True),  # Empty input with default_yes=True
        ]

        for input_value, expected in test_cases:
            mock_input.return_value = input_value
            result = confirm_choice("확인하시겠습니까?", default_yes=True)
            assert result == expected

    @patch("builtins.input")
    def test_confirm_choice_no_responses(self, mock_input):
        """Test confirm_choice with no responses."""
        test_cases = [
            ("n", False),
            ("N", False),
            ("no", False),
            ("anything_else", False),
        ]

        for input_value, expected in test_cases:
            mock_input.return_value = input_value
            result = confirm_choice("확인하시겠습니까?", default_yes=True)
            assert result == expected

    @patch("builtins.input")
    def test_confirm_choice_default_no(self, mock_input):
        """Test confirm_choice with default_yes=False."""
        mock_input.return_value = ""  # Empty input
        result = confirm_choice("정말 삭제하시겠습니까?", default_yes=False)
        assert result == False


class TestUserChoiceFunctions:
    """Test user choice functions with mocked input."""

    @patch("builtins.input")
    def test_get_user_choice_from_list_valid_selection(self, mock_input):
        """Test valid selection from list."""
        options = SampleDocuments.get_all_task_card_titles()
        mock_input.return_value = "1"

        result, value = get_user_choice_from_list(options, allow_skip=False)

        assert result == SelectionResult.SELECTED
        assert value == options[0]

    @patch("builtins.input")
    def test_get_user_choice_from_list_skip(self, mock_input):
        """Test skipping selection from list."""
        options = ["옵션1", "옵션2"]
        mock_input.return_value = "0"

        result, value = get_user_choice_from_list(options, allow_skip=True)

        assert result == SelectionResult.SKIPPED
        assert value is None

    @patch("builtins.input")
    @patch("builtins.print")
    def test_get_user_choice_from_list_invalid_then_valid(self, mock_print, mock_input):
        """Test invalid input followed by valid input."""
        options = ["옵션1", "옵션2"]
        # First invalid, then valid
        mock_input.side_effect = ["invalid", "1"]

        result, value = get_user_choice_from_list(options, allow_skip=False)

        assert result == SelectionResult.SELECTED
        assert value == "옵션1"
        # Should print error message for invalid input
        assert mock_print.called

    @patch("builtins.input")
    @patch("builtins.print")
    def test_get_user_choice_retry_logic(self, mock_print, mock_input):
        """Test retry logic for invalid inputs."""
        options = ["옵션1", "옵션2"]
        # Multiple invalid inputs, then valid
        mock_input.side_effect = ["0", "abc", "99", "1"]  # 0 invalid (skip not allowed)

        result, value = get_user_choice_from_list(options, allow_skip=False)

        assert result == SelectionResult.SELECTED
        assert value == "옵션1"
        assert mock_input.call_count == 4  # Called 4 times
        assert mock_print.call_count >= 3  # Error messages printed


class TestConsoleInterface:
    """Test the main ConsoleInterface class."""

    def setup_method(self):
        """Set up test environment."""
        self.console = ConsoleInterface()
        self.sample_docs = SampleDocuments()

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_select_approval_and_share_single_approval(
        self, mock_input, mock_clear, mock_subprocess
    ):
        """Test approval and share selection with single approval option."""
        approval_list = ["담당자1"]  # Single option
        share_list = ["팀1", "팀2"]

        mock_input.return_value = "1"  # Select first share option

        approval, share = self.console.select_approval_and_share(
            approval_list, share_list
        )

        assert approval == "담당자1"  # Auto-selected
        assert share == "팀1"
        assert mock_clear.called

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_select_approval_and_share_multiple_options(
        self, mock_input, mock_clear, mock_subprocess
    ):
        """Test approval and share selection with multiple options."""
        approval_list = ["담당자1", "담당자2"]
        share_list = ["팀1", "팀2"]

        mock_input.side_effect = ["2", "1"]  # Select second approval, first share

        approval, share = self.console.select_approval_and_share(
            approval_list, share_list
        )

        assert approval == "담당자2"
        assert share == "팀1"

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_confirm_recommendation_yes(self, mock_input, mock_clear, mock_subprocess):
        """Test recommendation confirmation - yes."""
        mock_input.return_value = "y"

        result = self.console.confirm_recommendation("테스트 문서", "추천 과제카드")

        assert result == True
        assert mock_clear.called

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_confirm_recommendation_no(self, mock_input, mock_clear, mock_subprocess):
        """Test recommendation confirmation - no."""
        mock_input.return_value = "n"

        result = self.console.confirm_recommendation("테스트 문서", "추천 과제카드")

        assert result == False

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_choose_from_predefined_list(self, mock_input, mock_clear, mock_subprocess):
        """Test choosing from predefined list."""
        card_list = self.sample_docs.get_all_task_card_titles()
        mock_input.return_value = "1"

        result, value = self.console.choose_from_predefined_list(
            "테스트 문서", card_list
        )

        assert result == SelectionResult.SELECTED
        assert value == card_list[0]
        assert mock_clear.called

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_choose_from_predefined_list_skip(
        self, mock_input, mock_clear, mock_subprocess
    ):
        """Test skipping predefined list selection."""
        card_list = self.sample_docs.get_all_task_card_titles()
        mock_input.return_value = "0"  # Skip

        result, value = self.console.choose_from_predefined_list(
            "테스트 문서", card_list
        )

        assert result == SelectionResult.SKIPPED
        assert value is None

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_get_manual_task_card(self, mock_input, mock_clear, mock_subprocess):
        """Test manual task card input."""
        mock_input.return_value = "수동 입력 과제카드"

        result = self.console.get_manual_task_card("테스트 문서")

        assert result == "수동 입력 과제카드"
        assert mock_clear.called


class TestDeletionInterface:
    """Test deletion-related interface methods."""

    def setup_method(self):
        """Set up test environment."""
        self.console = ConsoleInterface()

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_show_deletion_menu(self, mock_input, mock_clear, mock_subprocess):
        """Test deletion menu display."""
        mock_input.return_value = "1"  # Select first option

        choice = self.console.show_deletion_menu()

        assert choice == "과제 카드 목록 보기 및 삭제"
        assert mock_clear.called

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_get_title_for_deletion_confirm(
        self, mock_input, mock_clear, mock_subprocess
    ):
        """Test getting title for deletion with confirmation."""
        mock_input.side_effect = ["삭제할 문서", "y"]  # Title input, then confirm

        result = self.console.get_title_for_deletion("과제 카드")

        assert result == "삭제할 문서"
        assert mock_clear.called

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_get_title_for_deletion_cancel(
        self, mock_input, mock_clear, mock_subprocess
    ):
        """Test getting title for deletion and canceling."""
        mock_input.side_effect = ["삭제할 문서", "n"]  # Title input, then cancel

        result = self.console.get_title_for_deletion("과제 카드")

        assert result is None

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_confirm_bulk_deletion_confirm(
        self, mock_input, mock_clear, mock_subprocess
    ):
        """Test bulk deletion confirmation - confirm."""
        mock_input.return_value = "y"

        result = self.console.confirm_bulk_deletion()

        assert result == True
        assert mock_clear.called

    @patch("subprocess.run")
    @patch("ui.console_interface.clear_screen")
    @patch("builtins.input")
    def test_confirm_bulk_deletion_cancel(
        self, mock_input, mock_clear, mock_subprocess
    ):
        """Test bulk deletion confirmation - cancel."""
        mock_input.return_value = "n"

        result = self.console.confirm_bulk_deletion()

        assert result == False


class TestIntegrationScenarios:
    """Test integrated UI scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.console = ConsoleInterface()

    @patch("builtins.print")
    def test_print_final_result_all_success(self, mock_print):
        """Test final result printing - all successful."""
        print_final_result(5, 5)

        # Should print success message
        assert mock_print.called
        print_calls = [str(call) for call in mock_print.call_args_list]
        success_found = any("모든 문서 처리 완료" in call for call in print_calls)
        assert success_found

    @patch("builtins.print")
    def test_print_final_result_partial_success(self, mock_print):
        """Test final result printing - partial success."""
        print_final_result(3, 5)

        # Should print warning and error messages
        assert mock_print.called
        print_calls = [str(call) for call in mock_print.call_args_list]
        partial_found = any("일부 문서 처리 완료" in call for call in print_calls)
        failure_found = any("실패: 2건" in call for call in print_calls)
        assert partial_found
        assert failure_found

    @patch("builtins.print")
    def test_print_final_result_zero_success(self, mock_print):
        """Test final result printing - zero success."""
        print_final_result(0, 3)

        assert mock_print.called
        print_calls = [str(call) for call in mock_print.call_args_list]
        failure_found = any("실패: 3건" in call for call in print_calls)
        assert failure_found
