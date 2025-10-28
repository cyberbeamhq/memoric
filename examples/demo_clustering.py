from __future__ import annotations

from memoric.core.memory_manager import Memoric


def main() -> None:
    m = Memoric()
    # Seed multiple memories with same topic/category
    for i in range(12):
        m.save(user_id="u_demo", thread_id=f"th_{i%3}", content=f"Refund policy update iteration {i}", metadata={"topic": "refund", "category": "support", "importance": "high"})

    # Run policies to create clusters and summaries
    result = m.run_policies()
    print(result)

    # Retrieve top results
    results = m.retrieve(user_id="u_demo", scope="user", top_k=5, metadata_filter={"topic": "refund"})
    for r in results:
        print(r.get("id"), r.get("_score"), r.get("content")[:60])


if __name__ == "__main__":
    main()


