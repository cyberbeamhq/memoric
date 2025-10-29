"""
Authentication and authorization utilities for Memoric.

This module provides JWT-based authentication and role-based access control (RBAC).
It includes utilities for:
- Creating and validating JWT tokens
- Password hashing and verification
- Role-based access control
- User management

Example:
    from memoric.utils.auth import AuthService, Role

    # Initialize auth service
    auth = AuthService(secret_key="your-secret-key")

    # Create a user token
    token = auth.create_token(user_id="user123", roles=[Role.USER])

    # Verify token
    payload = auth.verify_token(token)

    # Check permissions
    if auth.has_permission(payload, "memories:write"):
        # Allow operation
        pass
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import jwt
from passlib.context import CryptContext

from .logger import get_logger

logger = get_logger(__name__)


class Role(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"      # Full access to all resources
    USER = "user"        # Access to own resources only
    READ_ONLY = "readonly"  # Read-only access


class Permission(str, Enum):
    """Permissions for fine-grained access control."""
    MEMORIES_READ = "memories:read"
    MEMORIES_WRITE = "memories:write"
    MEMORIES_DELETE = "memories:delete"
    CLUSTERS_READ = "clusters:read"
    CLUSTERS_WRITE = "clusters:write"
    POLICIES_EXECUTE = "policies:execute"
    ADMIN_ACCESS = "admin:*"


# Role-to-permissions mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: list(Permission),  # All permissions
    Role.USER: [
        Permission.MEMORIES_READ,
        Permission.MEMORIES_WRITE,
        Permission.MEMORIES_DELETE,
        Permission.CLUSTERS_READ,
        Permission.POLICIES_EXECUTE,
    ],
    Role.READ_ONLY: [
        Permission.MEMORIES_READ,
        Permission.CLUSTERS_READ,
    ],
}


class AuthService:
    """
    JWT-based authentication and authorization service.

    Attributes:
        secret_key: Secret key for JWT signing
        algorithm: JWT algorithm (default: HS256)
        token_expiry: Token expiration time in seconds
    """

    def __init__(
        self,
        *,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        token_expiry_seconds: int = 3600,  # 1 hour default
    ):
        """
        Initialize the authentication service.

        Args:
            secret_key: Secret key for JWT signing. If None, loads from
                       MEMORIC_JWT_SECRET environment variable.
            algorithm: JWT algorithm to use
            token_expiry_seconds: Token expiration time in seconds

        Raises:
            ValueError: If no secret key provided
        """
        self.secret_key = secret_key or os.getenv("MEMORIC_JWT_SECRET")

        if not self.secret_key:
            logger.error("No JWT secret key provided")
            raise ValueError(
                "JWT secret key required. Set MEMORIC_JWT_SECRET environment variable "
                "or pass secret_key parameter."
            )

        self.algorithm = algorithm
        self.token_expiry = token_expiry_seconds

        # Password hashing context
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        logger.info("Authentication service initialized")

    def create_token(
        self,
        *,
        user_id: str,
        roles: List[Role] = None,
        namespace: Optional[str] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a JWT token for a user.

        Args:
            user_id: Unique user identifier
            roles: List of user roles (default: [Role.USER])
            namespace: Optional namespace for multi-tenancy
            extra_claims: Additional claims to include in token

        Returns:
            JWT token string

        Example:
            token = auth.create_token(
                user_id="user123",
                roles=[Role.USER],
                namespace="company_a"
            )
        """
        if roles is None:
            roles = [Role.USER]

        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=self.token_expiry)

        payload = {
            "sub": user_id,  # Subject (user ID)
            "roles": [r.value for r in roles],
            "namespace": namespace,
            "iat": now,  # Issued at
            "exp": expiry,  # Expiration
            "jti": f"{user_id}_{int(now.timestamp())}",  # JWT ID
        }

        if extra_claims:
            payload.update(extra_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.info(
            "Created JWT token",
            extra={
                "user_id": user_id,
                "roles": [r.value for r in roles],
                "namespace": namespace,
                "expiry": expiry.isoformat(),
            },
        )

        return token

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            logger.debug(
                "Token verified successfully",
                extra={"user_id": payload.get("sub")},
            )

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise

        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise

    def has_permission(
        self,
        token_payload: Dict[str, Any],
        permission: Permission | str,
    ) -> bool:
        """
        Check if user has a specific permission.

        Args:
            token_payload: Decoded JWT token payload
            permission: Permission to check

        Returns:
            True if user has permission, False otherwise

        Example:
            if auth.has_permission(payload, Permission.MEMORIES_WRITE):
                # Allow write operation
                pass
        """
        roles = [Role(r) for r in token_payload.get("roles", [])]

        # Convert string to enum if needed
        if isinstance(permission, str):
            try:
                permission = Permission(permission)
            except ValueError:
                logger.warning(f"Unknown permission: {permission}")
                return False

        # Check if any role grants the permission
        for role in roles:
            role_perms = ROLE_PERMISSIONS.get(role, [])
            if permission in role_perms or Permission.ADMIN_ACCESS in role_perms:
                return True

        return False

    def check_resource_access(
        self,
        token_payload: Dict[str, Any],
        resource_user_id: str,
        resource_namespace: Optional[str] = None,
    ) -> bool:
        """
        Check if user can access a resource.

        Users can access resources if:
        - They are the owner (user_id matches)
        - They are in the same namespace (if multi-tenant)
        - They have admin role

        Args:
            token_payload: Decoded JWT token payload
            resource_user_id: User ID that owns the resource
            resource_namespace: Namespace of the resource

        Returns:
            True if user can access resource

        Example:
            if auth.check_resource_access(payload, memory["user_id"], memory["namespace"]):
                # Allow access
                pass
        """
        user_id = token_payload.get("sub")
        user_namespace = token_payload.get("namespace")
        roles = [Role(r) for r in token_payload.get("roles", [])]

        # Admins can access everything
        if Role.ADMIN in roles:
            return True

        # Check ownership
        if user_id == resource_user_id:
            # In multi-tenant mode, also check namespace
            if resource_namespace and user_namespace != resource_namespace:
                logger.warning(
                    "Namespace mismatch",
                    extra={
                        "user_namespace": user_namespace,
                        "resource_namespace": resource_namespace,
                    },
                )
                return False
            return True

        logger.warning(
            "Access denied to resource",
            extra={
                "user_id": user_id,
                "resource_user_id": resource_user_id,
            },
        )
        return False

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password

        Example:
            hashed = auth.hash_password("user_password")
            # Store hashed in database
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password from database

        Returns:
            True if password matches

        Example:
            if auth.verify_password(input_password, user["password_hash"]):
                # Password correct, create token
                token = auth.create_token(user_id=user["id"])
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def generate_secret_key(length: int = 64) -> str:
        """
        Generate a random secret key for JWT signing.

        Args:
            length: Length of secret key in bytes

        Returns:
            Hex-encoded secret key

        Example:
            secret = AuthService.generate_secret_key()
            print(f"MEMORIC_JWT_SECRET={secret}")
            # Save this securely!
        """
        import secrets
        return secrets.token_hex(length)


__all__ = ["AuthService", "Role", "Permission", "ROLE_PERMISSIONS"]
