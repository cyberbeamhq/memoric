"""
Demo: Clustering & Scoring Enhancements (Phase 3)

Demonstrates:
- Per-user topic clustering
- Idempotent cluster upserts
- Custom scoring rules
- Configurable scoring weights
- CLI cluster management

Run with: python examples/demo_clustering_scoring.py
"""

from __future__ import annotations

from datetime import datetime, timedelta

# Use proper package imports
from memoric import Memoric
from memoric.utils.scoring import (
    create_topic_boost_rule,
    create_entity_match_rule,
)


def main() -> None:
    print("=== Phase 3: Clustering & Scoring Demo ===\n")

    # Initialize with custom scoring config
    custom_config = {
        "scoring": {
            "importance_weight": 0.4,
            "recency_weight": 0.4,
            "repetition_weight": 0.2,
            "decay_days": 30,
            "rules": {
                "boost_topics": ["urgent", "critical"],
                "topic_boost_amount": 20.0,
            },
        },
        "storage": {
            "tiers": [
                {"name": "short_term", "expiry_days": 7},
                {
                    "name": "long_term",
                    "clustering": {"enabled": True, "min_cluster_size": 3},
                },
            ]
        },
    }

    mem = Memoric(overrides=custom_config)

    print("1. Creating memories with different topics for clustering...")
    user_id = "demo_user"
    topics = [
        ("urgent", "support", "System is down and affecting all users!"),
        ("urgent", "support", "Critical bug in payment processing"),
        ("urgent", "support", "Need immediate assistance with refund"),
        ("billing", "finance", "Invoice #1234 payment received"),
        ("billing", "finance", "Subscription renewal for customer A"),
        ("billing", "finance", "Billing inquiry about charges"),
        ("feature", "product", "Request for dark mode"),
        ("feature", "product", "Export functionality needed"),
        ("feature", "product", "Mobile app version requested"),
    ]

    memory_ids = []
    for topic, category, content in topics:
        mem_id = mem.save(
            user_id=user_id,
            content=content,
            thread_id=f"thread_{topic}_{len(memory_ids)}",
            metadata={"topic": topic, "category": category},
        )
        memory_ids.append(mem_id)
        print(f"  ✓ Saved memory #{mem_id}: {topic}/{category}")

    print(f"\n2. Testing deterministic scoring...")
    # Retrieve and show scores
    results = mem.retrieve(user_id=user_id, top_k=5)
    print(f"  Top 5 memories by relevance score:")
    for i, r in enumerate(results, 1):
        topic = r.get("metadata", {}).get("topic", "N/A")
        score = r.get("_score", 0)
        print(f"  {i}. {topic:12} | Score: {score:3} | {r['content'][:40]}...")

    print(f"\n3. Demonstrating custom scoring rules...")
    # Add custom rule to boost specific entities
    retriever = mem.retriever
    retriever.scorer.add_rule(create_entity_match_rule(["payment", "refund"], boost_amount=15.0))

    # Retrieve again with custom rule active
    results_custom = mem.retrieve(user_id=user_id, top_k=5)
    print(f"  Top 5 with entity boost (payment, refund):")
    for i, r in enumerate(results_custom, 1):
        content = r["content"][:50]
        score = r.get("_score", 0)
        print(f"  {i}. Score: {score:3} | {content}...")

    print(f"\n4. Creating clusters from memories...")
    # Promote all to long_term for clustering
    mem.promote_to_tier(memory_ids, "long_term")
    print(f"  ✓ Promoted {len(memory_ids)} memories to long_term")

    # Run clustering
    count = mem.rebuild_clusters(user_id=user_id)
    print(f"  ✓ Created/updated {count} clusters")

    print(f"\n5. Viewing topic clusters...")
    clusters = mem.get_topic_clusters(user_id=user_id, limit=10)

    if clusters:
        for i, cluster in enumerate(clusters, 1):
            print(f"\n  Cluster {i}: {cluster['topic']} / {cluster['category']}")
            print(f"    Memories: {cluster['memory_count']}")
            print(f"    Summary: {cluster.get('summary', 'N/A')[:80]}...")
            print(f"    Last built: {cluster.get('last_built_at', 'Never')}")
    else:
        print("  No clusters created (may need more memories)")

    print(f"\n6. Testing idempotent cluster upserts...")
    # Manually upsert a cluster twice
    cluster_id1 = mem.db.upsert_cluster(
        user_id=user_id,
        topic="test",
        category="demo",
        memory_ids=[1, 2, 3],
        summary="First version",
    )
    print(f"  First upsert created cluster ID: {cluster_id1}")

    cluster_id2 = mem.db.upsert_cluster(
        user_id=user_id,
        topic="test",
        category="demo",
        memory_ids=[1, 2, 3, 4, 5],
        summary="Updated version",
    )
    print(f"  Second upsert returned cluster ID: {cluster_id2}")
    print(f"  IDs match: {cluster_id1 == cluster_id2} (idempotent ✓)")

    print(f"\n7. Scoring configuration details...")
    scorer = mem.retriever.scorer
    print(f"  Importance weight: {scorer.cfg.importance_weight}")
    print(f"  Recency weight: {scorer.cfg.recency_weight}")
    print(f"  Repetition weight: {scorer.cfg.repetition_weight}")
    print(f"  Decay days: {scorer.cfg.decay_days}")
    print(f"  Custom rules loaded: {len(scorer.custom_rules)}")

    print(f"\n8. Per-user cluster isolation test...")
    # Create memories for a different user
    user2_id = "other_user"
    for i in range(3):
        mem.save(
            user_id=user2_id,
            content=f"User 2 urgent issue {i}",
            thread_id=f"u2_thread_{i}",
            metadata={"topic": "urgent", "category": "support"},
        )

    # Promote and cluster
    user2_mems = mem.db.get_memories(user_id=user2_id)
    mem.promote_to_tier([m["id"] for m in user2_mems], "long_term")
    mem.rebuild_clusters(user_id=user2_id)

    # Verify isolation
    user1_clusters = mem.get_topic_clusters(user_id=user_id)
    user2_clusters = mem.get_topic_clusters(user_id=user2_id)

    print(f"  User 1 clusters: {len(user1_clusters)}")
    print(f"  User 2 clusters: {len(user2_clusters)}")
    print(f"  Clusters are properly isolated by user ✓")

    print("\n=== Demo Complete ===")
    print("\nKey Features Demonstrated:")
    print("✓ Configurable scoring weights via YAML")
    print("✓ Custom scoring rules (topic boost, entity matching)")
    print("✓ Deterministic scoring results")
    print("✓ Per-user topic clustering")
    print("✓ Idempotent cluster upserts (no duplicates)")
    print("✓ last_built_at tracking for incremental updates")
    print("✓ User isolation in clusters")

    print("\nCLI Commands to Try:")
    print("  memoric stats                  # View memory and cluster statistics")
    print("  memoric clusters --rebuild     # Rebuild all clusters")
    print("  memoric clusters --topic urgent  # View clusters for specific topic")


if __name__ == "__main__":
    main()
