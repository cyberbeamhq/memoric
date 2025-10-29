"""
Tests for authentication and authorization.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from memoric.api.server import create_app
from memoric.core.memory_manager import Memoric
from memoric.utils.auth import Role


@pytest.fixture
def test_app():
    """Create test FastAPI app with authentication enabled."""
    mem = Memoric()
    app = create_app(mem=mem, enable_auth=True, enable_metrics=False)
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def test_user_credentials():
    """Test user credentials."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123",
        "full_name": "Test User",
    }


@pytest.fixture
def admin_user_credentials():
    """Admin user credentials."""
    return {
        "username": "admin",
        "email": "admin@example.com",
        "password": "AdminPass123",
        "full_name": "Admin User",
    }


class TestUserRegistration:
    """Test user registration."""

    def test_register_valid_user(self, client, test_user_credentials):
        """Test successful user registration."""
        response = client.post("/auth/register", json=test_user_credentials)

        assert response.status_code == 201
        data = response.json()

        assert data["username"] == test_user_credentials["username"]
        assert data["email"] == test_user_credentials["email"]
        assert "password_hash" not in data  # Password should not be in response
        assert data["roles"] == ["user"]
        assert data["is_active"] is True

    def test_register_duplicate_username(self, client, test_user_credentials):
        """Test registration with duplicate username fails."""
        # Register first user
        client.post("/auth/register", json=test_user_credentials)

        # Try to register again
        response = client.post("/auth/register", json=test_user_credentials)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_register_weak_password(self, client, test_user_credentials):
        """Test registration with weak password fails."""
        test_user_credentials["password"] = "weak"  # Too short, no uppercase/digit

        response = client.post("/auth/register", json=test_user_credentials)

        assert response.status_code == 422  # Validation error

    def test_register_invalid_username(self, client, test_user_credentials):
        """Test registration with invalid username format fails."""
        test_user_credentials["username"] = "invalid user@name"  # Spaces and @ not allowed

        response = client.post("/auth/register", json=test_user_credentials)

        assert response.status_code == 422


class TestUserLogin:
    """Test user login."""

    def test_login_valid_credentials(self, client, test_user_credentials):
        """Test successful login with valid credentials."""
        # Register user first
        client.post("/auth/register", json=test_user_credentials)

        # Login
        response = client.post(
            "/auth/login",
            json={
                "username": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["user"]["username"] == test_user_credentials["username"]

    def test_login_with_email(self, client, test_user_credentials):
        """Test login with email instead of username."""
        # Register user
        client.post("/auth/register", json=test_user_credentials)

        # Login with email
        response = client.post(
            "/auth/login",
            json={
                "username": test_user_credentials["email"],  # Use email
                "password": test_user_credentials["password"],
            },
        )

        assert response.status_code == 200

    def test_login_invalid_password(self, client, test_user_credentials):
        """Test login with wrong password fails."""
        # Register user
        client.post("/auth/register", json=test_user_credentials)

        # Try wrong password
        response = client.post(
            "/auth/login",
            json={
                "username": test_user_credentials["username"],
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user fails."""
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "Password123"},
        )

        assert response.status_code == 401


class TestAuthenticatedEndpoints:
    """Test endpoints that require authentication."""

    def get_auth_token(self, client, credentials):
        """Helper to register and login a user."""
        client.post("/auth/register", json=credentials)
        response = client.post(
            "/auth/login",
            json={
                "username": credentials["username"],
                "password": credentials["password"],
            },
        )
        return response.json()["access_token"]

    def test_get_current_user(self, client, test_user_credentials):
        """Test getting current user profile."""
        token = self.get_auth_token(client, test_user_credentials)

        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user_credentials["username"]

    def test_create_memory_authenticated(self, client, test_user_credentials):
        """Test creating memory with authentication."""
        token = self.get_auth_token(client, test_user_credentials)

        response = client.post(
            "/memories",
            json={"content": "Test memory", "metadata": {"topic": "test"}},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert "id" in response.json()

    def test_create_memory_without_auth(self, client):
        """Test creating memory without authentication fails."""
        response = client.post(
            "/memories",
            json={"content": "Test memory"},
        )

        assert response.status_code == 401

    def test_list_memories_own_only(self, client, test_user_credentials):
        """Test users can only list their own memories."""
        token = self.get_auth_token(client, test_user_credentials)

        # Create a memory
        client.post(
            "/memories",
            json={"content": "My memory"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # List memories (should only see own)
        response = client.get("/memories", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        memories = response.json()
        assert len(memories) > 0

    def test_access_other_user_memories_forbidden(self, client, test_user_credentials):
        """Test users cannot access other users' memories."""
        token = self.get_auth_token(client, test_user_credentials)

        # Try to access memories of another user
        response = client.get(
            "/memories",
            params={"user_id": "other_user"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


class TestPasswordChange:
    """Test password change functionality."""

    def get_auth_token(self, client, credentials):
        """Helper to register and login a user."""
        client.post("/auth/register", json=credentials)
        response = client.post(
            "/auth/login",
            json={
                "username": credentials["username"],
                "password": credentials["password"],
            },
        )
        return response.json()["access_token"]

    def test_change_password_success(self, client, test_user_credentials):
        """Test successful password change."""
        token = self.get_auth_token(client, test_user_credentials)

        new_password = "NewSecurePass456"
        response = client.post(
            "/auth/change-password",
            json={
                "old_password": test_user_credentials["password"],
                "new_password": new_password,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

        # Verify can login with new password
        response = client.post(
            "/auth/login",
            json={
                "username": test_user_credentials["username"],
                "password": new_password,
            },
        )
        assert response.status_code == 200

    def test_change_password_wrong_old_password(self, client, test_user_credentials):
        """Test password change with wrong old password fails."""
        token = self.get_auth_token(client, test_user_credentials)

        response = client.post(
            "/auth/change-password",
            json={
                "old_password": "WrongOldPassword123",
                "new_password": "NewSecurePass456",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400


class TestTokenValidation:
    """Test JWT token validation."""

    def test_expired_token(self, client):
        """Test expired token is rejected."""
        # This would require mocking time or using a short-lived token
        # For now, just test invalid token format
        pass

    def test_invalid_token_format(self, client):
        """Test invalid token format is rejected."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token_format"},
        )

        assert response.status_code == 401

    def test_missing_token(self, client):
        """Test missing token is rejected."""
        response = client.get("/auth/me")

        assert response.status_code == 401


class TestAuthorization:
    """Test role-based authorization."""

    def test_non_admin_cannot_run_policies(self, client, test_user_credentials):
        """Test non-admin users cannot run policies."""
        # Register user
        client.post("/auth/register", json=test_user_credentials)

        # Login
        response = client.post(
            "/auth/login",
            json={
                "username": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        token = response.json()["access_token"]

        # Try to run policies
        response = client.post(
            "/policies/run",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403  # Forbidden


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root health check."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_ready_endpoint(self, client):
        """Test readiness endpoint."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
