"""
Prometheus metrics for Memoric.

Provides instrumentation for monitoring memory operations.
"""
from __future__ import annotations

from typing import Optional

try:
    from prometheus_client import Counter, Histogram, Gauge, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    # Graceful fallback if prometheus_client not installed
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = Info = None  # type: ignore


# Define metrics (will be None if Prometheus not available)
if PROMETHEUS_AVAILABLE:
    # Memory operations
    memories_created_total = Counter(
        'memoric_memories_created_total',
        'Total number of memories created',
        ['user_id']
    )

    memories_retrieved_total = Counter(
        'memoric_memories_retrieved_total',
        'Total number of memory retrievals',
        ['user_id', 'scope']
    )

    retrieval_latency_seconds = Histogram(
        'memoric_retrieval_latency_seconds',
        'Latency of memory retrieval operations',
        ['scope'],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
    )

    retrieval_result_count = Histogram(
        'memoric_retrieval_result_count',
        'Number of results returned by retrieval',
        ['scope'],
        buckets=(1, 5, 10, 20, 50, 100, 200, 500, 1000)
    )

    retrieval_avg_score = Histogram(
        'memoric_retrieval_avg_score',
        'Average relevance score of retrieved memories',
        ['scope'],
        buckets=(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
    )

    # Policy execution
    policy_executions_total = Counter(
        'memoric_policy_executions_total',
        'Total number of policy executions',
        ['policy_type']
    )

    policy_affected_records = Histogram(
        'memoric_policy_affected_records',
        'Number of records affected by policy execution',
        ['policy_type'],
        buckets=(1, 5, 10, 50, 100, 500, 1000, 5000, 10000)
    )

    # Clustering
    clusters_built_total = Counter(
        'memoric_clusters_built_total',
        'Total number of clusters built'
    )

    cluster_size = Histogram(
        'memoric_cluster_size',
        'Number of memories per cluster',
        buckets=(1, 5, 10, 20, 50, 100, 200, 500)
    )

    # Database metrics
    db_query_latency_seconds = Histogram(
        'memoric_db_query_latency_seconds',
        'Database query latency',
        ['operation', 'table'],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
    )

    db_rows_affected = Histogram(
        'memoric_db_rows_affected',
        'Number of database rows affected',
        ['operation', 'table'],
        buckets=(1, 10, 50, 100, 500, 1000, 5000, 10000)
    )

    # Tier statistics (gauges updated periodically)
    tier_memory_count = Gauge(
        'memoric_tier_memory_count',
        'Current number of memories in tier',
        ['tier']
    )

    tier_utilization_percent = Gauge(
        'memoric_tier_utilization_percent',
        'Tier capacity utilization percentage',
        ['tier']
    )

    # System info
    memoric_info = Info(
        'memoric',
        'Memoric system information'
    )

else:
    # No-op placeholders
    memories_created_total = None
    memories_retrieved_total = None
    retrieval_latency_seconds = None
    retrieval_result_count = None
    retrieval_avg_score = None
    policy_executions_total = None
    policy_affected_records = None
    clusters_built_total = None
    cluster_size = None
    db_query_latency_seconds = None
    db_rows_affected = None
    tier_memory_count = None
    tier_utilization_percent = None
    memoric_info = None


def record_memory_created(user_id: str) -> None:
    """Record memory creation metric."""
    if PROMETHEUS_AVAILABLE and memories_created_total:
        memories_created_total.labels(user_id=user_id or "unknown").inc()


def record_memory_retrieval(
    user_id: Optional[str],
    scope: str,
    latency_seconds: float,
    result_count: int,
    avg_score: Optional[float] = None,
) -> None:
    """Record memory retrieval metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    if memories_retrieved_total:
        memories_retrieved_total.labels(
            user_id=user_id or "unknown",
            scope=scope
        ).inc()

    if retrieval_latency_seconds:
        retrieval_latency_seconds.labels(scope=scope).observe(latency_seconds)

    if retrieval_result_count:
        retrieval_result_count.labels(scope=scope).observe(result_count)

    if avg_score is not None and retrieval_avg_score:
        retrieval_avg_score.labels(scope=scope).observe(avg_score)


def record_policy_execution(policy_type: str, affected_count: int) -> None:
    """Record policy execution metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    if policy_executions_total:
        policy_executions_total.labels(policy_type=policy_type).inc()

    if policy_affected_records:
        policy_affected_records.labels(policy_type=policy_type).observe(affected_count)


def record_cluster_built(memory_count: int) -> None:
    """Record cluster building metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    if clusters_built_total:
        clusters_built_total.inc()

    if cluster_size:
        cluster_size.observe(memory_count)


def record_db_operation(
    operation: str,
    table: str,
    latency_seconds: float,
    rows_affected: int,
) -> None:
    """Record database operation metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    if db_query_latency_seconds:
        db_query_latency_seconds.labels(
            operation=operation,
            table=table
        ).observe(latency_seconds)

    if db_rows_affected:
        db_rows_affected.labels(
            operation=operation,
            table=table
        ).observe(rows_affected)


def update_tier_metrics(tier: str, memory_count: int, utilization_percent: float) -> None:
    """Update tier gauge metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    if tier_memory_count:
        tier_memory_count.labels(tier=tier).set(memory_count)

    if tier_utilization_percent:
        tier_utilization_percent.labels(tier=tier).set(utilization_percent)


def set_system_info(version: str, database: str) -> None:
    """Set system information."""
    if PROMETHEUS_AVAILABLE and memoric_info:
        memoric_info.info({
            'version': version,
            'database': database,
        })
