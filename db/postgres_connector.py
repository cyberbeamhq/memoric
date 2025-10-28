from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, String, Table, Text, and_, create_engine, func, insert, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool


DEFAULT_TABLE_NAME = "memories"


class PostgresConnector:
    def __init__(self, dsn: str, table_name: str = DEFAULT_TABLE_NAME, pool_size: int = 5, max_overflow: int = 10) -> None:
        self.dsn = dsn
        self.table_name = table_name
        self.engine: Engine = create_engine(
            dsn,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            future=True,
        )
        self.metadata = MetaData()
        self.table = Table(
            self.table_name,
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("user_id", String(128), index=True, nullable=False),
            Column("namespace", String(128), index=True, nullable=True),
            Column("thread_id", String(128), index=True, nullable=True),
            Column("content", Text, nullable=False),
            Column("tier", String(64), index=True, nullable=True),
            Column("score", Integer, nullable=True),
            Column("metadata", JSONB().with_variant(JSON, "sqlite"), nullable=True),
            Column("related_threads", JSONB().with_variant(JSON, "sqlite"), nullable=True),
            Column("summarized", Integer, nullable=True),  # 1=true, 0/NULL=false
            Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
            Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        )
        # clusters table
        self.clusters_table = Table(
            "memory_clusters",
            self.metadata,
            Column("cluster_id", Integer, primary_key=True, autoincrement=True),
            Column("topic", String, nullable=False),
            Column("category", String, nullable=False),
            Column("memory_ids", JSONB().with_variant(JSON, "sqlite"), nullable=False),
            Column("summary", Text, nullable=True),
            Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
        )

    def create_schema_if_not_exists(self) -> None:
        self.metadata.create_all(self.engine, checkfirst=True)

    # CRUD Operations
    def insert_memory(
        self,
        *,
        user_id: str,
        content: str,
        thread_id: Optional[str] = None,
        tier: Optional[str] = None,
        score: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> int:
        with self.engine.begin() as conn:
            stmt = insert(self.table).values(
                user_id=user_id,
                namespace=namespace,
                thread_id=thread_id,
                content=content,
                tier=tier,
                score=score,
                metadata=metadata,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ).returning(self.table.c.id)
            result = conn.execute(stmt)
            new_id = result.scalar_one()
            return int(new_id)

    def get_memories(
        self,
        *,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        tier: Optional[str] = None,
        where_metadata: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
        related_threads_any_of: Optional[List[str]] = None,
        summarized: Optional[bool] = None,
        limit: Optional[int] = 50,
    ) -> List[Dict[str, Any]]:
        conditions: List[Any] = []
        if user_id:
            conditions.append(self.table.c.user_id == user_id)
        if namespace:
            conditions.append(self.table.c.namespace == namespace)
        if thread_id:
            conditions.append(self.table.c.thread_id == thread_id)
        if tier:
            conditions.append(self.table.c.tier == tier)
        if where_metadata:
            # Simple containment filter for JSONB
            conditions.append(self.table.c.metadata.contains(where_metadata))
        if summarized is not None:
            if summarized:
                conditions.append((self.table.c.summarized == 1))
            else:
                conditions.append((self.table.c.summarized.is_(None)) | (self.table.c.summarized == 0))
        if related_threads_any_of:
            if self.engine.url.get_backend_name().startswith("postgres"):
                # OR of JSONB array contains checks
                contains_clauses = [self.table.c.related_threads.contains([t]) for t in related_threads_any_of]
                if contains_clauses:
                    conditions.append(or_(*contains_clauses))
            else:
                # Fallback: match by thread_id being in the list
                conditions.append(self.table.c.thread_id.in_(related_threads_any_of))

        stmt = select(self.table)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        if limit:
            stmt = stmt.limit(limit)

        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [dict(row) for row in rows]

    def update_tier(self, *, memory_ids: Iterable[int], new_tier: str) -> int:
        with self.engine.begin() as conn:
            stmt = (
                update(self.table)
                .where(self.table.c.id.in_(list(memory_ids)))
                .values(tier=new_tier, updated_at=datetime.utcnow())
            )
            result = conn.execute(stmt)
            return int(result.rowcount or 0)

    def mark_summarized(self, *, memory_ids: Iterable[int]) -> int:
        with self.engine.begin() as conn:
            stmt = (
                update(self.table)
                .where(self.table.c.id.in_(list(memory_ids)))
                .values(summarized=1, updated_at=datetime.utcnow())
            )
            result = conn.execute(stmt)
            return int(result.rowcount or 0)

    # Cluster CRUD
    def upsert_cluster(self, *, topic: str, category: str, memory_ids: List[int], summary: str = "") -> int:
        with self.engine.begin() as conn:
            # naive: insert new cluster
            stmt = insert(self.clusters_table).values(
                topic=topic,
                category=category,
                memory_ids=memory_ids,
                summary=summary,
                created_at=datetime.utcnow(),
            ).returning(self.clusters_table.c.cluster_id)
            result = conn.execute(stmt)
            cid = result.scalar_one()
            return int(cid)

    def get_clusters(self, *, topic: str | None = None, limit: int = 100) -> List[Dict[str, Any]]:
        stmt = select(self.clusters_table)
        if topic:
            stmt = stmt.where(self.clusters_table.c.topic == topic)
        stmt = stmt.limit(limit)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [dict(r) for r in rows]

    def update_content(self, *, memory_id: int, new_content: str) -> int:
        with self.engine.begin() as conn:
            stmt = (
                update(self.table)
                .where(self.table.c.id == memory_id)
                .values(content=new_content, updated_at=datetime.utcnow())
            )
            result = conn.execute(stmt)
            return int(result.rowcount or 0)

    def update_metadata(self, *, memory_id: int, new_metadata: Dict[str, Any]) -> int:
        with self.engine.begin() as conn:
            stmt = (
                update(self.table)
                .where(self.table.c.id == memory_id)
                .values(metadata=new_metadata, updated_at=datetime.utcnow())
            )
            result = conn.execute(stmt)
            return int(result.rowcount or 0)

    def set_updated_at(self, *, memory_ids: Iterable[int], updated_at: datetime) -> int:
        with self.engine.begin() as conn:
            stmt = (
                update(self.table)
                .where(self.table.c.id.in_(list(memory_ids)))
                .values(updated_at=updated_at)
            )
            result = conn.execute(stmt)
            return int(result.rowcount or 0)

    # Thread helpers
    def set_related_threads(self, *, memory_id: int, related_threads: List[str]) -> int:
        with self.engine.begin() as conn:
            stmt = (
                update(self.table)
                .where(self.table.c.id == memory_id)
                .values(related_threads=related_threads, updated_at=datetime.utcnow())
            )
            result = conn.execute(stmt)
            return int(result.rowcount or 0)

    def distinct_threads(self, *, user_id: Optional[str] = None, tier: Optional[str] = None, limit: int = 1000) -> List[str]:
        stmt = select(self.table.c.thread_id).distinct()
        conditions: List[Any] = []
        if user_id:
            conditions.append(self.table.c.user_id == user_id)
        if tier:
            conditions.append(self.table.c.tier == tier)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.limit(limit)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
            return [r[0] for r in rows if r[0]]

    def link_threads_by_topic(self, *, user_id: str, topic: str, limit: int = 100) -> List[str]:
        # Find threads for topic and return list; client can store into related_threads
        stmt = (
            select(self.table.c.thread_id)
            .where(and_(self.table.c.user_id == user_id, self.table.c.metadata["topic"].as_string() == topic))
            .distinct()
            .limit(limit)
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
            return [r[0] for r in rows if r[0]]


    # Policy helpers
    def count_by_tier(self) -> Dict[str, int]:
        stmt = select(self.table.c.tier, func.count()).group_by(self.table.c.tier)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
            return {str(tier): int(count) for tier, count in rows}

    def find_older_than(self, *, days: int, from_tier: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        conditions = [self.table.c.updated_at < cutoff]
        if from_tier:
            conditions.append(self.table.c.tier == from_tier)
        stmt = select(self.table).where(and_(*conditions)).limit(limit)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [dict(r) for r in rows]



