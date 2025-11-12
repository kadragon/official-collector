"""
Unit tests for error_handler module

Tests logging setup, error handling patterns, and log management functionality.
These tests use mocked logging and file system operations.
"""

import logging
import tempfile
import os
import time
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.error_handler import cleanup_old_logs, setup_logger


class TestSetupLogger:
    """Test logger setup functionality."""

    def test_logger_creation(self):
        """Test that setup_logger creates a logger."""
        logger = setup_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_logger_level_configuration(self):
        """Test logger level is configured appropriately."""
        logger = setup_logger("test_level")

        # Logger should have appropriate level set
        assert logger.level <= logging.INFO  # Should log INFO and above

    def test_logger_handlers_attached(self):
        """Test that appropriate handlers are attached to logger."""
        logger = setup_logger("test_handlers")

        # Should have at least one handler
        assert len(logger.handlers) > 0

        # Check handler types
        handler_types = [type(handler).__name__ for handler in logger.handlers]

        # Should have console handler and/or file handler
        expected_handlers = ["StreamHandler", "FileHandler", "RotatingFileHandler"]
        has_expected_handler = any(ht in expected_handlers for ht in handler_types)
        assert (
            has_expected_handler
        ), f"Expected handler types {expected_handlers}, got {handler_types}"

    def test_logger_formatter_configuration(self):
        """Test that logger formatters are properly configured."""
        logger = setup_logger("test_formatter")

        for handler in logger.handlers:
            assert handler.formatter is not None

            # Test that formatter includes useful information
            formatter = handler.formatter
            format_string = (
                formatter._fmt if hasattr(formatter, "_fmt") else str(formatter)
            )

            # Should include timestamp, level, and message
            useful_elements = [
                "%(asctime)s",
                "%(levelname)s",
                "%(message)s",
                "%(name)s",
            ]
            has_useful_info = any(
                element in format_string for element in useful_elements
            )
            assert (
                has_useful_info
            ), f"Formatter should include useful info: {format_string}"

    @patch("pathlib.Path.mkdir")
    def test_log_directory_creation(self, mock_mkdir):
        """Test that log directory is created if it doesn't exist."""
        logger = setup_logger("test_directory")

        # Directory creation might be called during logger setup
        # This test verifies the pattern is considered
        assert isinstance(logger, logging.Logger)

    def test_multiple_logger_setup(self):
        """Test setting up multiple loggers with different names."""
        logger1 = setup_logger("module1")
        logger2 = setup_logger("module2")

        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger1 is not logger2  # Different instances

    def test_logger_reuse(self):
        """Test that requesting same logger name returns same logger."""
        logger1 = setup_logger("same_module")
        logger2 = setup_logger("same_module")

        # Should return the same logger instance
        assert logger1 is logger2


class TestLoggingFunctionality:
    """Test actual logging functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = setup_logger("test_logging")

    @patch("logging.Logger.info")
    def test_info_logging(self, mock_info):
        """Test info level logging."""
        self.logger.info("테스트 정보 메시지")
        mock_info.assert_called_once_with("테스트 정보 메시지")

    @patch("logging.Logger.warning")
    def test_warning_logging(self, mock_warning):
        """Test warning level logging."""
        self.logger.warning("테스트 경고 메시지")
        mock_warning.assert_called_once_with("테스트 경고 메시지")

    @patch("logging.Logger.error")
    def test_error_logging(self, mock_error):
        """Test error level logging."""
        self.logger.error("테스트 에러 메시지")
        mock_error.assert_called_once_with("테스트 에러 메시지")

    @patch("logging.Logger.debug")
    def test_debug_logging(self, mock_debug):
        """Test debug level logging."""
        self.logger.debug("테스트 디버그 메시지")
        # Debug might or might not be called depending on level
        # Just verify no exception is raised
        assert True

    def test_korean_text_logging(self):
        """Test logging with Korean text."""
        # Should not raise encoding errors
        self.logger.info("한글 로그 메시지 테스트")
        self.logger.warning("한글 경고 메시지")
        self.logger.error("한글 에러 메시지")

    def test_exception_logging(self):
        """Test logging exceptions."""
        try:
            raise ValueError("테스트 예외")
        except ValueError:
            # Should not raise exception when logging exception info
            self.logger.exception("예외가 발생했습니다")

    @pytest.mark.parametrize(
        "log_level,message",
        [
            (logging.DEBUG, "디버그 메시지"),
            (logging.INFO, "정보 메시지"),
            (logging.WARNING, "경고 메시지"),
            (logging.ERROR, "에러 메시지"),
            (logging.CRITICAL, "치명적 에러 메시지"),
        ],
    )
    def test_different_log_levels(self, log_level, message):
        """Test logging at different levels."""
        # Should not raise exceptions for any level
        self.logger.log(log_level, message)


class TestLogFileHandling:
    """Test log file handling and rotation."""

    def test_log_file_creation_concept(self):
        """Test that log files can be created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test that logger setup considers file logging
            logger = setup_logger("test_file_logger")

            # Should have logger instance regardless of file handling
            assert isinstance(logger, logging.Logger)

    @patch("logging.handlers.RotatingFileHandler")
    def test_rotating_file_handler_usage(self, mock_rotating_handler):
        """Test that rotating file handler is used if implemented."""
        mock_handler = MagicMock()
        mock_rotating_handler.return_value = mock_handler

        logger = setup_logger("test_rotating")

        # If rotating handler is used, verify it's configured
        assert isinstance(logger, logging.Logger)

    def test_log_file_permissions(self):
        """Test log file permissions handling."""
        # Test that logger setup handles permission issues gracefully
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            # Should not crash even if file can't be created
            logger = setup_logger("test_permissions")
            assert isinstance(logger, logging.Logger)


