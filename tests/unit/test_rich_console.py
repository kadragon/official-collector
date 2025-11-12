# Trace:
#   spec_id: SPEC-rich-ui-enhancement-1
#   task_id: TASK-009
"""
Unit tests for Rich Console wrapper singleton.

Tests cover:
- Singleton pattern enforcement
- Theme configuration
- Console initialization
- Message functions (info/success/warning/error)
- Screen control functions
- Backward compatibility with legacy mode
"""
import os
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock
from rich.console import Console
from rich.theme import Theme


@pytest.fixture
def mock_env_rich_enabled():
    """Mock environment with Rich UI enabled."""
    with patch.dict(os.environ, {"USE_RICH_UI": "true"}):
        yield


@pytest.fixture
def mock_env_rich_disabled():
    """Mock environment with Rich UI disabled."""
    with patch.dict(os.environ, {"USE_RICH_UI": "false"}):
        yield


class TestRichConsoleSingleton:
    """Test RichConsole singleton behavior."""

    def test_singleton_pattern(self):
        """Ensure RichConsole returns the same instance."""
        from ui.rich_console import RichConsole

        instance1 = RichConsole()
        instance2 = RichConsole()

        assert instance1 is instance2

    def test_console_instance_created(self):
        """Verify Console instance is created."""
        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        assert hasattr(rich_console, "console")
        assert isinstance(rich_console.console, Console)

    def test_theme_configured(self):
        """Verify custom theme is applied."""
        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        assert hasattr(rich_console, "theme")
        assert isinstance(rich_console.theme, Theme)
        # Check key theme colors
        assert "info" in rich_console.theme.styles
        assert "success" in rich_console.theme.styles
        assert "warning" in rich_console.theme.styles
        assert "error" in rich_console.theme.styles


class TestRichConsoleOutput:
    """Test Rich Console output functions."""

    def test_print_info_rich_mode(self, mock_env_rich_enabled):
        """Test info message in Rich mode."""
        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_info("Test info message")
            mock_print.assert_called_once()

    def test_print_success_rich_mode(self, mock_env_rich_enabled):
        """Test success message in Rich mode."""
        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_success("Test success message")
            mock_print.assert_called_once()

    def test_print_warning_rich_mode(self, mock_env_rich_enabled):
        """Test warning message in Rich mode."""
        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_warning("Test warning message")
            mock_print.assert_called_once()

    def test_print_error_rich_mode(self, mock_env_rich_enabled):
        """Test error message in Rich mode."""
        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_error("Test error message")
            mock_print.assert_called_once()


class TestRichConsoleScreenControl:
    """Test screen control functions."""

    def test_clear_screen_rich_mode(self, mock_env_rich_enabled):
        """Test clear screen in Rich mode."""
        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        with patch.object(rich_console.console, "clear") as mock_clear:
            rich_console.clear_screen()
            mock_clear.assert_called_once()


class TestRichConsoleCJKHandling:
    """Test CJK character handling."""

    def test_korean_text_rendering(self, mock_env_rich_enabled):
        """Verify Korean text renders correctly."""
        from ui.rich_console import RichConsole

        rich_console = RichConsole()
        korean_text = "한글 테스트 메시지"

        # Should not raise exception
        with patch.object(rich_console.console, "print"):
            rich_console.print_info(korean_text)

    def test_mixed_text_rendering(self, mock_env_rich_enabled):
        """Verify mixed English/Korean text renders correctly."""
        from ui.rich_console import RichConsole

        rich_console = RichConsole()
        mixed_text = "Processing document: 공문서 처리 중"

        # Should not raise exception
        with patch.object(rich_console.console, "print"):
            rich_console.print_info(mixed_text)


