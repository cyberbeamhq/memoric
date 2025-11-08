"""
Provider Interfaces - Plug-and-play architecture for external services.

Memoric is a framework, not a monolith. We provide solid interfaces and let
users choose their preferred services for:
- Vector databases (Pinecone, Qdrant, Weaviate, Chroma)
- Caching (Redis, Memcached)
- Embeddings (OpenAI, Cohere, HuggingFace)
- Observability (OpenTelemetry, Sentry, DataDog)

This module defines the base interfaces that all providers must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


class VectorStoreProvider(ABC):
    """
    Interface for vector database providers.

    Implementations: Pinecone, Qdrant, Weaviate, Chroma, pgvector, etc.

    Memoric doesn't store embeddings in PostgreSQL - we outsource to
    specialized vector databases that do it better.
    """

    @abstractmethod
    def upsert(
        self,
        *,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Insert or update a vector.

        Args:
            id: Unique identifier for the vector
            vector: Embedding vector
            metadata: Optional metadata to store with vector

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def search(
        self,
        *,
        vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            vector: Query vector
            top_k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of results with id, score, and metadata
        """
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete a vector by ID."""
        pass

    @abstractmethod
    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the vector store is healthy."""
        pass


class CacheProvider(ABC):
    """
    Interface for caching providers.

    Implementations: Redis, Memcached, in-memory (development).

    Use for:
    - Rate limiting counters
    - Session management
    - Frequently accessed data
    - Query result caching
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = no expiry)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass

    @abstractmethod
    def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter.

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New value
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if cache is healthy."""
        pass


class LLMProvider(ABC):
    """
    Interface for LLM providers.

    Implementations: OpenAI, Anthropic, Cohere, Ollama, etc.

    Use for:
    - Metadata extraction
    - Summarization
    - Entity recognition
    - Content classification
    """

    @abstractmethod
    def complete(
        self,
        *,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Generate completion.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific parameters

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def chat(
        self,
        *,
        messages: List[Dict[str, str]],
        max_tokens: int = 100,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Generate chat completion.

        Args:
            messages: List of chat messages [{"role": "user", "content": "..."}]
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific parameters

        Returns:
            Generated response
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if LLM provider is healthy."""
        pass


class ObservabilityProvider(ABC):
    """
    Interface for observability providers.

    Implementations: OpenTelemetry, Sentry, DataDog, New Relic.

    Use for:
    - Distributed tracing
    - Error tracking
    - Performance monitoring
    - Custom metrics
    """

    @abstractmethod
    def trace_span(
        self,
        *,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Create a trace span (context manager).

        Args:
            name: Span name
            attributes: Span attributes

        Example:
            with observability.trace_span(name="retrieve_memories"):
                # Your code here
                pass
        """
        pass

    @abstractmethod
    def record_error(
        self,
        *,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record an error.

        Args:
            error: Exception that occurred
            context: Additional context
        """
        pass

    @abstractmethod
    def record_metric(
        self,
        *,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record a metric.

        Args:
            name: Metric name
            value: Metric value
            tags: Metric tags/labels
        """
        pass


class MessageQueueProvider(ABC):
    """
    Interface for message queue providers.

    Implementations: Redis Queue, Celery, AWS SQS, RabbitMQ.

    Use for:
    - Async embedding generation
    - Background summarization
    - Scheduled policy execution
    - Batch operations
    """

    @abstractmethod
    def enqueue(
        self,
        *,
        task: str,
        payload: Dict[str, Any],
        delay: Optional[int] = None,
    ) -> str:
        """
        Enqueue a task.

        Args:
            task: Task name/type
            payload: Task payload
            delay: Delay in seconds before processing

        Returns:
            Task ID
        """
        pass

    @abstractmethod
    def dequeue(self, timeout: Optional[int] = None) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Dequeue a task.

        Args:
            timeout: Timeout in seconds (None = block forever)

        Returns:
            (task_type, payload) or None if timeout
        """
        pass

    @abstractmethod
    def get_status(self, task_id: str) -> Optional[str]:
        """
        Get task status.

        Returns:
            Status string: "pending", "processing", "completed", "failed", or None
        """
        pass


__all__ = [
    "VectorStoreProvider",
    "CacheProvider",
    "LLMProvider",
    "ObservabilityProvider",
    "MessageQueueProvider",
]
