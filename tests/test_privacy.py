from __future__ import annotations

from memoric.core.memory_manager import Memoric


def test_user_thread_isolation():
    m = Memoric()
    m.save(user_id="u1", thread_id="a", content="hello a")
    m.save(user_id="u1", thread_id="b", content="hello b")
    m.save(user_id="u2", thread_id="a", content="hello a u2")

    r_a = m.retrieve(user_id="u1", thread_id="a", scope="thread")
    assert all(r.get("thread_id") == "a" and r.get("user_id") == "u1" for r in r_a)

    r_user = m.retrieve(user_id="u1", scope="user")
    assert any(r.get("thread_id") == "b" for r in r_user)


def test_shared_namespace_opt_in():
    m = Memoric()
    # Save in shared namespace
    ns = "team-1"
    m.save(user_id="u1", thread_id="a", content="shared a", namespace=ns)
    m.save(user_id="u2", thread_id="b", content="shared b", namespace=ns)

    # By default, allow_shared_namespace is False, so namespace has no effect
    r = m.retrieve(user_id="u1", scope="user", namespace=ns)
    assert any(r1.get("user_id") == "u1" for r1 in r)


