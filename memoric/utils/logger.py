"""
Structured logging for Memoric.

Provides JSON-formatted logs with context for observability.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional
from functools import wraps
from contextlib import contextmanager


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "thread_id"):
            log_data["thread_id"] = record.thread_id
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "count"):
            log_data["count"] = record.count
        if hasattr(record, "metadata"):
            log_data["metadata"] = record.metadata

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Set up structured logging for Memoric.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON formatting
        log_file: Optional file path for logs

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("memoric")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Create formatter
    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "memoric") -> logging.Logger:
    """Get logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_operation(operation: str):
    """Decorator to log operation execution time and result.

    Args:
        operation: Operation name for logging

    Example:
        @log_operation("save_memory")
        def save(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Log success
                extra = {
                    "operation": operation,
                    "duration_ms": round(duration_ms, 2),
                }

                # Extract context from kwargs
                if "user_id" in kwargs:
                    extra["user_id"] = kwargs["user_id"]
                if "thread_id" in kwargs:
                    extra["thread_id"] = kwargs["thread_id"]

                logger.info(
                    f"Operation {operation} completed successfully",
                    extra=extra
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                # Log failure
                extra = {
                    "operation": operation,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                }

                if "user_id" in kwargs:
                    extra["user_id"] = kwargs["user_id"]
                if "thread_id" in kwargs:
                    extra["thread_id"] = kwargs["thread_id"]

                logger.error(
                    f"Operation {operation} failed: {e}",
                    extra=extra,
                    exc_info=True
                )

                raise

        return wrapper
    return decorator


@contextmanager
def log_context(operation: str, **context):
    """Context manager for logging operations with timing.

    Args:
        operation: Operation name
        **context: Additional context fields

    Example:
        with log_context("retrieve_memories", user_id="user123", top_k=10):
            results = db.get_memories(...)
    """
    logger = get_logger()
    start_time = time.time()

    try:
        yield

        duration_ms = (time.time() - start_time) * 1000
        extra = {
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            **context
        }

        logger.info(
            f"Operation {operation} completed",
            extra=extra
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        extra = {
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            "error": str(e),
            **context
        }

        logger.error(
            f"Operation {operation} failed: {e}",
            extra=extra,
            exc_info=True
        )

        raise


def log_policy_execution(
    policy_type: str,
    affected_count: int,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log policy execution results.

    Args:
        policy_type: Type of policy (migrate, trim, summarize, cluster)
        affected_count: Number of records affected
        details: Additional details
    """
    logger = get_logger()

    extra = {
        "operation": f"policy_{policy_type}",
        "count": affected_count,
        "metadata": details or {},
    }

    logger.info(
        f"Policy {policy_type} executed: {affected_count} records affected",
        extra=extra
    )


def log_retrieval(
    user_id: Optional[str],
    thread_id: Optional[str],
    scope: str,
    result_count: int,
    duration_ms: float,
    avg_score: Optional[float] = None,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> None:
    """Log retrieval operation.

    Args:
        user_id: User ID
        thread_id: Thread ID
        scope: Retrieval scope
        result_count: Number of results returned
        duration_ms: Execution time in milliseconds
        avg_score: Average relevance score
        metadata_filter: Metadata filter used
    """
    logger = get_logger()

    extra = {
        "operation": "retrieve",
        "user_id": user_id,
        "thread_id": thread_id,
        "scope": scope,
        "count": result_count,
        "duration_ms": round(duration_ms, 2),
    }

    if avg_score is not None:
        extra["avg_score"] = round(avg_score, 2)

    if metadata_filter:
        extra["metadata_filter"] = metadata_filter

    score_str = f"{avg_score:.1f}" if avg_score is not None else "N/A"
    logger.info(
        f"Retrieved {result_count} memories (scope={scope}, avg_score={score_str})",
        extra=extra
    )


def log_cluster_operation(
    operation: str,
    user_id: Optional[str],
    cluster_count: int,
    duration_ms: float,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log clustering operation.

    Args:
        operation: Operation type (build, rebuild, update)
        user_id: User ID
        cluster_count: Number of clusters affected
        duration_ms: Execution time
        details: Additional details
    """
    logger = get_logger()

    extra = {
        "operation": f"cluster_{operation}",
        "user_id": user_id,
        "count": cluster_count,
        "duration_ms": round(duration_ms, 2),
        "metadata": details or {},
    }

    logger.info(
        f"Cluster {operation}: {cluster_count} clusters affected",
        extra=extra
    )


def log_database_operation(
    operation: str,
    table: str,
    affected_rows: int,
    duration_ms: float,
) -> None:
    """Log database operation.

    Args:
        operation: SQL operation (INSERT, UPDATE, DELETE, SELECT)
        table: Table name
        affected_rows: Number of rows affected
        duration_ms: Execution time
    """
    logger = get_logger()

    extra = {
        "operation": f"db_{operation.lower()}",
        "table": table,
        "count": affected_rows,
        "duration_ms": round(duration_ms, 2),
    }

    logger.debug(
        f"Database {operation} on {table}: {affected_rows} rows",
        extra=extra
    )
