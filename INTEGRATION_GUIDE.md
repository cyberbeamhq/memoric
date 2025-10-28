# Memoric Integration Guide

Complete guide for integrating Memoric into your AI applications.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [SDK Integration](#sdk-integration)
4. [API Integration](#api-integration)
5. [LangChain Integration](#langchain-integration)
6. [Configuration](#configuration)
7. [Production Deployment](#production-deployment)
8. [Best Practices](#best-practices)

## Installation

### Core Package

```bash
# Minimal installation (SDK only)
pip install memoric

# With REST API support
pip install memoric[api]

# With LangChain integration
pip install memoric[langchain]

# Everything
pip install memoric[all]
```

### Development Setup

```bash
# Clone repository
git clone <repo-url>
cd memoric

# Install in development mode
pip install -e .[all]

# Initialize database
memoric init-db --migrate
```

## Quick Start

### 1. Basic SDK Usage

```python
from memoric import Memoric

# Initialize with defaults
mem = Memoric()

# Save a memory
memory_id = mem.save(
    user_id="user123",
    content="Customer reported issue with order #5678",
    metadata={"priority": "high", "topic": "support"}
)

# Retrieve relevant memories
results = mem.retrieve(
    user_id="user123",
    top_k=10
)

for memory in results:
    print(f"[{memory['_score']:.1f}] {memory['content']}")
```

### 2. Start API Server

```bash
# Development server with auto-reload
uvicorn api.server:app --reload

# Access interactive docs
open http://localhost:8000/docs
```

### 3. Use with LangChain

```python
from memoric.integrations import create_langchain_memory
from langchain.chains import ConversationChain
from langchain.llms import OpenAI

# Create persistent memory
memory = create_langchain_memory(
    user_id="user123",
    thread_id="conversation_1"
)

# Use in chain
chain = ConversationChain(llm=OpenAI(), memory=memory)
chain.run("Hello, my name is Alice")
```

## SDK Integration

### Initialization Options

```python
from memoric import Memoric

# Option 1: Default configuration
mem = Memoric()

# Option 2: Custom config file
mem = Memoric(config_path="config/production.yaml")

# Option 3: Runtime overrides
mem = Memoric(overrides={
    "database": {
        "dsn": "postgresql://user:pass@host/db"
    },
    "recall": {
        "default_top_k": 20
    }
})

# Option 4: Environment variable
import os
os.environ["MEMORIC_DATABASE_URL"] = "postgresql://localhost/memoric"
mem = Memoric()
```

### Core Methods

#### Saving Memories

```python
# Basic save
mem_id = mem.save(
    user_id="user123",
    content="Memory content"
)

# With metadata
mem_id = mem.save(
    user_id="user123",
    content="Customer feedback about mobile app",
    metadata={
        "topic": "feedback",
        "category": "mobile",
        "priority": "medium",
        "entities": ["mobile app", "performance"]
    }
)

# Thread-aware save
mem_id = mem.save(
    user_id="user123",
    thread_id="support_ticket_42",
    content="Issue resolved successfully",
    metadata={"status": "resolved"}
)

# With namespace (shared memories)
mem_id = mem.save(
    user_id="user123",
    content="Company-wide announcement",
    namespace="company_news"
)
```

#### Retrieving Memories

```python
# Retrieve by user
results = mem.retrieve(user_id="user123", top_k=10)

# Retrieve by thread
results = mem.retrieve(
    user_id="user123",
    thread_id="support_ticket_42",
    top_k=5
)

# Retrieve with metadata filter
results = mem.retrieve(
    user_id="user123",
    metadata_filter={"priority": "high"},
    top_k=10
)

# Complex metadata filter
results = mem.retrieve(
    user_id="user123",
    metadata_filter={
        "topic": "support",
        "priority": "high",
        "status": "open"
    },
    top_k=20
)

# Retrieve with scope
results = mem.retrieve(
    user_id="user123",
    scope="topic",  # thread, topic, user, or global
    top_k=10
)

# Access results
for memory in results:
    print(f"ID: {memory['id']}")
    print(f"Content: {memory['content']}")
    print(f"Score: {memory['_score']}")
    print(f"Tier: {memory['tier']}")
    print(f"Metadata: {memory['metadata']}")
```

#### Policy Management

```python
# Run all policies
results = mem.run_policies()
print(f"Migrated: {results['migrated']}")
print(f"Trimmed: {results['trimmed']}")
print(f"Summarized: {results['summarized']}")

# Manually promote memories
mem.promote_to_tier(
    memory_ids=[1, 2, 3],
    target_tier="long_term"
)

# Rebuild clusters
count = mem.rebuild_clusters(user_id="user123")
print(f"Rebuilt {count} clusters")
```

#### Statistics & Diagnostics

```python
# Get tier statistics
stats = mem.get_tier_stats()
for tier, tier_stats in stats.items():
    print(f"{tier}: {tier_stats['total_memories']} memories")

# Get topic clusters
clusters = mem.get_topic_clusters(
    user_id="user123",
    topic="support",
    limit=10
)

# System diagnostics
info = mem.inspect()
print(info)
```

### Advanced SDK Features

#### Custom Scoring Rules

```python
from memoric import Memoric, create_topic_boost_rule, create_stale_penalty_rule

mem = Memoric()

# Add custom scoring rules
mem.retriever.scorer.add_rule(
    create_topic_boost_rule(
        topics=["urgent", "critical"],
        boost_amount=20.0
    )
)

mem.retriever.scorer.add_rule(
    create_stale_penalty_rule(
        threshold_days=180,
        penalty=-15.0
    )
)

# Now retrievals use custom scoring
results = mem.retrieve(user_id="user123", top_k=10)
```

#### Multi-Instance Usage

```python
# Production database
prod_mem = Memoric(overrides={
    "database": {"dsn": "postgresql://prod-host/memoric"}
})

# Staging database
staging_mem = Memoric(overrides={
    "database": {"dsn": "postgresql://staging-host/memoric"}
})

# Local development
dev_mem = Memoric()  # Uses SQLite by default
```

## API Integration

### Starting the Server

```bash
# Development
uvicorn api.server:app --reload --port 8000

# Production with Gunicorn
gunicorn api.server:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# With custom Memoric instance
python -c "
from memoric import Memoric
from api.server import create_app
import uvicorn

mem = Memoric(config_path='production.yaml')
app = create_app(mem=mem)
uvicorn.run(app, host='0.0.0.0', port=8000)
"
```

### API Endpoints

#### Create Memory

```bash
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "content": "Customer feedback about checkout flow",
    "thread_id": "feedback_session_7",
    "metadata": {
      "topic": "ux",
      "priority": "medium"
    }
  }'

# Response
{
  "id": 42,
  "status": "created"
}
```

#### Retrieve Memories

```bash
# POST method (with complex filters)
curl -X POST http://localhost:8000/memories/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "metadata_filter": {"priority": "high"},
    "top_k": 10
  }'

# GET method (simple filtering)
curl "http://localhost:8000/memories?user_id=user123&top_k=10"

# Response
{
  "memories": [
    {
      "id": 42,
      "user_id": "user123",
      "content": "...",
      "tier": "short_term",
      "_score": 85.3
    }
  ],
  "count": 1
}
```

#### Run Policies

```bash
curl -X POST http://localhost:8000/policies/run

# Response
{
  "migrated": 5,
  "trimmed": 12,
  "summarized": 3,
  "clusters_rebuilt": 8
}
```

#### Get Statistics

```bash
curl "http://localhost:8000/stats?user_id=user123"

# Response
{
  "tier_stats": {
    "short_term": {
      "total_memories": 150,
      "summarized_count": 0
    },
    "mid_term": {
      "total_memories": 450,
      "summarized_count": 50
    }
  },
  "count_by_tier": {
    "short_term": 150,
    "mid_term": 450,
    "long_term": 100
  }
}
```

#### Get Clusters

```bash
curl "http://localhost:8000/clusters?user_id=user123&limit=10"

# Response
{
  "clusters": [
    {
      "cluster_id": 1,
      "user_id": "user123",
      "topic": "support",
      "category": "technical",
      "memory_count": 25,
      "summary": "Technical support queries..."
    }
  ],
  "count": 1
}
```

### Python Client for API

```python
import requests

class MemoricClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def save(self, user_id, content, **kwargs):
        response = requests.post(
            f"{self.base_url}/memories",
            json={
                "user_id": user_id,
                "content": content,
                **kwargs
            }
        )
        return response.json()

    def retrieve(self, user_id, **kwargs):
        response = requests.post(
            f"{self.base_url}/memories/retrieve",
            json={"user_id": user_id, **kwargs}
        )
        return response.json()["memories"]

    def run_policies(self):
        response = requests.post(f"{self.base_url}/policies/run")
        return response.json()

# Usage
client = MemoricClient()
memory_id = client.save(
    user_id="user123",
    content="Important note"
)
memories = client.retrieve(user_id="user123", top_k=10)
```

## LangChain Integration

### Basic Usage

```python
from memoric.integrations import MemoricChatMemory
from langchain.chains import ConversationChain
from langchain.llms import OpenAI

# Create memory
memory = MemoricChatMemory(
    user_id="user123",
    thread_id="conversation_1",
    top_k=10,
    return_messages=False  # or True for message objects
)

# Create chain
llm = OpenAI(temperature=0.7)
chain = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)

# Have a conversation
response = chain.run("My name is Alice and I love Python")
print(response)

response = chain.run("What's my name?")
print(response)  # Will remember "Alice"
```

### Persistent Conversations

```python
from memoric.integrations import MemoricConversationBufferMemory

# Session 1
memory = MemoricConversationBufferMemory(
    user_id="user123",
    thread_id="support_chat"
)
chain = ConversationChain(llm=OpenAI(), memory=memory)
chain.run("I need help with billing")

# Session 2 (later, different process)
memory = MemoricConversationBufferMemory(
    user_id="user123",
    thread_id="support_chat"  # Same thread_id loads conversation
)
chain = ConversationChain(llm=OpenAI(), memory=memory)
chain.run("Did you resolve my billing issue?")
# AI will have context from previous session!
```

### Multi-User Applications

```python
def create_user_chain(user_id):
    memory = MemoricChatMemory(
        user_id=user_id,
        thread_id=f"chat_{user_id}",
        top_k=10
    )
    return ConversationChain(llm=OpenAI(), memory=memory)

# Different users get isolated memories
alice_chain = create_user_chain("alice")
bob_chain = create_user_chain("bob")

alice_chain.run("My favorite color is blue")
bob_chain.run("My favorite color is red")

# Memories are isolated per user
alice_chain.run("What's my favorite color?")  # Returns "blue"
bob_chain.run("What's my favorite color?")    # Returns "red"
```

### Advanced Retrieval

```python
from memoric import Memoric
from memoric.integrations import MemoricChatMemory

# Create memory with custom config
mem = Memoric(overrides={
    "recall": {
        "default_top_k": 20,
        "scope": "topic"
    },
    "scoring": {
        "importance_weight": 0.7,
        "recency_weight": 0.3
    }
})

memory = MemoricChatMemory(
    user_id="user123",
    memoric=mem,  # Use custom Memoric instance
    top_k=20
)

# Use with LangChain
chain = ConversationChain(llm=OpenAI(), memory=memory)
```

## Configuration

### Database Configuration

```yaml
# config/production.yaml
database:
  dsn: "postgresql://user:pass@host:5432/memoric"
  pool_size: 20
  max_overflow: 10
```

```python
mem = Memoric(config_path="config/production.yaml")
```

### Retrieval Configuration

```yaml
recall:
  thread_awareness: true
  default_top_k: 10
  scope: thread  # thread, topic, user, or global
  include_summarized: false
```

### Scoring Configuration

```yaml
scoring:
  importance_weight: 0.5
  recency_weight: 0.3
  repetition_weight: 0.2
  decay_days: 60

  rules:
    boost_topics: ["urgent", "critical"]
    topic_boost_amount: 10.0
    penalize_stale: true
    stale_threshold_days: 180
    stale_penalty: -15.0
```

### Privacy Configuration

```yaml
privacy:
  enforce_user_scope: true
  allow_shared_namespace: false
  default_namespace: null
```

### Policy Configuration

```yaml
policies:
  write:
    - when: always
      to: [short_term]
    - when: score >= 80
      to: [mid_term]

  migrate:
    - from: short_term
      to: mid_term
      when: age_days >= 7

  evict:
    - when: over_capacity
      from: short_term
      strategy: lru
```

## Production Deployment

### Prerequisites

```bash
# PostgreSQL 12+
sudo apt-get install postgresql

# Python 3.9+
python --version

# Install Memoric
pip install memoric[all]
```

### Database Setup

```bash
# Create database
createdb memoric

# Set database URL
export MEMORIC_DATABASE_URL="postgresql://user:pass@localhost/memoric"

# Run migrations
memoric init-db --migrate

# Verify setup
memoric stats
```

### API Deployment

```bash
# Install production server
pip install gunicorn

# Start with Gunicorn
gunicorn api.server:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/memoric/access.log \
  --error-logfile /var/log/memoric/error.log

# Or with systemd service
sudo systemctl enable memoric
sudo systemctl start memoric
```

### Systemd Service

```ini
# /etc/systemd/system/memoric.service
[Unit]
Description=Memoric API Server
After=network.target postgresql.service

[Service]
Type=notify
User=memoric
Group=memoric
WorkingDirectory=/opt/memoric
Environment="MEMORIC_DATABASE_URL=postgresql://localhost/memoric"
Environment="OPENAI_API_KEY=sk-..."
ExecStart=/opt/memoric/venv/bin/gunicorn api.server:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/memoric
server {
    listen 80;
    server_name memoric.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Monitoring

```python
# Add Prometheus metrics (future)
from prometheus_client import Counter, Histogram

memories_created = Counter('memories_created_total', 'Total memories created')
retrieval_latency = Histogram('retrieval_latency_seconds', 'Retrieval latency')

# In your code
memories_created.inc()
with retrieval_latency.time():
    results = mem.retrieve(...)
```

## Best Practices

### 1. User Isolation

**Always** use `user_id` for multi-user applications:

```python
# Good
mem.save(user_id="user123", content="...")
mem.retrieve(user_id="user123", top_k=10)

# Bad (no user isolation)
mem.save(content="...")  # May leak to other users
```

### 2. Thread Awareness

Use `thread_id` for conversation context:

```python
# Good (thread-aware)
mem.save(
    user_id="user123",
    thread_id="support_ticket_42",
    content="Issue resolved"
)

results = mem.retrieve(
    user_id="user123",
    thread_id="support_ticket_42",
    top_k=10
)

# Acceptable (global retrieval)
results = mem.retrieve(user_id="user123", scope="user", top_k=10)
```

### 3. Metadata Enrichment

Use rich metadata for better retrieval:

```python
# Good (rich metadata)
mem.save(
    user_id="user123",
    content="Customer complaint about shipping delay",
    metadata={
        "topic": "shipping",
        "category": "complaint",
        "priority": "high",
        "sentiment": "negative",
        "entities": ["shipping", "delay", "order #5678"]
    }
)

# Acceptable (minimal metadata)
mem.save(
    user_id="user123",
    content="Shipping issue",
    metadata={"topic": "shipping"}
)
```

### 4. Policy Execution

Run policies regularly:

```bash
# Cron job (daily at 2 AM)
0 2 * * * /usr/bin/memoric run-policies

# Or programmatically
import schedule
import time

def run_policies():
    mem = Memoric()
    results = mem.run_policies()
    print(f"Policies executed: {results}")

schedule.every().day.at("02:00").do(run_policies)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 5. Error Handling

Handle errors gracefully:

```python
from memoric import Memoric

try:
    mem = Memoric()
    results = mem.retrieve(user_id="user123", top_k=10)
except Exception as e:
    # Log error
    print(f"Error retrieving memories: {e}")
    # Fallback to empty results
    results = []
```

### 6. Performance Optimization

```python
# Use metadata filters to reduce result set
results = mem.retrieve(
    user_id="user123",
    metadata_filter={"topic": "billing"},  # Narrows search
    top_k=10
)

# Batch operations when possible
for item in batch:
    mem.save(user_id=item['user'], content=item['text'])

# Use appropriate scope
results = mem.retrieve(
    user_id="user123",
    scope="thread",  # Faster than "user" or "global"
    top_k=10
)
```

### 7. Testing

```python
import pytest
from memoric import Memoric

@pytest.fixture
def mem():
    """Test fixture with SQLite database."""
    return Memoric(overrides={
        "database": {"dsn": "sqlite:///:memory:"}
    })

def test_save_and_retrieve(mem):
    # Save memory
    mem_id = mem.save(user_id="test_user", content="Test content")
    assert mem_id > 0

    # Retrieve memory
    results = mem.retrieve(user_id="test_user", top_k=10)
    assert len(results) == 1
    assert results[0]['content'] == "Test content"
```

## Troubleshooting

See [PHASE5_SUMMARY.md](PHASE5_SUMMARY.md#troubleshooting) for detailed troubleshooting guide.

## Support

- Documentation: [PHASE5_SUMMARY.md](PHASE5_SUMMARY.md)
- Examples: [examples/](examples/)
- Issues: GitHub Issues
- API Docs: http://localhost:8000/docs (when server running)

## Next Steps

1. **Try Examples**:
   ```bash
   python examples/quickstart_sdk.py
   python examples/api_usage.py
   python examples/langchain_integration.py
   ```

2. **Read Documentation**:
   - [PHASE5_SUMMARY.md](PHASE5_SUMMARY.md) - Complete Phase 5 docs
   - [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Database migrations
   - [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Full project overview

3. **Explore Features**:
   - Try CLI commands: `memoric --help`
   - Experiment with API: http://localhost:8000/docs
   - Test LangChain integration

4. **Deploy to Production**:
   - Set up PostgreSQL
   - Configure environment variables
   - Deploy API with Gunicorn
   - Set up monitoring

Happy memory management! 🎉
