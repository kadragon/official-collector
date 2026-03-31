"""Tests for .bandit configuration file format and bandit workflow."""

import configparser
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestBanditConfig:
    """Verify .bandit is valid INI format that bandit can parse."""

    def test_bandit_config_is_valid_ini(self):
        """Bandit uses configparser to read .bandit — the file must be valid INI."""
        config = configparser.ConfigParser()
        bandit_path = PROJECT_ROOT / ".bandit"

        # configparser.read returns list of successfully parsed files
        parsed = config.read(str(bandit_path))
        assert str(bandit_path) in parsed, ".bandit file could not be parsed as INI"

    def test_bandit_config_excludes_tests_directory(self):
        """The [bandit] section must exclude the tests directory."""
        config = configparser.ConfigParser()
        config.read(str(PROJECT_ROOT / ".bandit"))

        assert config.has_section("bandit"), ".bandit must have a [bandit] section"

        exclude = config.get("bandit", "exclude", fallback=None)
        assert exclude is not None, "[bandit] section must have an 'exclude' key"
        assert "tests" in exclude, "'tests' must be listed in exclude"


class TestBanditWorkflow:
    """Verify bandit.yml workflow excluded_paths has no redundant test patterns."""

    def test_workflow_excluded_paths_no_redundant_test_patterns(self):
        """excluded_paths should not duplicate test exclusions already in .bandit."""
        workflow_path = PROJECT_ROOT / ".github" / "workflows" / "bandit.yml"
        text = workflow_path.read_text()

        match = re.search(r"excluded_paths:\s*(.+)", text)
        assert match is not None, "excluded_paths not found in bandit.yml"
        excluded_paths = match.group(1).strip()

        paths = [p.strip() for p in excluded_paths.split(",") if p.strip()]
        test_patterns = [p for p in paths if p.startswith("tests")]
        assert test_patterns == [], (
            f"Redundant test patterns in excluded_paths: {test_patterns}. "
            "Test exclusion is handled by .bandit INI config."
        )
