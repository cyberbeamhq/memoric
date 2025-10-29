from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


def _key_from_metadata(metadata: Dict[str, Any]) -> Tuple[str, str]:
    """Extract (topic, category) tuple from metadata for clustering.

    Args:
        metadata: Memory metadata dictionary

    Returns:
        Tuple of (topic, category), both lowercased. Defaults to ("general", "general")
    """
    topic = str(metadata.get("topic", "general")).lower()
    category = str(metadata.get("category", "general")).lower()
    return topic, category


@dataclass
class Cluster:
    topic: str
    category: str
    memory_ids: List[int]
    summary: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SimpleClustering:
    """Simple clustering algorithm that groups memories by (topic, category) metadata."""

    def group(self, memories: List[Dict[str, Any]]) -> List[Cluster]:
        """Group memories into clusters based on their topic and category metadata.

        Args:
            memories: List of memory dictionaries with metadata

        Returns:
            List of Cluster objects, each containing memories with the same topic/category
        """
        buckets: Dict[Tuple[str, str], List[int]] = {}
        for m in memories:
            meta = m.get("metadata") or {}
            key = _key_from_metadata(meta)
            buckets.setdefault(key, []).append(int(m["id"]))
        clusters = [Cluster(topic=k[0], category=k[1], memory_ids=v) for k, v in buckets.items()]
        return clusters
