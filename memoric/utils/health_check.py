"""
Health check utilities for Memoric.

This module provides comprehensive health checking capabilities for:
- Liveness probes (is the service running?)
- Readiness probes (can the service handle traffic?)
- Dependency health (database, external services)
- Resource monitoring (memory, disk, connections)

Used for Kubernetes readiness/liveness probes and monitoring systems.
"""

from __future__ import annotations

import os
import psutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Engine, text

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class HealthStatus:
    """Health check result."""

    healthy: bool
    status: str  # "healthy", "unhealthy", "degraded"
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    check_time: Optional[datetime] = None


class HealthChecker:
    """
    Comprehensive health checking service.

    Attributes:
        engine: SQLAlchemy engine for database checks
        start_time: Service start timestamp
    """

    def __init__(
        self,
        *,
        engine: Optional[Engine] = None,
        start_time: Optional[datetime] = None,
    ):
        """
        Initialize health checker.

        Args:
            engine: SQLAlchemy engine for database checks
            start_time: Service start time (default: now)
        """
        self.engine = engine
        self.start_time = start_time or datetime.now(timezone.utc)

        logger.info("Health checker initialized")

    def check_liveness(self) -> HealthStatus:
        """
        Liveness probe - is the service running?

        This is a simple check that the service process is alive and responsive.
        Should return quickly (<100ms) and never fail unless the process is hung.

        Returns:
            HealthStatus indicating if service is alive

        Example:
            status = health_checker.check_liveness()
            if status.healthy:
                return {"status": "alive"}
        """
        try:
            # Simple check - if we can execute this code, we're alive
            return HealthStatus(
                healthy=True,
                status="healthy",
                message="Service is alive",
                check_time=datetime.now(timezone.utc),
                details={
                    "uptime_seconds": (
                        datetime.now(timezone.utc) - self.start_time
                    ).total_seconds(),
                    "pid": os.getpid(),
                },
            )
        except Exception as e:
            logger.error(f"Liveness check failed: {e}")
            return HealthStatus(
                healthy=False,
                status="unhealthy",
                message=f"Liveness check failed: {e}",
                check_time=datetime.now(timezone.utc),
            )

    def check_readiness(
        self, *, check_database: bool = True, check_resources: bool = True
    ) -> HealthStatus:
        """
        Readiness probe - can the service handle traffic?

        Checks if all critical dependencies are available and the service can
        handle requests. More comprehensive than liveness.

        Args:
            check_database: Check database connectivity
            check_resources: Check system resources

        Returns:
            HealthStatus indicating if service is ready

        Example:
            status = health_checker.check_readiness()
            if not status.healthy:
                return 503, {"status": "not_ready", "details": status.details}
        """
        checks = {}
        overall_healthy = True
        messages = []

        try:
            # Check database
            if check_database and self.engine:
                db_status = self.check_database()
                checks["database"] = {
                    "healthy": db_status.healthy,
                    "status": db_status.status,
                    "message": db_status.message,
                }
                if not db_status.healthy:
                    overall_healthy = False
                    messages.append(f"Database: {db_status.message}")

            # Check system resources
            if check_resources:
                resource_status = self.check_resources()
                checks["resources"] = {
                    "healthy": resource_status.healthy,
                    "status": resource_status.status,
                    "details": resource_status.details,
                }
                if not resource_status.healthy:
                    overall_healthy = False
                    messages.append(f"Resources: {resource_status.message}")

            # Overall status
            if overall_healthy:
                status = "healthy"
                message = "Service is ready to handle traffic"
            else:
                status = "unhealthy"
                message = "; ".join(messages)

            return HealthStatus(
                healthy=overall_healthy,
                status=status,
                message=message,
                check_time=datetime.now(timezone.utc),
                details=checks,
            )

        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return HealthStatus(
                healthy=False,
                status="unhealthy",
                message=f"Readiness check failed: {e}",
                check_time=datetime.now(timezone.utc),
            )

    def check_database(self, *, timeout_seconds: int = 5) -> HealthStatus:
        """
        Check database connectivity and health.

        Args:
            timeout_seconds: Query timeout in seconds

        Returns:
            HealthStatus for database

        Example:
            status = health_checker.check_database()
            if not status.healthy:
                logger.error(f"Database unhealthy: {status.message}")
        """
        if not self.engine:
            return HealthStatus(
                healthy=True,
                status="healthy",
                message="No database configured (not checked)",
                check_time=datetime.now(timezone.utc),
            )

        try:
            start_time = time.time()

            # Test connection with simple query
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            query_time = time.time() - start_time

            # Check if query is slow (potential issue)
            if query_time > timeout_seconds:
                logger.warning(f"Database query slow: {query_time:.2f}s")
                return HealthStatus(
                    healthy=False,
                    status="unhealthy",
                    message=f"Database responding slowly ({query_time:.2f}s)",
                    check_time=datetime.now(timezone.utc),
                    details={
                        "query_time_seconds": query_time,
                        "timeout_seconds": timeout_seconds,
                    },
                )

            return HealthStatus(
                healthy=True,
                status="healthy",
                message="Database is healthy",
                check_time=datetime.now(timezone.utc),
                details={
                    "query_time_seconds": round(query_time, 3),
                    "pool_size": self.engine.pool.size() if hasattr(self.engine, "pool") else None,
                    "checked_out": self.engine.pool.checkedout() if hasattr(self.engine, "pool") else None,
                },
            )

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return HealthStatus(
                healthy=False,
                status="unhealthy",
                message=f"Database connection failed: {str(e)[:100]}",
                check_time=datetime.now(timezone.utc),
            )

    def check_resources(
        self,
        *,
        memory_threshold_percent: float = 90.0,
        disk_threshold_percent: float = 90.0,
    ) -> HealthStatus:
        """
        Check system resource usage.

        Args:
            memory_threshold_percent: Memory usage warning threshold
            disk_threshold_percent: Disk usage warning threshold

        Returns:
            HealthStatus for system resources

        Example:
            status = health_checker.check_resources(
                memory_threshold_percent=85.0,
                disk_threshold_percent=85.0
            )
        """
        try:
            # Get current process
            process = psutil.Process(os.getpid())

            # Memory usage
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            # System memory
            sys_memory = psutil.virtual_memory()

            # Disk usage (current working directory)
            disk_usage = psutil.disk_usage(os.getcwd())

            # CPU usage (non-blocking, recent average)
            cpu_percent = process.cpu_percent(interval=0.1)

            # Check thresholds
            issues = []
            if sys_memory.percent > memory_threshold_percent:
                issues.append(
                    f"System memory high ({sys_memory.percent:.1f}% > {memory_threshold_percent}%)"
                )

            if disk_usage.percent > disk_threshold_percent:
                issues.append(
                    f"Disk space low ({disk_usage.percent:.1f}% > {disk_threshold_percent}%)"
                )

            # Determine status
            if issues:
                healthy = False
                status = "unhealthy"
                message = "; ".join(issues)
            else:
                healthy = True
                status = "healthy"
                message = "System resources normal"

            return HealthStatus(
                healthy=healthy,
                status=status,
                message=message,
                check_time=datetime.now(timezone.utc),
                details={
                    "process": {
                        "pid": os.getpid(),
                        "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                        "memory_percent": round(memory_percent, 2),
                        "cpu_percent": round(cpu_percent, 2),
                        "num_threads": process.num_threads(),
                    },
                    "system": {
                        "memory_total_gb": round(sys_memory.total / 1024 / 1024 / 1024, 2),
                        "memory_available_gb": round(sys_memory.available / 1024 / 1024 / 1024, 2),
                        "memory_percent": round(sys_memory.percent, 2),
                        "disk_total_gb": round(disk_usage.total / 1024 / 1024 / 1024, 2),
                        "disk_free_gb": round(disk_usage.free / 1024 / 1024 / 1024, 2),
                        "disk_percent": round(disk_usage.percent, 2),
                        "cpu_count": psutil.cpu_count(),
                    },
                    "thresholds": {
                        "memory_threshold_percent": memory_threshold_percent,
                        "disk_threshold_percent": disk_threshold_percent,
                    },
                },
            )

        except Exception as e:
            logger.error(f"Resource health check failed: {e}")
            return HealthStatus(
                healthy=False,
                status="unhealthy",
                message=f"Resource check failed: {e}",
                check_time=datetime.now(timezone.utc),
            )

    def check_all(
        self,
        *,
        check_database: bool = True,
        check_resources: bool = True,
    ) -> Dict[str, HealthStatus]:
        """
        Run all health checks and return comprehensive status.

        Args:
            check_database: Check database health
            check_resources: Check system resources

        Returns:
            Dictionary of all health check results

        Example:
            results = health_checker.check_all()
            if not results["readiness"].healthy:
                send_alert("Service not ready!")
        """
        return {
            "liveness": self.check_liveness(),
            "readiness": self.check_readiness(
                check_database=check_database,
                check_resources=check_resources,
            ),
            "database": self.check_database() if check_database else None,
            "resources": self.check_resources() if check_resources else None,
        }

    def get_service_info(self) -> Dict[str, Any]:
        """
        Get general service information.

        Returns:
            Dictionary with service metadata

        Example:
            info = health_checker.get_service_info()
            print(f"Service uptime: {info['uptime_seconds']}s")
        """
        uptime = datetime.now(timezone.utc) - self.start_time

        return {
            "service": "memoric-api",
            "version": "0.1.0",
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_human": str(uptime).split(".")[0],  # Remove microseconds
            "pid": os.getpid(),
            "python_version": os.sys.version.split()[0],
        }


__all__ = ["HealthChecker", "HealthStatus"]
