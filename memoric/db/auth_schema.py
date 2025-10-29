"""
Authentication database schema.

This module defines database tables for user authentication and management.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB


def create_users_table(metadata: MetaData) -> Table:
    """
    Create the users table for authentication.

    Schema:
        - id: Primary key
        - username: Unique username
        - email: Unique email address
        - password_hash: Bcrypt hashed password
        - full_name: User's full name (optional)
        - namespace: Namespace for multi-tenancy
        - roles: JSON array of roles
        - is_active: Whether user account is active
        - is_verified: Whether email is verified
        - created_at: Account creation timestamp
        - updated_at: Last update timestamp
        - last_login_at: Last login timestamp
        - metadata: Additional user metadata (JSONB)

    Returns:
        SQLAlchemy Table object
    """
    return Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("username", String(128), unique=True, nullable=False, index=True),
        Column("email", String(255), unique=True, nullable=False, index=True),
        Column("password_hash", String(255), nullable=False),
        Column("full_name", String(255), nullable=True),
        Column("namespace", String(128), index=True, nullable=True),
        Column("roles", JSONB().with_variant(JSON, "sqlite"), nullable=False, default=["user"]),
        Column("is_active", Boolean, nullable=False, default=True),
        Column("is_verified", Boolean, nullable=False, default=False),
        Column("created_at", DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)),
        Column(
            "updated_at",
            DateTime,
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        Column("last_login_at", DateTime, nullable=True),
        Column("metadata", JSONB().with_variant(JSON, "sqlite"), nullable=True),
    )


def create_api_keys_table(metadata: MetaData) -> Table:
    """
    Create the API keys table for programmatic access.

    Schema:
        - id: Primary key
        - user_id: Foreign key to users table
        - key_hash: Hashed API key
        - name: Descriptive name for the key
        - scopes: JSON array of permitted scopes
        - expires_at: Expiration timestamp (optional)
        - last_used_at: Last usage timestamp
        - is_active: Whether key is active
        - created_at: Key creation timestamp

    Returns:
        SQLAlchemy Table object
    """
    return Table(
        "api_keys",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", Integer, nullable=False, index=True),
        Column("key_hash", String(255), unique=True, nullable=False, index=True),
        Column("name", String(128), nullable=True),
        Column("scopes", JSONB().with_variant(JSON, "sqlite"), nullable=False, default=[]),
        Column("expires_at", DateTime, nullable=True),
        Column("last_used_at", DateTime, nullable=True),
        Column("is_active", Boolean, nullable=False, default=True),
        Column("created_at", DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)),
    )


def create_refresh_tokens_table(metadata: MetaData) -> Table:
    """
    Create the refresh tokens table for token rotation.

    Schema:
        - id: Primary key
        - user_id: Foreign key to users table
        - token_hash: Hashed refresh token
        - expires_at: Expiration timestamp
        - is_revoked: Whether token has been revoked
        - created_at: Token creation timestamp

    Returns:
        SQLAlchemy Table object
    """
    return Table(
        "refresh_tokens",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", Integer, nullable=False, index=True),
        Column("token_hash", String(255), unique=True, nullable=False, index=True),
        Column("expires_at", DateTime, nullable=False),
        Column("is_revoked", Boolean, nullable=False, default=False),
        Column("created_at", DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)),
    )


__all__ = [
    "create_users_table",
    "create_api_keys_table",
    "create_refresh_tokens_table",
]
