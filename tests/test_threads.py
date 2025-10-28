from __future__ import annotations

from memoric.core.memory_manager import Memoric


def test_thread_scoped_retrieval():
    m = Memoric()
    t1 = "th_a"
    t2 = "th_b"
    m.save(user_id="u1", thread_id=t1, content="Topic alpha one")
    m.save(user_id="u1", thread_id=t2, content="Topic alpha two")

    r_thread = m.retrieve(user_id="u1", thread_id=t1, scope="thread", top_k=10)
    assert all(r.get("thread_id") == t1 for r in r_thread)

    r_user = m.retrieve(user_id="u1", scope="user", top_k=10)
    assert any(r.get("thread_id") == t2 for r in r_user)

    r_global = m.retrieve(scope="global", top_k=10)
    assert len(r_global) >= len(r_user)
