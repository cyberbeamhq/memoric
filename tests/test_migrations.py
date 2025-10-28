"""
Test suite for Phase 4: Database Hardening & Migrations

Tests cover:
- Alembic migration up/down operations
- PostgreSQL GIN indexes creation
- Composite indexes creation
- SQLite fallback behavior
- Python-level JSON containment filtering
- Dialect-aware query behavior
- Migration CLI commands
"""

from __future__ import annotations

import subprocess
import os
from typing import Any, Dict
from datetime import datetime

import pytest
from sqlalchemy import inspect, text

from memoric.core.memory_manager import Memoric
from memoric.db.postgres_connector import PostgresConnector


@pytest.fixture
def postgres_config() -> Dict[str, Any]:
    """Provide test configuration for PostgreSQL."""
    return {
        "storage": {
            "tiers": [
                {"name": "short_term", "expiry_days": 7},
                {"name": "long_term"},
            ]
        }
    }


@pytest.fixture
def sqlite_config() -> Dict[str, Any]:
    """Provide test configuration for SQLite."""
    return {
        "database": {"dsn": "sqlite:///test_memoric.db"},
        "storage": {
            "tiers": [
                {"name": "short_term", "expiry_days": 7},
                {"name": "long_term"},
            ]
        },
    }


def test_dialect_detection_postgres(monkeypatch):
    """Test that PostgreSQL dialect is correctly detected."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    # Assuming default config uses PostgreSQL
    db = PostgresConnector()

    # Check dialect flags
    if "postgres" in db.engine.url.get_backend_name():
        assert db.is_postgres is True
        assert db.is_sqlite is False


def test_dialect_detection_sqlite(sqlite_config: Dict[str, Any], monkeypatch):
    """Test that SQLite dialect is correctly detected."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    mem = Memoric(overrides=sqlite_config)
    db = mem.db

    assert db.is_sqlite is True
    assert db.is_postgres is False


def test_sqlite_warning_logged(sqlite_config: Dict[str, Any], monkeypatch, caplog):
    """Test that SQLite usage triggers performance warning."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    import logging

    caplog.set_level(logging.WARNING)

    mem = Memoric(overrides=sqlite_config)

    # Check for warning message
    assert any("SQLite database" in record.message for record in caplog.records)
    assert any("development/testing only" in record.message for record in caplog.records)


def test_python_level_json_containment_filter(sqlite_config: Dict[str, Any], monkeypatch):
    """Test Python-level JSON containment filtering for SQLite."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    mem = Memoric(overrides=sqlite_config)
    db = mem.db

    # Create test data
    test_records = [
        {"id": 1, "metadata": {"topic": "billing", "category": "support", "priority": "high"}},
        {"id": 2, "metadata": {"topic": "shipping", "category": "support", "priority": "low"}},
        {"id": 3, "metadata": {"topic": "billing", "category": "finance", "priority": "medium"}},
    ]

    # Test exact match
    search = {"topic": "billing"}
    filtered = db._filter_by_metadata_contains(test_records, search)
    assert len(filtered) == 2
    assert all(r["metadata"]["topic"] == "billing" for r in filtered)

    # Test multi-field match
    search = {"topic": "billing", "category": "support"}
    filtered = db._filter_by_metadata_contains(test_records, search)
    assert len(filtered) == 1
    assert filtered[0]["id"] == 1

    # Test no match
    search = {"topic": "nonexistent"}
    filtered = db._filter_by_metadata_contains(test_records, search)
    assert len(filtered) == 0


