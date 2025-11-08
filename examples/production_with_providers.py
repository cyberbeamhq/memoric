"""
Production Setup with External Providers - Plug-and-play architecture.

This example shows how to use Memoric with best-in-class external services:
- Pinecone for vector search (managed, scalable)
- Redis for caching (fast, distributed)
- OpenAI for embeddings (high quality)
- Resilience patterns for robustness

This is the recommended production setup.

Architecture:
- Memoric: Core memory management + PostgreSQL for structured data
- Pinecone: Vector search for semantic retrieval
- Redis: Caching for performance + rate limiting
- OpenAI: Embeddings + LLM for metadata extraction

Benefits:
- Each service does what it does best
- Horizontally scalable
- Battle-tested components
- Easy to monitor and maintain
"""

import os
from typing import Dict, Any, List

from memoric import Memoric
from memoric.providers.vector_stores import PineconeVectorStore
from memoric.providers.cache import RedisCacheProvider
from memoric.utils.resilience import retry_with_backoff, CircuitBreaker


class ProductionMemorySystem:
    """
    Production-ready memory system with external providers.

    Setup required:
    1. Pinecone account: https://www.pinecone.io/
    2. Redis instance: docker run -p 6379:6379 redis
    3. OpenAI API key
    4. PostgreSQL database (optional, SQLite works too)

    Environment variables:
    - PINECONE_API_KEY
    - PINECONE_ENVIRONMENT
    - OPENAI_API_KEY
    - REDIS_HOST (default: localhost)
    - DATABASE_URL (optional)
    """

    def __init__(self):
        """Initialize production memory system."""
        print("🚀 Initializing Production Memory System...")

        # 1. Initialize core Memoric (PostgreSQL for structured data)
        db_url = os.getenv("DATABASE_URL", "sqlite:///./memoric_prod.db")
        self.memoric = Memoric(overrides={
            "database": {"dsn": db_url},
            "privacy": {"encrypt_content": True}  # Production: encrypt at rest
        })
        print("✅ Core Memoric initialized")

        # 2. Initialize Pinecone for vector search
        try:
            self.vector_store = PineconeVectorStore(
                index_name="memoric-production",
                dimension=1536,  # OpenAI embedding dimension
                metric="cosine"
            )
            print("✅ Pinecone vector store connected")
        except Exception as e:
            print(f"⚠️  Pinecone not available: {e}")
            print("   Using in-memory fallback (not for production!)")
            from memoric.providers.vector_stores import InMemoryVectorStore
            self.vector_store = InMemoryVectorStore()

        # 3. Initialize Redis for caching
        try:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            self.cache = RedisCacheProvider(
                host=redis_host,
                prefix="memoric:prod:"
            )
            print("✅ Redis cache connected")
        except Exception as e:
            print(f"⚠️  Redis not available: {e}")
            print("   Using in-memory fallback (not for production!)")
            from memoric.providers.cache import InMemoryCacheProvider
            self.cache = InMemoryCacheProvider()

        # 4. Initialize circuit breaker for vector operations
        self.vector_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0
        )
        print("✅ Circuit breakers initialized")

        print("\n🎉 Production system ready!\n")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    def save_with_embedding(
        self,
        *,
        content: str,
        user_id: str,
        thread_id: str,
        metadata: Dict[str, Any] = None,
    ) -> int:
        """
        Save memory with automatic embedding generation.

        Uses retry pattern for robustness.
        """
        # 1. Save to core database
        memory_id = self.memoric.save(
            content=content,
            user_id=user_id,
            thread_id=thread_id,
            metadata=metadata or {}
        )

        # 2. Generate and store embedding in Pinecone
        try:
            embedding = self._generate_embedding(content)

            @self.vector_breaker
            def store_embedding():
                return self.vector_store.upsert(
                    id=str(memory_id),
                    vector=embedding,
                    metadata={
                        "user_id": user_id,
                        "thread_id": thread_id,
                        "content_preview": content[:100],
                    }
                )

            store_embedding()
            print(f"✅ Saved memory {memory_id} with embedding")

        except Exception as e:
            print(f"⚠️  Failed to store embedding: {e}")
            # Core memory still saved, embedding is best-effort

        return memory_id

    def semantic_search(
        self,
        *,
        query: str,
        user_id: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using Pinecone.

        With caching for performance.
        """
        # Check cache first
        cache_key = f"search:{user_id}:{hash(query)}"
        cached = self.cache.get(cache_key)
        if cached:
            print("💨 Cache hit!")
            return cached

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Search Pinecone
        @self.vector_breaker
        def search_vectors():
            return self.vector_store.search(
                vector=query_embedding,
                top_k=top_k,
                filter={"user_id": user_id}
            )

        try:
            results = search_vectors()

            # Cache results for 5 minutes
            self.cache.set(cache_key, results, ttl=300)

            print(f"🔍 Found {len(results)} semantically similar memories")
            return results

        except Exception as e:
            print(f"⚠️  Semantic search failed: {e}")
            # Fallback to keyword search in core database
            return self._keyword_fallback(query, user_id, top_k)

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        # This would use your embedding provider
        # For now, return mock embedding
        import random
        return [random.random() for _ in range(1536)]

    def _keyword_fallback(
        self,
        query: str,
        user_id: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Fallback to keyword search if semantic search fails."""
        print("📝 Using keyword fallback...")
        memories = self.memoric.retrieve(
            user_id=user_id,
            scope="user",
            top_k=top_k
        )
        return memories

    def health_check(self) -> Dict[str, bool]:
        """Check health of all components."""
        return {
            "database": self.memoric.db is not None,
            "vector_store": self.vector_store.health_check(),
            "cache": self.cache.health_check(),
        }


def demo_production_system():
    """Demonstrate production system with all providers."""
    print("=" * 60)
    print("Production Memory System with External Providers")
    print("=" * 60)
    print()

    # Initialize system
    system = ProductionMemorySystem()

    # Check health
    print("🏥 Health Check:")
    health = system.health_check()
    for component, status in health.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {component}: {'healthy' if status else 'unhealthy'}")
    print()

    # Save some memories with embeddings
    print("💾 Saving memories with automatic embedding...")
    system.save_with_embedding(
        content="Customer prefers email communication over phone",
        user_id="agent_support_001",
        thread_id="customer_12345",
        metadata={"importance": "high", "category": "preference"}
    )

    system.save_with_embedding(
        content="Order #99887 shipped yesterday via FedEx",
        user_id="agent_support_001",
        thread_id="customer_12345",
        metadata={"importance": "medium", "category": "order"}
    )

    system.save_with_embedding(
        content="Customer asked about return policy for electronics",
        user_id="agent_support_001",
        thread_id="customer_12345",
        metadata={"importance": "medium", "category": "inquiry"}
    )

    print()

    # Semantic search
    print("🔍 Semantic Search (with caching):")
    results = system.semantic_search(
        query="How does customer like to be contacted?",
        user_id="agent_support_001",
        top_k=5
    )

    for result in results:
        print(f"  - Score: {result.get('score', 0):.3f}")
        print(f"    Content: {result.get('metadata', {}).get('content_preview', 'N/A')}")

    print()

    # Second search (should hit cache)
    print("🔍 Same search again (should use cache):")
    results = system.semantic_search(
        query="How does customer like to be contacted?",
        user_id="agent_support_001",
        top_k=5
    )

    print("\n" + "=" * 60)
    print("✅ Production demo complete!")
    print()
    print("Key features demonstrated:")
    print("  ✅ Pinecone for vector search")
    print("  ✅ Redis for caching")
    print("  ✅ Retry logic for robustness")
    print("  ✅ Circuit breakers for failure isolation")
    print("  ✅ Graceful degradation (fallbacks)")
    print("  ✅ Health checks")
    print("=" * 60)


if __name__ == "__main__":
    # Optional: Set environment variables
    # os.environ["PINECONE_API_KEY"] = "your-key"
    # os.environ["PINECONE_ENVIRONMENT"] = "your-env"
    # os.environ["OPENAI_API_KEY"] = "sk-..."
    # os.environ["REDIS_HOST"] = "localhost"

    demo_production_system()
