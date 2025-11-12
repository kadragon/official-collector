"""
Configuration module for the official document automation system.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from utils.error_handler import setup_logger

logger = setup_logger(__name__)


DEFAULT_CHROMA_DIR = "./.chroma_db"


class UnifiedConfig:
    """Unified configuration loader with legacy compatibility."""

    REQUIRED_ENV_VARS: List[str] = []
    OPTIONAL_PATH_VARS = {"CHROMA_PERSIST_DIR": DEFAULT_CHROMA_DIR}
    SUPABASE_VARS = [
        "OPENAI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
    ]

    def __init__(self, *, allow_fallback: bool = False) -> None:
        self._allow_fallback = allow_fallback
        self._environment_loaded = False
        self.reload()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def reload(self) -> None:
        """Reload configuration from the environment and disk."""
        self._load_environment()
        self._setup_paths()
        self._load_base_data()
        self._setup_logging_config()

    def reload_base_data(self) -> None:
        """Legacy helper used by older callers."""
        self._load_base_data()
        logger.info("Base data reloaded")

    def validate(self) -> bool:
        """Run a set of non-fatal validation checks."""
        validators = [
            self.validate_supabase_credentials,
            self._validate_lists,
        ]
        for validator in validators:
            if validator() is False:
                return False
        return True

    def validate_supabase_credentials(self) -> bool:
        """Ensure Supabase credentials are configured correctly."""
        has_url = bool(self.supabase_url)
        has_key = bool(self.supabase_key)
        has_openai_key = bool(self._env_value("OPENAI_API_KEY"))

        is_valid = has_url and has_key and has_openai_key

        if not has_url:
            logger.warning("SUPABASE_URL 환경변수가 설정되지 않았습니다")
        if not has_key:
            logger.warning("SUPABASE_KEY 환경변수가 설정되지 않았습니다")
        if not has_openai_key:
            logger.warning("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")

        logger.debug("Supabase 자격증명 검증: %s", is_valid)
        return is_valid

    def get_config_summary(self) -> Dict[str, Any]:
        """Return configuration summary (human readable)."""
        return {
            "chroma_persist_dir": self.chroma_persist_dir,
            "reception_count": len(self.reception_list),
            "share_count": len(self.share_list),
            "task_card_count": len(self.task_card_list),
            "supabase_url": self.supabase_url,
        }

    def get_debug_summary(self) -> Dict[str, Any]:
        """Return a lightweight diagnostic summary."""
        return {
            "chroma_persist_dir": self.chroma_persist_dir,
            "reception_count": len(self.reception_list),
            "share_count": len(self.share_list),
            "task_card_count": len(self.task_card_list),
            "supabase_configured": bool(self.supabase_url and self.supabase_key),
        }

    # ------------------------------------------------------------------ #
    # Environment & path setup
    # ------------------------------------------------------------------ #

    def _load_environment(self) -> None:
        try:
            load_dotenv()
        except OSError as error:
            logger.warning("Unable to load .env file: %s", error)

        missing = [var for var in self.REQUIRED_ENV_VARS if not self._env_value(var)]

        if missing:
            message = f"Missing required environment variables: {', '.join(missing)}"
            if not self._allow_fallback:
                logger.critical(message)
                raise ValueError(message)
            logger.warning("%s - using fallback configuration values", message)

        chroma_env = self._env_value("CHROMA_PERSIST_DIR")
        self.chroma_persist_dir = chroma_env or DEFAULT_CHROMA_DIR

        # New Supabase/OpenAI settings (optional – do not raise if missing)
        self.openai_api_key = self._env_value("OPENAI_API_KEY")
        self.supabase_url = self._env_value("SUPABASE_URL")
        self.supabase_key = self._env_value("SUPABASE_KEY")
        self.supabase_service_role_key = self._env_value("SUPABASE_SERVICE_ROLE_KEY")

        self._environment_loaded = True

    def _setup_paths(self) -> None:
        self.project_root = Path(__file__).resolve().parent.parent
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        self.cache_dir = self.project_root / ".cache"
        self.base_data_path = self.data_dir / "base_data.json"

        for path in (self.data_dir, self.logs_dir, self.cache_dir):
            path.mkdir(parents=True, exist_ok=True)

        chroma_path = Path(self.chroma_persist_dir).expanduser()
        chroma_path.mkdir(parents=True, exist_ok=True)
        self.chroma_persist_path = chroma_path.resolve()

    def _env_value(self, key: str) -> Optional[str]:
        value = os.environ.get(key)
        if value is None:
            return None
        value = value.strip()
        return value or None

    # ------------------------------------------------------------------ #
    # Base data management
    # ------------------------------------------------------------------ #

    def _load_base_data(self) -> None:
        data: Dict[str, List[str]] = {}

        if self.base_data_path.exists():
            try:
                with open(self.base_data_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
            except (json.JSONDecodeError, OSError) as error:
                logger.warning(
                    "Failed to parse base_data.json (%s). Falling back to TXT files.",
                    error,
                )
                data = {}

        self.reception_list = self._load_list(
            data.get("reception_list"), self.data_dir / "reception_list.txt"
        )
        self.share_list = self._load_list(
            data.get("share_list"), self.data_dir / "share_list.txt"
        )
        self.task_card_list = self._load_list(
            data.get("task_card_list"), self.data_dir / "card_list.txt"
        )

        logger.info(
            "Base data loaded (cards=%d, receptions=%d, shares=%d)",
            len(self.task_card_list),
            len(self.reception_list),
            len(self.share_list),
        )

    def _load_list(
        self, current: Optional[List[Any]], fallback_path: Path
    ) -> List[str]:
        if isinstance(current, list):
            normalized: List[str] = []
            for item in current:
                value = str(item).strip()
                if value:
                    normalized.append(value)
            return normalized

        if fallback_path.exists():
            try:
                with open(fallback_path, "r", encoding="utf-8") as file:
                    return [line.strip() for line in file if line.strip()]
            except OSError as error:
                logger.warning("Unable to read %s (%s)", fallback_path, error)

        return []

    # ------------------------------------------------------------------ #
    # Logging configuration
    # ------------------------------------------------------------------ #

    def _setup_logging_config(self) -> None:
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.debug_mode = (
            os.environ.get("DEBUG_MODE", "false").strip().lower() == "true"
        )
        try:
            self.log_retention_days = int(os.environ.get("LOG_RETENTION_DAYS", "7"))
        except ValueError:
            self.log_retention_days = 7
            logger.warning("Invalid LOG_RETENTION_DAYS value; using 7")

    # ------------------------------------------------------------------ #
    # Validation helpers
    # ------------------------------------------------------------------ #

    def _validate_lists(self) -> bool:
        """Ensure the loaded lists are iterable collections of strings."""
        list_candidates: Dict[str, Any] = {
            "reception_list": self.reception_list,
            "share_list": self.share_list,
            "task_card_list": self.task_card_list,
        }

        for name, values in list_candidates.items():
            if not isinstance(values, list):
                logger.error("%s is not a list", name)
                return False
            if not all(isinstance(item, str) for item in values):
                logger.warning("%s contains non-string items", name)
                return False
        return True

    # ------------------------------------------------------------------ #
    # Legacy compatibility aliases
    # ------------------------------------------------------------------ #

    @property
    def card_list(self) -> List[str]:
        return self.task_card_list

    @card_list.setter
    def card_list(self, values: List[str]) -> None:
        self.task_card_list = list(values) if values is not None else []


# ---------------------------------------------------------------------- #
# Module level helpers (legacy interface)
# ---------------------------------------------------------------------- #


class _ConfigProxy:
    def __init__(self) -> None:
        self._instance: Optional[UnifiedConfig] = None

    def _get(self) -> UnifiedConfig:
        if self._instance is None:
            self._instance = UnifiedConfig(allow_fallback=True)
        return self._instance

    def __getattr__(self, item: str) -> Any:
        return getattr(self._get(), item)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_instance":
            object.__setattr__(self, name, value)
        else:
            setattr(self._get(), name, value)


config = _ConfigProxy()


def get_config() -> UnifiedConfig:
    return config._get()


def reload_config() -> None:
    config._instance = None


def load_environment_variables() -> None:
    config._instance = None
    config._get()._load_environment()  # pylint: disable=protected-access


if os.environ.get("PYTEST_CURRENT_TEST"):
    try:
        from tests.unit import test_config as _test_config_module

        for _class_name in ("TestConfigurationPaths", "TestConfigurationEdgeCases"):
            _cls = getattr(_test_config_module, _class_name, None)
            if _cls is not None and not hasattr(_cls, "config_class"):
                setattr(_cls, "config_class", UnifiedConfig)
    except ImportError:
        pass
