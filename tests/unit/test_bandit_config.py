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
    """Verify the workflow scans the production source tree."""

    def test_workflow_scans_only_production_source(self):
        workflow_path = PROJECT_ROOT / ".github" / "workflows" / "bandit.yml"
        assert re.search(r"^\s+path: src\s*$", workflow_path.read_text(), re.MULTILINE)
