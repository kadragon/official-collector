"""
Audit logging module for tracking critical operations
Provides structured audit logs for compliance and security monitoring
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    """Audit action types for classification"""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SEARCH = "SEARCH"
    API_CALL = "API_CALL"


class AuditResource(Enum):
    """Resource types being audited"""

    RECEPTION_DOCUMENT = "reception_document"
    TASK_CARD = "task_card"
    EMBEDDING = "embedding"
    SUPABASE = "supabase"
    OPENAI = "openai"
    CONFIGURATION = "configuration"


@dataclass
class AuditEntry:
    """Structured audit log entry"""

    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    action: AuditAction = AuditAction.READ
    resource: AuditResource = AuditResource.SUPABASE
    resource_id: Optional[str] = None
    user: str = "system"
    status: str = "success"  # success, failure, error
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result["action"] = self.action.value
        result["resource"] = self.resource.value
        return result

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """
    Audit logger for tracking critical operations.
    Provides structured logging for compliance, security, and debugging.
    """

    def __init__(
        self,
        log_to_file: bool = True,
        audit_log_dir: Optional[Path] = None,
        log_level: int = logging.INFO,
    ):
        """
        Initialize audit logger.

        Args:
            log_to_file: Whether to write audit logs to separate file
            audit_log_dir: Directory for audit log files (default: ./logs/audit)
            log_level: Logging level for audit entries
        """
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(log_level)

        # Set up file handler for audit logs
        if log_to_file:
            if audit_log_dir is None:
                audit_log_dir = Path("./logs/audit")
            audit_log_dir.mkdir(parents=True, exist_ok=True)

            # Rotate daily audit logs
            log_filename = (
                audit_log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
            )

            # JSON Lines format handler
            file_handler = logging.FileHandler(log_filename, encoding="utf-8")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(file_handler)

    def log_entry(self, entry: AuditEntry) -> None:
        """Log an audit entry"""
        # Log to audit logger (file)
        self.logger.info(entry.to_json())

        # Also log to main logger for visibility
        if entry.status == "success":
            logger.debug(
                "[AUDIT] %s %s %s: %s",
                entry.action.value,
                entry.resource.value,
                entry.resource_id or "",
                entry.status,
            )
        else:
            logger.warning(
                "[AUDIT] %s %s %s: %s - %s",
                entry.action.value,
                entry.resource.value,
                entry.resource_id or "",
                entry.status,
                entry.error_message or "",
            )

    def log_create(
        self,
        resource: AuditResource,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Log a CREATE operation"""
        entry = AuditEntry(
            action=AuditAction.CREATE,
            resource=resource,
            resource_id=resource_id,
            status=status,
            details=details or {},
            error_message=error_message,
            duration_ms=duration_ms,
        )
        self.log_entry(entry)

    def log_update(
        self,
        resource: AuditResource,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Log an UPDATE operation"""
        entry = AuditEntry(
            action=AuditAction.UPDATE,
            resource=resource,
            resource_id=resource_id,
            status=status,
            details=details or {},
            error_message=error_message,
            duration_ms=duration_ms,
        )
        self.log_entry(entry)

    def log_delete(
        self,
        resource: AuditResource,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Log a DELETE operation"""
        entry = AuditEntry(
            action=AuditAction.DELETE,
            resource=resource,
            resource_id=resource_id,
            status=status,
            details=details or {},
            error_message=error_message,
            duration_ms=duration_ms,
        )
        self.log_entry(entry)

    def log_api_call(
        self,
        resource: AuditResource,
        endpoint: str,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Log an API call"""
        entry = AuditEntry(
            action=AuditAction.API_CALL,
            resource=resource,
            resource_id=endpoint,
            status=status,
            details=details or {},
            error_message=error_message,
            duration_ms=duration_ms,
        )
        self.log_entry(entry)

    def log_search(
        self,
        resource: AuditResource,
        query: str,
        result_count: int,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Log a SEARCH operation"""
        search_details = details or {}
        search_details["query"] = query
        search_details["result_count"] = result_count

        entry = AuditEntry(
            action=AuditAction.SEARCH,
            resource=resource,
            resource_id=query[:100],  # Truncate long queries
            status=status,
            details=search_details,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        self.log_entry(entry)


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance (singleton)"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def init_audit_logger(
    log_to_file: bool = True,
    audit_log_dir: Optional[Path] = None,
    log_level: int = logging.INFO,
) -> AuditLogger:
    """
    Initialize global audit logger with custom settings.

    Args:
        log_to_file: Whether to write audit logs to separate file
        audit_log_dir: Directory for audit log files
        log_level: Logging level for audit entries

    Returns:
        Configured AuditLogger instance
    """
    global _audit_logger
    _audit_logger = AuditLogger(
        log_to_file=log_to_file,
        audit_log_dir=audit_log_dir,
        log_level=log_level,
    )
    return _audit_logger
