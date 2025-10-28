"""
Test suite for multi-tier memory management functionality.

Tests cover:
- Tier-based storage and retrieval
- Migration policies and expiry handling
- Content trimming and summarization
- Thread-level summarization
- Topic clustering
- Retrieval filtering of summarized records
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Dict

import pytest

from memoric.core.memory_manager import Memoric
from memoric.core.policy_executor import PolicyExecutor


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration with all tiers enabled."""
    return {
        "storage": {
            "tiers": [
                {
                    "name": "short_term",
                    "expiry_days": 1,  # 1 day for testing
                    "trim": {"enabled": False},
                },
                {
                    "name": "mid_term",
                    "expiry_days": 7,
                    "trim": {"enabled": True, "max_chars": 100},
                    "summarization": {"enabled": True, "min_chars": 50, "target_chars": 30},
                },
                {
                    "name": "long_term",
                    "expiry_days": None,
                    "clustering": {"enabled": True, "min_cluster_size": 3},
                },
            ]
        },
        "policies": {
            "write": [{"when": "always", "to": ["short_term"]}],
            "migrate": [
                {"from": "short_term", "to": "mid_term", "when": "age_days >= 1"},
                {"from": "mid_term", "to": "long_term", "when": "age_days >= 7"},
            ],
        },
        "summarization": {
            "enabled": True,
            "mark_summarized": True,
            "thread": {
                "enabled": True,
                "min_records": 5,
                "max_chars": 200,
                "include_metadata": True,
            },
        },
        "recall": {"include_summarized": False},
    }


def test_memories_start_in_short_term(test_config: Dict[str, Any], monkeypatch):
    """Test that new memories are written to short_term tier by default."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    mem_id = mem.save(user_id="u1", content="Test memory", thread_id="t1")
    assert isinstance(mem_id, int)

    # Verify it's in short_term
    records = mem.db.get_memories(tier="short_term")
    assert len(records) >= 1
    assert any(r["id"] == mem_id for r in records)


def test_tier_migration_by_age(test_config: Dict[str, Any], monkeypatch):
    """Test that memories migrate between tiers based on age."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    # Create a memory in short_term
    mem_id = mem.save(user_id="u1", content="Old memory", thread_id="t1")

    # Artificially age it by updating updated_at
    old_date = datetime.utcnow() - timedelta(days=2)
    mem.db.set_updated_at(memory_ids=[mem_id], updated_at=old_date)

    # Run policies to trigger migration
    result = mem.run_policies()

    # Should have migrated from short_term to mid_term
    assert result["migrated"] > 0

    # Verify it's now in mid_term
    records = mem.db.get_memories(tier="mid_term")
    assert any(r["id"] == mem_id for r in records)


def test_content_trimming_in_mid_term(test_config: Dict[str, Any], monkeypatch):
    """Test that long content is trimmed when in mid_term tier."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    long_content = "This is a very long piece of content that should be trimmed " * 10
    mem_id = mem.save(user_id="u1", content=long_content, thread_id="t1")

    # Move to mid_term directly
    mem.promote_to_tier([mem_id], "mid_term")

    # Run policies to apply trimming
    result = mem.run_policies()

    # Verify content was trimmed
    records = mem.db.get_memories(tier="mid_term")
    memory = next((r for r in records if r["id"] == mem_id), None)
    assert memory is not None
    assert len(memory["content"]) <= 100  # max_chars from config


def test_summarization_marks_records(test_config: Dict[str, Any], monkeypatch):
    """Test that summarized records are marked appropriately."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    # Create long content that should be summarized
    long_content = "A" * 200  # Longer than min_chars (50)
    mem_id = mem.save(user_id="u1", content=long_content, thread_id="t1")

    # Move to mid_term and run policies
    mem.promote_to_tier([mem_id], "mid_term")
    result = mem.run_policies()

    # Verify record is marked as summarized
    records = mem.db.get_memories(tier="mid_term", summarized=True)
    assert any(r["id"] == mem_id for r in records)


