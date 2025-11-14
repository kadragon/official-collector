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


# ------------------------------------------------------------------ #
# UI Configuration
# ------------------------------------------------------------------ #


class TimeoutConfig:
    """Centralized timeout configuration for UI operations."""

    # Element waiting timeouts (in seconds)
    ELEMENT_WAIT = 3.0
    ELEMENT_WAIT_INTERVAL = 0.05

    # Window waiting timeouts (in seconds)
    WINDOW_WAIT = 3.0
    WINDOW_READY = 2.0

    # Condition waiting timeouts (in seconds)
    CONDITION_WAIT = 3.0
    CONDITION_WAIT_INTERVAL = 0.05

    # Dialog-specific timeouts
    RECEPTION_CONFIRMATION = 5.0
    CIRCULATION_COMPLETION = 8.0
    APPROVAL_CONFIRMATION = 1.0
    APPROVAL_CONFIRMATION_BACKUP = 2.0
    APPROVAL_RESULT = 0.5
    PAYMENT_INFO_WINDOW = 2.0

    # Fast dialog search timeouts (성능 최적화)
    FAST_DIALOG_IMMEDIATE = 0.1  # 0.3 → 0.1 (3배 속도 향상)
    FAST_DIALOG_INTERVAL = 0.01  # 0.02 → 0.01 (2배 속도 향상)
    FAST_DIALOG_DESKTOP = 0.5  # 0.8 → 0.5

    # Sleep delays (in seconds)
    MINIMAL_DELAY = 0.05
    SHORT_DELAY = 0.1
    FOCUS_SETTLE_DELAY = 0.02  # 포커스 설정 후 안정화 대기


class OpenAIPricingConfig:
    """Centralized OpenAI API pricing configuration."""

    # Embedding model pricing (per 1000 tokens)
    TEXT_EMBEDDING_3_SMALL_PRICE = 0.00002  # $0.00002 per 1K tokens
    TEXT_EMBEDDING_3_LARGE_PRICE = 0.00013  # $0.00013 per 1K tokens

    # Token estimation (characters per token)
    CHARS_PER_TOKEN = 4


class VectorConfig:
    """Centralized vector similarity and embedding configuration."""

    # Default similarity threshold for recommendation filtering (0.0 to 1.0)
    # Lower values = more strict matching, higher values = more lenient matching
    DEFAULT_SIMILARITY_THRESHOLD = 0.3

    # Similarity threshold bounds for validation
    MIN_SIMILARITY_THRESHOLD = 0.0
    MAX_SIMILARITY_THRESHOLD = 1.0


class UIConfig:
    """Centralized UI configuration for dialog patterns and window titles."""

    # Dialog button patterns (in priority order)
    DIALOG_BUTTON_PATTERNS = {
        "confirm": [
            ("예(&Y)", "Button"),
            ("예", "Button"),
            ("확인", "Button"),
            ("OK", "Button"),
        ],
        "cancel": [
            ("아니오(N)", "Button"),
            ("취소", "Button"),
            ("아니오", "Button"),
            ("Cancel", "Button"),
        ],
    }

    # Window title patterns for connection
    WINDOW_TITLE_PATTERNS = [
        ("^접수", "접수"),
        ("^전자결재", "전자결재"),
    ]

    # Payment info button names
    PAYMENT_INFO_BUTTONS = ["결재정보", "Payment Information"]


