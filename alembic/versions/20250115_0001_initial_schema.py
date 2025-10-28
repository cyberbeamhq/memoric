"""Initial schema with performance optimizations

Revision ID: 0001
Revises:
Create Date: 2025-01-15 00:01:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema with PostgreSQL optimizations."""

    # Check if we're using PostgreSQL
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Create memories table
    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("namespace", sa.String(length=128), nullable=True),
        sa.Column("thread_id", sa.String(length=128), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tier", sa.String(length=64), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB() if is_postgres else sa.JSON(), nullable=True),
        sa.Column(
            "related_threads", postgresql.JSONB() if is_postgres else sa.JSON(), nullable=True
        ),
        sa.Column("summarized", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Basic indexes
    op.create_index("idx_memories_user_id", "memories", ["user_id"])
    op.create_index("idx_memories_namespace", "memories", ["namespace"])
    op.create_index("idx_memories_thread_id", "memories", ["thread_id"])
    op.create_index("idx_memories_tier", "memories", ["tier"])
    op.create_index("idx_memories_updated_at", "memories", ["updated_at"])

    # Composite indexes for common query patterns
    op.create_index("idx_memories_user_thread", "memories", ["user_id", "thread_id"])
    op.create_index("idx_memories_user_tier", "memories", ["user_id", "tier"])
    op.create_index("idx_memories_tier_updated", "memories", ["tier", "updated_at"])
    op.create_index("idx_memories_user_tier_updated", "memories", ["user_id", "tier", "updated_at"])

    # PostgreSQL-specific: GIN indexes for JSONB fields
    if is_postgres:
        op.execute("CREATE INDEX idx_memories_metadata_gin ON memories USING GIN (metadata)")
        op.execute(
            "CREATE INDEX idx_memories_related_threads_gin ON memories USING GIN (related_threads)"
        )

    # Create memory_clusters table
    op.create_table(
        "memory_clusters",
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("topic", sa.String(length=256), nullable=False),
        sa.Column("category", sa.String(length=256), nullable=False),
        sa.Column("memory_ids", postgresql.JSONB() if is_postgres else sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("last_built_at", sa.DateTime(), nullable=True),
        sa.Column("memory_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("cluster_id"),
    )

    # Cluster indexes
    op.create_index("idx_memory_clusters_user_id", "memory_clusters", ["user_id"])
    op.create_index(
        "idx_cluster_unique", "memory_clusters", ["user_id", "topic", "category"], unique=True
    )

    # PostgreSQL-specific: GIN index for cluster memory_ids
    if is_postgres:
        op.execute(
            "CREATE INDEX idx_memory_clusters_ids_gin ON memory_clusters USING GIN (memory_ids)"
        )


def downgrade() -> None:
    """Drop all tables and indexes."""

    # Drop tables (indexes will be dropped automatically)
    op.drop_table("memory_clusters")
    op.drop_table("memories")
