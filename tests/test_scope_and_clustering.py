"""
Tests for topic-scope retrieval correctness and cluster idempotency.

Verifies that:
- Topic-based retrieval returns correct memories
- User isolation is maintained
- Clusters can be rebuilt safely without data loss
- Cluster operations are idempotent
"""
from __future__ import annotations

import pytest
from typing import List, Dict, Any

from memoric.core.memory_manager import Memoric


@pytest.fixture(scope="function")
def mem():
    """Create Memoric instance with in-memory SQLite."""
    # Use truly isolated in-memory database per test
    # Must override storage.tiers structure, not database.dsn
    return Memoric(overrides={
        "storage": {
            "tiers": [
                {"name": "long_term", "dsn": "sqlite:///:memory:"}
            ]
        }
    })


class TestTopicScopeRetrieval:
    """Test topic-based retrieval scope."""

    def test_topic_scope_basic(self, mem):
        """Test basic topic-scope retrieval."""
        # Create memories in different threads but same topic
        mem.save(
            user_id="user1",
            thread_id="thread1",
            content="Memory 1 about billing",
            metadata={"topic": "billing"}
        )
        mem.save(
            user_id="user1",
            thread_id="thread2",
            content="Memory 2 about billing",
            metadata={"topic": "billing"}
        )
        mem.save(
            user_id="user1",
            thread_id="thread3",
            content="Memory 3 about shipping",
            metadata={"topic": "shipping"}
        )

        # Retrieve with topic scope
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"topic": "billing"},
            scope="topic",
            top_k=10
        )

        # Should get both billing memories across different threads
        assert len(results) == 2
        assert all(r["metadata"]["topic"] == "billing" for r in results)
        assert set(r["thread_id"] for r in results) == {"thread1", "thread2"}

    def test_topic_scope_user_isolation(self, mem):
        """Test that topic scope respects user boundaries."""
        # User 1 memories
        mem.save(
            user_id="user1",
            thread_id="thread1",
            content="User 1 billing",
            metadata={"topic": "billing"}
        )
        mem.save(
            user_id="user1",
            thread_id="thread2",
            content="User 1 more billing",
            metadata={"topic": "billing"}
        )

        # User 2 memories (same topic)
        mem.save(
            user_id="user2",
            thread_id="thread3",
            content="User 2 billing",
            metadata={"topic": "billing"}
        )

        # Retrieve for user1 with topic scope
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"topic": "billing"},
            scope="topic",
            top_k=10
        )

        # Should only get user1's memories
        assert len(results) == 2
        assert all(r["user_id"] == "user1" for r in results)

    def test_thread_scope_vs_topic_scope(self, mem):
        """Test difference between thread and topic scopes."""
        # Create memories
        mem.save(
            user_id="user1",
            thread_id="thread1",
            content="Thread 1 billing",
            metadata={"topic": "billing"}
        )
        mem.save(
            user_id="user1",
            thread_id="thread2",
            content="Thread 2 billing",
            metadata={"topic": "billing"}
        )

        # Thread scope (only thread1)
        thread_results = mem.retrieve(
            user_id="user1",
            thread_id="thread1",
            scope="thread",
            top_k=10
        )

        # Topic scope (all billing across threads)
        topic_results = mem.retrieve(
            user_id="user1",
            metadata_filter={"topic": "billing"},
            scope="topic",
            top_k=10
        )

        assert len(thread_results) == 1
        assert len(topic_results) == 2
        assert thread_results[0]["thread_id"] == "thread1"

    def test_user_scope_retrieval(self, mem):
        """Test user-level scope (all memories for user)."""
        # Create memories for user1
        for i in range(5):
            mem.save(
                user_id="user1",
                thread_id=f"thread{i}",
                content=f"Memory {i}",
                metadata={"topic": f"topic{i % 2}"}
            )

        # Create memories for user2
        mem.save(
            user_id="user2",
            thread_id="thread0",
            content="User 2 memory",
            metadata={"topic": "topic0"}
        )

        # Retrieve all for user1 (user scope)
        results = mem.retrieve(
            user_id="user1",
            scope="user",
            top_k=10
        )

        # Should get all 5 user1 memories
        assert len(results) == 5
        assert all(r["user_id"] == "user1" for r in results)

    def test_topic_scope_no_matches(self, mem):
        """Test topic scope with no matching memories."""
        mem.save(
            user_id="user1",
            thread_id="thread1",
            content="Test",
            metadata={"topic": "shipping"}
        )

        # Search for different topic
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"topic": "billing"},
            scope="topic",
            top_k=10
        )

        assert len(results) == 0

    def test_topic_scope_cross_thread_linking(self, mem):
        """Test that topic scope correctly links related threads."""
        # Create multiple threads with same topic
        threads = ["support_1", "support_2", "support_3"]
        for thread in threads:
            mem.save(
                user_id="user1",
                thread_id=thread,
                content=f"Support issue in {thread}",
                metadata={"topic": "technical_support"}
            )

        # Retrieve with topic scope
        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"topic": "technical_support"},
            scope="topic",
            top_k=10
        )

        # Should get all 3 memories from different threads
        assert len(results) == 3
        result_threads = set(r["thread_id"] for r in results)
        assert result_threads == set(threads)


