"""
Test suite for Phase 3: Clustering & Scoring Enhancements

Tests cover:
- Per-user topic/category clustering
- Idempotent cluster upserts
- last_built_at tracking
- Configurable scoring weights
- Custom scoring rules
- CLI cluster commands
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

import pytest

from memoric.core.memory_manager import Memoric
from memoric.core.clustering import SimpleClustering, Cluster
from memoric.utils.scoring import (
    ScoringEngine,
    create_topic_boost_rule,
    create_stale_penalty_rule,
    create_entity_match_rule,
)


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration with clustering and custom scoring."""
    return {
        "storage": {
            "tiers": [
                {"name": "short_term", "expiry_days": 7},
                {
                    "name": "long_term",
                    "clustering": {"enabled": True, "min_cluster_size": 2},
                },
            ]
        },
        "scoring": {
            "importance_weight": 0.4,
            "recency_weight": 0.4,
            "repetition_weight": 0.2,
            "decay_days": 30,
            "rules": {
                "boost_topics": ["urgent", "critical"],
                "topic_boost_amount": 15.0,
            },
        },
    }


def test_clustering_groups_by_user_topic_category(monkeypatch):
    """Test that clustering isolates by user and groups by topic/category."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    memories = [
        {
            "id": 1,
            "user_id": "user1",
            "content": "Content 1",
            "metadata": {"topic": "refunds", "category": "support"},
        },
        {
            "id": 2,
            "user_id": "user1",
            "content": "Content 2",
            "metadata": {"topic": "refunds", "category": "support"},
        },
        {
            "id": 3,
            "user_id": "user2",
            "content": "Content 3",
            "metadata": {"topic": "refunds", "category": "support"},
        },
        {
            "id": 4,
            "user_id": "user1",
            "content": "Content 4",
            "metadata": {"topic": "shipping", "category": "support"},
        },
    ]

    engine = SimpleClustering(min_cluster_size=2)
    clusters = engine.group(memories)

    # Should create 2 clusters: user1/refunds/support and user1/shipping not included (only 1 member)
    assert len(clusters) == 1

    # Find user1 refunds cluster
    user1_refunds = next(
        (c for c in clusters if c.user_id == "user1" and c.topic == "refunds"), None
    )
    assert user1_refunds is not None
    assert len(user1_refunds.memory_ids) == 2
    assert set(user1_refunds.memory_ids) == {1, 2}


def test_idempotent_cluster_upsert(test_config: Dict[str, Any], monkeypatch):
    """Test that cluster upserts are idempotent and don't create duplicates."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    user_id = "test_user"
    topic = "billing"
    category = "support"

    # First upsert
    cluster_id1 = mem.db.upsert_cluster(
        user_id=user_id,
        topic=topic,
        category=category,
        memory_ids=[1, 2, 3],
        summary="Initial summary",
    )

    # Second upsert with same key should update, not create new
    cluster_id2 = mem.db.upsert_cluster(
        user_id=user_id,
        topic=topic,
        category=category,
        memory_ids=[1, 2, 3, 4, 5],
        summary="Updated summary",
    )

    # Should return same cluster ID
    assert cluster_id1 == cluster_id2

    # Verify only one cluster exists
    clusters = mem.db.get_clusters(user_id=user_id, topic=topic)
    assert len(clusters) == 1
    assert clusters[0]["memory_count"] == 5
    assert clusters[0]["summary"] == "Updated summary"


def test_last_built_at_tracking(test_config: Dict[str, Any], monkeypatch):
    """Test that last_built_at is tracked on cluster updates."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    before_time = datetime.utcnow()

    cluster_id = mem.db.upsert_cluster(
        user_id="user1",
        topic="test",
        category="general",
        memory_ids=[1, 2],
        summary="Test",
    )

    after_time = datetime.utcnow()

    # Retrieve and check last_built_at
    clusters = mem.db.get_clusters(user_id="user1", topic="test")
    assert len(clusters) == 1

    last_built = clusters[0]["last_built_at"]
    assert last_built is not None
    assert before_time <= last_built <= after_time


def test_configurable_scoring_weights(test_config: Dict[str, Any], monkeypatch):
    """Test that scoring weights are loaded from configuration."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    scoring_config = test_config["scoring"]
    engine = ScoringEngine(config=scoring_config)

    # Verify weights were loaded
    assert engine.cfg.importance_weight == 0.4
    assert engine.cfg.recency_weight == 0.4
    assert engine.cfg.repetition_weight == 0.2
    assert engine.cfg.decay_days == 30


