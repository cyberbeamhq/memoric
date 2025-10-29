"""
Dialect-aware tests for SQLite vs PostgreSQL behavior.

Tests verify that Memoric works correctly with both database backends
and handles dialect-specific features appropriately.
"""
from __future__ import annotations

import os
import pytest
from typing import Dict, Any

from memoric.core.memory_manager import Memoric
from memoric.db.postgres_connector import PostgresConnector


@pytest.fixture
def postgres_dsn():
    """Get PostgreSQL DSN from environment or skip."""
    dsn = os.getenv("MEMORIC_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("PostgreSQL tests require MEMORIC_TEST_POSTGRES_DSN environment variable")
    return dsn


@pytest.fixture(scope="function")
def sqlite_mem():
    """Create Memoric instance with SQLite backend."""
    # Use truly isolated in-memory database per test
    # Must override storage.tiers structure, not database.dsn
    return Memoric(overrides={
        "storage": {
            "tiers": [
                {"name": "long_term", "dsn": "sqlite:///:memory:"}
            ]
        }
    })


@pytest.fixture
def postgres_mem(postgres_dsn):
    """Create Memoric instance with PostgreSQL backend."""
    return Memoric(overrides={
        "database": {"dsn": postgres_dsn}
    })


class TestDialectDetection:
    """Test dialect detection and flag setting."""

    def test_sqlite_detection(self, sqlite_mem):
        """Test that SQLite dialect is correctly detected."""
        sqlite_mem._ensure_initialized()
        assert sqlite_mem.db.is_sqlite is True
        assert sqlite_mem.db.is_postgres is False

    def test_postgres_detection(self, postgres_mem):
        """Test that PostgreSQL dialect is correctly detected."""
        postgres_mem._ensure_initialized()
        assert postgres_mem.db.is_postgres is True
        assert sqlite_mem.db.is_sqlite is False


class TestMetadataFiltering:
    """Test JSONB filtering across dialects."""

    def test_sqlite_metadata_filter(self, sqlite_mem):
        """Test Python-level JSON filtering for SQLite."""
        # Save memories with metadata
        sqlite_mem.save(
            user_id="test_user",
            content="Memory 1",
            metadata={"topic": "billing", "priority": "high"}
        )
        sqlite_mem.save(
            user_id="test_user",
            content="Memory 2",
            metadata={"topic": "shipping", "priority": "low"}
        )
        sqlite_mem.save(
            user_id="test_user",
            content="Memory 3",
            metadata={"topic": "billing", "priority": "medium"}
        )

        # Filter by topic
        results = sqlite_mem.retrieve(
            user_id="test_user",
            metadata_filter={"topic": "billing"},
            top_k=10
        )

        assert len(results) == 2
        assert all(r["metadata"]["topic"] == "billing" for r in results)

    def test_postgres_metadata_filter(self, postgres_mem):
        """Test native JSONB containment for PostgreSQL."""
        # Save memories with metadata
        postgres_mem.save(
            user_id="test_user",
            content="Memory 1",
            metadata={"topic": "billing", "priority": "high"}
        )
        postgres_mem.save(
            user_id="test_user",
            content="Memory 2",
            metadata={"topic": "shipping", "priority": "low"}
        )
        postgres_mem.save(
            user_id="test_user",
            content="Memory 3",
            metadata={"topic": "billing", "priority": "medium"}
        )

        # Filter by topic (uses native JSONB @> operator)
        results = postgres_mem.retrieve(
            user_id="test_user",
            metadata_filter={"topic": "billing"},
            top_k=10
        )

        assert len(results) == 2
        assert all(r["metadata"]["topic"] == "billing" for r in results)

    def test_nested_metadata_sqlite(self, sqlite_mem):
        """Test nested metadata filtering in SQLite."""
        sqlite_mem.save(
            user_id="test_user",
            content="Nested metadata test",
            metadata={
                "customer": {"name": "Alice", "tier": "premium"},
                "issue": {"type": "technical", "severity": "high"}
            }
        )

        # Filter by nested field
        results = sqlite_mem.retrieve(
            user_id="test_user",
            metadata_filter={"customer": {"tier": "premium"}},
            top_k=10
        )

        assert len(results) == 1
        assert results[0]["metadata"]["customer"]["tier"] == "premium"

    def test_nested_metadata_postgres(self, postgres_mem):
        """Test nested metadata filtering in PostgreSQL."""
        postgres_mem.save(
            user_id="test_user",
            content="Nested metadata test",
            metadata={
                "customer": {"name": "Alice", "tier": "premium"},
                "issue": {"type": "technical", "severity": "high"}
            }
        )

        # Filter by nested field (native JSONB)
        results = postgres_mem.retrieve(
            user_id="test_user",
            metadata_filter={"customer": {"tier": "premium"}},
            top_k=10
        )

        assert len(results) == 1
        assert results[0]["metadata"]["customer"]["tier"] == "premium"

    def test_list_containment_sqlite(self, sqlite_mem):
        """Test list containment in SQLite."""
        sqlite_mem.save(
            user_id="test_user",
            content="Tagged memory",
            metadata={"tags": ["urgent", "billing", "customer"]}
        )

        # Filter by tag list
        results = sqlite_mem.retrieve(
            user_id="test_user",
            metadata_filter={"tags": ["urgent"]},
            top_k=10
        )

        assert len(results) == 1
        assert "urgent" in results[0]["metadata"]["tags"]

    def test_list_containment_postgres(self, postgres_mem):
        """Test list containment in PostgreSQL."""
        postgres_mem.save(
            user_id="test_user",
            content="Tagged memory",
            metadata={"tags": ["urgent", "billing", "customer"]}
        )

        # Filter by tag list (native JSONB)
        results = postgres_mem.retrieve(
            user_id="test_user",
            metadata_filter={"tags": ["urgent"]},
            top_k=10
        )

        assert len(results) == 1
        assert "urgent" in results[0]["metadata"]["tags"]


class TestPerformanceDifferences:
    """Test performance characteristics of each dialect."""

    def test_sqlite_python_filter_applied(self, sqlite_mem, caplog):
        """Verify that SQLite uses Python-level filtering."""
        import logging
        caplog.set_level(logging.DEBUG)

        sqlite_mem.save(
            user_id="test_user",
            content="Test",
            metadata={"topic": "test"}
        )

        sqlite_mem.retrieve(
            user_id="test_user",
            metadata_filter={"topic": "test"},
            top_k=10
        )

        # Check for debug log about Python filtering
        assert any("Python-level" in record.message for record in caplog.records)

    def test_postgres_native_jsonb(self, postgres_mem):
        """Verify PostgreSQL uses native JSONB operations."""
        postgres_mem._ensure_initialized()

        # Check that database is PostgreSQL
        assert postgres_mem.db.is_postgres is True

        # Create memory with metadata
        postgres_mem.save(
            user_id="test_user",
            content="Test",
            metadata={"topic": "test"}
        )

        # Retrieve with filter (should use JSONB @> operator)
        results = postgres_mem.retrieve(
            user_id="test_user",
            metadata_filter={"topic": "test"},
            top_k=10
        )

        assert len(results) == 1


class TestCrossDialectConsistency:
    """Test that both dialects produce consistent results."""

    def test_same_results_both_dialects(self, sqlite_mem, postgres_mem):
        """Verify both dialects return same results for same data."""
        test_data = [
            {"content": "Memory 1", "metadata": {"topic": "a", "priority": 1}},
            {"content": "Memory 2", "metadata": {"topic": "b", "priority": 2}},
            {"content": "Memory 3", "metadata": {"topic": "a", "priority": 3}},
        ]

        # Save to both databases
        for data in test_data:
            sqlite_mem.save(user_id="user1", **data)
            postgres_mem.save(user_id="user1", **data)

        # Retrieve from both
        sqlite_results = sqlite_mem.retrieve(
            user_id="user1",
            metadata_filter={"topic": "a"},
            top_k=10
        )
        postgres_results = postgres_mem.retrieve(
            user_id="user1",
            metadata_filter={"topic": "a"},
            top_k=10
        )

        # Compare results
        assert len(sqlite_results) == len(postgres_results) == 2

        # Both should have same content
        sqlite_contents = sorted([r["content"] for r in sqlite_results])
        postgres_contents = sorted([r["content"] for r in postgres_results])
        assert sqlite_contents == postgres_contents

    def test_complex_filter_consistency(self, sqlite_mem, postgres_mem):
        """Test complex filters produce consistent results."""
        # Save complex data
        sqlite_mem.save(
            user_id="user1",
            content="Complex test",
            metadata={
                "nested": {"level1": {"level2": "value"}},
                "list": [1, 2, 3],
                "mixed": {"items": ["a", "b", "c"]}
            }
        )
        postgres_mem.save(
            user_id="user1",
            content="Complex test",
            metadata={
                "nested": {"level1": {"level2": "value"}},
                "list": [1, 2, 3],
                "mixed": {"items": ["a", "b", "c"]}
            }
        )

        # Query with nested filter
        sqlite_results = sqlite_mem.retrieve(
            user_id="user1",
            metadata_filter={"nested": {"level1": {"level2": "value"}}},
            top_k=10
        )
        postgres_results = postgres_mem.retrieve(
            user_id="user1",
            metadata_filter={"nested": {"level1": {"level2": "value"}}},
            top_k=10
        )

        assert len(sqlite_results) == len(postgres_results) == 1


class TestIndexUsage:
    """Test that indexes are used appropriately."""

    def test_postgres_gin_indexes_exist(self, postgres_mem):
        """Verify GIN indexes exist on PostgreSQL."""
        postgres_mem._ensure_initialized()

        from sqlalchemy import inspect, text
        inspector = inspect(postgres_mem.db.engine)

        # Check for GIN indexes on metadata column
        with postgres_mem.db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'memories'
                AND indexdef LIKE '%USING gin%'
            """))
            gin_indexes = list(result)

        assert len(gin_indexes) > 0, "No GIN indexes found"
        assert any("metadata" in idx[1] for idx in gin_indexes)

    def test_composite_indexes_exist(self, postgres_mem):
        """Verify composite indexes exist."""
        postgres_mem._ensure_initialized()

        from sqlalchemy import inspect
        inspector = inspect(postgres_mem.db.engine)

        indexes = inspector.get_indexes("memories")
        index_names = [idx["name"] for idx in indexes]

        # Check for composite indexes
        assert "idx_memories_user_thread" in index_names
        assert "idx_memories_user_tier" in index_names


class TestWarnings:
    """Test warning messages for dialect limitations."""

    def test_sqlite_warning_logged(self, caplog):
        """Test that SQLite usage triggers warning."""
        import logging
        caplog.set_level(logging.WARNING)

        mem = Memoric(overrides={
            "database": {"dsn": "sqlite:///:memory:"}
        })
        mem._ensure_initialized()

        # Check for warning about SQLite
        warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("SQLite" in w for w in warnings)
        assert any("development/testing only" in w for w in warnings)

    def test_postgres_no_warning(self, postgres_mem, caplog):
        """Test that PostgreSQL doesn't trigger SQLite warning."""
        import logging
        caplog.set_level(logging.WARNING)

        postgres_mem._ensure_initialized()

        # Should not have SQLite warning
        warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert not any("SQLite" in w and "development/testing" in w for w in warnings)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_metadata_filter(self, sqlite_mem):
        """Test empty metadata filter."""
        sqlite_mem.save(user_id="user1", content="Test", metadata={"a": "b"})

        results = sqlite_mem.retrieve(
            user_id="user1",
            metadata_filter={},
            top_k=10
        )

        assert len(results) == 1

    def test_null_metadata_values(self, sqlite_mem):
        """Test null values in metadata."""
        sqlite_mem.save(
            user_id="user1",
            content="Test",
            metadata={"key": None, "other": "value"}
        )

        results = sqlite_mem.retrieve(
            user_id="user1",
            metadata_filter={"other": "value"},
            top_k=10
        )

        assert len(results) == 1

    def test_special_characters_sqlite(self, sqlite_mem):
        """Test special characters in metadata values."""
        special_chars = r'!@#$%^&*(){}[]<>?/\|~`"' + "'"

        sqlite_mem.save(
            user_id="user1",
            content="Test",
            metadata={"special": special_chars}
        )

        results = sqlite_mem.retrieve(
            user_id="user1",
            metadata_filter={"special": special_chars},
            top_k=10
        )

        assert len(results) == 1
        assert results[0]["metadata"]["special"] == special_chars

    def test_unicode_metadata(self, sqlite_mem, postgres_mem):
        """Test Unicode characters in metadata."""
        unicode_text = "Hello 世界 مرحبا мир 🌍"

        for mem in [sqlite_mem, postgres_mem]:
            mem.save(
                user_id="user1",
                content="Unicode test",
                metadata={"text": unicode_text}
            )

            results = mem.retrieve(
                user_id="user1",
                metadata_filter={"text": unicode_text},
                top_k=10
            )

            assert len(results) == 1
            assert results[0]["metadata"]["text"] == unicode_text
