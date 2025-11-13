"""
Pytest configuration and shared fixtures
"""

import shutil
import pytest
import time
import gc
import sys
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_databases():
    """
    Placeholder for test database cleanup.
    No cleanup needed for cloud-based Supabase.
    """
    # Before tests - no cleanup needed for Supabase (cloud-based)
    yield  # Run all tests
    # After all tests complete - no cleanup needed
