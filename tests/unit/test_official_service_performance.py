"""
Tests for OfficialCollector performance optimizations.
Focuses on wait time reductions and polling interval improvements.
"""

import time
import _ctypes
import pytest
from unittest.mock import Mock, MagicMock, patch
from services.official_service import OfficialCollector


class TestWaitComErrorResilience:
    """Polling helpers must survive pywinauto COM errors."""

    def test_wait_for_condition_retries_com_error(self):
        with patch("services.official_service.WindowManager.connect_to_window"):
            collector = OfficialCollector()

        calls = []

        def condition():
            calls.append(1)
            if len(calls) == 1:
                raise _ctypes.COMError(-2147220991, "transient", None)
            return True

        result = collector._wait_for_condition(condition, timeout=2.0, interval=0.05)
        assert result is True
        assert len(calls) >= 2

    def test_wait_for_element_retries_com_error(self):
        with patch("services.official_service.WindowManager.connect_to_window"):
            collector = OfficialCollector()

        calls = []

        def selector():
            calls.append(1)
            if len(calls) == 1:
                raise _ctypes.COMError(-2147220991, "transient", None)
            mock_element = Mock()
            mock_element.exists.return_value = True
            mock_element.is_enabled.return_value = True
            return mock_element

        result = collector._wait_for_element(selector, timeout=2.0, interval=0.05)
        assert result is True
        assert len(calls) >= 2


class TestWaitTimeOptimization:
    """Test suite for wait time optimization (0.1s → 0.05s)."""

    def test_wait_for_condition_uses_reduced_interval(self):
        """
        Test that _wait_for_condition uses 0.05s interval instead of 0.1s.

        This test verifies that the polling interval has been reduced from
        100ms to 50ms for faster UI element detection.
        """
        # Given: An OfficialCollector instance (mock the connection)
        with patch("services.official_service.WindowManager.connect_to_window"):
            collector = OfficialCollector()

        # Given: A condition that becomes True after a short delay
        call_count = 0

        def condition():
            nonlocal call_count
            call_count += 1
            return call_count >= 3  # True on 3rd call

        # When: We wait for the condition with default interval
        start_time = time.time()
        result = collector._wait_for_condition(condition, timeout=1.0)
        elapsed_time = time.time() - start_time

        # Then: The condition should be satisfied
        assert result is True, "Condition should be satisfied"

        # Then: The elapsed time should be approximately 0.1s (2 intervals * 0.05s)
        # We expect 2 intervals because condition is True on 3rd call
        # With 0.05s interval: ~0.1s total
        # With 0.1s interval: ~0.2s total
        assert elapsed_time < 0.15, (
            f"Expected < 0.15s with 0.05s interval, got {elapsed_time:.3f}s. "
            "This suggests interval is still 0.1s"
        )
        assert call_count == 3, f"Expected 3 calls, got {call_count}"


class TestMaximumTimeoutOptimization:
    """Test suite for maximum timeout reduction."""

    def test_wait_for_element_default_timeout_is_reduced(self):
        """
        Test that _wait_for_element default timeout is reasonable (not 10s).

        The task requires reducing excessive timeouts. A 10-second default
        is too long for RPA operations where UI elements should appear quickly.
        """
        # Given: An OfficialCollector instance (mock the connection)
        with patch("services.official_service.WindowManager.connect_to_window"):
            collector = OfficialCollector()

        # Given: An element that never appears
        def never_exists():
            mock_element = Mock()
            mock_element.exists.return_value = False
            return mock_element

        # When: We wait for an element with default timeout
        start_time = time.time()
        result = collector._wait_for_element(never_exists)
        elapsed_time = time.time() - start_time

        # Then: The element should not be found
        assert result is False, "Element should not be found"

        # Then: The timeout should be less than 5 seconds (much better than 10s)
        assert elapsed_time < 5.0, (
            f"Expected timeout < 5.0s for better performance, got {elapsed_time:.3f}s. "
            "Current default might still be 10.0s"
        )

    def test_wait_for_condition_default_timeout_is_reduced(self):
        """
        Test that _wait_for_condition default timeout is reasonable (not 10s).

        Similar to wait_for_element, we want faster failures when conditions
        aren't met to avoid long blocking times.
        """
        # Given: An OfficialCollector instance (mock the connection)
        with patch("services.official_service.WindowManager.connect_to_window"):
            collector = OfficialCollector()

        # Given: A condition that never becomes True
        def never_true():
            return False

        # When: We wait for the condition with default timeout
        start_time = time.time()
        result = collector._wait_for_condition(never_true)
        elapsed_time = time.time() - start_time

        # Then: The condition should timeout
        assert result is False, "Condition should timeout"

        # Then: The timeout should be less than 5 seconds
        assert elapsed_time < 5.0, (
            f"Expected timeout < 5.0s for better performance, got {elapsed_time:.3f}s. "
            "Current default might still be 10.0s"
        )


# Trace: backlog.md - Task-card selection and confirmation fast pass
class TestVerifiedTaskCardSelection:
    """Legacy entry points must use verified selection before approval."""

    def make_collector(self):
        collector = OfficialCollector.__new__(OfficialCollector)
        collector.dlg = Mock()
        collector.dlg.texts.return_value = ["전자결재: original"]
        collector.window_manager = Mock()
        collector.button_controller = Mock()
        collector.dialog_handler = Mock()
        collector.task_card_capture = Mock(return_value="Actual card")
        collector.approve_reviewed_document = Mock(return_value=True)
        return collector

    @patch("services.official_service.wait_for_ui_settle")
    @patch("services.official_service.keyboard")
    @patch("services.official_service.pyperclip")
    def test_task_card_selection_uses_verified_capture_without_fixed_waits(
        self, clipboard, keyboard, settle
    ):
        collector = self.make_collector()
        with patch("pywinauto.mouse.click") as click:
            assert collector._perform_task_card_selection("Suggested card") is True
        collector.task_card_capture.assert_called_once_with(collector, "Suggested card")
        click.assert_not_called()
        keyboard.send_keys.assert_not_called()
        clipboard.copy.assert_not_called()
        settle.assert_not_called()

    @pytest.mark.parametrize("selected", [None, "", "   "])
    def test_task_card_capture_failure_never_approves(self, selected):
        collector = self.make_collector()
        collector.task_card_capture.return_value = selected
        collector.document_sort("Suggested card")
        collector.approve_reviewed_document.assert_not_called()
        collector.button_controller.click_approval_button.assert_not_called()

    def test_task_card_missing_capture_never_approves(self):
        collector = self.make_collector()
        collector.task_card_capture = None
        collector.document_sort("Suggested card")
        collector.approve_reviewed_document.assert_not_called()
        collector.button_controller.click_approval_button.assert_not_called()

    def test_task_card_capture_uses_existing_guarded_approval(self):
        collector = self.make_collector()
        collector.document_sort("Suggested card")
        collector.approve_reviewed_document.assert_called_once_with(
            "전자결재: original"
        )
        collector.button_controller.click_approval_button.assert_not_called()

    def test_task_card_capture_document_change_never_approves(self):
        collector = self.make_collector()
        collector.dlg.texts.side_effect = [
            ["전자결재: original"],
            ["전자결재: changed"],
        ]
        collector.document_sort("Suggested card")
        collector.approve_reviewed_document.assert_not_called()

    def test_task_card_capture_is_injected_without_constructing_a_sibling(self):
        capture = Mock()
        with patch("services.official_service.WindowManager.connect_to_window"):
            collector = OfficialCollector(task_card_capture=capture)
        assert collector.task_card_capture is capture


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
