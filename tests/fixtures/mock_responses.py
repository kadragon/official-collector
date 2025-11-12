"""
Mock responses and service fixtures for testing

This module provides mocked responses for external services
to enable fast, isolated unit testing without dependencies.
"""

from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock


class MockUserInterface:
    """Mocked user interface responses for testing."""

    def __init__(self) -> None:
        self.responses: List[Any] = []  # Queue of responses to return
        self.interactions: List[Dict[str, Any]] = []  # Log of interactions

    def set_responses(self, responses: List[Any]) -> None:
        """Set predefined responses for user interactions."""
        self.responses = responses.copy()

    def mock_user_choice(self, options: List[str], allow_skip: bool = False) -> Any:
        """Mock user selection from options."""
        interaction = {"type": "choice", "options": options, "allow_skip": allow_skip}
        self.interactions.append(interaction)

        if self.responses:
            response = self.responses.pop(0)
            if isinstance(response, int):
                # Return selection result
                from ui.console_interface import SelectionResult

                if 0 <= response < len(options):
                    return SelectionResult.SELECTED, options[response]
                elif response == -1 and allow_skip:
                    return SelectionResult.SKIPPED, None
            return response

        # Default: select first option
        from ui.console_interface import SelectionResult

        return (
            (SelectionResult.SELECTED, options[0])
            if options
            else (SelectionResult.SKIPPED, None)
        )

    def mock_confirmation(self, message: str, default_yes: bool = True) -> bool:
        """Mock user confirmation."""
        interaction = {
            "type": "confirmation",
            "message": message,
            "default_yes": default_yes,
        }
        self.interactions.append(interaction)

        if self.responses:
            response = self.responses.pop(0)
            return bool(response)

        return default_yes  # Default response


class MockFileSystem:
    """Mocked file system operations for testing."""

    def __init__(self) -> None:
        self.files: Dict[str, str] = {}  # path -> content mapping
        self.directories: set[str] = set()

    def create_file(self, path: str, content: str = "") -> None:
        """Create a mock file."""
        self.files[path] = content

    def create_directory(self, path: str) -> None:
        """Create a mock directory."""
        self.directories.add(path)

    def file_exists(self, path: str) -> bool:
        """Check if mock file exists."""
        return path in self.files

    def directory_exists(self, path: str) -> bool:
        """Check if mock directory exists."""
        return path in self.directories

    def read_file(self, path: str) -> Optional[str]:
        """Read mock file content."""
        return self.files.get(path)


class MockEnvironment:
    """Mocked environment variables for testing."""

    def __init__(self) -> None:
        self.variables: Dict[str, str] = {
            "CHROMA_PERSIST_DIR": "./.test_chroma_db",
        }

    def set_variable(self, key: str, value: str) -> None:
        """Set environment variable."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable."""
        return self.variables.get(key, default)

    def unset_variable(self, key: str) -> None:
        """Unset environment variable."""
        self.variables.pop(key, None)