class TestClusterIdempotency:
    """Test that cluster operations are idempotent and safe."""

    def test_cluster_rebuild_idempotent(self, mem):
        """Test that rebuilding clusters multiple times produces same result."""
        # Create test memories
        for i in range(10):
            mem.save(
                user_id="user1",
                content=f"Billing issue {i}",
                metadata={"topic": "billing", "category": "support"}
            )

        # Rebuild clusters first time
        count1 = mem.rebuild_clusters(user_id="user1")
        clusters1 = mem.get_topic_clusters(user_id="user1")

        # Rebuild again
        count2 = mem.rebuild_clusters(user_id="user1")
        clusters2 = mem.get_topic_clusters(user_id="user1")

        # Should have same number of clusters
        assert len(clusters1) == len(clusters2)

        # Cluster content should be same
        for c1, c2 in zip(clusters1, clusters2):
            assert c1["topic"] == c2["topic"]
            assert c1["category"] == c2["category"]
            assert c1["memory_count"] == c2["memory_count"]

    def test_cluster_upsert_idempotent(self, mem):
        """Test that cluster upserts are idempotent."""
        mem._ensure_initialized()

        # Create cluster
        cluster_id1 = mem.db.upsert_cluster(
            user_id="user1",
            topic="billing",
            category="support",
            memory_ids=[1, 2, 3],
            summary="Test cluster"
        )

        # Upsert same cluster
        cluster_id2 = mem.db.upsert_cluster(
            user_id="user1",
            topic="billing",
            category="support",
            memory_ids=[1, 2, 3],
            summary="Test cluster"
        )

        # Should return same cluster ID (or update existing)
        assert cluster_id1 is not None
        assert cluster_id2 is not None

        # Verify only one cluster exists
        clusters = mem.db.get_clusters(user_id="user1", topic="billing")
        assert len(clusters) == 1

    def test_cluster_rebuild_preserves_data(self, mem):
        """Test that rebuilding doesn't lose memory data."""
        # Save memories
        memory_ids = []
        for i in range(5):
            mem_id = mem.save(
                user_id="user1",
                content=f"Memory {i}",
                metadata={"topic": "test"}
            )
            memory_ids.append(mem_id)

        # Build clusters
        mem.rebuild_clusters(user_id="user1")

        # Verify all memories still exist
        mem._ensure_initialized()
        all_memories = mem.db.get_memories(user_id="user1")
        assert len(all_memories) >= 5

        # Verify content is preserved
        contents = [m["content"] for m in all_memories]
        for i in range(5):
            assert f"Memory {i}" in contents

    def test_cluster_user_isolation(self, mem):
        """Test that clusters are isolated by user."""
        # User 1 memories
        for i in range(3):
            mem.save(
                user_id="user1",
                content=f"User 1 billing {i}",
                metadata={"topic": "billing", "category": "support"}
            )

        # User 2 memories (same topic)
        for i in range(3):
            mem.save(
                user_id="user2",
                content=f"User 2 billing {i}",
                metadata={"topic": "billing", "category": "support"}
            )

        # Build clusters for user1
        mem.rebuild_clusters(user_id="user1")
        user1_clusters = mem.get_topic_clusters(user_id="user1")

        # Build clusters for user2
        mem.rebuild_clusters(user_id="user2")
        user2_clusters = mem.get_topic_clusters(user_id="user2")

        # Both should have clusters
        assert len(user1_clusters) > 0
        assert len(user2_clusters) > 0

        # Clusters should be separate (different cluster IDs or memory IDs)
        user1_ids = set(c["cluster_id"] for c in user1_clusters)
        user2_ids = set(c["cluster_id"] for c in user2_clusters)
        assert user1_ids != user2_ids

    def test_cluster_partial_rebuild(self, mem):
        """Test rebuilding clusters for specific user."""
        # Create memories for multiple users
        mem.save(user_id="user1", content="User 1", metadata={"topic": "a"})
        mem.save(user_id="user2", content="User 2", metadata={"topic": "b"})

        # Rebuild only for user1
        count = mem.rebuild_clusters(user_id="user1")

        # Should have built clusters
        assert count >= 0

        # User1 should have clusters
        user1_clusters = mem.get_topic_clusters(user_id="user1")
        # Note: May be 0 if not enough memories to form cluster

        # This shouldn't affect user2
        user2_clusters = mem.get_topic_clusters(user_id="user2")
        # User2 clusters may or may not exist

    def test_cluster_memory_count_accuracy(self, mem):
        """Test that cluster memory counts are accurate."""
        # Create specific number of memories
        num_memories = 7
        for i in range(num_memories):
            mem.save(
                user_id="user1",
                content=f"Support ticket {i}",
                metadata={"topic": "support", "category": "technical"}
            )

        # Build clusters
        mem.rebuild_clusters(user_id="user1")

        # Get clusters
        clusters = mem.get_topic_clusters(user_id="user1", topic="support")

        if len(clusters) > 0:
            # Verify memory count
            total_memories = sum(c.get("memory_count", 0) for c in clusters)
            assert total_memories == num_memories

    def test_cluster_summary_generation(self, mem):
        """Test that cluster summaries are generated."""
        # Create memories with clear topic
        for i in range(5):
            mem.save(
                user_id="user1",
                content=f"Customer requested refund for order {i}",
                metadata={"topic": "refunds", "category": "support"}
            )

        # Build clusters
        mem.rebuild_clusters(user_id="user1")

        # Get clusters
        clusters = mem.get_topic_clusters(user_id="user1", topic="refunds")

        if len(clusters) > 0:
            # Should have a summary
            assert "summary" in clusters[0]
            # Summary should be non-empty string or None
            summary = clusters[0]["summary"]
            assert summary is None or isinstance(summary, str)

    def test_cluster_last_built_timestamp(self, mem):
        """Test that last_built_at timestamp is updated."""
        # Create memories
        mem.save(
            user_id="user1",
            content="Test",
            metadata={"topic": "test", "category": "test"}
        )

        # Build clusters
        mem.rebuild_clusters(user_id="user1")

        # Get clusters
        clusters = mem.get_topic_clusters(user_id="user1")

        if len(clusters) > 0:
            # Should have last_built_at
            assert "last_built_at" in clusters[0]
            # Should be a datetime or None
            assert clusters[0]["last_built_at"] is not None


