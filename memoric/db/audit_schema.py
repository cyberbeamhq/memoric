"""
Audit logging database schema for Memoric.

This module defines the database schema for audit logs, which track all security-relevant
events and operations in the system. Audit logs are critical for:
- Security monitoring and incident response
- Compliance requirements (SOC2, GDPR, HIPAA)
- Debugging and troubleshooting
- User activity tracking

Example:
    from memoric.db.audit_schema import create_audit_logs_table
    from sqlalchemy import MetaData

    metadata = MetaData()
    audit_logs = create_audit_logs_table(metadata)
    metadata.create_all(engine)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILED = "auth.login.failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_CREATED = "auth.token.created"
    AUTH_TOKEN_EXPIRED = "auth.token.expired"
    AUTH_TOKEN_INVALID = "auth.token.invalid"

    # User management events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_PASSWORD_CHANGED = "user.password.changed"
    USER_PASSWORD_RESET = "user.password.reset"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"

    # Memory operations
    MEMORY_CREATED = "memory.created"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DELETED = "memory.deleted"
    MEMORY_SEARCHED = "memory.searched"

    # Cluster operations
    CLUSTER_CREATED = "cluster.created"
    CLUSTER_RETRIEVED = "cluster.retrieved"
    CLUSTER_UPDATED = "cluster.updated"
    CLUSTER_DELETED = "cluster.deleted"

    # Policy operations
    POLICY_EXECUTED = "policy.executed"
    POLICY_FAILED = "policy.failed"

    # Authorization events
    AUTHZ_ACCESS_GRANTED = "authz.access.granted"
    AUTHZ_ACCESS_DENIED = "authz.access.denied"
    AUTHZ_PERMISSION_CHECKED = "authz.permission.checked"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

    # Security events
    SECURITY_BREACH_ATTEMPT = "security.breach.attempt"
    SECURITY_RATE_LIMIT_EXCEEDED = "security.rate_limit.exceeded"
    SECURITY_SUSPICIOUS_ACTIVITY = "security.suspicious.activity"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def create_audit_logs_table(metadata: MetaData) -> Table:
    """
    Create the audit logs table.

    The audit logs table stores comprehensive information about all security-relevant
    events in the system. Each log entry includes:
    - Event type and severity
    - User and session information
    - Resource details
    - Timestamp and IP address
    - Before/after state (for changes)
    - Additional metadata

    Args:
        metadata: SQLAlchemy MetaData instance

    Returns:
        Configured Table object

    Example:
        metadata = MetaData()
        audit_logs = create_audit_logs_table(metadata)
        metadata.create_all(engine)
    """
    return Table(
        "audit_logs",
        metadata,
        # Primary key
        Column("id", Integer, primary_key=True, autoincrement=True),

        # Event information
        Column("event_type", String(128), nullable=False, index=True),
        Column("severity", String(32), nullable=False, default=AuditSeverity.INFO.value),
        Column("description", Text, nullable=True),

        # Actor information (who did it)
        Column("user_id", String(128), nullable=True, index=True),
        Column("username", String(128), nullable=True, index=True),
        Column("session_id", String(256), nullable=True, index=True),
        Column("ip_address", String(45), nullable=True),  # IPv6 compatible
        Column("user_agent", Text, nullable=True),

        # Resource information (what was affected)
        Column("resource_type", String(64), nullable=True, index=True),
        Column("resource_id", String(256), nullable=True, index=True),
        Column("namespace", String(128), nullable=True, index=True),

        # Change tracking
        Column("action", String(64), nullable=True),  # create, read, update, delete
        Column("before_state", JSONB().with_variant(JSON, "sqlite"), nullable=True),
        Column("after_state", JSONB().with_variant(JSON, "sqlite"), nullable=True),

        # Request information
        Column("request_method", String(16), nullable=True),
        Column("request_path", String(512), nullable=True),
        Column("request_params", JSONB().with_variant(JSON, "sqlite"), nullable=True),

        # Result information
        Column("success", Boolean, nullable=False, default=True),
        Column("error_message", Text, nullable=True),
        Column("status_code", Integer, nullable=True),

        # Additional context
        Column("metadata", JSONB().with_variant(JSON, "sqlite"), nullable=True),
        Column("tags", JSONB().with_variant(JSON, "sqlite"), nullable=True),

        # Timestamp
        Column(
            "timestamp",
            DateTime,
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
            index=True,
        ),

        # Compliance tracking
        Column("compliance_tags", JSONB().with_variant(JSON, "sqlite"), nullable=True),
        Column("retention_policy", String(64), nullable=True),
    )


def create_audit_summary_table(metadata: MetaData) -> Table:
    """
    Create the audit summary table for aggregated statistics.

    This table stores daily/hourly aggregations of audit events for performance
    and reporting purposes. It's populated by a background job.

    Args:
        metadata: SQLAlchemy MetaData instance

    Returns:
        Configured Table object
    """
    return Table(
        "audit_summary",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("date", DateTime, nullable=False, index=True),
        Column("event_type", String(128), nullable=False, index=True),
        Column("user_id", String(128), nullable=True, index=True),
        Column("count", Integer, nullable=False, default=0),
        Column("success_count", Integer, nullable=False, default=0),
        Column("failure_count", Integer, nullable=False, default=0),
        Column("metadata", JSONB().with_variant(JSON, "sqlite"), nullable=True),
        Column(
            "created_at",
            DateTime,
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
        ),
    )


__all__ = [
    "create_audit_logs_table",
    "create_audit_summary_table",
    "AuditEventType",
    "AuditSeverity",
]
