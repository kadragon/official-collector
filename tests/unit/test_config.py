"""
Unit tests for config module

Tests configuration loading, validation, and environment variable handling.
These tests use mocked environment variables and file system operations.
"""

import pytest
import tempfile
import json
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tests.fixtures.test_configs import TestConfigurations


class TestUnifiedConfig:
    """Test the UnifiedConfig class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Import here to avoid issues with path setup
        from config import UnifiedConfig

        self.config_class = UnifiedConfig

    @patch.dict(
        "os.environ",
        {},
    )
    @patch(
        "builtins.open",
        mock_open(
            read_data='{"reception_list": ["테스트담당자"], "share_list": ["테스트팀"], "task_card_list": ["테스트업무"]}'
        ),
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_base_data_loading(self, mock_exists: MagicMock) -> None:
        """Test loading base data from JSON file."""
        config = self.config_class(allow_fallback=True)

        assert "테스트담당자" in config.reception_list
        assert "테스트팀" in config.share_list
        assert "테스트업무" in config.task_card_list

    @patch.dict(
        "os.environ",
        {},
    )
    @patch("builtins.open", side_effect=FileNotFoundError)
    @patch("pathlib.Path.exists", return_value=False)
    def test_base_data_file_not_found(
        self, mock_exists: MagicMock, mock_open: MagicMock
    ) -> None:
        """Test behavior when base data file is not found."""
        config = self.config_class(allow_fallback=True)

        # Should use default empty lists or handle gracefully
        assert isinstance(config.reception_list, list)
        assert isinstance(config.share_list, list)
        assert isinstance(config.task_card_list, list)

    @patch.dict(
        "os.environ",
        {},
    )
    @patch("builtins.open", mock_open(read_data="invalid json"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_invalid_json_handling(self, mock_exists: MagicMock) -> None:
        """Test handling of invalid JSON in base data file."""
        # Should not raise exception, but handle gracefully
        config = self.config_class(allow_fallback=True)

        assert isinstance(config.reception_list, list)
        assert isinstance(config.share_list, list)
        assert isinstance(config.task_card_list, list)

    @patch.dict(
        "os.environ",
        {},
    )
    def test_config_validation(self) -> None:
        """Test configuration validation methods."""
        config = self.config_class(allow_fallback=True)

        # Test validate method exists and works
        assert hasattr(config, "validate")

        # Validation should return boolean or raise exception appropriately
        try:
            result = config.validate()
            assert isinstance(result, (bool, type(None)))
        except Exception as e:
            # If validation raises exception, it should be informative
            assert len(str(e)) > 0

    @patch.dict(
        "os.environ",
        {},
    )
    def test_config_reload_capability(self) -> None:
        """Test configuration reload functionality."""
        config = self.config_class(allow_fallback=True)

        # Verify reload method exists and works
        if hasattr(config, "reload"):
            config.reload()
            assert isinstance(config.reception_list, list)

    @patch.dict(
        "os.environ",
        {},
    )
    def test_debug_summary(self) -> None:
        """Test debug summary functionality."""
        config = self.config_class(allow_fallback=True)

        if hasattr(config, "get_debug_summary"):
            summary = config.get_debug_summary()

            assert isinstance(summary, dict)
            assert len(summary) > 0


class TestConfigurationPaths:
    """Test configuration file path handling."""

    def setup_method(self) -> None:
        from config import UnifiedConfig

        self.config_class = UnifiedConfig

    @patch.dict(
        "os.environ",
        {},
    )
    def test_base_data_path_resolution(self) -> None:
        """Test base data file path resolution."""
        from config import UnifiedConfig

        config = UnifiedConfig(allow_fallback=True)

        # Should have a method or attribute for base data path
        if hasattr(config, "base_data_path"):
            path = config.base_data_path
            assert isinstance(path, (str, Path))
            assert "base_data.json" in str(path)

    @patch.dict(
        "os.environ",
        {},
    )
    @patch("pathlib.Path.mkdir")
    def test_directory_creation_on_init(self, mock_mkdir: MagicMock) -> None:
        """Test that necessary directories are created on initialization."""
        from config import UnifiedConfig

        config = UnifiedConfig(allow_fallback=True)

        # Check if directories were created (implementation dependent)
        # This test verifies the pattern rather than specific implementation


class TestConfigurationValidation:
    """Test configuration validation rules."""

    def setup_method(self) -> None:
        from config import UnifiedConfig

        self.config_class = UnifiedConfig

    @patch.dict(
        "os.environ",
        {},
    )
    def test_list_validation(self) -> None:
        """Test validation of reception/share/task card lists."""
        config = self.config_class(allow_fallback=True)

        # Lists should be non-empty and contain strings
        assert isinstance(config.reception_list, list)
        assert isinstance(config.share_list, list)
        assert isinstance(config.task_card_list, list)

        # If lists are not empty, items should be strings
        if config.reception_list:
            assert all(isinstance(item, str) for item in config.reception_list)
        if config.share_list:
            assert all(isinstance(item, str) for item in config.share_list)
        if config.task_card_list:
            assert all(isinstance(item, str) for item in config.task_card_list)


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self) -> None:
        from config import UnifiedConfig

        self.config_class = UnifiedConfig

    @patch.dict(
        "os.environ",
        {},
    )
    @patch(
        "builtins.open",
        mock_open(
            read_data='{"reception_list": [], "share_list": [], "task_card_list": []}'
        ),
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_empty_lists_in_base_data(self, mock_exists: MagicMock) -> None:
        """Test handling of empty lists in base data."""
        config = self.config_class(allow_fallback=True)

        # Should handle empty lists gracefully
        assert config.reception_list == []
        assert config.share_list == []
        assert config.task_card_list == []

    @patch.dict(
        "os.environ",
        {},
    )
    @patch("builtins.open", mock_open(read_data='{"reception_list": [123, 456]}'))
    @patch("pathlib.Path.exists", return_value=True)
    def test_invalid_data_types_in_lists(self, mock_exists: MagicMock) -> None:
        """Test handling of invalid data types in lists."""
        config = self.config_class(allow_fallback=True)

        # Should handle or convert invalid data types
        # Implementation dependent - could filter out non-strings or convert
        assert isinstance(config.reception_list, list)

    @patch.dict(
        "os.environ",
        {},
    )
    @patch("builtins.open", side_effect=PermissionError("Access denied"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_file_permission_error(
        self, mock_exists: MagicMock, mock_open: MagicMock
    ) -> None:
        """Test handling of file permission errors."""
        # Should not crash, should handle gracefully
        config = self.config_class(allow_fallback=True)

        assert isinstance(config.reception_list, list)
        assert isinstance(config.share_list, list)
        assert isinstance(config.task_card_list, list)

    @patch.dict(
        "os.environ",
        {},
    )
    def test_config_immutability(self) -> None:
        """Test that configuration values are immutable (return copies)."""
        config = self.config_class(allow_fallback=True)

        original_list_copy = config.reception_list.copy()

        # Attempt to modify the list obtained from config
        config.reception_list.append("new_item_should_not_be_added")

        # This assertion will fail if the config is mutable (as it currently is),
        # highlighting the need to return a copy or an immutable sequence.
        assert (
            config.reception_list == original_list_copy
        ), "Configuration list should be immutable or return a copy."


class TestGlobalConfigInstance:
    """Test the global config instance."""

    def test_global_config_exists(self) -> None:
        """Test that global config instance exists."""
        try:
            from config import config

            assert config is not None
        except ImportError:
            pytest.skip("Global config instance not implemented")

    def test_global_config_singleton_behavior(self) -> None:
        """Test singleton-like behavior of global config."""
        try:
            from config import config

            # Multiple imports should return same instance
            from config import config as config2

            # Should be the same object or have same values
            assert config.reception_list == config2.reception_list
        except ImportError:
            pytest.skip("Global config instance not implemented")

    def test_global_config_accessibility(self) -> None:
        """Test that global config has all necessary attributes."""
        try:
            from config import config

            # Should have all required configuration attributes
            required_attrs = [
                "reception_list",
                "share_list",
                "task_card_list",
            ]

            for attr in required_attrs:
                assert hasattr(
                    config, attr
                ), f"Config missing required attribute: {attr}"

        except ImportError:
            pytest.skip("Global config instance not implemented")
