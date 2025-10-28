from __future__ import annotations

from memoric.core.memory_manager import Memoric


def main() -> None:
    m = Memoric()
    mem_id = m.save(user_id="u_123", thread_id="t_abc", content="Meeting notes about quarterly goals and OKRs")
    print("Saved memory id:", mem_id)

    results = m.retrieve(user_id="u_123", thread_id="t_abc", top_k=5)
    print("Retrieved:")
    for r in results:
        print({k: r[k] for k in ("id", "tier", "_score", "content") if k in r})


if __name__ == "__main__":
    main()


