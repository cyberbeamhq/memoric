"""
Memoric SDK Quick Start Guide

This example demonstrates basic usage of the Memoric SDK for memory management.
"""

from memoric import Memoric


def main():
    # Initialize Memoric (uses default config)
    mem = Memoric()

    print("=== Memoric SDK Quick Start ===\n")

    # 1. Save memories
    print("1. Saving memories...")
    user_id = "demo_user"

    mem_id1 = mem.save(
        user_id=user_id,
        content="Customer requested refund for order #1234 due to defect",
        thread_id="support_ticket_42",
        metadata={"priority": "high", "topic": "refunds"},
    )
    print(f"   Saved memory {mem_id1}")

    mem_id2 = mem.save(
        user_id=user_id,
        content="Customer satisfied with resolution, issue closed",
        thread_id="support_ticket_42",
        metadata={"priority": "low", "topic": "resolution"},
    )
    print(f"   Saved memory {mem_id2}")

    mem_id3 = mem.save(
        user_id=user_id,
        content="New feature request: dark mode for mobile app",
        thread_id="product_feedback_7",
        metadata={"priority": "medium", "topic": "features"},
    )
    print(f"   Saved memory {mem_id3}\n")

    # 2. Retrieve memories by thread
    print("2. Retrieving memories by thread...")
    thread_memories = mem.retrieve(
        user_id=user_id,
        thread_id="support_ticket_42",
        top_k=10,
    )
    print(f"   Found {len(thread_memories)} memories in thread")
    for mem in thread_memories:
        print(f"   - {mem['content'][:60]}...")

    # 3. Retrieve by metadata filter
    print("\n3. Retrieving high-priority memories...")
    high_priority = mem.retrieve(
        user_id=user_id,
        metadata_filter={"priority": "high"},
        top_k=5,
    )
    print(f"   Found {len(high_priority)} high-priority memories")

    # 4. Get statistics
    print("\n4. Memory statistics:")
    stats = mem.get_tier_stats()
    for tier, tier_stats in stats.items():
        print(f"   {tier}: {tier_stats['total_memories']} memories")

    # 5. Run policies (migration, trimming, clustering)
    print("\n5. Running memory policies...")
    policy_results = mem.run_policies()
    print(f"   Migrated: {policy_results.get('migrated', 0)}")
    print(f"   Trimmed: {policy_results.get('trimmed', 0)}")
    print(f"   Clusters rebuilt: {policy_results.get('clusters_rebuilt', 0)}")

    print("\n=== Quick Start Complete ===")


if __name__ == "__main__":
    main()