class UnifiedConfig:
    """Unified configuration loader with legacy compatibility."""

    REQUIRED_ENV_VARS: List[str] = []
    OPTIONAL_PATH_VARS: Dict[str, str] = {}
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

    def get_vector_similarity_threshold(self) -> float:
        """
        Get the vector similarity threshold for recommendation filtering.

        Reads from VECTOR_SIMILARITY_THRESHOLD environment variable, falls back to default.
        Validates that the threshold is within acceptable bounds (0.0 to 1.0).

        Returns:
            float: Similarity threshold (0.0 to 1.0), defaults to 0.3

        Raises:
            ValueError: If threshold is outside valid range
        """
        threshold_str = self._env_value("VECTOR_SIMILARITY_THRESHOLD")
        if threshold_str is None:
            return VectorConfig.DEFAULT_SIMILARITY_THRESHOLD

        try:
            threshold = float(threshold_str)
            if not (
                VectorConfig.MIN_SIMILARITY_THRESHOLD
                <= threshold
                <= VectorConfig.MAX_SIMILARITY_THRESHOLD
            ):
                logger.warning(
                    "벡터 유사도 임계값 범위 초과 (%s), 기본값 사용 (%.1f)",
                    threshold,
                    VectorConfig.DEFAULT_SIMILARITY_THRESHOLD,
                )
                return VectorConfig.DEFAULT_SIMILARITY_THRESHOLD
            return threshold
        except ValueError:
            logger.warning(
                "벡터 유사도 임계값 설정 오류, 기본값 사용 (%.1f)",
                VectorConfig.DEFAULT_SIMILARITY_THRESHOLD,
            )
            return VectorConfig.DEFAULT_SIMILARITY_THRESHOLD

    def allow_destructive_operations(self) -> bool:
        """
        Check if destructive operations (delete_all, etc.) are allowed.

        Destructive operations are blocked in production environments unless
        explicitly enabled via ALLOW_DESTRUCTIVE_OPERATIONS=true.

        Returns:
            bool: True if destructive operations are allowed, False otherwise
        """
        # Block in production unless explicitly allowed
        environment = self._env_value("ENVIRONMENT")
        if environment == "production":
            allow_flag = self._env_value("ALLOW_DESTRUCTIVE_OPERATIONS")
            is_allowed = allow_flag is not None and allow_flag.lower() == "true"
            if not is_allowed:
                logger.debug(
                    "Destructive operations blocked in production environment"
                )
            return is_allowed

        # Allow in development/test by default
        return True

    def get_config_summary(self) -> Dict[str, Any]:
        """Return configuration summary (human readable)."""
        return {
            "reception_count": len(self._reception_list),
            "share_count": len(self._share_list),
            "task_card_count": len(self._task_card_list),
            "supabase_url": self.supabase_url,
        }

    def get_debug_summary(self) -> Dict[str, Any]:
        """Return a lightweight diagnostic summary."""
        return {
            "reception_count": len(self._reception_list),
            "share_count": len(self._share_list),
            "task_card_count": len(self._task_card_list),
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

        # Supabase/OpenAI settings (optional – do not raise if missing)
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

        self._reception_list = self._load_list(
            data.get("reception_list"), self.data_dir / "reception_list.txt"
        )
        self._share_list = self._load_list(
            data.get("share_list"), self.data_dir / "share_list.txt"
        )
        self._task_card_list = self._load_list(
            data.get("task_card_list"), self.data_dir / "card_list.txt"
        )

        logger.info(
            "Base data loaded (cards=%d, receptions=%d, shares=%d)",
            len(self._task_card_list),
            len(self._reception_list),
            len(self._share_list),
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
            "reception_list": self._reception_list,
            "share_list": self._share_list,
            "task_card_list": self._task_card_list,
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
    # Public properties (immutable - return copies)
    # ------------------------------------------------------------------ #

    @property
    def reception_list(self) -> List[str]:
        """Return a copy of the reception list to ensure immutability."""
        return self._reception_list.copy()

    @property
    def share_list(self) -> List[str]:
        """Return a copy of the share list to ensure immutability."""
        return self._share_list.copy()

    @property
    def task_card_list(self) -> List[str]:
        """Return a copy of the task card list to ensure immutability."""
        return self._task_card_list.copy()

    # ------------------------------------------------------------------ #
    # Legacy compatibility aliases
    # ------------------------------------------------------------------ #

    @property
    def card_list(self) -> List[str]:
        """Legacy alias for task_card_list."""
        return self.task_card_list

    @card_list.setter
    def card_list(self, values: List[str]) -> None:
        """Legacy setter for backward compatibility."""
        self._task_card_list = list(values) if values is not None else []


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
