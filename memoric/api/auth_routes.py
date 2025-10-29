"""
Authentication API routes.

This module provides login, register, and user management endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, validator

from ..db.audit_schema import AuditEventType
from ..utils.audit_logger import AuditLogger
from ..utils.auth import AuthService, Role
from ..utils.logger import get_logger
from ..utils.user_manager import UserManager
from .auth_middleware import AuthDependency

logger = get_logger(__name__)


# Pydantic models for request/response validation
class RegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    namespace: Optional[str] = Field(None, max_length=128)

    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """User login request."""

    username: str = Field(..., description="Username or email")
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: Dict[str, Any]


class UserResponse(BaseModel):
    """User profile response."""

    id: int
    username: str
    email: str
    full_name: Optional[str]
    namespace: Optional[str]
    roles: List[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]


class ChangePasswordRequest(BaseModel):
    """Password change request."""

    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


def create_auth_router(
    *,
    user_manager: UserManager,
    auth_service: AuthService,
    auth_dependency: AuthDependency,
    audit_logger: Optional[AuditLogger] = None,
) -> APIRouter:
    """
    Create authentication router with all auth endpoints.

    Args:
        user_manager: UserManager instance
        auth_service: AuthService instance
        auth_dependency: AuthDependency instance
        audit_logger: Optional AuditLogger instance for audit logging

    Returns:
        Configured FastAPI router

    Example:
        app.include_router(
            create_auth_router(
                user_manager=user_mgr,
                auth_service=auth_svc,
                auth_dependency=auth_dep,
                audit_logger=audit_log
            ),
            prefix="/auth",
            tags=["authentication"]
        )
    """
    router = APIRouter()

    @router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
    async def register(req: RegisterRequest, http_request: Request):
        """
        Register a new user account.

        Creates a new user with USER role by default.
        Email verification required for full access (if configured).

        **Request Body:**
        - username: Unique username (alphanumeric, dash, underscore only)
        - email: Valid email address
        - password: Strong password (min 8 chars, must include uppercase, lowercase, digit)
        - full_name: Optional full name
        - namespace: Optional namespace for multi-tenancy

        **Returns:**
        - User profile (without password)

        **Errors:**
        - 400: Invalid input or user already exists
        - 500: Server error
        """
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")

        try:
            user = user_manager.create_user(
                username=req.username,
                email=req.email,
                password=req.password,
                full_name=req.full_name,
                namespace=req.namespace,
                roles=[Role.USER],
            )

            logger.info(
                "User registered successfully",
                extra={"user_id": user["id"], "username": req.username},
            )

            # Audit log
            if audit_logger:
                audit_logger.log_event(
                    event_type=AuditEventType.USER_CREATED,
                    user_id=str(user["id"]),
                    username=user["username"],
                    resource_type="user",
                    resource_id=str(user["id"]),
                    action="create",
                    after_state={
                        "username": user["username"],
                        "email": user["email"],
                        "roles": user["roles"],
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True,
                )

            return user

        except ValueError as e:
            logger.warning(f"Registration failed: {e}")

            # Audit log failure
            if audit_logger:
                audit_logger.log_event(
                    event_type=AuditEventType.USER_CREATED,
                    username=req.username,
                    resource_type="user",
                    action="create",
                    success=False,
                    error_message=str(e),
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        except Exception as e:
            logger.error(f"Registration error: {e}")

            # Audit log failure
            if audit_logger:
                audit_logger.log_event(
                    event_type=AuditEventType.USER_CREATED,
                    username=req.username,
                    resource_type="user",
                    action="create",
                    success=False,
                    error_message="Internal server error",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed",
            )

    @router.post("/login", response_model=TokenResponse)
    async def login(req: LoginRequest, http_request: Request):
        """
        Authenticate user and receive JWT token.

        **Request Body:**
        - username: Username or email address
        - password: User password

        **Returns:**
        - access_token: JWT token for API authentication
        - token_type: "bearer"
        - expires_in: Token expiration in seconds
        - user: User profile

        **Headers for authenticated requests:**
        ```
        Authorization: Bearer <access_token>
        ```

        **Errors:**
        - 401: Invalid credentials or inactive account
        - 500: Server error
        """
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")

        user = user_manager.authenticate_user(
            username=req.username,
            password=req.password,
        )

        if not user:
            logger.warning(
                "Login failed",
                extra={"username": req.username},
            )

            # Audit log failed login
            if audit_logger:
                audit_logger.log_auth_event(
                    event_type=AuditEventType.AUTH_LOGIN_FAILED,
                    username=req.username,
                    success=False,
                    error_message="Invalid credentials",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create JWT token
        user_roles = [Role(r) for r in user.get("roles", [])]
        token = auth_service.create_token(
            user_id=str(user["id"]),
            roles=user_roles,
            namespace=user.get("namespace"),
        )

        logger.info(
            "User logged in",
            extra={"user_id": user["id"], "username": user["username"]},
        )

        # Audit log successful login
        if audit_logger:
            audit_logger.log_auth_event(
                event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                user_id=str(user["id"]),
                username=user["username"],
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"roles": user["roles"]},
            )

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": auth_service.token_expiry,
            "user": user,
        }

    @router.get("/me", response_model=UserResponse)
    async def get_current_user_profile(
        current_user: dict = Depends(auth_dependency.get_current_user),
    ):
        """
        Get current user profile.

        **Authentication required:** Yes

        **Returns:**
        - User profile of authenticated user

        **Errors:**
        - 401: Not authenticated
        - 404: User not found
        """
        user_id = int(current_user["sub"])
        user = user_manager.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user

    @router.post("/change-password")
    async def change_password(
        req: ChangePasswordRequest,
        http_request: Request,
        current_user: dict = Depends(auth_dependency.get_current_user),
    ):
        """
        Change user password.

        **Authentication required:** Yes

        **Request Body:**
        - old_password: Current password
        - new_password: New password (must meet strength requirements)

        **Returns:**
        - Success message

        **Errors:**
        - 400: Invalid old password or weak new password
        - 401: Not authenticated
        """
        user_id = int(current_user["sub"])
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")

        success = user_manager.change_password(
            user_id=user_id,
            old_password=req.old_password,
            new_password=req.new_password,
        )

        if not success:
            # Audit log failed password change
            if audit_logger:
                audit_logger.log_event(
                    event_type=AuditEventType.USER_PASSWORD_CHANGED,
                    user_id=str(user_id),
                    resource_type="user",
                    resource_id=str(user_id),
                    action="update",
                    success=False,
                    error_message="Invalid old password",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password change failed. Check your current password.",
            )

        logger.info("Password changed", extra={"user_id": user_id})

        # Audit log successful password change
        if audit_logger:
            audit_logger.log_event(
                event_type=AuditEventType.USER_PASSWORD_CHANGED,
                user_id=str(user_id),
                resource_type="user",
                resource_id=str(user_id),
                action="update",
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return {"message": "Password changed successfully"}

    @router.get("/users/{username}", response_model=UserResponse)
    async def get_user_by_username(
        username: str,
        current_user: dict = Depends(auth_dependency.get_current_user),
    ):
        """
        Get user profile by username.

        **Authentication required:** Yes
        **Permission required:** Admin or same user

        **Path Parameters:**
        - username: Username to lookup

        **Returns:**
        - User profile

        **Errors:**
        - 401: Not authenticated
        - 403: Not authorized to view this user
        - 404: User not found
        """
        user = user_manager.get_user_by_username(username)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Check if user can access this profile
        current_user_id = str(current_user["sub"])
        target_user_id = str(user["id"])

        if current_user_id != target_user_id:
            # Only admins can view other users' profiles
            user_roles = [Role(r) for r in current_user.get("roles", [])]
            if Role.ADMIN not in user_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this profile",
                )

        return user

    @router.post("/logout")
    async def logout(
        http_request: Request,
        current_user: dict = Depends(auth_dependency.get_current_user),
    ):
        """
        Logout user (client-side token invalidation).

        Since JWTs are stateless, logout is handled client-side by discarding the token.
        For additional security, implement token blacklisting with Redis.

        **Authentication required:** Yes

        **Returns:**
        - Success message

        **Note:**
        Client should:
        1. Delete the token from storage
        2. Remove Authorization header
        3. Redirect to login page
        """
        user_id = current_user["sub"]
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")

        logger.info("User logged out", extra={"user_id": user_id})

        # Audit log logout
        if audit_logger:
            audit_logger.log_auth_event(
                event_type=AuditEventType.AUTH_LOGOUT,
                user_id=str(user_id),
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return {
            "message": "Logged out successfully",
            "note": "Discard your token on the client side",
        }

    return router


__all__ = [
    "create_auth_router",
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "UserResponse",
    "ChangePasswordRequest",
]
