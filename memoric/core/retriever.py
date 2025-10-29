from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ..db.postgres_connector import PostgresConnector
from ..utils.scoring import ScoringEngine, ScoringWeights, score_memory
from ..utils.logger import log_retrieval
from ..utils.metrics import record_memory_retrieval


class Retriever:
    def __init__(
        self,
        *,
        db: PostgresConnector,
        default_top_k: int = 10,
        scoring_config: Optional[dict] = None,
        custom_rules: Optional[list] = None,
    ) -> None:
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
    ) -> List[Dict[str, Any]]:
        """Search and retrieve memories.

        Args:
            user_id: User ID to filter by
            thread_id: Thread ID to filter by
            metadata_filter: Metadata filter dict
            scope: Retrieval scope (thread, topic, user, global)
            namespace: Namespace filter
            top_k: Maximum number of results

        Returns:
            List of memory dictionaries with computed scores
        """
        start_time = time.time()

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
                # Topic scope requires a topic filter
                import warnings
                warnings.warn(
                    "Topic scope used without 'topic' in metadata_filter. "
                    "Falling back to thread scope.",
                    UserWarning
                )
        elif scope == "user":
            thread_id = None
        elif scope == "global":
            # Global scope is dangerous - it violates user isolation
            # Only allow if user_id is explicitly None (admin use case)
            import warnings
            if user_id is not None:
                warnings.warn(
                    "Global scope requested but user_id provided. This violates privacy. "
                    "Use scope='user' instead or set user_id=None explicitly.",
                    UserWarning
                )
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

        # Score and rank records
        ranked: List[Dict[str, Any]] = []
        for r in records:
            # Create a copy with score added (records may be immutable Row objects)
            scored = {**r, "_score": self.scorer.compute(r)}
            ranked.append(scored)

        ranked.sort(key=lambda x: x.get("_score", 0), reverse=True)
        limit = top_k or self.default_top_k
        results = ranked[:limit]

        # Log retrieval operation
        duration_ms = (time.time() - start_time) * 1000
        duration_seconds = duration_ms / 1000
        avg_score = sum(r.get("_score", 0) for r in results) / len(results) if results else None

        log_retrieval(
            user_id=user_id,
            thread_id=thread_id,
            scope=scope,
            result_count=len(results),
            duration_ms=duration_ms,
            avg_score=avg_score,
            metadata_filter=metadata_filter,
        )

        # Record metrics
        record_memory_retrieval(
            user_id=user_id,
            scope=scope,
            latency_seconds=duration_seconds,
            result_count=len(results),
            avg_score=avg_score,
        )

        return results
