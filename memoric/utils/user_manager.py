"""
User management service for authentication and authorization.

This module provides user CRUD operations and integrates with the AuthService.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, insert, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .auth import AuthService, Role
from .logger import get_logger

logger = get_logger(__name__)


class UserManager:
    """
    User management service for authentication operations.

    Handles user registration, login, and profile management.
    """

    def __init__(self, *, engine: Engine, users_table, auth_service: AuthService):
        """
        Initialize the user manager.

        Args:
            engine: SQLAlchemy engine
            users_table: SQLAlchemy Table object for users
            auth_service: AuthService instance for JWT operations
        """
        self.engine = engine
        self.users_table = users_table
        self.auth_service = auth_service

    def create_user(
        self,
        *,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        namespace: Optional[str] = None,
        roles: Optional[List[Role]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new user account.

        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password (will be hashed)
            full_name: User's full name
            namespace: Namespace for multi-tenancy
            roles: List of roles (default: [Role.USER])
            metadata: Additional user metadata

        Returns:
            Created user dict (without password_hash)

        Raises:
            ValueError: If username or email already exists
            SQLAlchemyError: If database operation fails

        Example:
            user = user_mgr.create_user(
                username="alice",
                email="alice@example.com",
                password="secure_password_123",
                roles=[Role.USER]
            )
        """
        if roles is None:
            roles = [Role.USER]

        # Hash password
        password_hash = self.auth_service.hash_password(password)

        # Convert roles to strings
        role_strings = [r.value for r in roles]

        try:
            with self.engine.begin() as conn:
                stmt = (
                    insert(self.users_table)
                    .values(
                        username=username,
                        email=email,
                        password_hash=password_hash,
                        full_name=full_name,
                        namespace=namespace,
                        roles=role_strings,
                        metadata=metadata or {},
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    .returning(
                        self.users_table.c.id,
                        self.users_table.c.username,
                        self.users_table.c.email,
                        self.users_table.c.full_name,
                        self.users_table.c.namespace,
                        self.users_table.c.roles,
                        self.users_table.c.is_active,
                        self.users_table.c.is_verified,
                        self.users_table.c.created_at,
                        self.users_table.c.last_login_at,
                    )
                )
                result = conn.execute(stmt)
                row = result.mappings().one()
                user = dict(row)

                logger.info(
                    "User created",
                    extra={
                        "user_id": user["id"],
                        "username": username,
                        "namespace": namespace,
                    },
                )

                return user

        except IntegrityError as e:
            error_msg = str(e)
            if "username" in error_msg:
                raise ValueError(f"Username '{username}' already exists")
            elif "email" in error_msg:
                raise ValueError(f"Email '{email}' already exists")
            else:
                raise ValueError(f"User creation failed: {error_msg}")

        except SQLAlchemyError as e:
            logger.error(f"Failed to create user: {e}")
            raise

    def authenticate_user(
        self, *, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with username/password.

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            User dict if authentication successful, None otherwise

        Example:
            user = user_mgr.authenticate_user(
                username="alice",
                password="secure_password_123"
            )
            if user:
                token = auth_service.create_token(user_id=str(user["id"]))
        """
        try:
            with self.engine.connect() as conn:
                # Support login with username or email
                stmt = select(self.users_table).where(
                    and_(
                        (
                            (self.users_table.c.username == username)
                            | (self.users_table.c.email == username)
                        ),
                        self.users_table.c.is_active == True,
                    )
                )

                result = conn.execute(stmt)
                row = result.mappings().first()

                if not row:
                    logger.warning(
                        "Authentication failed: user not found",
                        extra={"username": username},
                    )
                    return None

                user = dict(row)

                # Verify password
                if not self.auth_service.verify_password(password, user["password_hash"]):
                    logger.warning(
                        "Authentication failed: invalid password",
                        extra={"username": username},
                    )
                    return None

                # Update last login timestamp
                self._update_last_login(user["id"])

                # Remove password hash from response
                user.pop("password_hash", None)

                logger.info(
                    "User authenticated successfully",
                    extra={"user_id": user["id"], "username": username},
                )

                return user

        except SQLAlchemyError as e:
            logger.error(f"Authentication error: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User dict (without password_hash) or None
        """
        try:
            with self.engine.connect() as conn:
                stmt = select(self.users_table).where(
                    self.users_table.c.id == user_id
                )
                result = conn.execute(stmt)
                row = result.mappings().first()

                if row:
                    user = dict(row)
                    user.pop("password_hash", None)
                    return user

                return None

        except SQLAlchemyError as e:
            logger.error(f"Failed to get user: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            User dict (without password_hash) or None
        """
        try:
            with self.engine.connect() as conn:
                stmt = select(self.users_table).where(
                    self.users_table.c.username == username
                )
                result = conn.execute(stmt)
                row = result.mappings().first()

                if row:
                    user = dict(row)
                    user.pop("password_hash", None)
                    return user

                return None

        except SQLAlchemyError as e:
            logger.error(f"Failed to get user: {e}")
            return None

    def update_user(
        self,
        user_id: int,
        *,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        namespace: Optional[str] = None,
        roles: Optional[List[Role]] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update user profile.

        Args:
            user_id: User ID
            full_name: New full name
            email: New email
            namespace: New namespace
            roles: New roles
            is_active: Active status
            is_verified: Verified status
            metadata: New metadata

        Returns:
            True if update successful

        Example:
            success = user_mgr.update_user(
                user_id=1,
                roles=[Role.ADMIN],
                is_verified=True
            )
        """
        updates = {"updated_at": datetime.now(timezone.utc)}

        if full_name is not None:
            updates["full_name"] = full_name
        if email is not None:
            updates["email"] = email
        if namespace is not None:
            updates["namespace"] = namespace
        if roles is not None:
            updates["roles"] = [r.value for r in roles]
        if is_active is not None:
            updates["is_active"] = is_active
        if is_verified is not None:
            updates["is_verified"] = is_verified
        if metadata is not None:
            updates["metadata"] = metadata

        try:
            with self.engine.begin() as conn:
                stmt = (
                    update(self.users_table)
                    .where(self.users_table.c.id == user_id)
                    .values(**updates)
                )
                result = conn.execute(stmt)

                logger.info(
                    "User updated",
                    extra={"user_id": user_id, "fields": list(updates.keys())},
                )

                return result.rowcount > 0

        except SQLAlchemyError as e:
            logger.error(f"Failed to update user: {e}")
            return False

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully

        Example:
            success = user_mgr.change_password(
                user_id=1,
                old_password="old_pass",
                new_password="new_secure_pass"
            )
        """
        try:
            with self.engine.connect() as conn:
                # Get current password hash
                stmt = select(self.users_table.c.password_hash).where(
                    self.users_table.c.id == user_id
                )
                result = conn.execute(stmt)
                row = result.first()

                if not row:
                    logger.warning(f"User {user_id} not found")
                    return False

                current_hash = row[0]

                # Verify old password
                if not self.auth_service.verify_password(old_password, current_hash):
                    logger.warning(
                        "Password change failed: incorrect old password",
                        extra={"user_id": user_id},
                    )
                    return False

            # Hash new password and update
            new_hash = self.auth_service.hash_password(new_password)

            with self.engine.begin() as conn:
                stmt = (
                    update(self.users_table)
                    .where(self.users_table.c.id == user_id)
                    .values(
                        password_hash=new_hash,
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                conn.execute(stmt)

            logger.info("Password changed", extra={"user_id": user_id})
            return True

        except SQLAlchemyError as e:
            logger.error(f"Failed to change password: {e}")
            return False

    def _update_last_login(self, user_id: int) -> None:
        """Update last login timestamp."""
        try:
            with self.engine.begin() as conn:
                stmt = (
                    update(self.users_table)
                    .where(self.users_table.c.id == user_id)
                    .values(last_login_at=datetime.now(timezone.utc))
                )
                conn.execute(stmt)
        except SQLAlchemyError as e:
            logger.error(f"Failed to update last login: {e}")

    def record_failed_login(self, username: str) -> None:
        """
        Record a failed login attempt for a user.

        Args:
            username: Username or email that failed login
        """
        try:
            with self.engine.begin() as conn:
                # Get current failed attempts
                stmt = select(
                    self.users_table.c.id,
                    self.users_table.c.failed_login_attempts
                ).where(
                    (self.users_table.c.username == username) |
                    (self.users_table.c.email == username)
                )
                result = conn.execute(stmt)
                row = result.first()

                if row:
                    user_id, current_attempts = row
                    new_attempts = current_attempts + 1

                    # Update failed attempts count
                    update_stmt = (
                        update(self.users_table)
                        .where(self.users_table.c.id == user_id)
                        .values(
                            failed_login_attempts=new_attempts,
                            updated_at=datetime.now(timezone.utc)
                        )
                    )
                    conn.execute(update_stmt)

                    logger.info(
                        "Failed login attempt recorded",
                        extra={"username": username, "attempts": new_attempts}
                    )

        except SQLAlchemyError as e:
            logger.error(f"Failed to record failed login: {e}")

    def is_account_locked(self, username: str) -> bool:
        """
        Check if account is locked due to failed login attempts.

        Args:
            username: Username or email to check

        Returns:
            True if account is locked, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                stmt = select(self.users_table.c.locked_until).where(
                    and_(
                        (self.users_table.c.username == username) |
                        (self.users_table.c.email == username),
                        self.users_table.c.is_active == True
                    )
                )
                result = conn.execute(stmt)
                row = result.first()

                if row and row[0]:
                    locked_until = row[0]
                    # Check if still locked
                    if datetime.now(timezone.utc) < locked_until:
                        logger.warning(
                            "Account is locked",
                            extra={"username": username, "locked_until": locked_until.isoformat()}
                        )
                        return True
                    else:
                        # Lock expired, clear it
                        self.unlock_account(username)

                return False

        except SQLAlchemyError as e:
            logger.error(f"Failed to check account lock: {e}")
            return False

    def lock_account(self, username: str, duration_minutes: int = 15) -> None:
        """
        Lock an account for a specified duration.

        Args:
            username: Username or email to lock
            duration_minutes: Duration of lockout in minutes
        """
        try:
            with self.engine.begin() as conn:
                locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)

                stmt = (
                    update(self.users_table)
                    .where(
                        (self.users_table.c.username == username) |
                        (self.users_table.c.email == username)
                    )
                    .values(
                        locked_until=locked_until,
                        updated_at=datetime.now(timezone.utc)
                    )
                )
                conn.execute(stmt)

                logger.warning(
                    "Account locked",
                    extra={
                        "username": username,
                        "locked_until": locked_until.isoformat(),
                        "duration_minutes": duration_minutes
                    }
                )

        except SQLAlchemyError as e:
            logger.error(f"Failed to lock account: {e}")

    def unlock_account(self, username: str) -> None:
        """
        Unlock an account and reset failed login attempts.

        Args:
            username: Username or email to unlock
        """
        try:
            with self.engine.begin() as conn:
                stmt = (
                    update(self.users_table)
                    .where(
                        (self.users_table.c.username == username) |
                        (self.users_table.c.email == username)
                    )
                    .values(
                        locked_until=None,
                        failed_login_attempts=0,
                        updated_at=datetime.now(timezone.utc)
                    )
                )
                conn.execute(stmt)

                logger.info("Account unlocked", extra={"username": username})

        except SQLAlchemyError as e:
            logger.error(f"Failed to unlock account: {e}")

    def clear_failed_login_attempts(self, username: str) -> None:
        """
        Clear failed login attempts (called on successful login).

        Args:
            username: Username or email to clear attempts for
        """
        try:
            with self.engine.begin() as conn:
                stmt = (
                    update(self.users_table)
                    .where(
                        (self.users_table.c.username == username) |
                        (self.users_table.c.email == username)
                    )
                    .values(
                        failed_login_attempts=0,
                        locked_until=None,
                        updated_at=datetime.now(timezone.utc)
                    )
                )
                conn.execute(stmt)

                logger.debug("Failed login attempts cleared", extra={"username": username})

        except SQLAlchemyError as e:
            logger.error(f"Failed to clear failed login attempts: {e}")

    def get_failed_login_attempts(self, username: str) -> int:
        """
        Get number of failed login attempts for a user.

        Args:
            username: Username or email to check

        Returns:
            Number of failed attempts
        """
        try:
            with self.engine.connect() as conn:
                stmt = select(self.users_table.c.failed_login_attempts).where(
                    (self.users_table.c.username == username) |
                    (self.users_table.c.email == username)
                )
                result = conn.execute(stmt)
                row = result.first()

                return row[0] if row else 0

        except SQLAlchemyError as e:
            logger.error(f"Failed to get failed login attempts: {e}")
            return 0


__all__ = ["UserManager"]