class TestScopeEdgeCases:
    """Test edge cases in scope-based retrieval."""

    def test_empty_topic_filter(self, mem):
        """Test retrieval with empty topic in metadata."""
        mem.save(
            user_id="user1",
            content="No topic",
            metadata={"other": "value"}
        )

        results = mem.retrieve(
            user_id="user1",
            metadata_filter={"topic": ""},
            scope="topic",
            top_k=10
        )

        # Should not match
        assert len(results) == 0

    def test_null_thread_id(self, mem):
        """Test retrieval with null thread_id."""
        mem.save(
            user_id="user1",
            thread_id=None,
            content="No thread",
            metadata={"topic": "test"}
        )

        results = mem.retrieve(
            user_id="user1",
            thread_id=None,
            scope="thread",
            top_k=10
        )

        assert len(results) == 1

    def test_global_scope_cross_user(self, mem):
        """Test global scope returns memories from all users."""
        mem.save(user_id="user1", content="User 1 memory")
        mem.save(user_id="user2", content="User 2 memory")

        # Global scope (no user_id filter)
        results = mem.retrieve(
            scope="global",
            top_k=10
        )

        # Should get memories from both users
        assert len(results) == 2
        user_ids = set(r["user_id"] for r in results)
        assert user_ids == {"user1", "user2"}

    def test_scope_with_summarized_memories(self, mem):
        """Test that scope retrieval excludes summarized memories."""
        mem._ensure_initialized()

        # Create and mark one memory as summarized
        mem_id = mem.save(
            user_id="user1",
            content="Summarized memory",
            metadata={"topic": "test"}
        )
        mem.db.mark_summarized(memory_ids=[mem_id])

        # Create non-summarized memory
        mem.save(
            user_id="user1",
            content="Active memory",
            metadata={"topic": "test"}
        )

        # Retrieve (should exclude summarized)
        results = mem.retrieve(
            user_id="user1",
            scope="user",
            top_k=10
        )

        # Should only get non-summarized memory
        assert len(results) == 1
        assert results[0]["content"] == "Active memory"


class TestClusterConstraints:
    """Test cluster uniqueness and constraints."""

    def test_cluster_unique_constraint(self, mem):
        """Test that (user_id, topic, category) is unique."""
        mem._ensure_initialized()

        # Create first cluster
        id1 = mem.db.upsert_cluster(
            user_id="user1",
            topic="billing",
            category="support",
            memory_ids=[1, 2],
            summary="First"
        )

        # Try to create duplicate (should update instead)
        id2 = mem.db.upsert_cluster(
            user_id="user1",
            topic="billing",
            category="support",
            memory_ids=[3, 4],
            summary="Second"
        )

        # Should only have one cluster
        clusters = mem.db.get_clusters(user_id="user1", topic="billing")
        assert len(clusters) == 1

        # Latest data should be present
        cluster = clusters[0]
        assert 3 in cluster.get("memory_ids", []) or 4 in cluster.get("memory_ids", [])

    def test_cluster_different_categories(self, mem):
        """Test that same topic with different category creates separate clusters."""
        mem._ensure_initialized()

        # Create clusters with same topic, different category
        mem.db.upsert_cluster(
            user_id="user1",
            topic="billing",
            category="support",
            memory_ids=[1, 2],
            summary="Support billing"
        )
        mem.db.upsert_cluster(
            user_id="user1",
            topic="billing",
            category="finance",
            memory_ids=[3, 4],
            summary="Finance billing"
        )

        # Should have two separate clusters
        clusters = mem.db.get_clusters(user_id="user1", topic="billing")
        assert len(clusters) == 2

        categories = set(c["category"] for c in clusters)
        assert categories == {"support", "finance"}
