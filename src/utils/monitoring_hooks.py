"""
Monitoring hooks for tracking system health and alerting
Provides hooks for critical failures, performance degradation, and quota violations
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels"""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertType(Enum):
    """Types of alerts"""

    API_FAILURE = "api_failure"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    QUOTA_VIOLATION = "quota_violation"
    DATABASE_ERROR = "database_error"
    COST_THRESHOLD = "cost_threshold"
    RATE_LIMIT = "rate_limit"


@dataclass
class Alert:
    """Alert data structure"""

    level: AlertLevel
    alert_type: AlertType
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "level": self.level.value,
            "type": self.alert_type.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "source": self.source,
        }


@dataclass
class HealthMetrics:
    """System health metrics"""

    api_success_rate: float = 1.0  # 0.0 to 1.0
    avg_response_time_ms: float = 0.0
    error_count: int = 0
    total_requests: int = 0
    last_error_time: Optional[datetime] = None
    consecutive_failures: int = 0

    def update_success(self, response_time_ms: float) -> None:
        """Update metrics for successful request"""
        self.total_requests += 1
        self.consecutive_failures = 0

        # Update rolling average response time
        if self.total_requests == 1:
            self.avg_response_time_ms = response_time_ms
        else:
            # Exponential moving average (weight: 0.3)
            self.avg_response_time_ms = (
                0.3 * response_time_ms + 0.7 * self.avg_response_time_ms
            )

        # Update success rate
        self.api_success_rate = (
            self.total_requests - self.error_count
        ) / self.total_requests

    def update_failure(self) -> None:
        """Update metrics for failed request"""
        self.total_requests += 1
        self.error_count += 1
        self.consecutive_failures += 1
        self.last_error_time = datetime.now()

        # Update success rate
        self.api_success_rate = (
            self.total_requests - self.error_count
        ) / self.total_requests


