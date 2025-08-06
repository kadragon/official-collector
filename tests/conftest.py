"""
Pytest configuration and shared fixtures
"""
import shutil
import pytest
import time
import gc
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_databases():
    """
    Automatically clean up test databases after all tests complete.
    This runs once per test session and ensures test databases are removed.
    """
    # Before tests - clean up any leftover test databases
    test_db_paths = [
        "./.chroma_db_test",
        ".chroma_db_test"
    ]

    for db_path in test_db_paths:
        if Path(db_path).exists():
            try:
                shutil.rmtree(db_path)
            except Exception:
                pass

    yield  # Run all tests

    # After all tests complete - clean up test databases
    for db_path in test_db_paths:
        if Path(db_path).exists():
            # Force cleanup with multiple attempts
            for attempt in range(5):
                try:
                    gc.collect()  # Force garbage collection
                    time.sleep(0.2)  # Give file handles time to close
                    shutil.rmtree(db_path)
                    break
                except Exception as e:
                    if attempt < 4:
                        time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    else:
                        print(
                            f"Warning: Could not remove test database {db_path}: {e}")