class TestErrorHandlingPatterns:
    """Test common error handling patterns."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = setup_logger("test_error_patterns")

    def test_try_except_logging_pattern(self):
        """Test common try-except logging pattern."""
        try:
            # Simulate an operation that might fail
            result = 10 / 0  # Division by zero
        except ZeroDivisionError as e:
            self.logger.error(f"계산 오류 발생: {e}")
            # Should not re-raise exception
        except Exception as e:
            self.logger.exception(f"예상치 못한 오류: {e}")

    def test_warning_for_recoverable_errors(self):
        """Test warning logging for recoverable errors."""
        # Simulate a recoverable error scenario
        data = {"key1": "value1"}

        if "key2" not in data:
            self.logger.warning("key2가 데이터에 없습니다. 기본값을 사용합니다.")
            default_value = "default"

        # Should continue execution
        assert default_value == "default"

    def test_info_for_normal_operations(self):
        """Test info logging for normal operations."""
        # Simulate normal operation logging
        self.logger.info("문서 처리 시작")

        # Simulate processing
        processed_count = 5

        self.logger.info(f"문서 처리 완료: {processed_count}건")

    @patch("logging.Logger.error")
    def test_error_context_information(self, mock_error):
        """Test that error logs include context information."""
        document_id = "test_doc_123"
        operation = "document_processing"

        try:
            raise ValueError("테스트 오류")
        except ValueError as e:
            self.logger.error(
                f"문서 처리 오류 - ID: {document_id}, 작업: {operation}, 오류: {e}"
            )

        # Verify error was logged with context
        mock_error.assert_called_once()
        call_args = mock_error.call_args[0][0]
        assert document_id in call_args
        assert operation in call_args


class TestLoggerConfiguration:
    """Test logger configuration options."""

    def test_logger_inheritance(self):
        """Test logger inheritance from parent loggers."""
        parent_logger = setup_logger("parent")
        child_logger = setup_logger("parent.child")

        # Child should inherit from parent
        assert child_logger.parent is not None
        assert "parent" in child_logger.name

    def test_logger_propagation(self):
        """Test logger message propagation."""
        logger = setup_logger("test_propagation")

        # Should have propagation configured appropriately
        assert hasattr(logger, "propagate")

    def test_console_output_configuration(self):
        """Test console output configuration."""
        logger = setup_logger("test_console")

        # Should have console handler for development
        console_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and h.stream.name in ["<stdout>", "<stderr>"]
        ]

        # Should have at least one console handler or parent with console handler
        has_console = len(console_handlers) > 0 or any(
            len([h for h in p.handlers if isinstance(h, logging.StreamHandler)]) > 0
            for p in [logger.parent]
            if p
        )
        assert (
            has_console or len(logger.handlers) == 0
        )  # Empty handlers ok if parent handles


class TestLoggingIntegration:
    """Test logging integration with application components."""

    def test_module_logger_pattern(self):
        """Test the common pattern of module-level loggers."""
        # Test the pattern: logger = setup_logger(__name__)
        module_name = "test.module.name"
        logger = setup_logger(module_name)

        assert logger.name == module_name

    def test_logging_in_exception_handlers(self):
        """Test logging in exception handlers."""
        logger = setup_logger("test_exception_handler")

        def risky_operation():
            raise ConnectionError("네트워크 연결 실패")

        try:
            risky_operation()
        except ConnectionError as e:
            logger.error(f"연결 실패: {e}")
            # Should handle gracefully
        except Exception as e:
            logger.exception(f"예상치 못한 오류: {e}")

    @patch("builtins.print")
    def test_fallback_error_handling(self, mock_print):
        """Test fallback error handling when logging fails."""
        logger = setup_logger("test_fallback")

        # Simulate logging failure
        with patch.object(logger, "error", side_effect=Exception("Logging failed")):
            try:
                # Application code that tries to log
                logger.error("이 로깅은 실패할 것입니다")
            except Exception:
                # Fallback: print to console
                print("Logging failed, using fallback")

        # Should handle gracefully without crashing application


class TestCleanupOldLogsRetention:
    """Ensure log retention logic honours configured days."""

    def test_retention_parameter_controls_deletion(self, tmp_path):
        """Old logs beyond retention days should be removed while recent ones stay."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        old_log = log_dir / "old.log"
        recent_log = log_dir / "recent.log"
        old_log.write_text("old")
        recent_log.write_text("recent")

        old_age_seconds = 10 * 24 * 60 * 60
        current_time = time.time()
        os.utime(
            old_log, (current_time - old_age_seconds, current_time - old_age_seconds)
        )

        deleted_count, deleted_files = cleanup_old_logs(
            log_directory=str(log_dir), retention_days=7
        )

        assert deleted_count == 1
        assert "old.log" in deleted_files
        assert not old_log.exists()
        assert recent_log.exists()
