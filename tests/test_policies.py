from __future__ import annotations

from datetime import datetime, timedelta

from memoric.core.memory_manager import Memoric


def test_run_policies_migrates(monkeypatch):
    m = Memoric()

    # Insert two memories that will appear old by forcing updated_at
    id1 = m.save(user_id="u1", thread_id="th1", content="A" * 900)
    id2 = m.save(user_id="u1", thread_id="th1", content="B" * 900)

    past = datetime.utcnow() - timedelta(days=40)
    m.db.set_updated_at(memory_ids=[id1, id2], updated_at=past)

    result = m.run_policies()
    assert result["migrated"] >= 1
    assert "by_tier" in result


