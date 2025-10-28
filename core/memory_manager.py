from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .config_loader import ConfigLoader
from .config_loader import load_yaml, _deep_merge  # type: ignore
from ..db.postgres_connector import PostgresConnector
from ..agents.metadata_agent import MetadataAgent
from ..utils.scoring import score_memory
from .retriever import Retriever
from .policy_executor import PolicyExecutor


class Memoric:
    def __init__(
        self,
        *,
        config_path: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._init_args = {"config_path": config_path, "overrides": overrides}
        self._initialized = False
        self.config: Dict[str, Any] = {}
        self.db: Optional[PostgresConnector] = None
        self.metadata_agent = None
        self.retriever = None

    def _create_sqlite_fallback(self) -> PostgresConnector:
        # For local dev without PG, allow sqlite URL via config or fallback file
        sqlite_dsn = self.config.get("storage", {}).get("sqlite_dsn") or "sqlite:///memoric_dev.db"
        return PostgresConnector(dsn=sqlite_dsn)

    def _resolve_db_config(self) -> Dict[str, Any]:
        # Pick long_term or mid_term sqlite/postgres as primary write store
        storage = self.config.get("storage", {})
        tiers = storage.get("tiers", [])
        for preferred in ("long_term", "mid_term"):
            for tier in tiers:
                if tier.get("name") == preferred and tier.get("dsn"):
                    return {"dsn": tier["dsn"]}
        return {"dsn": None}

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        config_path = self._init_args.get("config_path")
        overrides = self._init_args.get("overrides")
        loader = ConfigLoader(runtime_overrides=overrides)
        self.config = loader.load()
        if config_path:
            from pathlib import Path

            self.config = _deep_merge(self.config, load_yaml(Path(config_path)))  # type: ignore

        db_cfg = self._resolve_db_config()
        self.db = (
            PostgresConnector(dsn=db_cfg["dsn"])
            if db_cfg.get("dsn")
            else self._create_sqlite_fallback()
        )
        self.db.create_schema_if_not_exists()

        self.metadata_agent = MetadataAgent(api_key=os.getenv("OPENAI_API_KEY"))
        recall_cfg = self.config.get("recall") or {}
        scoring_cfg = self.config.get("scoring") or {}
        self.retriever = Retriever(
            db=self.db,
            default_top_k=int(recall_cfg.get("default_top_k", 10)),
            scoring_config=scoring_cfg,
            custom_rules=None,
        )
        self._initialized = True

    # Public API
    def save(
        self,
        *,
        user_id: str,
        content: str,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> int:
        self._ensure_initialized()
        metadata = dict(metadata or {})
        enriched = self.metadata_agent.extract(
            text=content, user_id=user_id, thread_id=thread_id, session_id=session_id
        )
        merged_meta = {**metadata, **enriched}

        importance_map = {"low": 3, "medium": 5, "high": 8}
        importance_level = importance_map.get(
            str(merged_meta.get("importance", "medium")).lower(), 5
        )
        score = score_memory(
            importance_level=importance_level,
            last_seen_at=None,
            seen_count=int(merged_meta.get("seen_count", 1)),
        )

        write_policy = self.config.get("policies", {}).get("write") or []
        target_tier = None
        for rule in write_policy:
            when = (rule.get("when") or "").strip().lower()
            if when == "always":
                target_tier = (rule.get("to") or [None])[0]
                break
            if ">=" in when and "score" in when:
                try:
                    threshold = float(when.split(">=")[-1].strip())
                    if score >= int(threshold * 100):
                        target_tier = (rule.get("to") or [None])[0]
                        break
                except Exception:
                    continue

        new_id = self.db.insert_memory(
            user_id=user_id,
            thread_id=thread_id,
            content=content,
            tier=target_tier,
            score=score,
            metadata=merged_meta,
            namespace=namespace or (self.config.get("privacy", {}).get("default_namespace")),
        )
        return new_id

    def retrieve(
        self,
        *,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None,
        top_k: Optional[int] = None,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        recall_scope = scope or (self.config.get("recall", {}).get("scope") or "thread")
        privacy_cfg = self.config.get("privacy", {})
        enforce_user = bool(privacy_cfg.get("enforce_user_scope", True))
        allow_shared = bool(privacy_cfg.get("allow_shared_namespace", False))

        # Enforce user scope unless explicitly allowed via namespace
        eff_user_id = user_id
        eff_namespace = namespace or privacy_cfg.get("default_namespace")
        if not allow_shared:
            eff_namespace = None
        if enforce_user and not eff_namespace:
            # user_id required for retrieval in privacy-first mode
            pass
        return self.retriever.search(
            user_id=eff_user_id,
            thread_id=thread_id,
            metadata_filter=metadata_filter,
            scope=recall_scope,
            namespace=eff_namespace,
            top_k=top_k,
        )

    def run_policies(self) -> None:
        self._ensure_initialized()
        executor = PolicyExecutor(db=self.db, config=self.config)
        return executor.run()

    def inspect(self) -> Dict[str, Any]:
        self._ensure_initialized()
        return {
            "config": self.config,
            "db_table": self.db.table_name,
            "counts_by_tier": self.db.count_by_tier(),
        }
