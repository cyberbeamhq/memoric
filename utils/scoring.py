from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional


@dataclass(frozen=True)
class ScoringWeights:
    importance: float = 0.6
    recency: float = 0.3
    repetition: float = 0.1


@dataclass(frozen=True)
class ScoringConfig:
    importance_weight: float = 0.5
    recency_weight: float = 0.3
    repetition_weight: float = 0.2
    decay_days: int = 60


def _normalize(value: float, min_value: float, max_value: float) -> float:
    if max_value <= min_value:
        return 0.0
    clamped = max(min(value, max_value), min_value)
    return (clamped - min_value) / (max_value - min_value)


def score_memory(
    *,
    importance_level: int,
    last_seen_at: Optional[datetime],
    seen_count: int,
    now: Optional[datetime] = None,
    weights: Optional[ScoringWeights] = None,
) -> int:
    """Deterministic score in range [0, 100]. Higher is more relevant.

    - importance_level: expected 0..10
    - last_seen_at: older memories decay
    - seen_count: diminishing returns
    """
    if weights is None:
        weights = ScoringWeights()
    if now is None:
        now = datetime.now(timezone.utc)

    importance_norm = _normalize(float(importance_level), 0.0, 10.0)

    if last_seen_at is None:
        recency_norm = 1.0
    else:
        age_seconds = max((now - last_seen_at).total_seconds(), 0.0)
        # Half-life style decay: 0 at 30 days, 1 at now
        recency_norm = 1.0 - _normalize(age_seconds, 0.0, 30.0 * 24 * 3600)

    repetition_norm = 1.0 - _normalize(float(seen_count), 0.0, 20.0)

    combined = (
        weights.importance * importance_norm
        + weights.recency * recency_norm
        + weights.repetition * repetition_norm
    )
    return int(round(max(0.0, min(1.0, combined)) * 100))


class ScoringEngine:
    def __init__(
        self,
        *,
        config: Optional[Dict[str, Any]] = None,
        custom_rules: Optional[Iterable[Callable[[Dict[str, Any]], float]]] = None,
    ) -> None:
        cfg = config or {}
        self.cfg = ScoringConfig(
            importance_weight=float(cfg.get("importance_weight", 0.5)),
            recency_weight=float(cfg.get("recency_weight", 0.3)),
            repetition_weight=float(cfg.get("repetition_weight", 0.2)),
            decay_days=int(cfg.get("decay_days", 60)),
        )
        self.custom_rules = list(custom_rules or [])

    def compute(self, memory: Dict[str, Any], now: Optional[datetime] = None) -> int:
        if now is None:
            now = datetime.now(timezone.utc)

        meta = memory.get("metadata") or {}
        importance_text = str(meta.get("importance", "medium")).lower()
        importance_level = {"low": 3, "medium": 5, "high": 8, "critical": 10}.get(importance_text, 5)

        created_at = memory.get("created_at")
        last_seen_at = memory.get("updated_at") or created_at
        seen_count = int(meta.get("seen_count", 1))

        # recency decay based on configured decay_days
        age_seconds = 0.0
        if last_seen_at is not None:
            age_seconds = max((now - last_seen_at).total_seconds(), 0.0)
        recency_norm = 1.0 - _normalize(age_seconds, 0.0, float(self.cfg.decay_days) * 24.0 * 3600.0)

        importance_norm = _normalize(float(importance_level), 0.0, 10.0)
        repetition_norm = 1.0 - _normalize(float(seen_count), 0.0, 20.0)

        combined = (
            self.cfg.importance_weight * importance_norm
            + self.cfg.recency_weight * recency_norm
            + self.cfg.repetition_weight * repetition_norm
        )

        base_score = max(0.0, min(1.0, combined)) * 100.0

        # apply custom rules (additive, small range)
        bonus = 0.0
        for rule in self.custom_rules:
            try:
                bonus += float(rule(memory))
            except Exception:
                continue
        final = max(0.0, min(100.0, base_score + bonus))
        return int(round(final))



