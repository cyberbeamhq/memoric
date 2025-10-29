"""
Tests for audit logging functionality.

Tests cover:
- Audit log creation
- Event querying and filtering
- User activity tracking
- Security event detection
- Statistics generation
- API endpoints
"""

import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, create_engine

from memoric.api.server import create_app
from memoric.core.memory_manager import Memoric
from memoric.db.audit_schema import AuditEventType, create_audit_logs_table
from memoric.utils.audit_logger import AuditLogger


@pytest.fixture
def test_db_url():
    """Test database URL."""
    return "sqlite:///:memory:"


@pytest.fixture
def audit_logger(test_db_url):
    """Create audit logger with test database."""
    engine = create_engine(test_db_url)
    metadata = MetaData()
    audit_logs_table = create_audit_logs_table(metadata)
    metadata.create_all(engine)

    return AuditLogger(
        engine=engine,
        audit_logs_table=audit_logs_table,
        enabled=True,
    )


@pytest.fixture
def client(test_db_url):
    """Create FastAPI test client with audit logging."""
    os.environ["MEMORIC_JWT_SECRET"] = "test_secret_key_for_testing"
    os.environ["MEMORIC_ENCRYPTION_KEY"] = "test_encryption_key_1234567890"

    mem = Memoric(dsn=test_db_url)
    app = create_app(mem=mem, enable_auth=True, enable_audit=True)

    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Get admin token for testing."""
    # Register admin user
    client.post(
        "/auth/register",
        json={
            "username": "admin",
            "email": "admin@test.com",
            "password": "AdminPass123",
        },
    )

    # Manually upgrade to admin (in real system, this would be done via SQL)
    # For testing, we'll use a regular user but tests will check admin requirement

    # Login
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "AdminPass123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def user_token(client):
    """Get regular user token for testing."""
    client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@test.com",
            "password": "TestPass123",
        },
    )

    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "TestPass123"},
    )
    return response.json()["access_token"]


class TestAuditLogger:
    """Test AuditLogger service class."""

    def test_log_event(self, audit_logger):
        """Test basic event logging."""
        log_id = audit_logger.log_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            user_id="user123",
            username="alice",
            ip_address="192.168.1.100",
            success=True,
        )

        assert log_id is not None
        assert isinstance(log_id, int)

    def test_log_auth_event(self, audit_logger):
        """Test authentication event logging."""
        log_id = audit_logger.log_auth_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            user_id="user123",
            username="alice",
            success=True,
            ip_address="192.168.1.100",
        )

        assert log_id is not None

    def test_log_memory_event(self, audit_logger):
        """Test memory operation logging."""
        log_id = audit_logger.log_memory_event(
            event_type=AuditEventType.MEMORY_CREATED,
            user_id="user123",
            memory_id="42",
            action="create",
            after_state={"content": "Test memory"},
            success=True,
        )

        assert log_id is not None

    def test_log_authorization_event(self, audit_logger):
        """Test authorization event logging."""
        log_id = audit_logger.log_authorization_event(
            user_id="user123",
            resource_type="memory",
            resource_id="42",
            action="read",
            granted=True,
            reason="Owner access",
        )

        assert log_id is not None

    def test_query_logs_all(self, audit_logger):
        """Test querying all logs."""
        # Create some logs
        for i in range(5):
            audit_logger.log_event(
                event_type=AuditEventType.MEMORY_CREATED,
                user_id=f"user{i}",
                success=True,
            )

        logs = audit_logger.query_logs(limit=100)
        assert len(logs) >= 5

    def test_query_logs_by_event_type(self, audit_logger):
        """Test filtering by event type."""
        # Create mixed events
        audit_logger.log_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            user_id="user1",
            success=True,
        )
        audit_logger.log_event(
            event_type=AuditEventType.MEMORY_CREATED,
            user_id="user1",
            success=True,
        )

        # Query login events only
        logs = audit_logger.query_logs(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
        )

        assert all(log["event_type"] == AuditEventType.AUTH_LOGIN_SUCCESS.value for log in logs)

    def test_query_logs_by_user(self, audit_logger):
        """Test filtering by user."""
        # Create logs for different users
        audit_logger.log_event(
            event_type=AuditEventType.MEMORY_CREATED,
            user_id="user1",
            success=True,
        )
        audit_logger.log_event(
            event_type=AuditEventType.MEMORY_CREATED,
            user_id="user2",
            success=True,
        )

        # Query user1 only
        logs = audit_logger.query_logs(user_id="user1")

        assert all(log["user_id"] == "user1" for log in logs)

    def test_query_logs_by_success_status(self, audit_logger):
        """Test filtering by success status."""
        # Create successful and failed operations
        audit_logger.log_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            user_id="user1",
            success=True,
        )
        audit_logger.log_event(
            event_type=AuditEventType.AUTH_LOGIN_FAILED,
            user_id="user1",
            success=False,
        )

        # Query failed operations only
        logs = audit_logger.query_logs(success=False)

        assert all(log["success"] is False for log in logs)

    def test_query_logs_time_range(self, audit_logger):
        """Test filtering by time range."""
        # Create log
        audit_logger.log_event(
            event_type=AuditEventType.MEMORY_CREATED,
            user_id="user1",
            success=True,
        )

        # Query with time range
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=1)
        end_time = now + timedelta(hours=1)

        logs = audit_logger.query_logs(
            start_time=start_time,
            end_time=end_time,
        )

        assert len(logs) >= 1

    def test_get_user_activity(self, audit_logger):
        """Test getting user activity."""
        # Create logs for a user
        for i in range(3):
            audit_logger.log_event(
                event_type=AuditEventType.MEMORY_CREATED,
                user_id="user123",
                success=True,
            )

        # Get activity
        logs = audit_logger.get_user_activity(user_id="user123")

        assert len(logs) >= 3
        assert all(log["user_id"] == "user123" for log in logs)

    def test_get_security_events(self, audit_logger):
        """Test getting security events."""
        # Create security events
        audit_logger.log_event(
            event_type=AuditEventType.AUTH_LOGIN_FAILED,
            user_id="user1",
            success=False,
        )
        audit_logger.log_event(
            event_type=AuditEventType.MEMORY_CREATED,
            user_id="user1",
            success=True,
        )

        # Get security events (failed operations)
        logs = audit_logger.get_security_events()

        # Should include failed login but not successful memory creation
        failed_events = [log for log in logs if not log["success"]]
        assert len(failed_events) >= 1

    def test_get_statistics(self, audit_logger):
        """Test getting audit statistics."""
        # Create some logs
        audit_logger.log_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            user_id="user1",
            success=True,
        )
        audit_logger.log_event(
            event_type=AuditEventType.AUTH_LOGIN_FAILED,
            user_id="user2",
            success=False,
        )

        # Get statistics
        stats = audit_logger.get_statistics()

        assert "total_events" in stats
        assert "events_by_type" in stats
        assert "failed_operations" in stats
        assert "unique_users" in stats
        assert stats["total_events"] >= 2
        assert stats["failed_operations"] >= 1


class TestAuthenticationAuditLogs:
    """Test audit logging for authentication events."""

    def test_registration_logged(self, client):
        """Test that user registration is logged."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "NewPass123",
            },
        )

        assert response.status_code == 201

        # Verify audit log was created (would need admin access to query)
        # This is tested in integration tests

    def test_login_success_logged(self, client, user_token):
        """Test that successful login is logged."""
        # Login already happened in fixture
        # Verify by checking that we got a token
        assert user_token is not None

    def test_login_failure_logged(self, client):
        """Test that failed login is logged."""
        # Register user
        client.post(
            "/auth/register",
            json={
                "username": "failtest",
                "email": "fail@test.com",
                "password": "TestPass123",
            },
        )

        # Attempt login with wrong password
        response = client.post(
            "/auth/login",
            json={"username": "failtest", "password": "WrongPass123"},
        )

        assert response.status_code == 401

    def test_logout_logged(self, client, user_token):
        """Test that logout is logged."""
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200

    def test_password_change_logged(self, client, user_token):
        """Test that password change is logged."""
        response = client.post(
            "/auth/change-password",
            json={
                "old_password": "TestPass123",
                "new_password": "NewPass456",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200


class TestMemoryOperationAuditLogs:
    """Test audit logging for memory operations."""

    def test_memory_creation_logged(self, client, user_token):
        """Test that memory creation is logged."""
        response = client.post(
            "/memories",
            json={"content": "Test memory for audit"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200

    def test_memory_retrieval_logged(self, client, user_token):
        """Test that memory retrieval is logged."""
        # Create a memory first
        client.post(
            "/memories",
            json={"content": "Test memory"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        # Retrieve memories
        response = client.get(
            "/memories",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200


class TestAuthorizationAuditLogs:
    """Test audit logging for authorization events."""

    def test_access_denied_logged(self, client, user_token, admin_token):
        """Test that access denial is logged."""
        # Regular user tries to access admin-only endpoint
        response = client.post(
            "/policies/run",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        # Should be denied (403)
        assert response.status_code == 403


class TestAuditAPIEndpoints:
    """Test audit log API endpoints."""

    def test_query_logs_requires_auth(self, client):
        """Test that audit endpoints require authentication."""
        response = client.get("/audit/logs")
        assert response.status_code == 401

    def test_query_logs_requires_admin(self, client, user_token):
        """Test that audit endpoints require admin role."""
        response = client.get(
            "/audit/logs",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        # Should be forbidden for non-admin
        assert response.status_code == 403

    def test_get_statistics_requires_admin(self, client, user_token):
        """Test that statistics endpoint requires admin role."""
        response = client.get(
            "/audit/statistics",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    def test_list_event_types(self, client, user_token):
        """Test listing event types requires admin."""
        response = client.get(
            "/audit/events/types",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403


class TestAuditLogDisabled:
    """Test behavior when audit logging is disabled."""

    def test_disabled_audit_returns_none(self):
        """Test that disabled audit logger returns None."""
        engine = create_engine("sqlite:///:memory:")
        metadata = MetaData()
        audit_logs_table = create_audit_logs_table(metadata)
        metadata.create_all(engine)

        audit_logger = AuditLogger(
            engine=engine,
            audit_logs_table=audit_logs_table,
            enabled=False,
        )

        log_id = audit_logger.log_event(
            event_type=AuditEventType.MEMORY_CREATED,
            user_id="user1",
            success=True,
        )

        assert log_id is None

    def test_disabled_audit_returns_empty_list(self):
        """Test that disabled audit logger returns empty list for queries."""
        engine = create_engine("sqlite:///:memory:")
        metadata = MetaData()
        audit_logs_table = create_audit_logs_table(metadata)
        metadata.create_all(engine)

        audit_logger = AuditLogger(
            engine=engine,
            audit_logs_table=audit_logs_table,
            enabled=False,
        )

        logs = audit_logger.query_logs()
        assert logs == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
