# Memoric Providers - Plug-and-Play Architecture

Memoric is a **framework**, not a monolith. We provide solid foundations and let you choose the best services for your needs.

## Philosophy

**We don't reinvent the wheel.** Each service type has specialized providers that do it better than we ever could:

- **Vector Search**: Pinecone, Qdrant, Weaviate (not our homegrown solution)
- **Caching**: Redis, Memcached (not in-memory dictionaries)
- **Embeddings**: OpenAI, Cohere, HuggingFace (pluggable)
- **Observability**: OpenTelemetry, Sentry, DataDog (integrate with your stack)

**Memoric focuses on**: Memory management, tiering, policies, retrieval scoring, and orchestration.

---

## Provider Types

### 🔍 Vector Stores (`VectorStoreProvider`)

For semantic/vector search of embeddings.

**Available Providers:**
- `PineconeVectorStore` - Managed, scalable, easy (recommended for production)
- `QdrantVectorStore` - Open-source, self-hosted, fast
- `InMemoryVectorStore` - Development/testing only

**Example:**
```python
from memoric.providers.vector_stores import PineconeVectorStore

vector_store = PineconeVectorStore(
    index_name="my-vectors",
    dimension=1536  # OpenAI embedding size
)

# Store vector
vector_store.upsert(
    id="mem_123",
    vector=[0.1, 0.2, ...],  # 1536 dimensions
    metadata={"user_id": "alice", "content": "..."}
)

# Search similar vectors
results = vector_store.search(
    vector=[0.15, 0.18, ...],
    top_k=10,
    filter={"user_id": "alice"}
)
```

---

### ⚡ Cache Providers (`CacheProvider`)

For performance and rate limiting.

**Available Providers:**
- `RedisCacheProvider` - Production-ready, distributed
- `InMemoryCacheProvider` - Development/testing only

**Example:**
```python
from memoric.providers.cache import RedisCacheProvider

cache = RedisCacheProvider(
    host="localhost",
    prefix="memoric:"
)

# Cache query results
cache.set("search_results_123", results, ttl=300)  # 5 min TTL

# Rate limiting
attempts = cache.increment("login_attempts:user_123")
if attempts > 5:
    raise TooManyAttempts()
```

---

### 🛡️ Resilience Utilities

Make external calls robust with retry, circuit breakers, and timeouts.

**Available Patterns:**
- `retry_with_backoff` - Exponential backoff retries
- `CircuitBreaker` - Prevent cascading failures
- `with_timeout` - Add timeouts to functions
- `fallback` - Graceful degradation
- `create_resilient_caller` - All-in-one

**Example:**
```python
from memoric.utils.resilience import retry_with_backoff, CircuitBreaker

# Retry on transient failures
@retry_with_backoff(max_attempts=3, initial_delay=1.0)
def call_external_api():
    return requests.get("https://api.example.com").json()

# Circuit breaker for persistent failures
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

@breaker
def call_unreliable_service():
    return unstable_api.call()
```

---

## Production Architecture

### Recommended Setup

```
┌─────────────────────────────────────────────────────────┐
│                     Your Application                      │
│                  (AI Agent / Chatbot)                     │
└─────────────────┬───────────────────────────────────────┘
                  │
                  v
          ┌───────────────┐
          │    Memoric    │  Core memory management
          │   Framework   │  Tiering, policies, scoring
          └───────┬───────┘
                  │
        ┌─────────┼─────────┬─────────────┬───────────────┐
        │         │         │             │               │
        v         v         v             v               v
   PostgreSQL  Pinecone   Redis       OpenAI        Prometheus
   (Structured) (Vectors) (Cache)  (Embeddings)   (Metrics)
```

### What Goes Where?

| Data Type | Service | Why |
|-----------|---------|-----|
| **Structured Memories** | PostgreSQL / SQLite | Transactions, queries, metadata |
| **Vector Embeddings** | Pinecone / Qdrant | Optimized for similarity search |
| **Hot Cache** | Redis | Sub-millisecond reads, rate limiting |
| **Embeddings Generation** | OpenAI / Cohere | High-quality vectors |
| **Metrics** | Prometheus | Monitoring, alerting |

---

## Quick Start Guide

### 1. Development Setup (Minimal)

```python
from memoric import Memoric

# Just works with SQLite (no external services needed)
m = Memoric()
m.save(user_id="alice", content="Hello world")
memories = m.retrieve(user_id="alice")
```

### 2. Production Setup (Recommended)

```python
from memoric import Memoric
from memoric.providers.vector_stores import PineconeVectorStore
from memoric.providers.cache import RedisCacheProvider

# Core Memoric with PostgreSQL
m = Memoric(overrides={
    "database": {"dsn": "postgresql://user:pass@localhost/memoric"},
    "privacy": {"encrypt_content": True}
})

# Vector search with Pinecone
vector_store = PineconeVectorStore(index_name="prod-vectors")

# Caching with Redis
cache = RedisCacheProvider(host="redis.example.com")

# Use them together (see examples/production_with_providers.py)
```

---

## Adding New Providers

Want to integrate a different service? Implement the interface:

```python
from memoric.providers.interfaces import VectorStoreProvider

class MyCustomVectorStore(VectorStoreProvider):
    def upsert(self, *, id, vector, metadata=None):
        # Your implementation
        pass

    def search(self, *, vector, top_k=10, filter=None):
        # Your implementation
        pass

    # Implement other required methods...
```

Then use it just like built-in providers!

---

## Environment Variables

```bash
# Vector Stores
export PINECONE_API_KEY=your-key
export PINECONE_ENVIRONMENT=your-env

# Cache
export REDIS_HOST=localhost
export REDIS_PASSWORD=your-password  # if needed

# LLM / Embeddings
export OPENAI_API_KEY=sk-...

# Database
export DATABASE_URL=postgresql://user:pass@host/db

# Memoric
export MEMORIC_ENCRYPTION_KEY=your-encryption-key
export MEMORIC_JWT_SECRET=your-jwt-secret
```

---

## Examples

- `examples/minimal_agent.py` - No external services
- `examples/production_agent.py` - OpenAI only
- `examples/production_with_providers.py` - Full stack (Pinecone + Redis)

---

## Provider Roadmap

### ✅ Implemented
- Pinecone vector store
- Qdrant vector store
- Redis cache
- In-memory fallbacks
- Resilience patterns

### 🚧 Coming Soon
- Weaviate vector store
- Chroma vector store
- Memcached provider
- OpenTelemetry observability
- AWS SQS message queue
- Anthropic LLM provider

### 💡 Contributions Welcome
Want to add support for your favorite service? PRs welcome!

---

## Design Principles

1. **Interface over Implementation** - All providers implement standard interfaces
2. **Fail Gracefully** - Fallbacks when external services unavailable
3. **Observable** - All providers support health checks
4. **Battle-Tested** - Use production-proven services
5. **Vendor Agnostic** - Easy to switch providers

---

## Support

- GitHub Issues: https://github.com/yourusername/memoric/issues
- Documentation: https://docs.memoric.dev
- Examples: `examples/` directory

---

**Remember**: Memoric is a framework. Choose the best tools for your job! 🚀
