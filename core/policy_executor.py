from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..db.postgres_connector import PostgresConnector
from ..utils.text import summarize_simple, trim_text
from .clustering import SimpleClustering


class PolicyExecutor:
    def __init__(self, *, db: PostgresConnector, config: Dict[str, Any]) -> None:
        self.db = db
        self.config = config

    def run(self) -> Dict[str, Any]:
        summary: Dict[str, Any] = {"migrated": 0, "summarized": 0, "trimmed": 0, "thread_summaries": 0, "clusters": 0}

        tiers = (self.config.get("storage", {}).get("tiers", []) or [])
        for tier in tiers:
            name = tier.get("name")
            expiry_days = int(tier.get("expiry_days", 0) or 0)

            # Trim long content in this tier
            trim_cfg = tier.get("trim") or {}
            max_chars = int(trim_cfg.get("max_chars", 0) or 0)
            if max_chars > 0:
                records = self.db.get_memories(tier=name, limit=1000)
                for r in records:
                    original = r.get("content", "")
                    trimmed = trim_text(original, max_chars)
                    if trimmed != original:
                        self.db.update_content(memory_id=r["id"], new_content=trimmed)
                        summary["trimmed"] += 1

            # Expiry-based migration
            if expiry_days > 0:
                older = self.db.find_older_than(days=expiry_days, from_tier=name, limit=1000)
                target_tier = self._next_tier(name)
                if target_tier:
                    moved_ids: List[int] = [int(x["id"]) for x in older]
                    if moved_ids:
                        self.db.update_tier(memory_ids=moved_ids, new_tier=target_tier)
                        summary["migrated"] += len(moved_ids)

        # Summarization pass for long texts globally
        sum_cfg = self.config.get("summarization") or {}
        if bool(sum_cfg.get("enabled", False)):
            min_chars = int(sum_cfg.get("min_chars", 600))
            target_chars = int(sum_cfg.get("target_chars", 300))
            mark_sum = bool(sum_cfg.get("mark_summarized", True))
            records = self.db.get_memories(limit=1000)
            for r in records:
                content = r.get("content", "")
                if len(content) >= min_chars:
                    new_content = summarize_simple(content, target_chars)
                    if new_content != content:
                        self.db.update_content(memory_id=r["id"], new_content=new_content)
                        summary["summarized"] += 1
                        if mark_sum:
                            self.db.mark_summarized(memory_ids=[int(r["id"])])

        # Thread-level summarization for long_term tier: collapse many entries per thread
        long_term_threads = self.db.distinct_threads(tier="long_term")
        if long_term_threads:
            for th in long_term_threads:
                records = self.db.get_memories(thread_id=th, tier="long_term", summarized=False, limit=200)
                if len(records) >= 10:
                    # Concatenate and summarize
                    joined = "\n".join([r.get("content", "") for r in records])
                    summary_text = summarize_simple(joined, 1000)
                    # Store summary as a new memory in long_term
                    self.db.insert_memory(user_id=records[0]["user_id"], content=summary_text, thread_id=th, tier="long_term", score=None, metadata={"kind": "thread_summary"})
                    summary["thread_summaries"] += 1
                    # Mark originals summarized to reduce retrieval load
                    self.db.mark_summarized(memory_ids=[int(r["id"]) for r in records])

        summary["by_tier"] = self.db.count_by_tier()
        summary["ran_at"] = datetime.utcnow().isoformat() + "Z"
        return summary

    def cluster_and_aggregate(self) -> int:
        # Fetch recent memories and group into clusters; store clusters table
        memories = self.db.get_memories(limit=1000)
        engine = SimpleClustering()
        clusters = engine.group(memories)
        created = 0
        for c in clusters:
            cid = self.db.upsert_cluster(topic=c.topic, category=c.category, memory_ids=c.memory_ids, summary=c.summary)
            if cid:
                created += 1
        return created

    def _next_tier(self, name: str) -> str | None:
        order = ["short_term", "mid_term", "long_term"]
        if name not in order:
            return None
        idx = order.index(name)
        return order[idx + 1] if idx + 1 < len(order) else None


