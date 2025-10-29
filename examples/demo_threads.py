from __future__ import annotations

# Use proper package imports
from memoric import Memoric


def main() -> None:
    m = Memoric()

    # Two threads with overlapping topic
    t1 = "thread_sales_q1"
    t2 = "thread_sales_q2"
    m.save(user_id="u_sales", thread_id=t1, content="Sales discussion for Q1 targets and KPIs")
    m.save(user_id="u_sales", thread_id=t2, content="Sales planning for Q2 targets and KPIs")

    print("Thread scope (t1):")
    print(
        [
            r.get("content")
            for r in m.retrieve(user_id="u_sales", thread_id=t1, scope="thread", top_k=5)
        ]
    )

    print("User scope:")
    print([r.get("content") for r in m.retrieve(user_id="u_sales", scope="user", top_k=5)])

    print("Global scope:")
    print([r.get("content") for r in m.retrieve(scope="global", top_k=5)])


if __name__ == "__main__":
    main()