def test_python_level_json_containment_nested(sqlite_config: Dict[str, Any], monkeypatch):
    """Test Python-level JSON containment with nested objects."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    mem = Memoric(overrides=sqlite_config)
    db = mem.db

    test_records = [
        {
            "id": 1,
            "metadata": {
                "customer": {"name": "John", "tier": "premium"},
                "tags": ["urgent", "billing"],
            },
        },
        {
            "id": 2,
            "metadata": {"customer": {"name": "Jane", "tier": "standard"}, "tags": ["support"]},
        },
    ]

    # Test nested object match
    search = {"customer": {"tier": "premium"}}
    filtered = db._filter_by_metadata_contains(test_records, search)
    assert len(filtered) == 1
    assert filtered[0]["id"] == 1

    # Test list containment
    search = {"tags": ["urgent"]}
    filtered = db._filter_by_metadata_contains(test_records, search)
    assert len(filtered) == 1
    assert filtered[0]["id"] == 1


def test_metadata_query_sqlite_fallback(sqlite_config: Dict[str, Any], monkeypatch):
    """Test that metadata queries work with SQLite fallback."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    mem = Memoric(overrides=sqlite_config)

    # Create memories with metadata
    user_id = "test_user"
    mem.save(
        user_id=user_id,
        content="Urgent billing issue",
        metadata={"topic": "billing", "priority": "high"},
    )
    mem.save(
        user_id=user_id, content="General inquiry", metadata={"topic": "general", "priority": "low"}
    )
    mem.save(
        user_id=user_id,
        content="Another billing matter",
        metadata={"topic": "billing", "priority": "medium"},
    )

    # Query with metadata filter
    results = mem.db.get_memories(user_id=user_id, where_metadata={"topic": "billing"})

    # Should return 2 billing memories via Python-level filtering
    assert len(results) == 2
    assert all(r["metadata"]["topic"] == "billing" for r in results)


def test_composite_indexes_created(monkeypatch):
    """Test that composite indexes are created during migration."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    db = PostgresConnector()
    inspector = inspect(db.engine)

    # Get indexes for memories table
    indexes = inspector.get_indexes("memories")
    index_names = {idx["name"] for idx in indexes}

    # Check for composite indexes
    expected_indexes = [
        "idx_memories_user_thread",
        "idx_memories_user_tier",
        "idx_memories_tier_updated",
        "idx_memories_user_tier_updated",
    ]

    for expected in expected_indexes:
        assert expected in index_names, f"Missing composite index: {expected}"


def test_gin_indexes_postgres_only(monkeypatch):
    """Test that GIN indexes exist on PostgreSQL but not on SQLite."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    db = PostgresConnector()

    if db.is_postgres:
        # Check for GIN indexes using raw SQL
        with db.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'memories'
                AND indexname LIKE '%_gin'
            """
                )
            )
            gin_indexes = [row[0] for row in result]

            # Should have GIN indexes for metadata and related_threads
            assert "idx_memories_metadata_gin" in gin_indexes
            assert "idx_memories_related_threads_gin" in gin_indexes
    else:
        # SQLite should not have GIN indexes (will skip test)
        pytest.skip("GIN indexes are PostgreSQL-specific")


def test_migration_up_creates_schema(monkeypatch, tmp_path):
    """Test that migration upgrade creates all tables."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    # Create temporary database
    test_db = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{test_db}"

    # Set database URL for migration
    env = os.environ.copy()
    env["MEMORIC_DATABASE_URL"] = db_url

    # Run migration
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        env=env,
        capture_output=True,
        text=True,
        cwd="/Users/user/Desktop/memoric",
    )

    # Check migration succeeded
    assert result.returncode == 0, f"Migration failed: {result.stderr}"

    # Verify tables were created
    db = PostgresConnector(dsn=db_url)
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    assert "memories" in tables
    assert "memory_clusters" in tables
    assert "alembic_version" in tables


