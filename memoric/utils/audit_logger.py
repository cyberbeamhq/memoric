"""
Audit logging service for Memoric.

This module provides comprehensive audit logging for security-relevant events
and operations. All logs are stored in the database and can be queried for:
- Security monitoring and alerting
- Compliance reporting (SOC2, GDPR, HIPAA)
- Incident investigation and forensics
- User activity tracking
- Debugging and troubleshooting

The AuditLogger is designed to be:
- Non-blocking: Logs are written asynchronously
- Comprehensive: Captures all relevant context
- Queryable: Supports filtering and aggregation
- Compliant: Meets regulatory requirements

Example:
    from memoric.utils.audit_logger import AuditLogger, AuditEventType

    # Initialize
    audit_logger = AuditLogger(engine=engine, audit_logs_table=audit_logs_table)

    # Log an event
    audit_logger.log_event(
        event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
        user_id="user123",
        username="alice",
        ip_address="192.168.1.100",
        metadata={"user_agent": "Mozilla/5.0..."}
    )

    # Query logs
    logs = audit_logger.query_logs(
        event_type=AuditEventType.AUTH_LOGIN_FAILED,
        start_time=datetime.now() - timedelta(hours=24)
    )
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Engine, and_, desc, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..db.audit_schema import AuditEventType, AuditSeverity
from .logger import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """
    Audit logging service for security and compliance.

    Attributes:
        engine: SQLAlchemy engine
        audit_logs_table: Audit logs table
        enabled: Whether audit logging is enabled
    """

    def __init__(
        self,
        *,
        engine: Engine,
        audit_logs_table,
        enabled: bool = True,
    ):
        """
        Initialize the audit logger.

        Args:
            engine: SQLAlchemy engine
            audit_logs_table: Audit logs table from create_audit_logs_table()
            enabled: Whether to enable audit logging (default: True)

        Example:
            from memoric.db.audit_schema import create_audit_logs_table
            from sqlalchemy import create_engine, MetaData

            engine = create_engine("postgresql://...")
            metadata = MetaData()
            audit_logs = create_audit_logs_table(metadata)
            metadata.create_all(engine)

            audit_logger = AuditLogger(
                engine=engine,
                audit_logs_table=audit_logs
            )
        """
        self.engine = engine
        self.audit_logs_table = audit_logs_table
        self.enabled = enabled

        if not enabled:
            logger.warning("Audit logging is DISABLED")
        else:
            logger.info("Audit logging initialized")

    def log_event(
        self,
        *,
        event_type: AuditEventType | str,
        severity: AuditSeverity = AuditSeverity.INFO,
        description: Optional[str] = None,
        # Actor information
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        # Resource information
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        namespace: Optional[str] = None,
        # Change tracking
        action: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        # Request information
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        request_params: Optional[Dict[str, Any]] = None,
        # Result information
        success: bool = True,
        error_message: Optional[str] = None,
        status_code: Optional[int] = None,
        # Additional context
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        compliance_tags: Optional[List[str]] = None,
    ) -> Optional[int]:
        """
        Log an audit event to the database.

        Args:
            event_type: Type of event (from AuditEventType enum)
            severity: Severity level (default: INFO)
            description: Human-readable description
            user_id: User ID who performed the action
            username: Username who performed the action
            session_id: Session or JWT ID
            ip_address: IP address of the actor
            user_agent: User agent string
            resource_type: Type of resource affected (memory, cluster, user, etc.)
            resource_id: ID of the resource affected
            namespace: Namespace for multi-tenancy
            action: Action performed (create, read, update, delete)
            before_state: State before the change (for updates)
            after_state: State after the change (for creates/updates)
            request_method: HTTP method (GET, POST, etc.)
            request_path: Request path
            request_params: Query/body parameters
            success: Whether the operation succeeded
            error_message: Error message if failed
            status_code: HTTP status code
            metadata: Additional metadata
            tags: Tags for categorization
            compliance_tags: Compliance framework tags (SOC2, GDPR, etc.)

        Returns:
            Audit log ID if successful, None if disabled

        Example:
            audit_logger.log_event(
                event_type=AuditEventType.MEMORY_CREATED,
                user_id="user123",
                username="alice",
                resource_type="memory",
                resource_id="42",
                action="create",
                after_state={"content": "...", "thread_id": "..."},
                success=True
            )
        """
        if not self.enabled:
            return None

        # Convert enum to value if needed
        if isinstance(event_type, AuditEventType):
            event_type = event_type.value
        if isinstance(severity, AuditSeverity):
            severity = severity.value

        try:
            with self.engine.begin() as conn:
                stmt = insert(self.audit_logs_table).values(
                    event_type=event_type,
                    severity=severity,
                    description=description,
                    # Actor
                    user_id=user_id,
                    username=username,
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    # Resource
                    resource_type=resource_type,
                    resource_id=resource_id,
                    namespace=namespace,
                    # Changes
                    action=action,
                    before_state=before_state,
                    after_state=after_state,
                    # Request
                    request_method=request_method,
                    request_path=request_path,
                    request_params=request_params,
                    # Result
                    success=success,
                    error_message=error_message,
                    status_code=status_code,
                    # Context
                    metadata=metadata,
                    tags=tags,
                    compliance_tags=compliance_tags,
                    # Timestamp
                    timestamp=datetime.now(timezone.utc),
                )

                result = conn.execute(stmt)
                log_id = result.inserted_primary_key[0]

                logger.debug(
                    f"Audit log created: {event_type}",
                    extra={
                        "audit_log_id": log_id,
                        "event_type": event_type,
                        "user_id": user_id,
                        "resource_type": resource_type,
                        "success": success,
                    },
                )

                return log_id

        except Exception as e:
            # Never let audit logging break the main operation
            logger.error(
                f"Failed to write audit log: {e}",
                extra={
                    "event_type": event_type,
                    "error": str(e),
                },
            )
            return None

    def log_auth_event(
        self,
        *,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Log an authentication-related event.

        Args:
            event_type: Authentication event type
            user_id: User ID
            username: Username
            success: Whether authentication succeeded
            ip_address: IP address
            user_agent: User agent string
            error_message: Error message if failed
            metadata: Additional metadata

        Returns:
            Audit log ID

        Example:
            audit_logger.log_auth_event(
                event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                user_id="user123",
                username="alice",
                success=True,
                ip_address="192.168.1.100"
            )
        """
        return self.log_event(
            event_type=event_type,
            severity=AuditSeverity.WARNING if not success else AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="user",
            resource_id=user_id,
            success=success,
            error_message=error_message,
            metadata=metadata,
            compliance_tags=["auth", "security"],
        )

    def log_memory_event(
        self,
        *,
        event_type: AuditEventType,
        user_id: str,
        memory_id: Optional[str] = None,
        action: str,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """
        Log a memory operation event.

        Args:
            event_type: Memory event type
            user_id: User ID performing the operation
            memory_id: Memory ID
            action: Action performed (create, read, update, delete)
            before_state: State before change
            after_state: State after change
            success: Whether operation succeeded
            error_message: Error message if failed

        Returns:
            Audit log ID

        Example:
            audit_logger.log_memory_event(
                event_type=AuditEventType.MEMORY_CREATED,
                user_id="user123",
                memory_id="42",
                action="create",
                after_state={"content": "Meeting notes", "thread_id": "thread1"},
                success=True
            )
        """
        return self.log_event(
            event_type=event_type,
            user_id=user_id,
            resource_type="memory",
            resource_id=memory_id,
            action=action,
            before_state=before_state,
            after_state=after_state,
            success=success,
            error_message=error_message,
            compliance_tags=["data_access"],
        )

    def log_authorization_event(
        self,
        *,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        granted: bool,
        reason: Optional[str] = None,
    ) -> Optional[int]:
        """
        Log an authorization check event.

        Args:
            user_id: User ID
            resource_type: Type of resource
            resource_id: Resource ID
            action: Action being checked
            granted: Whether access was granted
            reason: Reason for decision

        Returns:
            Audit log ID

        Example:
            audit_logger.log_authorization_event(
                user_id="user123",
                resource_type="memory",
                resource_id="42",
                action="read",
                granted=True,
                reason="Owner access"
            )
        """
        return self.log_event(
            event_type=AuditEventType.AUTHZ_ACCESS_GRANTED
            if granted
            else AuditEventType.AUTHZ_ACCESS_DENIED,
            severity=AuditSeverity.WARNING if not granted else AuditSeverity.INFO,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            success=granted,
            description=reason,
            compliance_tags=["authorization", "security"],
        )

    def query_logs(
        self,
        *,
        event_type: Optional[AuditEventType | str] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success: Optional[bool] = None,
        severity: Optional[AuditSeverity | str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filters.

        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            success: Filter by success status
            severity: Filter by severity level
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of audit log entries

        Example:
            # Get all failed login attempts in last 24 hours
            failed_logins = audit_logger.query_logs(
                event_type=AuditEventType.AUTH_LOGIN_FAILED,
                start_time=datetime.now() - timedelta(hours=24),
                success=False
            )

            # Get all memory operations by a user
            user_activity = audit_logger.query_logs(
                user_id="user123",
                resource_type="memory",
                limit=50
            )
        """
        if not self.enabled:
            return []

        # Build filter conditions
        conditions = []

        if event_type:
            if isinstance(event_type, AuditEventType):
                event_type = event_type.value
            conditions.append(self.audit_logs_table.c.event_type == event_type)

        if user_id:
            conditions.append(self.audit_logs_table.c.user_id == user_id)

        if resource_type:
            conditions.append(self.audit_logs_table.c.resource_type == resource_type)

        if resource_id:
            conditions.append(self.audit_logs_table.c.resource_id == resource_id)

        if start_time:
            conditions.append(self.audit_logs_table.c.timestamp >= start_time)

        if end_time:
            conditions.append(self.audit_logs_table.c.timestamp <= end_time)

        if success is not None:
            conditions.append(self.audit_logs_table.c.success == success)

        if severity:
            if isinstance(severity, AuditSeverity):
                severity = severity.value
            conditions.append(self.audit_logs_table.c.severity == severity)

        try:
            with self.engine.connect() as conn:
                stmt = (
                    select(self.audit_logs_table)
                    .where(and_(*conditions) if conditions else True)
                    .order_by(desc(self.audit_logs_table.c.timestamp))
                    .limit(limit)
                    .offset(offset)
                )

                result = conn.execute(stmt)
                logs = [dict(row._mapping) for row in result]

                logger.debug(
                    f"Query returned {len(logs)} audit logs",
                    extra={
                        "filters": {
                            "event_type": event_type,
                            "user_id": user_id,
                            "resource_type": resource_type,
                        },
                        "count": len(logs),
                    },
                )

                return logs

        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            return []

    def get_user_activity(
        self,
        *,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all activity for a specific user.

        Args:
            user_id: User ID
            start_time: Start time (default: last 7 days)
            end_time: End time (default: now)
            limit: Maximum results

        Returns:
            List of audit log entries for the user

        Example:
            # Get user's activity in last 24 hours
            activity = audit_logger.get_user_activity(
                user_id="user123",
                start_time=datetime.now() - timedelta(hours=24)
            )
        """
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(days=7)

        return self.query_logs(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def get_security_events(
        self,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get security-relevant events (failed logins, access denials, etc.).

        Args:
            start_time: Start time (default: last 24 hours)
            end_time: End time (default: now)
            limit: Maximum results

        Returns:
            List of security-relevant audit logs

        Example:
            # Get security events in last hour
            security_events = audit_logger.get_security_events(
                start_time=datetime.now() - timedelta(hours=1)
            )
        """
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(hours=24)

        try:
            with self.engine.connect() as conn:
                # Get all events with severity WARNING or higher, or failed operations
                stmt = (
                    select(self.audit_logs_table)
                    .where(
                        and_(
                            self.audit_logs_table.c.timestamp >= start_time,
                            self.audit_logs_table.c.timestamp <= end_time
                            if end_time
                            else True,
                            (
                                self.audit_logs_table.c.severity.in_(
                                    [AuditSeverity.WARNING.value, AuditSeverity.ERROR.value, AuditSeverity.CRITICAL.value]
                                )
                                | (self.audit_logs_table.c.success == False)
                            ),
                        )
                    )
                    .order_by(desc(self.audit_logs_table.c.timestamp))
                    .limit(limit)
                )

                result = conn.execute(stmt)
                return [dict(row._mapping) for row in result]

        except Exception as e:
            logger.error(f"Failed to get security events: {e}")
            return []

    def get_statistics(
        self,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get audit log statistics.

        Args:
            start_time: Start time (default: last 24 hours)
            end_time: End time (default: now)

        Returns:
            Dictionary with statistics

        Example:
            stats = audit_logger.get_statistics(
                start_time=datetime.now() - timedelta(days=7)
            )
            print(f"Total events: {stats['total_events']}")
            print(f"Failed operations: {stats['failed_operations']}")
        """
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(hours=24)

        try:
            with self.engine.connect() as conn:
                # Total events
                stmt = select(func.count()).select_from(self.audit_logs_table)
                conditions = [self.audit_logs_table.c.timestamp >= start_time]
                if end_time:
                    conditions.append(self.audit_logs_table.c.timestamp <= end_time)
                stmt = stmt.where(and_(*conditions))

                total_events = conn.execute(stmt).scalar()

                # Events by type
                stmt = (
                    select(
                        self.audit_logs_table.c.event_type,
                        func.count().label("count"),
                    )
                    .where(and_(*conditions))
                    .group_by(self.audit_logs_table.c.event_type)
                    .order_by(desc("count"))
                )
                events_by_type = dict(conn.execute(stmt).fetchall())

                # Failed operations
                stmt = (
                    select(func.count())
                    .select_from(self.audit_logs_table)
                    .where(
                        and_(
                            *conditions,
                            self.audit_logs_table.c.success == False,
                        )
                    )
                )
                failed_operations = conn.execute(stmt).scalar()

                # Unique users
                stmt = (
                    select(func.count(func.distinct(self.audit_logs_table.c.user_id)))
                    .select_from(self.audit_logs_table)
                    .where(and_(*conditions))
                )
                unique_users = conn.execute(stmt).scalar()

                return {
                    "total_events": total_events,
                    "events_by_type": events_by_type,
                    "failed_operations": failed_operations,
                    "unique_users": unique_users,
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None,
                }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


__all__ = ["AuditLogger", "AuditEventType", "AuditSeverity"]
