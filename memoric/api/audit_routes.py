"""
Audit log API routes.

This module provides endpoints for querying and analyzing audit logs.
These endpoints are typically restricted to admin users for security compliance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..db.audit_schema import AuditEventType, AuditSeverity
from ..utils.audit_logger import AuditLogger
from ..utils.auth import Role
from ..utils.logger import get_logger
from .auth_middleware import AuthDependency

logger = get_logger(__name__)


# Pydantic models
class AuditLogResponse(BaseModel):
    """Single audit log entry response."""

    id: int
    event_type: str
    severity: str
    description: Optional[str]
    user_id: Optional[str]
    username: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: Optional[str]
    success: bool
    timestamp: datetime
    ip_address: Optional[str]
    error_message: Optional[str]


class AuditLogsListResponse(BaseModel):
    """List of audit logs with pagination."""

    logs: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int


class AuditStatisticsResponse(BaseModel):
    """Audit log statistics."""

    total_events: int
    events_by_type: Dict[str, int]
    failed_operations: int
    unique_users: int
    start_time: Optional[str]
    end_time: Optional[str]


def create_audit_router(
    *,
    audit_logger: AuditLogger,
    auth_dependency: AuthDependency,
) -> APIRouter:
    """
    Create audit log router with query endpoints.

    Args:
        audit_logger: AuditLogger instance
        auth_dependency: AuthDependency instance for authorization

    Returns:
        Configured FastAPI router

    Example:
        app.include_router(
            create_audit_router(
                audit_logger=audit_log,
                auth_dependency=auth_dep
            ),
            prefix="/audit",
            tags=["audit"]
        )
    """
    router = APIRouter()

    def require_admin(current_user: dict = Depends(auth_dependency.get_current_user)) -> dict:
        """Dependency to require admin role."""
        user_roles = [Role(r) for r in current_user.get("roles", [])]
        if Role.ADMIN not in user_roles:
            logger.warning(
                "Non-admin user attempted to access audit logs",
                extra={"user_id": current_user["sub"]},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return current_user

    @router.get("/logs", response_model=AuditLogsListResponse)
    async def query_audit_logs(
        event_type: Optional[str] = Query(None, description="Filter by event type"),
        user_id: Optional[str] = Query(None, description="Filter by user ID"),
        resource_type: Optional[str] = Query(None, description="Filter by resource type"),
        resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
        success: Optional[bool] = Query(None, description="Filter by success status"),
        severity: Optional[str] = Query(None, description="Filter by severity level"),
        hours: int = Query(24, ge=1, le=720, description="Hours to look back (max 30 days)"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
        offset: int = Query(0, ge=0, description="Pagination offset"),
        current_user: dict = Depends(require_admin),
    ):
        """
        Query audit logs with filters.

        **Authentication required:** Yes (Admin only)

        **Query Parameters:**
        - event_type: Filter by specific event type (e.g., "auth.login.success")
        - user_id: Filter by user ID
        - resource_type: Filter by resource type (memory, cluster, user, etc.)
        - resource_id: Filter by resource ID
        - success: Filter by success status (true/false)
        - severity: Filter by severity (debug, info, warning, error, critical)
        - hours: Hours to look back (default: 24, max: 720)
        - limit: Maximum results (default: 100, max: 1000)
        - offset: Pagination offset (default: 0)

        **Returns:**
        - List of audit log entries matching the filters

        **Example:**
        ```bash
        # Get all failed login attempts in last 24 hours
        GET /audit/logs?event_type=auth.login.failed&hours=24

        # Get all actions by a specific user
        GET /audit/logs?user_id=user123&limit=50

        # Get security events (warnings and errors)
        GET /audit/logs?severity=warning&hours=1
        ```
        """
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        logs = audit_logger.query_logs(
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            start_time=start_time,
            success=success,
            severity=severity,
            limit=limit,
            offset=offset,
        )

        logger.info(
            "Audit logs queried",
            extra={
                "admin_user_id": current_user["sub"],
                "filters": {
                    "event_type": event_type,
                    "user_id": user_id,
                    "resource_type": resource_type,
                },
                "result_count": len(logs),
            },
        )

        return {
            "logs": logs,
            "total": len(logs),
            "offset": offset,
            "limit": limit,
        }

    @router.get("/logs/user/{user_id}")
    async def get_user_activity(
        user_id: str,
        hours: int = Query(24, ge=1, le=720, description="Hours to look back"),
        limit: int = Query(100, ge=1, le=1000),
        current_user: dict = Depends(require_admin),
    ):
        """
        Get all activity for a specific user.

        **Authentication required:** Yes (Admin only)

        **Path Parameters:**
        - user_id: User ID to query

        **Query Parameters:**
        - hours: Hours to look back (default: 24)
        - limit: Maximum results (default: 100)

        **Returns:**
        - List of all audit logs for the user

        **Example:**
        ```bash
        GET /audit/logs/user/user123?hours=168  # Last week
        ```
        """
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        logs = audit_logger.get_user_activity(
            user_id=user_id,
            start_time=start_time,
            limit=limit,
        )

        logger.info(
            "User activity queried",
            extra={
                "admin_user_id": current_user["sub"],
                "target_user_id": user_id,
                "result_count": len(logs),
            },
        )

        return {
            "user_id": user_id,
            "logs": logs,
            "total": len(logs),
            "start_time": start_time.isoformat(),
        }

    @router.get("/logs/security")
    async def get_security_events(
        hours: int = Query(24, ge=1, le=720, description="Hours to look back"),
        limit: int = Query(100, ge=1, le=1000),
        current_user: dict = Depends(require_admin),
    ):
        """
        Get security-relevant events.

        Returns all events with:
        - Severity WARNING, ERROR, or CRITICAL
        - Failed operations (success=false)
        - Access denied events

        **Authentication required:** Yes (Admin only)

        **Query Parameters:**
        - hours: Hours to look back (default: 24)
        - limit: Maximum results (default: 100)

        **Returns:**
        - List of security-relevant audit logs

        **Example:**
        ```bash
        GET /audit/logs/security?hours=1  # Security events in last hour
        ```
        """
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        logs = audit_logger.get_security_events(
            start_time=start_time,
            limit=limit,
        )

        logger.info(
            "Security events queried",
            extra={
                "admin_user_id": current_user["sub"],
                "result_count": len(logs),
            },
        )

        return {
            "logs": logs,
            "total": len(logs),
            "start_time": start_time.isoformat(),
        }

    @router.get("/statistics", response_model=AuditStatisticsResponse)
    async def get_audit_statistics(
        hours: int = Query(24, ge=1, le=720, description="Hours to look back"),
        current_user: dict = Depends(require_admin),
    ):
        """
        Get audit log statistics and summary.

        **Authentication required:** Yes (Admin only)

        **Query Parameters:**
        - hours: Hours to look back (default: 24)

        **Returns:**
        - total_events: Total number of events
        - events_by_type: Breakdown by event type
        - failed_operations: Number of failed operations
        - unique_users: Number of unique users active
        - start_time: Start of time range
        - end_time: End of time range

        **Example:**
        ```bash
        GET /audit/statistics?hours=168  # Weekly statistics
        ```
        """
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        stats = audit_logger.get_statistics(start_time=start_time)

        logger.info(
            "Audit statistics queried",
            extra={
                "admin_user_id": current_user["sub"],
                "total_events": stats.get("total_events", 0),
            },
        )

        return stats

    @router.get("/events/types")
    async def list_event_types(
        current_user: dict = Depends(require_admin),
    ):
        """
        List all available audit event types.

        **Authentication required:** Yes (Admin only)

        **Returns:**
        - List of all event type enum values with descriptions

        **Example:**
        ```bash
        GET /audit/events/types
        ```
        """
        event_types = []

        for event_type in AuditEventType:
            # Parse description from enum value
            category, subcategory = event_type.value.split(".", 1)
            event_types.append(
                {
                    "value": event_type.value,
                    "name": event_type.name,
                    "category": category,
                    "description": f"{category.title()} - {subcategory.replace('.', ' ').title()}",
                }
            )

        return {
            "event_types": event_types,
            "total": len(event_types),
        }

    @router.get("/severity/levels")
    async def list_severity_levels(
        current_user: dict = Depends(require_admin),
    ):
        """
        List all available severity levels.

        **Authentication required:** Yes (Admin only)

        **Returns:**
        - List of all severity level enum values

        **Example:**
        ```bash
        GET /audit/severity/levels
        ```
        """
        severity_levels = [
            {
                "value": severity.value,
                "name": severity.name,
                "description": f"{severity.name.title()} level events",
            }
            for severity in AuditSeverity
        ]

        return {
            "severity_levels": severity_levels,
            "total": len(severity_levels),
        }

    return router


__all__ = [
    "create_audit_router",
    "AuditLogResponse",
    "AuditLogsListResponse",
    "AuditStatisticsResponse",
]