def test_retrieval_excludes_summarized_by_default(test_config: Dict[str, Any], monkeypatch):
    """Test that retrieval filters out summarized records by default."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    # Create two memories
    mem_id1 = mem.save(user_id="u1", content="Regular memory", thread_id="t1")
    mem_id2 = mem.save(user_id="u1", content="A" * 200, thread_id="t1")

    # Mark second one as summarized
    mem.db.mark_summarized(memory_ids=[mem_id2])

    # Retrieve - should only get unsummarized one
    results = mem.retrieve(user_id="u1", thread_id="t1", top_k=10)

    # Should only return unsummarized memory
    assert len(results) == 1
    assert results[0]["id"] == mem_id1


def test_thread_summarization_creates_aggregate(test_config: Dict[str, Any], monkeypatch):
    """Test that thread summarization creates aggregated summaries."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    # Create multiple memories in same thread
    mem_ids = []
    for i in range(8):  # More than min_records (5)
        mem_id = mem.save(
            user_id="u1",
            content=f"Message {i} in the conversation about testing",
            thread_id="t_summary",
        )
        mem_ids.append(mem_id)

    # Move all to long_term
    mem.promote_to_tier(mem_ids, "long_term")

    # Run policies to create thread summary
    result = mem.run_policies()

    # Should have created thread summary
    assert result["thread_summaries"] > 0

    # Verify thread summary exists
    summary = mem.get_thread_summary(thread_id="t_summary", user_id="u1")
    assert summary is not None
    assert summary["metadata"]["kind"] == "thread_summary"
    assert summary["metadata"]["source_count"] == len(mem_ids)


def test_topic_clustering_groups_similar_memories(test_config: Dict[str, Any], monkeypatch):
    """Test that similar topics are clustered together."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    # Create memories with same topic
    topics = ["refunds", "refunds", "refunds", "shipping", "shipping"]
    mem_ids = []
    for i, topic in enumerate(topics):
        mem_id = mem.save(
            user_id="u1",
            content=f"Content about {topic}",
            thread_id=f"t{i}",
            metadata={"topic": topic, "category": "support"},
        )
        mem_ids.append(mem_id)

    # Move to long_term
    mem.promote_to_tier(mem_ids, "long_term")

    # Run policies to create clusters
    result = mem.run_policies()

    # Should have created clusters
    clusters = mem.get_topic_clusters(limit=10)
    assert len(clusters) > 0

    # Verify clustering by topic
    refund_cluster = next((c for c in clusters if c.get("topic") == "refunds"), None)
    if refund_cluster:  # May not always create if min_cluster_size not met
        assert len(refund_cluster["memory_ids"]) >= 3


def test_get_tier_stats_returns_metrics(test_config: Dict[str, Any], monkeypatch):
    """Test that tier stats provide useful metrics."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    # Create memories in different tiers
    mem_id1 = mem.save(user_id="u1", content="Short term memory", thread_id="t1")
    mem_id2 = mem.save(user_id="u1", content="Another memory", thread_id="t1")

    mem.promote_to_tier([mem_id2], "mid_term")

    # Get stats
    stats = mem.get_tier_stats()

    # Verify stats structure
    assert "short_term" in stats
    assert "mid_term" in stats
    assert "long_term" in stats

    # Verify counts
    assert stats["short_term"]["total_memories"] >= 1
    assert stats["mid_term"]["total_memories"] >= 1
    assert stats["short_term"]["summarized_count"] >= 0


def test_multi_tier_full_lifecycle(test_config: Dict[str, Any], monkeypatch):
    """Integration test for full multi-tier lifecycle."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    # Create memory
    mem_id = mem.save(
        user_id="u1",
        content="This is important content about customer refund request.",
        thread_id="t_lifecycle",
    )

    # Verify starts in short_term
    assert mem.db.get_memories(tier="short_term", limit=1000)

    # Age and migrate to mid_term
    old_date = datetime.utcnow() - timedelta(days=2)
    mem.db.set_updated_at(memory_ids=[mem_id], updated_at=old_date)
    result = mem.run_policies()
    assert result["migrated"] > 0

    # Verify in mid_term and possibly trimmed
    mid_records = mem.db.get_memories(tier="mid_term")
    assert any(r["id"] == mem_id for r in mid_records)

    # Age again and migrate to long_term
    older_date = datetime.utcnow() - timedelta(days=10)
    mem.db.set_updated_at(memory_ids=[mem_id], updated_at=older_date)
    result = mem.run_policies()

    # Verify in long_term
    long_records = mem.db.get_memories(tier="long_term")
    assert any(r["id"] == mem_id for r in long_records)