def test_topic_boost_custom_rule(monkeypatch):
    """Test that topic boost rule increases scores."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    config = {
        "importance_weight": 0.5,
        "recency_weight": 0.3,
        "repetition_weight": 0.2,
        "decay_days": 60,
    }
    engine = ScoringEngine(config=config)

    # Add custom rule to boost "urgent" topics
    engine.add_rule(create_topic_boost_rule(["urgent"], boost_amount=20.0))

    # Memory with urgent topic
    urgent_memory = {
        "id": 1,
        "content": "Urgent issue",
        "metadata": {"topic": "urgent", "importance": "high"},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    # Memory with normal topic
    normal_memory = {
        "id": 2,
        "content": "Normal issue",
        "metadata": {"topic": "general", "importance": "high"},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    urgent_score = engine.compute(urgent_memory)
    normal_score = engine.compute(normal_memory)

    # Urgent should score higher due to boost
    assert urgent_score > normal_score
    assert urgent_score - normal_score >= 15  # Should be close to boost amount


def test_stale_penalty_rule(monkeypatch):
    """Test that stale memory penalty reduces scores."""
    monkeypatch.setenv("OPENAI_API_KEY", "")

    engine = ScoringEngine(config={})
    engine.add_rule(create_stale_penalty_rule(stale_days=90, penalty=-20.0))

    # Fresh memory
    fresh_memory = {
        "id": 1,
        "content": "Recent",
        "metadata": {"importance": "high"},
        "created_at": datetime.utcnow() - timedelta(days=10),
        "updated_at": datetime.utcnow(),
    }

    # Stale memory
    stale_memory = {
        "id": 2,
        "content": "Old",
        "metadata": {"importance": "high"},
        "created_at": datetime.utcnow() - timedelta(days=200),
        "updated_at": datetime.utcnow() - timedelta(days=150),
    }

    fresh_score = engine.compute(fresh_memory)
    stale_score = engine.compute(stale_memory)

    # Stale should score lower
    assert stale_score < fresh_score


def test_entity_match_rule():
    """Test that entity matching boosts relevant memories."""
    engine = ScoringEngine(config={})
    engine.add_rule(create_entity_match_rule(["order #1234", "John Doe"], boost_amount=10.0))

    memory_with_entity = {
        "id": 1,
        "content": "Order issue",
        "metadata": {
            "importance": "medium",
            "entities": ["order #1234", "shipping"],
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    memory_without_entity = {
        "id": 2,
        "content": "Other issue",
        "metadata": {"importance": "medium", "entities": ["billing"]},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    with_score = engine.compute(memory_with_entity)
    without_score = engine.compute(memory_without_entity)

    assert with_score > without_score


def test_cluster_rebuild_integration(test_config: Dict[str, Any], monkeypatch):
    """Test full cluster rebuild integration."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    mem = Memoric(overrides=test_config)

    # Create memories with topics
    for i in range(5):
        mem.save(
            user_id="user1",
            content=f"Refund request {i}",
            thread_id=f"thread{i}",
            metadata={"topic": "refunds", "category": "support"},
        )

    for i in range(3):
        mem.save(
            user_id="user1",
            content=f"Shipping query {i}",
            thread_id=f"thread{i+5}",
            metadata={"topic": "shipping", "category": "support"},
        )

    # Promote to long_term for clustering
    all_memories = mem.db.get_memories(user_id="user1")
    mem_ids = [m["id"] for m in all_memories]
    mem.promote_to_tier(mem_ids, "long_term")

    # Rebuild clusters
    count = mem.rebuild_clusters()

    # Should create 2 clusters (refunds and shipping, both meet min size of 2)
    assert count == 2

    # Verify clusters
    clusters = mem.get_topic_clusters(user_id="user1")
    assert len(clusters) == 2

    topics = {c["topic"] for c in clusters}
    assert "refunds" in topics
    assert "shipping" in topics


def test_deterministic_scoring_results():
    """Test that scoring produces deterministic results."""
    engine = ScoringEngine(config={})

    memory = {
        "id": 1,
        "content": "Test content",
        "metadata": {"importance": "high"},
        "created_at": datetime(2024, 1, 1, 12, 0, 0),
        "updated_at": datetime(2024, 1, 1, 12, 0, 0),
    }

    # Score the same memory multiple times
    scores = [engine.compute(memory, now=datetime(2024, 6, 1, 12, 0, 0)) for _ in range(10)]

    # All scores should be identical
    assert len(set(scores)) == 1
    assert scores[0] > 0


def test_scoring_with_config_from_yaml(test_config: Dict[str, Any]):
    """Test that scoring configuration from YAML works correctly."""
    scoring_config = test_config["scoring"]
    engine = ScoringEngine(config=scoring_config)

    # Should have loaded boost topics rule
    assert len(engine.custom_rules) > 0

    # Test that urgent topic gets boosted
    memory = {
        "id": 1,
        "content": "Urgent matter",
        "metadata": {"topic": "urgent", "importance": "medium"},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    score = engine.compute(memory)
    # Should have received boost (base score + 15)
    assert score > 50  # Base medium importance would be around 50


def test_cluster_get_unique_key():
    """Test that cluster unique key generation works correctly."""
    cluster = Cluster(
        user_id="user123",
        topic="billing",
        category="support",
        memory_ids=[1, 2, 3],
    )

    key = cluster.get_unique_key()
    assert key == "user123:billing:support"

    # Different order should produce same key
    cluster2 = Cluster(
        user_id="user123",
        category="support",
        topic="billing",
        memory_ids=[3, 2, 1],
    )

    assert cluster.get_unique_key() == cluster2.get_unique_key()
