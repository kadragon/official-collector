"""
API quota and budget management module
Tracks API usage, costs, and enforces budget limits
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from enum import Enum

from config import OpenAIPricingConfig

logger = logging.getLogger(__name__)


class QuotaStatus(Enum):
    """Quota status levels"""

    OK = "ok"  # Under 70% of budget
    WARNING = "warning"  # 70-90% of budget
    CRITICAL = "critical"  # 90-100% of budget
    EXCEEDED = "exceeded"  # Over budget


@dataclass
class QuotaMetrics:
    """Quota usage metrics"""

    total_tokens: int = 0
    total_requests: int = 0
    total_cost_usd: float = 0.0
    period_start: datetime = field(default_factory=datetime.now)
    last_reset: datetime = field(default_factory=datetime.now)

    def reset(self) -> None:
        """Reset metrics"""
        self.total_tokens = 0
        self.total_requests = 0
        self.total_cost_usd = 0.0
        self.last_reset = datetime.now()


@dataclass
class BudgetConfig:
    """Budget configuration"""

    daily_budget_usd: float = 10.0  # Default: $10/day
    monthly_budget_usd: float = 300.0  # Default: $300/month
    warning_threshold: float = 0.7  # Warn at 70%
    critical_threshold: float = 0.9  # Critical at 90%
    auto_stop_on_exceed: bool = False  # Stop API calls when exceeded


class QuotaManager:
    """
    API quota and budget manager.
    Tracks API usage, costs, and enforces budget limits.
    """

    def __init__(
        self,
        budget_config: Optional[BudgetConfig] = None,
        enable_enforcement: bool = True,
    ):
        """
        Initialize quota manager.

        Args:
            budget_config: Budget configuration (uses defaults if None)
            enable_enforcement: Whether to enforce quota limits
        """
        # Load budget from environment or use defaults
        self.budget_config = budget_config or self._load_budget_from_env()
        self.enable_enforcement = enable_enforcement

        # Metrics by period
        self.daily_metrics = QuotaMetrics()
        self.monthly_metrics = QuotaMetrics()

        # Alert tracking (avoid duplicate alerts)
        self.last_daily_alert_status: Optional[QuotaStatus] = None
        self.last_monthly_alert_status: Optional[QuotaStatus] = None

        logger.info(
            "QuotaManager initialized - Daily: $%.2f, Monthly: $%.2f, Enforcement: %s",
            self.budget_config.daily_budget_usd,
            self.budget_config.monthly_budget_usd,
            "enabled" if enable_enforcement else "disabled",
        )

    def _load_budget_from_env(self) -> BudgetConfig:
        """Load budget configuration from environment variables"""
        return BudgetConfig(
            daily_budget_usd=float(
                os.getenv("OPENAI_DAILY_BUDGET_USD", "10.0")
            ),
            monthly_budget_usd=float(
                os.getenv("OPENAI_MONTHLY_BUDGET_USD", "300.0")
            ),
            warning_threshold=float(os.getenv("QUOTA_WARNING_THRESHOLD", "0.7")),
            critical_threshold=float(os.getenv("QUOTA_CRITICAL_THRESHOLD", "0.9")),
            auto_stop_on_exceed=os.getenv("QUOTA_AUTO_STOP", "false").lower()
            == "true",
        )

    def _check_reset_needed(self) -> None:
        """Check if metrics need to be reset (daily/monthly)"""
        now = datetime.now()

        # Check daily reset (if last reset was yesterday or earlier)
        if self.daily_metrics.last_reset.date() < now.date():
            logger.info(
                "Resetting daily quota metrics (previous usage: $%.4f)",
                self.daily_metrics.total_cost_usd,
            )
            self.daily_metrics.reset()
            self.last_daily_alert_status = None

        # Check monthly reset (if last reset was in previous month)
        if (
            self.monthly_metrics.last_reset.year < now.year
            or self.monthly_metrics.last_reset.month < now.month
        ):
            logger.info(
                "Resetting monthly quota metrics (previous usage: $%.4f)",
                self.monthly_metrics.total_cost_usd,
            )
            self.monthly_metrics.reset()
            self.last_monthly_alert_status = None

    def record_api_usage(
        self,
        token_count: int,
        cost_per_1k_tokens: Optional[float] = None,
    ) -> None:
        """
        Record API usage and update metrics.

        Args:
            token_count: Number of tokens used
            cost_per_1k_tokens: Cost per 1K tokens (uses default if None)
        """
        # Check if reset needed
        self._check_reset_needed()

        # Calculate cost
        if cost_per_1k_tokens is None:
            cost_per_1k_tokens = OpenAIPricingConfig.TEXT_EMBEDDING_3_SMALL_PRICE
        cost_usd = (token_count / 1000.0) * cost_per_1k_tokens

        # Update metrics
        self.daily_metrics.total_tokens += token_count
        self.daily_metrics.total_requests += 1
        self.daily_metrics.total_cost_usd += cost_usd

        self.monthly_metrics.total_tokens += token_count
        self.monthly_metrics.total_requests += 1
        self.monthly_metrics.total_cost_usd += cost_usd

        # Check thresholds and alert
        self._check_thresholds()

    def _check_thresholds(self) -> None:
        """Check budget thresholds and trigger alerts if needed"""
        # Check daily budget
        daily_status = self._get_quota_status(
            self.daily_metrics.total_cost_usd,
            self.budget_config.daily_budget_usd,
        )
        if daily_status != self.last_daily_alert_status:
            self._trigger_quota_alert("daily", daily_status)
            self.last_daily_alert_status = daily_status

        # Check monthly budget
        monthly_status = self._get_quota_status(
            self.monthly_metrics.total_cost_usd,
            self.budget_config.monthly_budget_usd,
        )
        if monthly_status != self.last_monthly_alert_status:
            self._trigger_quota_alert("monthly", monthly_status)
            self.last_monthly_alert_status = monthly_status

    def _get_quota_status(self, current: float, budget: float) -> QuotaStatus:
        """Determine quota status based on usage"""
        ratio = current / budget if budget > 0 else 0

        if ratio >= 1.0:
            return QuotaStatus.EXCEEDED
        elif ratio >= self.budget_config.critical_threshold:
            return QuotaStatus.CRITICAL
        elif ratio >= self.budget_config.warning_threshold:
            return QuotaStatus.WARNING
        else:
            return QuotaStatus.OK

    def _trigger_quota_alert(self, period: str, status: QuotaStatus) -> None:
        """Trigger quota alert"""
        metrics = (
            self.daily_metrics if period == "daily" else self.monthly_metrics
        )
        budget = (
            self.budget_config.daily_budget_usd
            if period == "daily"
            else self.budget_config.monthly_budget_usd
        )

        usage_percent = (
            (metrics.total_cost_usd / budget * 100) if budget > 0 else 0
        )

        message = (
            f"{period.upper()} quota {status.value}: "
            f"${metrics.total_cost_usd:.4f} / ${budget:.2f} ({usage_percent:.1f}%)"
        )

        if status == QuotaStatus.OK:
            logger.info(message)
        elif status == QuotaStatus.WARNING:
            logger.warning(message)
        elif status == QuotaStatus.CRITICAL:
            logger.error(message)
        elif status == QuotaStatus.EXCEEDED:
            logger.critical(message)

    def can_make_request(
        self, estimated_tokens: Optional[int] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a request can be made within budget.

        Args:
            estimated_tokens: Estimated token count for the request

        Returns:
            Tuple of (can_proceed, reason_if_not)
        """
        if not self.enable_enforcement:
            return True, None

        # Check if reset needed
        self._check_reset_needed()

        # Check if already exceeded
        if self.daily_metrics.total_cost_usd >= self.budget_config.daily_budget_usd:
            if self.budget_config.auto_stop_on_exceed:
                return False, "Daily budget exceeded"

        if (
            self.monthly_metrics.total_cost_usd
            >= self.budget_config.monthly_budget_usd
        ):
            if self.budget_config.auto_stop_on_exceed:
                return False, "Monthly budget exceeded"

        # Estimate cost if tokens provided
        if estimated_tokens:
            estimated_cost = (
                estimated_tokens / 1000.0
            ) * OpenAIPricingConfig.TEXT_EMBEDDING_3_SMALL_PRICE

            # Check if this request would exceed daily budget
            if (
                self.daily_metrics.total_cost_usd + estimated_cost
                > self.budget_config.daily_budget_usd
            ):
                if self.budget_config.auto_stop_on_exceed:
                    return False, "Request would exceed daily budget"

        return True, None

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get current usage summary"""
        self._check_reset_needed()

        return {
            "daily": {
                "cost_usd": self.daily_metrics.total_cost_usd,
                "budget_usd": self.budget_config.daily_budget_usd,
                "tokens": self.daily_metrics.total_tokens,
                "requests": self.daily_metrics.total_requests,
                "usage_percent": (
                    self.daily_metrics.total_cost_usd
                    / self.budget_config.daily_budget_usd
                    * 100
                )
                if self.budget_config.daily_budget_usd > 0
                else 0,
                "status": self._get_quota_status(
                    self.daily_metrics.total_cost_usd,
                    self.budget_config.daily_budget_usd,
                ).value,
                "period_start": self.daily_metrics.period_start.isoformat(),
            },
            "monthly": {
                "cost_usd": self.monthly_metrics.total_cost_usd,
                "budget_usd": self.budget_config.monthly_budget_usd,
                "tokens": self.monthly_metrics.total_tokens,
                "requests": self.monthly_metrics.total_requests,
                "usage_percent": (
                    self.monthly_metrics.total_cost_usd
                    / self.budget_config.monthly_budget_usd
                    * 100
                )
                if self.budget_config.monthly_budget_usd > 0
                else 0,
                "status": self._get_quota_status(
                    self.monthly_metrics.total_cost_usd,
                    self.budget_config.monthly_budget_usd,
                ).value,
                "period_start": self.monthly_metrics.period_start.isoformat(),
            },
            "enforcement_enabled": self.enable_enforcement,
            "auto_stop_on_exceed": self.budget_config.auto_stop_on_exceed,
        }


# Global quota manager instance
_quota_manager: Optional[QuotaManager] = None


def get_quota_manager() -> QuotaManager:
    """Get global quota manager instance (singleton)"""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = QuotaManager()
    return _quota_manager


def init_quota_manager(
    budget_config: Optional[BudgetConfig] = None,
    enable_enforcement: bool = True,
) -> QuotaManager:
    """
    Initialize global quota manager with custom settings.

    Args:
        budget_config: Budget configuration
        enable_enforcement: Whether to enforce quota limits

    Returns:
        Configured QuotaManager instance
    """
    global _quota_manager
    _quota_manager = QuotaManager(
        budget_config=budget_config,
        enable_enforcement=enable_enforcement,
    )
    return _quota_manager
