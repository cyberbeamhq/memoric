from __future__ import annotations

import os
import tempfile

from memoric.core.config_loader import ConfigLoader
from memoric.core.memory_manager import Memoric
from memoric.utils.scoring import score_memory, ScoringWeights


def test_config_merge_works(tmp_path):
    default = tmp_path / "default.yaml"
    default.write_text("storage:\n  sqlite_dsn: sqlite:///test.db\n", encoding="utf-8")

    user = tmp_path / "user.yaml"
    user.write_text("logging:\n  level: DEBUG\n", encoding="utf-8")

    cfg = ConfigLoader(default_path=default, user_path=user).load()
    assert cfg["storage"]["sqlite_dsn"].startswith("sqlite:///")
    assert cfg["logging"]["level"] == "DEBUG"


def test_scoring_deterministic():
    s1 = score_memory(importance_level=5, last_seen_at=None, seen_count=1, weights=ScoringWeights())
    s2 = score_memory(importance_level=5, last_seen_at=None, seen_count=1, weights=ScoringWeights())
    assert s1 == s2


def test_save_and_retrieve_sqlite_fallback(monkeypatch):
    # Force sqlite fallback
    monkeypatch.setenv("OPENAI_API_KEY", "")
    m = Memoric()
    mid = m.save(user_id="u1", thread_id="th1", content="test content for retrieval")
    assert isinstance(mid, int)
    results = m.retrieve(user_id="u1", thread_id="th1", top_k=3)
    assert len(results) >= 1
