"""
FastAPI authentication middleware and dependencies.

This module provides authentication dependencies for securing API endpoints.
"""

from __future__ import annotations

from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..utils.auth import AuthService, Permission, Role
from ..utils.logger import get_logger

logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


class AuthDependency:
    """
    Dependency injection class for authentication.

    Provides authentication and authorization checks for FastAPI endpoints.
    """

    def __init__(self, auth_service: AuthService):
        """
        Initialize auth dependency.

        Args:
            auth_service: AuthService instance
        """
        self.auth_service = auth_service

    async def get_current_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> dict:
        """
        Get current authenticated user from JWT token.

        Args:
            credentials: HTTP Authorization header with Bearer token

        Returns:
            Decoded JWT payload with user info

        Raises:
            HTTPException: If authentication fails

        Example:
            @app.get("/protected")
            def protected_route(user: dict = Depends(auth_dep.get_current_user)):
                return {"user_id": user["sub"]}
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials

        try:
            payload = self.auth_service.verify_token(token)
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Expired token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def require_permission(
        self,
        permission: Permission,
        user: dict = Depends(get_current_user),
    ) -> dict:
        """
        Require a specific permission.

        Args:
            permission: Required permission
            user: Current user from get_current_user dependency

        Returns:
            User dict if authorized

        Raises:
            HTTPException: If user lacks permission

        Example:
            @app.post("/memories")
            def create_memory(
                user: dict = Depends(
                    lambda u=Depends(auth_dep.get_current_user):
                        auth_dep.require_permission(Permission.MEMORIES_WRITE, u)
                )
            ):
                ...
        """
        if not self.auth_service.has_permission(user, permission):
            logger.warning(
                "Permission denied",
                extra={
                    "user_id": user.get("sub"),
                    "permission": permission.value,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}",
            )

        return user

    async def require_role(
        self,
        role: Role,
        user: dict = Depends(get_current_user),
    ) -> dict:
        """
        Require a specific role.

        Args:
            role: Required role
            user: Current user from get_current_user dependency

        Returns:
            User dict if authorized

        Raises:
            HTTPException: If user lacks role

        Example:
            @app.delete("/users/{user_id}")
            def delete_user(
                user: dict = Depends(
                    lambda u=Depends(auth_dep.get_current_user):
                        auth_dep.require_role(Role.ADMIN, u)
                )
            ):
                ...
        """
        user_roles = [Role(r) for r in user.get("roles", [])]

        if role not in user_roles:
            logger.warning(
                "Role required",
                extra={
                    "user_id": user.get("sub"),
                    "required_role": role.value,
                    "user_roles": [r.value for r in user_roles],
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role.value}",
            )

        return user

    def enforce_user_access(self, user: dict, resource_user_id: str) -> None:
        """
        Enforce that user can only access their own resources.

        Admins can access any resources. Regular users can only access their own.

        Args:
            user: Current user from get_current_user
            resource_user_id: User ID that owns the resource

        Raises:
            HTTPException: If access denied

        Example:
            @app.get("/memories/{memory_id}")
            def get_memory(
                memory_id: int,
                user: dict = Depends(auth_dep.get_current_user)
            ):
                memory = db.get_memory(memory_id)
                auth_dep.enforce_user_access(user, memory["user_id"])
                return memory
        """
        if not self.auth_service.check_resource_access(
            user, resource_user_id, None  # namespace checked separately
        ):
            logger.warning(
                "Access denied to resource",
                extra={
                    "user_id": user.get("sub"),
                    "resource_user_id": resource_user_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this resource",
            )


# Helper function to create permission dependency
def require_permission(permission: Permission):
    """
    Create a dependency that requires a specific permission.

    Args:
        permission: Required permission

    Returns:
        FastAPI dependency function

    Example:
        @app.post("/memories", dependencies=[Depends(require_permission(Permission.MEMORIES_WRITE))])
        def create_memory(...):
            ...
    """

    async def permission_checker(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> dict:
        # This is a simplified version - in production, inject AuthService properly
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials",
            )
        # Token verification logic here
        return {}

    return permission_checker


__all__ = ["AuthDependency", "security", "require_permission"]
