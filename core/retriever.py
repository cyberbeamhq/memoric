from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..db.postgres_connector import PostgresConnector
from ..utils.scoring import ScoringEngine, ScoringWeights, score_memory


class Retriever:
    def __init__(self, *, db: PostgresConnector, default_top_k: int = 10, scoring_config: Optional[dict] = None, custom_rules: Optional[list] = None) -> None:
        self.db = db
        self.default_top_k = default_top_k
        self.scorer = ScoringEngine(config=scoring_config, custom_rules=custom_rules)

    def search(
        self,
        *,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        scope: str = "thread",
        namespace: Optional[str] = None,
        top_k: Optional[int] = None,
        scoring_weights: Optional[ScoringWeights] = None,
    ) -> List[Dict[str, Any]]:
        # Resolve scope to DB filters
        related_threads: Optional[List[str]] = None
        if scope == "thread":
            pass
        elif scope == "topic":
            # per-user topic scope: find threads that share the same topic
            if metadata_filter and "topic" in metadata_filter and user_id:
                topic = str(metadata_filter["topic"])
                related_threads = self.db.link_threads_by_topic(user_id=user_id, topic=topic)
            else:
                related_threads = None
        elif scope == "user":
            thread_id = None
        elif scope == "global":
            user_id = None
            thread_id = None

        records = self.db.get_memories(
            user_id=user_id,
            thread_id=thread_id,
            where_metadata=metadata_filter,
            namespace=namespace,
            related_threads_any_of=related_threads,
            summarized=False,
            limit=1000,
        )

        ranked: List[Dict[str, Any]] = []
        for r in records:
            r = dict(r)
            r["_score"] = self.scorer.compute(r)
            ranked.append(r)

        ranked.sort(key=lambda x: x.get("_score", 0), reverse=True)
        limit = top_k or self.default_top_k
        return ranked[:limit]


