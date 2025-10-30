"""
PolicyConfig - Simplified configuration builder for Memoric.

This provides a user-friendly Python API for configuring Memoric policies
without needing to write YAML files.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class TierConfig:
    """Configuration for a single memory tier."""

    def __init__(
        self,
        name: str,
        expiry_days: int,
        backend: str = "sqlite",
        dsn: Optional[str] = None,
        trim: bool = False,
        cluster_by: Optional[List[str]] = None,
    ):
        """
        Configure a memory tier.

        Args:
            name: Tier name (e.g., 'short_term', 'mid_term', 'long_term')
            expiry_days: Number of days before memories expire
            backend: Storage backend ('sqlite' or 'postgres')
            dsn: Database connection string
            trim: Whether to trim/summarize content
            cluster_by: Fields to cluster memories by
        """
        self.name = name
        self.expiry_days = expiry_days
        self.backend = backend
        self.dsn = dsn or f"sqlite:///memoric_{name}.db"
        self.trim = trim
        self.cluster_by = cluster_by or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "expiry_days": self.expiry_days,
            "backend": self.backend,
            "dsn": self.dsn,
            "trim": self.trim,
            "cluster_by": self.cluster_by,
        }


class ScoringConfig:
    """Configuration for memory scoring weights."""

    def __init__(
        self,
        importance: float = 0.5,
        recency: float = 0.3,
        repetition: float = 0.2,
        decay_days: int = 60,
    ):
        """
        Configure scoring weights.

        Args:
            importance: Weight for importance score (0-1)
            recency: Weight for recency score (0-1)
            repetition: Weight for repetition score (0-1)
            decay_days: Days until scores decay
        """
        self.importance = importance
        self.recency = recency
        self.repetition = repetition
        self.decay_days = decay_days

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "importance_weight": self.importance,
            "recency_weight": self.recency,
            "repetition_weight": self.repetition,
            "decay_days": self.decay_days,
        }


class RetrievalConfig:
    """Configuration for memory retrieval."""

    def __init__(
        self,
        scope: str = "thread",
        default_top_k: int = 10,
        fallback_order: Optional[List[str]] = None,
    ):
        """
        Configure retrieval behavior.

        Args:
            scope: Default scope ('thread', 'topic', 'user', 'global')
            default_top_k: Default number of results to return
            fallback_order: Fallback scopes if primary scope has no results
        """
        self.scope = scope
        self.default_top_k = default_top_k
        self.fallback_order = fallback_order or ["thread", "topic", "user"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "scope": self.scope,
            "default_top_k": self.default_top_k,
            "fallback_order": self.fallback_order,
        }


class PolicyConfig:
    """
    Simplified policy configuration for Memoric.

    This provides a Python API for configuring Memoric without YAML files.

    Example:
        >>> policy = PolicyConfig(
        ...     tiers={
        ...         "short_term": {"expiry_days": 7},
        ...         "mid_term": {"expiry_days": 30},
        ...         "long_term": {"expiry_days": 365}
        ...     },
        ...     scoring={
        ...         "importance": 0.6,
        ...         "recency": 0.3,
        ...         "repetition": 0.1
        ...     }
        ... )
        >>> mem = Memoric(overrides=policy.to_config())
    """

    def __init__(
        self,
        tiers: Optional[Dict[str, Dict[str, Any]]] = None,
        scoring: Optional[Dict[str, float]] = None,
        retrieval: Optional[Dict[str, Any]] = None,
        metadata_model: Optional[str] = None,
        database_dsn: Optional[str] = None,
    ):
        """
        Create a policy configuration.

        Args:
            tiers: Tier configurations as dict
            scoring: Scoring weights as dict
            retrieval: Retrieval config as dict
            metadata_model: AI model for metadata extraction
            database_dsn: Primary database connection string
        """
        self.tiers = tiers or {}
        self.scoring = scoring or {}
        self.retrieval = retrieval or {}
        self.metadata_model = metadata_model
        self.database_dsn = database_dsn

        # Parse tier configs
        self._tier_configs: List[TierConfig] = []
        for tier_name, tier_opts in self.tiers.items():
            self._tier_configs.append(
                TierConfig(
                    name=tier_name,
                    expiry_days=tier_opts.get("expiry_days", 30),
                    backend=tier_opts.get("backend", "sqlite"),
                    dsn=tier_opts.get("dsn"),
                    trim=tier_opts.get("trim", False),
                    cluster_by=tier_opts.get("cluster_by", []),
                )
            )

        # Parse scoring config
        if self.scoring:
            self._scoring_config = ScoringConfig(
                importance=self.scoring.get("importance", 0.5),
                recency=self.scoring.get("recency", 0.3),
                repetition=self.scoring.get("repetition", 0.2),
                decay_days=self.scoring.get("decay_days", 60),
            )
        else:
            self._scoring_config = ScoringConfig()

        # Parse retrieval config
        if self.retrieval:
            self._retrieval_config = RetrievalConfig(
                scope=self.retrieval.get("scope", "thread"),
                default_top_k=self.retrieval.get("default_top_k", 10),
                fallback_order=self.retrieval.get("fallback_order"),
            )
        else:
            self._retrieval_config = RetrievalConfig()

    def to_config(self) -> Dict[str, Any]:
        """
        Convert to Memoric config dictionary format.

        Returns:
            Configuration dictionary compatible with Memoric
        """
        config: Dict[str, Any] = {}

        # Storage tiers
        if self._tier_configs:
            config["storage"] = {
                "tiers": [tier.to_dict() for tier in self._tier_configs]
            }

        # Scoring
        config["scoring"] = self._scoring_config.to_dict()

        # Retrieval/Recall
        config["recall"] = self._retrieval_config.to_dict()

        # Metadata
        if self.metadata_model:
            config["metadata"] = {
                "enrichment": {
                    "model": self.metadata_model,
                    "enabled": True,
                }
            }

        return config

    def add_tier(
        self,
        name: str,
        expiry_days: int,
        backend: str = "sqlite",
        dsn: Optional[str] = None,
    ) -> PolicyConfig:
        """
        Add a tier configuration (builder pattern).

        Args:
            name: Tier name
            expiry_days: Expiry in days
            backend: Storage backend
            dsn: Database DSN

        Returns:
            Self for chaining
        """
        self._tier_configs.append(
            TierConfig(
                name=name,
                expiry_days=expiry_days,
                backend=backend,
                dsn=dsn,
            )
        )
        return self

    def set_scoring(
        self,
        importance: float = 0.5,
        recency: float = 0.3,
        repetition: float = 0.2,
    ) -> PolicyConfig:
        """
        Set scoring weights (builder pattern).

        Args:
            importance: Importance weight
            recency: Recency weight
            repetition: Repetition weight

        Returns:
            Self for chaining
        """
        self._scoring_config = ScoringConfig(
            importance=importance,
            recency=recency,
            repetition=repetition,
        )
        return self

    def set_retrieval(
        self,
        scope: str = "thread",
        default_top_k: int = 10,
    ) -> PolicyConfig:
        """
        Set retrieval configuration (builder pattern).

        Args:
            scope: Default scope
            default_top_k: Default result count

        Returns:
            Self for chaining
        """
        self._retrieval_config = RetrievalConfig(
            scope=scope,
            default_top_k=default_top_k,
        )
        return self
