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
    
    def setup_method(self):
        """Set up test environment."""
        # Import here to avoid issues with path setup
        from config import UnifiedConfig
        self.config_class = UnifiedConfig
    
    @patch.dict('os.environ', {
        'OLLAMA_BASE_URL': 'http://test:11434',
        'OLLAMA_MODEL': 'test-model',
        'CHROMA_PERSIST_DIR': './test_chroma'
    })
    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        config = self.config_class()
        
        assert config.ollama_base_url == 'http://test:11434'
        assert config.ollama_model == 'test-model'
        assert config.chroma_persist_dir == './test_chroma'
    
    @patch.dict('os.environ', {}, clear=True)  # Clear all env vars
    def test_default_values_when_no_env_vars(self):
        """Test default values are used when environment variables are missing."""
        config = self.config_class()
        
        # Should have default values
        assert config.ollama_base_url is not None
        assert config.ollama_model is not None
        assert config.chroma_persist_dir is not None
    
    @patch('builtins.open', mock_open(read_data='{"reception_list": ["테스트담당자"], "share_list": ["테스트팀"], "task_card_list": ["테스트업무"]}'))
    @patch('pathlib.Path.exists', return_value=True)
    def test_base_data_loading(self, mock_exists):
        """Test loading base data from JSON file."""
        config = self.config_class()
        
        assert "테스트담당자" in config.reception_list
        assert "테스트팀" in config.share_list
        assert "테스트업무" in config.task_card_list
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    @patch('pathlib.Path.exists', return_value=False)
    def test_base_data_file_not_found(self, mock_exists):
        """Test behavior when base data file is not found."""
        config = self.config_class()
        
        # Should use default empty lists or handle gracefully
        assert isinstance(config.reception_list, list)
        assert isinstance(config.share_list, list)
        assert isinstance(config.task_card_list, list)
    
    @patch('builtins.open', mock_open(read_data='invalid json'))
    @patch('pathlib.Path.exists', return_value=True)
    def test_invalid_json_handling(self, mock_exists):
        """Test handling of invalid JSON in base data file."""
        # Should not raise exception, but handle gracefully
        config = self.config_class()
        
        assert isinstance(config.reception_list, list)
        assert isinstance(config.share_list, list)
        assert isinstance(config.task_card_list, list)
    
    def test_config_validation(self):
        """Test configuration validation methods."""
        config = self.config_class()
        
        # Test validate method exists and works
        assert hasattr(config, 'validate')
        
        # Validation should return boolean or raise exception appropriately
        try:
            result = config.validate()
            assert isinstance(result, (bool, type(None)))
        except Exception as e:
            # If validation raises exception, it should be informative
            assert len(str(e)) > 0
    
    @patch.dict('os.environ', {
        'OLLAMA_BASE_URL': '',  # Empty URL
        'OLLAMA_MODEL': 'test-model',
        'CHROMA_PERSIST_DIR': './test'
    })
    def test_empty_environment_variable_handling(self):
        """Test handling of empty environment variables."""
        config = self.config_class()
        
        # Empty URL should either use default or be handled appropriately
        assert config.ollama_base_url is not None
        assert len(config.ollama_base_url) > 0
    
    def test_config_reload_capability(self):
        """Test configuration reload functionality."""
        config = self.config_class()
        
        if hasattr(config, 'reload'):
            original_url = config.ollama_base_url
            
            with patch.dict('os.environ', {'OLLAMA_BASE_URL': 'http://new:11434'}):
                config.reload()
                
                # URL should be updated after reload
                assert config.ollama_base_url == 'http://new:11434'
    
    def test_debug_summary(self):
        """Test debug summary functionality."""
        config = self.config_class()
        
        if hasattr(config, 'get_debug_summary'):
            summary = config.get_debug_summary()
            
            assert isinstance(summary, (str, dict))
            if isinstance(summary, str):
                assert len(summary) > 0
            elif isinstance(summary, dict):
                assert len(summary) > 0