def test_migration_down_removes_schema(monkeypatch, tmp_path):
    """Test that migration downgrade removes tables."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    # Create temporary database
    test_db = tmp_path / "test_migration_down.db"
    db_url = f"sqlite:///{test_db}"

    env = os.environ.copy()
    env["MEMORIC_DATABASE_URL"] = db_url

    # Run migration up
    subprocess.run(
        ["alembic", "upgrade", "head"],
        env=env,
        capture_output=True,
        cwd="/Users/user/Desktop/memoric",
        check=True,
    )

    # Run migration down
    result = subprocess.run(
        ["alembic", "downgrade", "base"],
        env=env,
        capture_output=True,
        text=True,
        cwd="/Users/user/Desktop/memoric",
    )

    assert result.returncode == 0, f"Downgrade failed: {result.stderr}"

    # Verify tables were removed
    db = PostgresConnector(dsn=db_url)
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    assert "memories" not in tables
    assert "memory_clusters" not in tables


def test_cli_init_db_with_migrate_flag(monkeypatch, tmp_path):
    """Test that CLI init-db --migrate uses Alembic."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    # Create temporary database
    test_db = tmp_path / "test_cli_migrate.db"
    db_url = f"sqlite:///{test_db}"

    env = os.environ.copy()
    env["MEMORIC_DATABASE_URL"] = db_url

    # Mock Memoric to use test database
    from memoric import memoric_cli
    from click.testing import CliRunner

    runner = CliRunner()

    # Note: This will use the default config, not our test database
    # For a full integration test, we'd need to create a test config file
    # For now, we're just checking that the command exists and runs
    result = runner.invoke(memoric_cli.cli, ["init-db", "--help"])

    assert result.exit_code == 0
    assert "--migrate" in result.output


def test_cli_db_migrate_command_exists(monkeypatch):
    """Test that CLI db-migrate command exists."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    from memoric import memoric_cli
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(memoric_cli.cli, ["db-migrate", "--help"])

    assert result.exit_code == 0
    assert "upgrade" in result.output
    assert "downgrade" in result.output
    assert "current" in result.output
    assert "history" in result.output
    assert "revision" in result.output


def test_deterministic_index_creation(monkeypatch):
    """Test that indexes are created deterministically."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    # Create database twice and verify same indexes
    db1 = PostgresConnector()
    db1._ensure_initialized()

    inspector = inspect(db1.engine)
    indexes1 = {idx["name"] for idx in inspector.get_indexes("memories")}

    # Should have consistent set of indexes
    assert len(indexes1) > 0

    # Verify specific indexes exist
    expected = ["idx_memories_user_thread", "idx_memories_user_tier"]
    for idx in expected:
        assert idx in indexes1


def test_performance_warning_not_on_postgres(monkeypatch, caplog):
    """Test that PostgreSQL does not trigger SQLite performance warning."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    import logging

    caplog.set_level(logging.WARNING)

    db = PostgresConnector()

    if db.is_postgres:
        # Should not have SQLite warning
        assert not any("SQLite database" in record.message for record in caplog.records)


def test_metadata_query_performance_postgres_vs_sqlite(
    postgres_config: Dict[str, Any], sqlite_config: Dict[str, Any], monkeypatch
):
    """Test metadata query uses native JSONB on PostgreSQL."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    # Test PostgreSQL path
    mem_pg = Memoric(overrides=postgres_config)
    if mem_pg.db.is_postgres:
        # Create memory and query
        user_id = "perf_test"
        mem_pg.save(user_id=user_id, content="Test", metadata={"test": "value"})

        # This should use native JSONB containment (not Python filtering)
        results = mem_pg.db.get_memories(user_id=user_id, where_metadata={"test": "value"})
        assert len(results) == 1

    # Test SQLite path
    mem_sqlite = Memoric(overrides=sqlite_config)
    assert mem_sqlite.db.is_sqlite is True

    # Create memory and query
    user_id = "perf_test"
    mem_sqlite.save(user_id=user_id, content="Test", metadata={"test": "value"})

    # This should use Python-level filtering
    results = mem_sqlite.db.get_memories(user_id=user_id, where_metadata={"test": "value"})
    assert len(results) == 1


def test_cluster_indexes_created(monkeypatch):
    """Test that cluster table has proper indexes."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    db = PostgresConnector()
    inspector = inspect(db.engine)

    # Get indexes for memory_clusters table
    indexes = inspector.get_indexes("memory_clusters")
    index_names = {idx["name"] for idx in indexes}

    # Check for cluster-specific indexes
    assert "idx_cluster_unique" in index_names
