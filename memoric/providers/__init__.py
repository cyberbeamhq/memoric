"""
Memoric Providers - Plug-and-play integrations with external services.

Import providers you need:

Vector Stores:
    from memoric.providers import PineconeVectorStore, QdrantVectorStore

Cache:
    from memoric.providers import RedisCacheProvider

Interfaces (for custom providers):
    from memoric.providers import VectorStoreProvider, CacheProvider
"""

from .interfaces import (
    VectorStoreProvider,
    CacheProvider,
    LLMProvider,
    ObservabilityProvider,
    MessageQueueProvider,
)

from .vector_stores import (
    PineconeVectorStore,
    QdrantVectorStore,
    InMemoryVectorStore,
)

from .cache import (
    RedisCacheProvider,
    InMemoryCacheProvider,
)

__all__ = [
    # Interfaces
    "VectorStoreProvider",
    "CacheProvider",
    "LLMProvider",
    "ObservabilityProvider",
    "MessageQueueProvider",
    # Vector Stores
    "PineconeVectorStore",
    "QdrantVectorStore",
    "InMemoryVectorStore",
    # Cache
    "RedisCacheProvider",
    "InMemoryCacheProvider",
]
