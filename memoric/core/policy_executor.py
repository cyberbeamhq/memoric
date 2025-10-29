from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..db.postgres_connector import PostgresConnector
from ..utils.text_processors import (
    TextTrimmer,
    TextSummarizer,
    create_trimmer,
    create_summarizer,
)
from ..utils.logger import log_policy_execution
from ..utils.metrics import record_policy_execution
from .clustering import SimpleClustering

# Constants
MIN_RECORDS_FOR_THREAD_SUMMARY = 10
THREAD_SUMMARY_MAX_CHARS = 1000
THREAD_SUMMARY_BATCH_SIZE = 200


class PolicyExecutor:
    def __init__(
        self,
        *,
        db: PostgresConnector,
        config: Dict[str, Any],
        trimmer: Optional[TextTrimmer] = None,
        summarizer: Optional[TextSummarizer] = None,
    ) -> None:
        """Initialize policy executor with pluggable text processors.

        Args:
            db: Database connector
            config: Configuration dictionary
            trimmer: Optional custom text trimmer. If None, uses config or default.
            summarizer: Optional custom text summarizer. If None, uses config or default.
        """
        self.db = db
        self.config = config

        # Initialize text processors from config or use provided/default
        if trimmer is not None:
            self.trimmer = trimmer
        else:
            trimmer_config = config.get("text_processing", {}).get("trimmer", {"type": "simple"})
            self.trimmer = create_trimmer(trimmer_config)

        if summarizer is not None:
            self.summarizer = summarizer
        else:
            summarizer_config = config.get("text_processing", {}).get("summarizer", {"type": "simple"})
            self.summarizer = create_summarizer(summarizer_config)

    def run(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute policies across all tiers.

        Args:
            user_id: Optional user ID to limit policy execution to a specific user.
                     If None, policies are executed globally across all users.

        Returns:
            Summary of policy execution including counts of affected memories
        """
        summary: Dict[str, Any] = {
            "migrated": 0,
            "summarized": 0,
            "trimmed": 0,
            "thread_summaries": 0,
            "clusters": 0,
        }

        tiers = self.config.get("storage", {}).get("tiers", []) or []
        for tier in tiers:
            name = tier.get("name")
            expiry_days = int(tier.get("expiry_days", 0) or 0)

            # Trim long content in this tier
            trim_cfg = tier.get("trim") or {}
            max_chars = int(trim_cfg.get("max_chars", 0) or 0)
            if max_chars > 0:
                records = self.db.get_memories(user_id=user_id, tier=name, limit=1000)
                trimmed_count = 0
                for r in records:
                    original = r.get("content", "")
                    trimmed = self.trimmer.trim(original, max_chars)
                    if trimmed != original:
                        self.db.update_content(memory_id=r["id"], new_content=trimmed)
                        trimmed_count += 1
                        summary["trimmed"] += 1

                if trimmed_count > 0:
                    log_policy_execution(
                        policy_type="trim",
                        affected_count=trimmed_count,
                        details={"tier": name, "max_chars": max_chars}
                    )
                    record_policy_execution("trim", trimmed_count)

            # Expiry-based migration
            if expiry_days > 0:
                older = self.db.find_older_than(user_id=user_id, days=expiry_days, from_tier=name, limit=1000)
                target_tier = self._next_tier(name)
                if target_tier:
                    moved_ids: List[int] = [int(x["id"]) for x in older]
                    if moved_ids:
                        self.db.update_tier(memory_ids=moved_ids, new_tier=target_tier)
                        migrated_count = len(moved_ids)
                        summary["migrated"] += migrated_count

                        log_policy_execution(
                            policy_type="migrate",
                            affected_count=migrated_count,
                            details={"from_tier": name, "to_tier": target_tier, "age_days": expiry_days}
                        )
                        record_policy_execution("migrate", migrated_count)

        # Summarization pass for long texts globally
        sum_cfg = self.config.get("summarization") or {}
        if bool(sum_cfg.get("enabled", False)):
            min_chars = int(sum_cfg.get("min_chars", 600))
            target_chars = int(sum_cfg.get("target_chars", 300))
            mark_sum = bool(sum_cfg.get("mark_summarized", True))
            records = self.db.get_memories(user_id=user_id, limit=1000)
            summarized_count = 0
            for r in records:
                content = r.get("content", "")
                if len(content) >= min_chars:
                    new_content = self.summarizer.summarize(content, target_chars)
                    if new_content != content:
                        self.db.update_content(memory_id=r["id"], new_content=new_content)
                        summarized_count += 1
                        summary["summarized"] += 1
                        if mark_sum:
                            self.db.mark_summarized(memory_ids=[int(r["id"])])

            if summarized_count > 0:
                log_policy_execution(
                    policy_type="summarize",
                    affected_count=summarized_count,
                    details={"min_chars": min_chars, "target_chars": target_chars}
                )
                record_policy_execution("summarize", summarized_count)

        # Thread-level summarization for long_term tier: collapse many entries per thread
        long_term_threads = self.db.distinct_threads(user_id=user_id, tier="long_term")
        thread_summary_count = 0
        if long_term_threads:
            for th in long_term_threads:
                records = self.db.get_memories(
                    thread_id=th, tier="long_term", summarized=False, limit=THREAD_SUMMARY_BATCH_SIZE
                )
                if len(records) >= MIN_RECORDS_FOR_THREAD_SUMMARY:
                    # Check if a thread summary already exists
                    existing_summaries = self.db.get_memories(
                        thread_id=th,
                        tier="long_term",
                        where_metadata={"kind": "thread_summary"},
                        limit=1
                    )

                    # Only create summary if one doesn't exist
                    if not existing_summaries:
                        # Concatenate and summarize
                        joined = "\n".join([r.get("content", "") for r in records])
                        summary_text = self.summarizer.summarize(joined, THREAD_SUMMARY_MAX_CHARS)
                        # Store summary as a new memory in long_term
                        self.db.insert_memory(
                            user_id=records[0]["user_id"],
                            content=summary_text,
                            thread_id=th,
                            tier="long_term",
                            score=None,
                            metadata={"kind": "thread_summary"},
                        )
                        thread_summary_count += 1
                        summary["thread_summaries"] += 1

                    # Mark originals summarized to reduce retrieval load
                    self.db.mark_summarized(memory_ids=[int(r["id"]) for r in records])

            if thread_summary_count > 0:
                log_policy_execution(
                    policy_type="thread_summarize",
                    affected_count=thread_summary_count,
                    details={"min_records": MIN_RECORDS_FOR_THREAD_SUMMARY}
                )
                record_policy_execution("thread_summarize", thread_summary_count)

        summary["by_tier"] = self.db.count_by_tier()
        summary["ran_at"] = datetime.now(timezone.utc).isoformat() + "Z"
        return summary

    def cluster_and_aggregate(self, user_id: str) -> int:
        """Cluster memories for a specific user.

        Args:
            user_id: User ID to cluster memories for

        Returns:
            Number of clusters created
        """
        # Fetch recent memories for this user and group into clusters
        memories = self.db.get_memories(user_id=user_id, limit=1000)
        engine = SimpleClustering()
        clusters = engine.group(memories)
        created = 0
        for c in clusters:
            cid = self.db.upsert_cluster(
                user_id=user_id,
                topic=c.topic,
                category=c.category,
                memory_ids=c.memory_ids,
                summary=c.summary
            )
            if cid:
                created += 1
        return created

    def _get_tier_order(self) -> List[str]:
        """Extract tier order from config.

        Returns:
            List of tier names in order of progression
        """
        tiers = self.config.get("storage", {}).get("tiers", []) or []
        return [t.get("name") for t in tiers if t.get("name")]

    def _next_tier(self, name: str) -> Optional[str]:
        """Get the next tier in the progression order.

        Args:
            name: Current tier name

        Returns:
            Next tier name, or None if current tier is the last one
        """
        order = self._get_tier_order()
        if not order or name not in order:
            return None
        idx = order.index(name)
        return order[idx + 1] if idx + 1 < len(order) else None