class MonitoringHooks:
    """
    Monitoring hooks for tracking system health and alerting.
    Provides centralized monitoring for API calls, performance, and quotas.
    """

    def __init__(
        self,
        performance_threshold_ms: float = 5000.0,
        error_rate_threshold: float = 0.1,  # 10% error rate
        consecutive_failure_threshold: int = 3,
    ):
        """
        Initialize monitoring hooks.

        Args:
            performance_threshold_ms: Alert if response time exceeds this (ms)
            error_rate_threshold: Alert if error rate exceeds this (0.0 to 1.0)
            consecutive_failure_threshold: Alert after N consecutive failures
        """
        self.performance_threshold_ms = performance_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.consecutive_failure_threshold = consecutive_failure_threshold

        # Health metrics by service
        self.metrics: Dict[str, HealthMetrics] = {}

        # Alert history (keep last 100)
        self.alert_history: List[Alert] = []
        self.max_alert_history = 100

        # Alert callbacks
        self.alert_callbacks: List[Callable[[Alert], None]] = []

    def register_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """
        Register a callback to be called when alerts are triggered.

        Args:
            callback: Function that accepts Alert object
        """
        self.alert_callbacks.append(callback)

    def _trigger_alert(self, alert: Alert) -> None:
        """Trigger an alert"""
        # Add to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_alert_history:
            self.alert_history.pop(0)

        # Log alert
        log_method = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical,
        }.get(alert.level, logger.info)

        log_method(
            "[MONITORING] %s Alert: %s - %s",
            alert.level.value,
            alert.alert_type.value,
            alert.message,
        )

        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error("Alert callback failed: %s", e)

    def record_api_call(
        self,
        service: str,
        success: bool,
        response_time_ms: float,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Record an API call result and check thresholds.

        Args:
            service: Service name (e.g., "openai", "supabase")
            success: Whether the call succeeded
            response_time_ms: Response time in milliseconds
            error_message: Error message if failed
        """
        # Initialize metrics if needed
        if service not in self.metrics:
            self.metrics[service] = HealthMetrics()

        metrics = self.metrics[service]

        if success:
            metrics.update_success(response_time_ms)

            # Check performance degradation
            if response_time_ms > self.performance_threshold_ms:
                self._trigger_alert(
                    Alert(
                        level=AlertLevel.WARNING,
                        alert_type=AlertType.PERFORMANCE_DEGRADATION,
                        message=f"{service} response time exceeded threshold",
                        details={
                            "response_time_ms": response_time_ms,
                            "threshold_ms": self.performance_threshold_ms,
                            "avg_response_time_ms": metrics.avg_response_time_ms,
                        },
                        source=service,
                    )
                )
        else:
            metrics.update_failure()

            # Check consecutive failures
            if metrics.consecutive_failures >= self.consecutive_failure_threshold:
                self._trigger_alert(
                    Alert(
                        level=AlertLevel.ERROR,
                        alert_type=AlertType.API_FAILURE,
                        message=f"{service} experienced {metrics.consecutive_failures} consecutive failures",
                        details={
                            "consecutive_failures": metrics.consecutive_failures,
                            "error_message": error_message,
                            "last_error_time": metrics.last_error_time.isoformat()
                            if metrics.last_error_time
                            else None,
                        },
                        source=service,
                    )
                )

            # Check error rate
            if metrics.api_success_rate < (1.0 - self.error_rate_threshold):
                self._trigger_alert(
                    Alert(
                        level=AlertLevel.WARNING,
                        alert_type=AlertType.API_FAILURE,
                        message=f"{service} error rate exceeded threshold",
                        details={
                            "success_rate": metrics.api_success_rate,
                            "error_count": metrics.error_count,
                            "total_requests": metrics.total_requests,
                            "threshold": self.error_rate_threshold,
                        },
                        source=service,
                    )
                )

    def record_database_error(
        self, operation: str, error_message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a database error"""
        self._trigger_alert(
            Alert(
                level=AlertLevel.ERROR,
                alert_type=AlertType.DATABASE_ERROR,
                message=f"Database error during {operation}",
                details={
                    "operation": operation,
                    "error_message": error_message,
                    **(details or {}),
                },
                source="supabase",
            )
        )

    def record_rate_limit(
        self, service: str, retry_after: Optional[int] = None
    ) -> None:
        """Record a rate limit event"""
        self._trigger_alert(
            Alert(
                level=AlertLevel.WARNING,
                alert_type=AlertType.RATE_LIMIT,
                message=f"{service} rate limit exceeded",
                details={
                    "retry_after_seconds": retry_after,
                },
                source=service,
            )
        )

    def get_health_status(self, service: Optional[str] = None) -> Dict[str, Any]:
        """
        Get health status for a service or all services.

        Args:
            service: Service name, or None for all services

        Returns:
            Dictionary with health metrics
        """
        if service:
            if service not in self.metrics:
                return {"status": "unknown", "message": "No metrics available"}

            metrics = self.metrics[service]
            return {
                "service": service,
                "status": "healthy"
                if metrics.api_success_rate > 0.9 and metrics.consecutive_failures == 0
                else "degraded"
                if metrics.api_success_rate > 0.8
                else "unhealthy",
                "success_rate": metrics.api_success_rate,
                "avg_response_time_ms": metrics.avg_response_time_ms,
                "error_count": metrics.error_count,
                "total_requests": metrics.total_requests,
                "consecutive_failures": metrics.consecutive_failures,
                "last_error_time": metrics.last_error_time.isoformat()
                if metrics.last_error_time
                else None,
            }
        else:
            # Return all services
            return {
                service_name: self.get_health_status(service_name)
                for service_name in self.metrics.keys()
            }

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        return [alert.to_dict() for alert in self.alert_history[-limit:]]

    def reset_metrics(self, service: Optional[str] = None) -> None:
        """Reset metrics for a service or all services"""
        if service:
            if service in self.metrics:
                self.metrics[service] = HealthMetrics()
        else:
            self.metrics.clear()


# Global monitoring hooks instance
_monitoring_hooks: Optional[MonitoringHooks] = None


def get_monitoring_hooks() -> MonitoringHooks:
    """Get global monitoring hooks instance (singleton)"""
    global _monitoring_hooks
    if _monitoring_hooks is None:
        _monitoring_hooks = MonitoringHooks()
    return _monitoring_hooks


def init_monitoring_hooks(
    performance_threshold_ms: float = 5000.0,
    error_rate_threshold: float = 0.1,
    consecutive_failure_threshold: int = 3,
) -> MonitoringHooks:
    """
    Initialize global monitoring hooks with custom settings.

    Args:
        performance_threshold_ms: Alert if response time exceeds this (ms)
        error_rate_threshold: Alert if error rate exceeds this (0.0 to 1.0)
        consecutive_failure_threshold: Alert after N consecutive failures

    Returns:
        Configured MonitoringHooks instance
    """
    global _monitoring_hooks
    _monitoring_hooks = MonitoringHooks(
        performance_threshold_ms=performance_threshold_ms,
        error_rate_threshold=error_rate_threshold,
        consecutive_failure_threshold=consecutive_failure_threshold,
    )
    return _monitoring_hooks
