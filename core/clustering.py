from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple


def _key_from_metadata(metadata: Dict[str, Any]) -> Tuple[str, str]:
    topic = str(metadata.get("topic", "general")).lower()
    category = str(metadata.get("category", "general")).lower()
    return topic, category


@dataclass
class Cluster:
    topic: str
    category: str
    memory_ids: List[int]
    summary: str = ""
    created_at: datetime = datetime.utcnow()


class SimpleClustering:
    def group(self, memories: List[Dict[str, Any]]) -> List[Cluster]:
        buckets: Dict[Tuple[str, str], List[int]] = {}
        for m in memories:
            meta = m.get("metadata") or {}
            key = _key_from_metadata(meta)
            buckets.setdefault(key, []).append(int(m["id"]))
        clusters = [Cluster(topic=k[0], category=k[1], memory_ids=v) for k, v in buckets.items()]
        return clusters
