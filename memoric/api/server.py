"""
FastAPI server with authentication and authorization.

This module provides a production-ready API server with:
- JWT authentication
- Role-based access control
- Health check endpoints
- Prometheus metrics
- CORS protection
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from ..core.memory_manager import Memoric
from ..db.audit_schema import create_audit_logs_table, AuditEventType
from ..db.auth_schema import create_users_table, create_api_keys_table, create_refresh_tokens_table
from ..utils.audit_logger import AuditLogger
from ..utils.auth import AuthService
from ..utils.health_check import HealthChecker
from ..utils.logger import get_logger
from ..utils.user_manager import UserManager
from .audit_routes import create_audit_router
from .auth_middleware import AuthDependency
from .auth_routes import create_auth_router

logger = get_logger(__name__)

# Try to import Prometheus client
try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    generate_latest = CONTENT_TYPE_LATEST = None


# Pydantic models
class MemoryCreate(BaseModel):
    """Memory creation request."""

    content: str
    thread_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MemoryResponse(BaseModel):
    """Memory creation response."""

    id: int
    message: str = "Memory created successfully"


def create_app(
    mem: Optional[Memoric] = None,
    enable_metrics: bool = True,
    enable_auth: bool = True,
    enable_cors: bool = True,
    enable_audit: bool = True,
    allowed_origins: Optional[list] = None,
) -> FastAPI:
    """
    Create FastAPI application with authentication and audit logging.

    Args:
        mem: Memoric instance (creates new if None)
        enable_metrics: Enable Prometheus metrics endpoint
        enable_auth: Enable JWT authentication
        enable_cors: Enable CORS middleware
        enable_audit: Enable audit logging
        allowed_origins: List of allowed CORS origins

    Returns:
        Configured FastAPI application

    Example:
        app = create_app(enable_auth=True, enable_audit=True)
        uvicorn.run(app, host="0.0.0.0", port=8000)
    """
    app = FastAPI(
        title="Memoric API",
        description="Policy-driven memory management for AI agents",
        version="0.1.0",
        docs_url="/docs" if not enable_auth else None,  # Disable in prod
        redoc_url="/redoc" if not enable_auth else None,
    )

    # Initialize Memoric
    m = mem or Memoric()

    # Initialize health checker
    from datetime import datetime, timezone
    health_checker = HealthChecker(
        engine=m.db.engine,
        start_time=datetime.now(timezone.utc),
    )

    # Initialize audit logging (if enabled)
    audit_logger = None
    if enable_audit:
        audit_logs_table = create_audit_logs_table(m.db.metadata)
        m.db.metadata.create_all(m.db.engine, checkfirst=True)
        audit_logger = AuditLogger(
            engine=m.db.engine,
            audit_logs_table=audit_logs_table,
            enabled=True,
        )
        logger.info("Audit logging enabled")

    # Initialize authentication (if enabled)
    auth_service = None
    user_manager = None
    auth_dependency = None

    if enable_auth:
        # Create auth tables
        users_table = create_users_table(m.db.metadata)
        api_keys_table = create_api_keys_table(m.db.metadata)
        refresh_tokens_table = create_refresh_tokens_table(m.db.metadata)

        # Create tables in database
        m.db.metadata.create_all(m.db.engine, checkfirst=True)

        # Initialize auth services
        jwt_secret = os.getenv("MEMORIC_JWT_SECRET")
        if not jwt_secret:
            logger.warning(
                "MEMORIC_JWT_SECRET not set. Using fallback (INSECURE for production!)"
            )
            jwt_secret = "INSECURE_DEV_SECRET_CHANGE_IN_PRODUCTION"

        auth_service = AuthService(secret_key=jwt_secret)
        user_manager = UserManager(
            engine=m.db.engine,
            users_table=users_table,
            auth_service=auth_service,
        )
        auth_dependency = AuthDependency(auth_service=auth_service)

        # Include authentication routes
        app.include_router(
            create_auth_router(
                user_manager=user_manager,
                auth_service=auth_service,
                auth_dependency=auth_dependency,
                audit_logger=audit_logger,
            ),
            prefix="/auth",
            tags=["authentication"],
        )

        logger.info("Authentication enabled")

    # Include audit log routes (if enabled and authenticated)
    if enable_audit and enable_auth and audit_logger:
        app.include_router(
            create_audit_router(
                audit_logger=audit_logger,
                auth_dependency=auth_dependency,
            ),
            prefix="/audit",
            tags=["audit"],
        )
        logger.info("Audit log endpoints enabled")

    # CORS middleware
    if enable_cors:
        if allowed_origins is None:
            allowed_origins = [
                "http://localhost:3000",  # React default
                "http://localhost:8000",  # FastAPI default
            ]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )

    # Health check endpoints
    @app.get("/", tags=["health"])
    def root():
        """Basic health check with service info."""
        service_info = health_checker.get_service_info()
        return {
            "status": "ok",
            **service_info,
        }

    @app.get("/health", tags=["health"])
    def health_check():
        """
        Liveness probe - is service running?

        **Purpose**: Kubernetes liveness probe
        **Fast**: Returns in <100ms
        **Simple**: Only checks if process is responsive

        If this fails, the container should be restarted.
        """
        liveness = health_checker.check_liveness()

        if not liveness.healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=liveness.message,
            )

        return {
            "status": liveness.status,
            "message": liveness.message,
            "details": liveness.details,
            "timestamp": liveness.check_time.isoformat() if liveness.check_time else None,
        }

    @app.get("/ready", tags=["health"])
    def readiness_check():
        """
        Readiness probe - can service handle traffic?

        **Purpose**: Kubernetes readiness probe
        **Comprehensive**: Checks all critical dependencies
        **Detailed**: Returns status of each component

        Checks:
        - Database connectivity and performance
        - System resources (memory, disk, CPU)
        - Service configuration

        If this fails, traffic should not be routed to this instance.
        """
        readiness = health_checker.check_readiness(
            check_database=True,
            check_resources=True,
        )

        # Add authentication status
        if readiness.details is None:
            readiness.details = {}

        readiness.details["authentication"] = {
            "enabled": enable_auth,
            "status": "enabled" if enable_auth else "disabled",
        }

        readiness.details["audit_logging"] = {
            "enabled": enable_audit,
            "status": "enabled" if enable_audit else "disabled",
        }

        # Return 503 if not ready
        if not readiness.healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": readiness.status,
                    "message": readiness.message,
                    "details": readiness.details,
                    "timestamp": readiness.check_time.isoformat() if readiness.check_time else None,
                },
            )

        return {
            "status": readiness.status,
            "message": readiness.message,
            "details": readiness.details,
            "timestamp": readiness.check_time.isoformat() if readiness.check_time else None,
        }

    @app.get("/health/detailed", tags=["health"])
    def detailed_health_check(
        request: Request,
        current_user: dict = Depends(auth_dependency.get_current_user) if enable_auth else None,
    ):
        """
        Detailed health check with all component status.

        **Purpose**: Monitoring and debugging
        **Authentication**: Required if enabled
        **Authorization**: Admin role required
        **Comprehensive**: Runs all health checks
        **Slow**: May take several seconds

        Returns detailed status of:
        - Liveness
        - Readiness
        - Database
        - System resources
        - Service info

        Use this for monitoring dashboards and debugging, not for K8s probes.
        """
        # Require admin role if authentication is enabled
        if enable_auth:
            user_roles = current_user.get("roles", [])
            if "admin" not in user_roles:
                # Audit log access denied
                if audit_logger:
                    audit_logger.log_authorization_event(
                        user_id=current_user["sub"],
                        resource_type="health",
                        resource_id="detailed",
                        action="read",
                        granted=False,
                        reason="Non-admin user attempted to access detailed health endpoint",
                    )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin role required to access detailed health information",
                )

        all_checks = health_checker.check_all(
            check_database=True,
            check_resources=True,
        )

        service_info = health_checker.get_service_info()

        return {
            "service": service_info,
            "liveness": {
                "healthy": all_checks["liveness"].healthy,
                "status": all_checks["liveness"].status,
                "message": all_checks["liveness"].message,
                "details": all_checks["liveness"].details,
            },
            "readiness": {
                "healthy": all_checks["readiness"].healthy,
                "status": all_checks["readiness"].status,
                "message": all_checks["readiness"].message,
                "details": all_checks["readiness"].details,
            },
            "database": {
                "healthy": all_checks["database"].healthy if all_checks["database"] else None,
                "status": all_checks["database"].status if all_checks["database"] else None,
                "message": all_checks["database"].message if all_checks["database"] else None,
                "details": all_checks["database"].details if all_checks["database"] else None,
            } if all_checks["database"] else {"status": "not_checked"},
            "resources": {
                "healthy": all_checks["resources"].healthy if all_checks["resources"] else None,
                "status": all_checks["resources"].status if all_checks["resources"] else None,
                "message": all_checks["resources"].message if all_checks["resources"] else None,
                "details": all_checks["resources"].details if all_checks["resources"] else None,
            } if all_checks["resources"] else {"status": "not_checked"},
            "features": {
                "authentication": "enabled" if enable_auth else "disabled",
                "audit_logging": "enabled" if enable_audit else "disabled",
                "metrics": "enabled" if enable_metrics else "disabled",
                "cors": "enabled" if enable_cors else "disabled",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Memory endpoints
    @app.get("/memories", tags=["memories"])
    def list_memories(
        request: Request,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        top_k: int = 20,
        current_user: dict = Depends(auth_dependency.get_current_user) if enable_auth else None,
    ):
        """
        List memories.

        **Authentication:** Required if enabled
        **Permission:** memories:read

        Users can only access their own memories unless they have admin role.
        """
        if enable_auth:
            # Enforce user can only access their own memories
            authenticated_user_id = current_user["sub"]

            if user_id and user_id != authenticated_user_id:
                # Check if user is admin
                user_roles = current_user.get("roles", [])
                if "admin" not in user_roles:
                    # Audit log access denied
                    if audit_logger:
                        audit_logger.log_authorization_event(
                            user_id=authenticated_user_id,
                            resource_type="memory",
                            resource_id=user_id,
                            action="read",
                            granted=False,
                            reason="User attempted to access other user's memories without admin role",
                        )

                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Can only access your own memories",
                    )

            # Use authenticated user's ID if not specified
            if not user_id:
                user_id = authenticated_user_id

        memories = m.retrieve(user_id=user_id, thread_id=thread_id, top_k=top_k)

        # Audit log memory retrieval
        if audit_logger and enable_auth:
            audit_logger.log_memory_event(
                event_type=AuditEventType.MEMORY_RETRIEVED,
                user_id=current_user["sub"],
                action="read",
                success=True,
            )

        return memories

    @app.post("/memories", response_model=MemoryResponse, tags=["memories"])
    def create_memory(
        payload: MemoryCreate,
        request: Request,
        current_user: dict = Depends(auth_dependency.get_current_user) if enable_auth else None,
    ):
        """
        Create a new memory.

        **Authentication:** Required if enabled
        **Permission:** memories:write

        The user_id is automatically set from the authenticated user's token.
        This prevents users from creating memories for other users.
        """
        # Get user_id from authenticated user
        if enable_auth:
            user_id = current_user["sub"]
        else:
            # In non-auth mode, require user_id in payload
            if not hasattr(payload, "user_id"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="user_id required when authentication is disabled",
                )
            user_id = payload.user_id

        memory_id = m.save(
            user_id=user_id,
            thread_id=payload.thread_id,
            content=payload.content,
            metadata=payload.metadata,
        )

        # Audit log memory creation
        if audit_logger:
            audit_logger.log_memory_event(
                event_type=AuditEventType.MEMORY_CREATED,
                user_id=user_id,
                memory_id=str(memory_id),
                action="create",
                after_state={
                    "content": payload.content[:100] + "..." if len(payload.content) > 100 else payload.content,
                    "thread_id": payload.thread_id,
                    "metadata": payload.metadata,
                },
                success=True,
            )

        return {"id": memory_id}

    @app.get("/clusters", tags=["clusters"])
    def list_clusters(
        request: Request,
        user_id: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 50,
        current_user: dict = Depends(auth_dependency.get_current_user) if enable_auth else None,
    ):
        """
        List memory clusters.

        **Authentication:** Required if enabled
        **Permission:** clusters:read
        """
        if enable_auth:
            authenticated_user_id = current_user["sub"]

            if user_id and user_id != authenticated_user_id:
                user_roles = current_user.get("roles", [])
                if "admin" not in user_roles:
                    # Audit log access denied
                    if audit_logger:
                        audit_logger.log_authorization_event(
                            user_id=authenticated_user_id,
                            resource_type="cluster",
                            resource_id=user_id,
                            action="read",
                            granted=False,
                            reason="User attempted to access other user's clusters without admin role",
                        )

                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Can only access your own clusters",
                    )

            if not user_id:
                user_id = authenticated_user_id

        clusters = m.db.get_clusters(user_id=user_id, topic=topic, limit=limit)

        # Audit log cluster retrieval
        if audit_logger and enable_auth:
            audit_logger.log_event(
                event_type=AuditEventType.CLUSTER_RETRIEVED,
                user_id=current_user["sub"],
                resource_type="cluster",
                action="read",
                success=True,
            )

        return clusters

    @app.post("/policies/run", tags=["policies"])
    def run_policies(
        request: Request,
        current_user: dict = Depends(auth_dependency.get_current_user) if enable_auth else None,
    ):
        """
        Execute memory policies.

        **Authentication:** Required if enabled
        **Permission:** policies:execute
        **Role:** Admin only
        """
        if enable_auth:
            # Only admins can run policies
            user_roles = current_user.get("roles", [])
            if "admin" not in user_roles:
                # Audit log access denied
                if audit_logger:
                    audit_logger.log_authorization_event(
                        user_id=current_user["sub"],
                        resource_type="policy",
                        resource_id="system",
                        action="execute",
                        granted=False,
                        reason="Non-admin user attempted to execute policies",
                    )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only administrators can execute policies",
                )

        try:
            results = m.run_policies()

            # Audit log policy execution
            if audit_logger and enable_auth:
                audit_logger.log_event(
                    event_type=AuditEventType.POLICY_EXECUTED,
                    user_id=current_user["sub"],
                    resource_type="policy",
                    resource_id="system",
                    action="execute",
                    success=True,
                    metadata={"results": results},
                )

            return results

        except Exception as e:
            # Audit log policy execution failure
            if audit_logger and enable_auth:
                audit_logger.log_event(
                    event_type=AuditEventType.POLICY_FAILED,
                    user_id=current_user["sub"],
                    resource_type="policy",
                    resource_id="system",
                    action="execute",
                    success=False,
                    error_message=str(e),
                )

            raise

    # Prometheus metrics endpoint
    if enable_metrics and PROMETHEUS_AVAILABLE:

        @app.get("/metrics", tags=["monitoring"])
        def metrics():
            """Prometheus metrics endpoint."""
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # Store references for testing
    app.state.memoric = m
    app.state.auth_service = auth_service
    app.state.user_manager = user_manager
    app.state.audit_logger = audit_logger
    app.state.health_checker = health_checker

    logger.info(
        "Memoric API started",
        extra={
            "auth_enabled": enable_auth,
            "audit_enabled": enable_audit,
            "metrics_enabled": enable_metrics,
            "cors_enabled": enable_cors,
        },
    )

    return app


# For running with uvicorn
# Note: Only create app when running directly, not on import
if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
