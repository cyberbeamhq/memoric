"""
Demo: Multi-Tier Memory Management

Demonstrates the full lifecycle of memories across tiers:
- Short-term: Raw, enriched messages
- Mid-term: Trimmed, summarized content
- Long-term: Thread summaries and topic clusters

Run with: python examples/demo_multi_tier.py
"""

from __future__ import annotations

from datetime import datetime, timedelta

from memoric.core.memory_manager import Memoric


def main() -> None:
    print("=== Memoric Multi-Tier Memory Demo ===\n")

    # Initialize with default config
    mem = Memoric()

    print("1. Creating memories in short-term tier...")
    thread_id = "support-ticket-1234"
    user_id = "customer-789"

    # Simulate a customer support conversation
    messages = [
        "I ordered item #5678 two weeks ago but haven't received it yet.",
        "The tracking number shows it's stuck in transit.",
        "I've been waiting for 14 days now and need this urgently.",
        "Can you please help me get a refund or expedite shipping?",
        "I've contacted support twice before about this issue.",
        "The order total was $149.99 and I paid with credit card.",
        "My shipping address is 123 Main St, Springfield.",
        "I really need this resolved as soon as possible.",
    ]

    memory_ids = []
    for msg in messages:
        mem_id = mem.save(user_id=user_id, content=msg, thread_id=thread_id)
        memory_ids.append(mem_id)
        print(f"  ✓ Saved memory #{mem_id}")

    print(f"\n2. Checking tier statistics...")
    stats = mem.get_tier_stats()
    for tier_name, tier_stats in stats.items():
        print(f"  {tier_name}: {tier_stats['total_memories']} memories")

    print(f"\n3. Retrieving memories (unsummarized only)...")
    results = mem.retrieve(user_id=user_id, thread_id=thread_id, top_k=5)
    print(f"  Retrieved {len(results)} most relevant memories")
    for i, r in enumerate(results[:3], 1):
        print(f"  {i}. {r['content'][:60]}... (score: {r['_score']})")

    print(f"\n4. Simulating time passage and tier migration...")
    # Age some memories to trigger migration
    old_date = datetime.utcnow() - timedelta(days=8)
    mem.db.set_updated_at(memory_ids=memory_ids[:4], updated_at=old_date)

    result = mem.run_policies()
    print(f"  ✓ Migrated {result['migrated']} memories")
    print(f"  ✓ Trimmed {result['trimmed']} memories")
    print(f"  ✓ Summarized {result['summarized']} memories")

    print(f"\n5. Tier distribution after migration...")
    stats = mem.get_tier_stats()
    for tier_name, tier_stats in stats.items():
        print(
            f"  {tier_name}: {tier_stats['total_memories']} total, "
            f"{tier_stats['summarized_count']} summarized"
        )

    print(f"\n6. Creating more memories for thread summarization...")
    # Add more messages to trigger thread summary
    additional_messages = [
        "Thank you for looking into this.",
        "I appreciate your help with resolving this issue.",
        "Please keep me updated on the progress.",
        "Let me know if you need any additional information.",
    ]

    for msg in additional_messages:
        mem_id = mem.save(user_id=user_id, content=msg, thread_id=thread_id)
        memory_ids.append(mem_id)

    # Move all to long-term for demonstration
    mem.promote_to_tier(memory_ids, "long_term")

    print(f"  ✓ Promoted {len(memory_ids)} memories to long_term")

    print(f"\n7. Running policies to create thread summary...")
    result = mem.run_policies()
    print(f"  ✓ Created {result['thread_summaries']} thread summaries")
    print(f"  ✓ Created {result['clusters']} topic clusters")

    print(f"\n8. Retrieving thread summary...")
    summary = mem.get_thread_summary(thread_id=thread_id, user_id=user_id)
    if summary:
        print(f"  Thread Summary ({summary['metadata']['source_count']} messages):")
        print(f"  {summary['content'][:200]}...")
        if "topics" in summary["metadata"]:
            print(f"  Topics: {', '.join(summary['metadata']['topics'])}")
    else:
        print("  (No thread summary created yet - may need more messages)")

    print(f"\n9. Viewing topic clusters...")
    clusters = mem.get_topic_clusters(limit=5)
    if clusters:
        for i, cluster in enumerate(clusters, 1):
            print(
                f"  Cluster {i}: {cluster.get('topic', 'N/A')} / "
                f"{cluster.get('category', 'N/A')} "
                f"({len(cluster.get('memory_ids', []))} memories)"
            )
    else:
        print("  (No clusters created yet)")

    print(f"\n10. Final tier statistics...")
    stats = mem.get_tier_stats()
    print("\n  Tier Summary:")
    print("  " + "-" * 60)
    for tier_name, tier_stats in stats.items():
        util = tier_stats["utilization"]
        print(
            f"  {tier_name:12} | Total: {tier_stats['total_memories']:3} | "
            f"Summarized: {tier_stats['summarized_count']:3} | "
            f"Utilization: {util:5.1f}%"
        )

    print("\n=== Demo Complete ===")
    print("\nKey Takeaways:")
    print("- Memories automatically flow through tiers based on age")
    print("- Content is trimmed and summarized as it moves to higher tiers")
    print("- Thread summaries aggregate conversation history")
    print("- Topic clusters group related knowledge")
    print("- Retrieval excludes summarized records by default for efficiency")


if __name__ == "__main__":
    main()
