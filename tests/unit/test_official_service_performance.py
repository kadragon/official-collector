"""
Tests for OfficialCollector performance optimizations.
Focuses on wait time reductions and polling interval improvements.
"""

import time
import pytest
from unittest.mock import Mock, MagicMock, patch
from services.official_service import OfficialCollector


class TestWaitTimeOptimization:
    """Test suite for wait time optimization (0.1s → 0.05s)."""

    def test_wait_for_condition_uses_reduced_interval(self):
        """
        Test that _wait_for_condition uses 0.05s interval instead of 0.1s.

        This test verifies that the polling interval has been reduced from
        100ms to 50ms for faster UI element detection.
        """
        # Given: An OfficialCollector instance (mock the connection)
        with patch.object(OfficialCollector, "_connect_to_window"):
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
        with patch.object(OfficialCollector, "_connect_to_window"):
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
        with patch.object(OfficialCollector, "_connect_to_window"):
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


class TestPostActionWaitTimeOptimization:
    """Test suite for post-action wait time reduction (0.3s/0.5s → 0.1s)."""

    @patch("services.official_service.time.sleep")
    @patch("services.official_service.keyboard")
    @patch("services.official_service.mouse")
    @patch("services.official_service.pyperclip")
    def test_task_card_selection_uses_reduced_sleep(
        self, mock_pyperclip, mock_mouse, mock_keyboard, mock_sleep
    ):
        """
        Test that _perform_task_card_selection uses 0.1s sleeps instead of 0.3s.

        This test verifies that the post-keyboard-input sleep times have been
        reduced from 300ms to 100ms for faster task card selection.
        """
        # Given: An OfficialCollector instance (mock the connection)
        with patch.object(OfficialCollector, "_connect_to_window"):
            collector = OfficialCollector()

        # Given: Mock window objects
        mock_info_window = Mock()
        mock_dialog = Mock()
        mock_dialog.rectangle.return_value = Mock(right=100, top=50)

        # Mock _wait_for_window to return our mocks
        with patch.object(
            collector, "_wait_for_window", side_effect=[mock_info_window, mock_dialog]
        ):
            # When: We perform task card selection
            collector._perform_task_card_selection("test_card")

        # Then: time.sleep should be called with 0.1 (not 0.3)
        sleep_calls = [
            call[0][0] for call in mock_sleep.call_args_list if call[0][0] in [0.1, 0.3]
        ]

        # We expect 2 sleep calls in this method (after two ENTER keys)
        assert len(sleep_calls) == 2, f"Expected 2 sleep calls, got {len(sleep_calls)}"

        for sleep_time in sleep_calls:
            assert sleep_time == 0.1, (
                f"Expected 0.1s sleep (optimized), got {sleep_time}s. "
                "Sleep time should be reduced from 0.3s to 0.1s"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