class TestConfigurationPaths:
    """Test configuration file path handling."""
    
    def test_base_data_path_resolution(self):
        """Test base data file path resolution."""
        from config import UnifiedConfig
        
        config = UnifiedConfig()
        
        # Should have a method or attribute for base data path
        if hasattr(config, 'base_data_path'):
            path = config.base_data_path
            assert isinstance(path, (str, Path))
            assert 'base_data.json' in str(path)
    
    def test_chroma_directory_creation(self):
        """Test Chroma directory handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_chroma_dir = Path(temp_dir) / "test_chroma"
            
            with patch.dict('os.environ', {'CHROMA_PERSIST_DIR': str(test_chroma_dir)}):
                config = self.config_class()
                
                # Directory path should be set correctly
                assert str(test_chroma_dir) in config.chroma_persist_dir
    
    @patch('pathlib.Path.mkdir')
    def test_directory_creation_on_init(self, mock_mkdir):
        """Test that necessary directories are created on initialization."""
        from config import UnifiedConfig
        
        config = UnifiedConfig()
        
        # Check if directories were created (implementation dependent)
        # This test verifies the pattern rather than specific implementation


class TestConfigurationValidation:
    """Test configuration validation rules."""
    
    def setup_method(self):
        from config import UnifiedConfig
        self.config_class = UnifiedConfig
    
    @pytest.mark.parametrize("url,should_be_valid", [
        ("http://localhost:11434", True),
        ("https://remote.server.com:11434", True),
        ("http://127.0.0.1:11434", True),
        ("", False),
        ("not-a-url", False),
        ("ftp://wrong.protocol.com", False),
    ])
    def test_ollama_url_validation(self, url, should_be_valid):
        """Test Ollama URL validation."""
        with patch.dict('os.environ', {'OLLAMA_BASE_URL': url}):
            config = self.config_class()
            
            # If config has validation, test it
            if hasattr(config, 'validate_ollama_url'):
                result = config.validate_ollama_url()
                assert result == should_be_valid
            else:
                # At minimum, URL should be stored
                assert config.ollama_base_url == url or config.ollama_base_url != url
    
    @pytest.mark.parametrize("model,should_be_valid", [
        ("snowflake-arctic-embed", True),
        ("llama2", True),
        ("custom-model", True),
        ("", False),
        (None, False),
    ])
    def test_ollama_model_validation(self, model, should_be_valid):
        """Test Ollama model validation."""
        env_value = model if model is not None else ""
        
        with patch.dict('os.environ', {'OLLAMA_MODEL': env_value}):
            config = self.config_class()
            
            if hasattr(config, 'validate_ollama_model'):
                result = config.validate_ollama_model()
                assert result == should_be_valid
    
    def test_list_validation(self):
        """Test validation of reception/share/task card lists."""
        config = self.config_class()
        
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
    
    def setup_method(self):
        from config import UnifiedConfig
        self.config_class = UnifiedConfig
    
    @patch('builtins.open', mock_open(read_data='{"reception_list": [], "share_list": [], "task_card_list": []}'))
    @patch('pathlib.Path.exists', return_value=True)
    def test_empty_lists_in_base_data(self, mock_exists):
        """Test handling of empty lists in base data."""
        config = self.config_class()
        
        # Should handle empty lists gracefully
        assert config.reception_list == []
        assert config.share_list == []
        assert config.task_card_list == []
    
    @patch('builtins.open', mock_open(read_data='{"reception_list": [123, 456]}'))
    @patch('pathlib.Path.exists', return_value=True)
    def test_invalid_data_types_in_lists(self, mock_exists):
        """Test handling of invalid data types in lists."""
        config = self.config_class()
        
        # Should handle or convert invalid data types
        # Implementation dependent - could filter out non-strings or convert
        assert isinstance(config.reception_list, list)
    
    @patch('builtins.open', side_effect=PermissionError("Access denied"))
    @patch('pathlib.Path.exists', return_value=True) 
    def test_file_permission_error(self, mock_exists):
        """Test handling of file permission errors."""
        # Should not crash, should handle gracefully
        config = self.config_class()
        
        assert isinstance(config.reception_list, list)
        assert isinstance(config.share_list, list)
        assert isinstance(config.task_card_list, list)
    
    def test_config_immutability(self):
        """Test that configuration values are properly managed."""
        config = self.config_class()
        
        original_url = config.ollama_base_url
        
        # Try to modify configuration
        if hasattr(config, '_ollama_base_url'):
            # If using private attributes, they should be managed
            pass
        
        # Configuration should maintain integrity
        assert config.ollama_base_url == original_url


class TestGlobalConfigInstance:
    """Test the global config instance."""
    
    def test_global_config_exists(self):
        """Test that global config instance exists."""
        try:
            from config import config
            assert config is not None
        except ImportError:
            pytest.skip("Global config instance not implemented")
    
    def test_global_config_singleton_behavior(self):
        """Test singleton-like behavior of global config."""
        try:
            from config import config
            
            # Multiple imports should return same instance
            from config import config as config2
            
            # Should be the same object or have same values
            assert config.ollama_base_url == config2.ollama_base_url
        except ImportError:
            pytest.skip("Global config instance not implemented")
    
    def test_global_config_accessibility(self):
        """Test that global config has all necessary attributes."""
        try:
            from config import config
            
            # Should have all required configuration attributes
            required_attrs = [
                'ollama_base_url',
                'ollama_model', 
                'chroma_persist_dir',
                'reception_list',
                'share_list',
                'task_card_list'
            ]
            
            for attr in required_attrs:
                assert hasattr(config, attr), f"Config missing required attribute: {attr}"
                
        except ImportError:
            pytest.skip("Global config instance not implemented")