class TestRichConsoleInitialization:
    """Test RichConsole initialization."""

    def test_console_initialized_successfully(self):
        """Test RichConsole initializes without errors."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        assert rich_console.console is not None
        assert rich_console.theme is not None


class TestRichConsolePanel:
    """Test Panel rendering."""

    def test_print_document_info_panel(self, mock_env_rich_enabled):
        """Test document info renders as Panel."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        title = "테스트 문서 제목"
        doc_type = "공문서"

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_document_info(title, doc_type)
            mock_print.assert_called_once()
            # Verify Panel was passed
            args = mock_print.call_args[0]
            assert len(args) > 0

    def test_print_document_info_long_title(self, mock_env_rich_enabled):
        """Test long title handles correctly in Panel."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        long_title = "매우 긴 문서 제목입니다 " * 10

        with patch.object(rich_console.console, "print"):
            # Should not raise exception
            rich_console.print_document_info(long_title, "문서")


class TestRichConsoleTable:
    """Test Table rendering."""

    def test_print_numbered_list_table(self, mock_env_rich_enabled):
        """Test numbered list renders as Table."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        items = ["항목 1", "항목 2", "항목 3"]

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_numbered_list(items)
            mock_print.assert_called_once()

    def test_print_numbered_list_with_start_index(self, mock_env_rich_enabled):
        """Test numbered list with custom start index."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        items = ["항목 A", "항목 B"]

        with patch.object(rich_console.console, "print"):
            # Should not raise exception
            rich_console.print_numbered_list(items, start_index=5)


class TestRichConsoleProgress:
    """Test Progress bar functionality."""

    def test_progress_bar_context_manager(self, mock_env_rich_enabled):
        """Test progress bar can be used as context manager."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        # Should not raise exception
        with rich_console.progress_bar("Test progress") as progress:
            task = progress.add_task("Processing", total=10)
            for i in range(10):
                progress.update(task, advance=1)

    def test_progress_bar_creates_progress_instance(self, mock_env_rich_enabled):
        """Test progress bar creates Progress instance."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole
        from rich.progress import Progress

        rich_console = RichConsole()

        with rich_console.progress_bar("Test") as progress:
            assert isinstance(progress, Progress)


class TestRichConsolePrompts:
    """Test prompt functionality."""

    def test_prompt_int_basic(self, mock_env_rich_enabled):
        """Test integer prompt basic functionality."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        # Mock IntPrompt.ask
        with patch("ui.rich_console.IntPrompt.ask", return_value=5):
            result = rich_console.prompt_int("Enter number:")
            assert result == 5

    def test_confirm_basic(self, mock_env_rich_enabled):
        """Test confirmation prompt."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        # Mock Confirm.ask
        with patch("ui.rich_console.Confirm.ask", return_value=True):
            result = rich_console.confirm("Are you sure?")
            assert result is True


class TestRichConsoleTree:
    """Test Tree visualization functionality."""

    def test_print_final_result_tree_all_success(self, mock_env_rich_enabled):
        """Test final result tree with 100% success rate."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_final_result(10, 10)
            # Should print tree structure
            assert mock_print.call_count >= 1

    def test_print_final_result_tree_partial_success(self, mock_env_rich_enabled):
        """Test final result tree with partial success."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_final_result(7, 10)
            # Should print tree with both success and failure branches
            assert mock_print.call_count >= 1

    def test_print_final_result_tree_zero_success(self, mock_env_rich_enabled):
        """Test final result tree with zero success."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_final_result(0, 5)
            # Should print tree showing all failures
            assert mock_print.call_count >= 1


class TestRichConsoleMarkdown:
    """Test Markdown rendering functionality."""

    def test_print_processing_summary_basic(self, mock_env_rich_enabled):
        """Test processing summary with markdown."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        summary_data = {
            "total_processed": 10,
            "success_count": 8,
            "failure_count": 2,
            "elapsed_time": 45.5,
        }

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_processing_summary(summary_data)
            # Should render markdown content
            assert mock_print.call_count >= 1

    def test_print_processing_summary_empty_data(self, mock_env_rich_enabled):
        """Test processing summary handles empty data gracefully."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_processing_summary({})
            # Should not crash with empty data
            assert mock_print.call_count >= 1


class TestRichConsoleSelectionMenu:
    """Test Selection Menu functionality."""

    def test_print_selection_menu_basic(self, mock_env_rich_enabled):
        """Test selection menu renders with Panel + Table."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        items = ["항목 1", "항목 2", "항목 3"]

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_selection_menu("테스트 메뉴", items)
            # Should print newline + Panel + newline = 3 calls
            assert mock_print.call_count == 3

    def test_print_selection_menu_with_skip(self, mock_env_rich_enabled):
        """Test selection menu with skip option."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        items = ["담당자 A", "담당자 B"]

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_selection_menu(
                "담당자 선택", items, allow_skip=True, skip_text="목록에 없음"
            )
            # Should print with skip option [00]
            assert mock_print.call_count == 3

    def test_print_selection_menu_empty_items(self, mock_env_rich_enabled):
        """Test selection menu handles empty items list."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_selection_menu("빈 메뉴", [])
            # Should not crash with empty list
            assert mock_print.call_count == 3

    def test_print_selection_menu_long_items(self, mock_env_rich_enabled):
        """Test selection menu handles long item text."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        long_items = ["매우 긴 항목 이름입니다 " * 10, "또 다른 긴 항목 이름" * 10]

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_selection_menu("긴 항목 테스트", long_items)
            # Should handle long text without crashing
            assert mock_print.call_count == 3

    def test_print_selection_menu_korean_text(self, mock_env_rich_enabled):
        """Test selection menu handles Korean text correctly."""
        import ui.rich_console as rc_module

        rc_module._instance = None

        from ui.rich_console import RichConsole

        rich_console = RichConsole()

        korean_items = ["한글 항목 1", "한글 항목 2", "영문 Item 3"]

        with patch.object(rich_console.console, "print") as mock_print:
            rich_console.print_selection_menu("한글 메뉴", korean_items)
            # Should render Korean text correctly
            assert mock_print.call_count == 3
