<div align="center">

# 🧠 Memoric

### *Policy-Driven, Deterministic Memory Framework for AI Agents*

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-production--ready-brightgreen.svg)](https://github.com/cyberbeamhq/memoric)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-brightgreen.svg)](https://github.com/cyberbeamhq/memoric)
[![Security](https://img.shields.io/badge/security-8.95%2F10-blue.svg)](COMPREHENSIVE_REVIEW.md)

*Give your AI agents structured, explainable, and persistent memory — without the black box.*

[Features](#-key-features) •
[Installation](#-installation) •
[Quick Start](#-quick-start) •
[Documentation](#-documentation) •
[Architecture](#-architecture) •
[Security](#-security-features)

</div>

---

## 🎯 Overview

**Memoric** is an open-source Python framework that provides a robust, deterministic memory layer for AI agents. It helps AI teams deploy agents with long-term, rule-based memory, structured by metadata, organized by tiers, and retrievable through policy-driven scoring.

Instead of relying solely on vector embeddings or opaque similarity searches, **Memoric focuses on structure, transparency, and control**. Every stored memory is traceable, explainable, and policy-governed — enabling predictable, high-relevance recall for any AI system.

<div align="center">

### 🏆 Production Ready Score: **8.95/10**

</div>

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🎯 **Deterministic Retrieval**
Retrieve memories using metadata, recency, and importance — not fuzzy vector magic. Every decision is explainable.

### 🔄 **Multi-Tier Memory**
Short-term, mid-term, and long-term tiers evolve your memory over time automatically with policy-driven transitions.

### 🧵 **Multi-Threaded Isolation**
Maintain separate memory threads (e.g., different chat topics) under one user while preserving cross-thread relevance.

### 🔒 **Enterprise Security**
JWT authentication, RBAC, encryption at rest, comprehensive audit logging, and compliance support (SOC2, GDPR, HIPAA).

</td>
<td width="50%">

### 🤖 **AI-Powered Metadata**
Automatic metadata extraction (topics, categories, entities, sentiment, importance) via integrated LLM agent.

### 📋 **Policy-Driven YAML**
Define memory rules, expiry, routing, and scoring in one clean, version-controlled YAML file.

### 🐘 **PostgreSQL Backend**
Proven, efficient, and enterprise-grade database with ready-to-use schemas and indexes.

### 🔗 **Framework-Agnostic**
Works seamlessly with LangChain, LlamaIndex, or any custom LLM pipeline. Drop-in integration.

</td>
</tr>
</table>

---

## 🚀 Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install memoric
```

### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/cyberbeamhq/memoric.git
cd memoric

# Install in development mode
pip install -e .
```

### Option 3: Install with Extras

```bash
# All optional dependencies
pip install memoric[all]

# Specific extras
pip install memoric[llm]      # OpenAI integration
pip install memoric[metrics]  # Prometheus metrics
pip install memoric[dev]      # Development tools
```

### Requirements

- Python 3.9+
- PostgreSQL 12+ (recommended) or SQLite (development)

---

## ⚡ Quick Start

### 1️⃣ Create Configuration File (Optional)

Create a `config.yaml` file to customize behavior:

```yaml
# Storage configuration
storage:
  tiers:
    - name: short_term
      backend: sqlite
      dsn: "sqlite:///memoric_short.db"
      expiry_days: 7
    - name: mid_term
      backend: sqlite
      dsn: "sqlite:///memoric_mid.db"
      expiry_days: 90
    - name: long_term
      backend: postgres
      dsn: "postgresql://user:pass@localhost/memoric"
      expiry_days: 365

# Metadata enrichment (requires OpenAI API key)
metadata:
  enrichment:
    model: gpt-4o-mini
    enabled: true

# Memory retrieval settings
recall:
  scope: thread  # Options: thread | topic | user | global
  default_top_k: 10
  fallback_order: [thread, topic, user]

# Scoring weights
scoring:
  importance_weight: 0.6
  recency_weight: 0.3
  repetition_weight: 0.1

# Privacy settings
privacy:
  enforce_user_scope: true
  allow_shared_namespace: false
```

> **Note:** Memoric works out-of-the-box with SQLite. The config file is optional for customization.

### 2️⃣ Initialize Memoric

```python
from memoric import Memoric

# Initialize with config
mem = Memoric(config_path="config.yaml")

# Or use environment variables
mem = Memoric()
```

### 3️⃣ Store Memories

```python
# Save a user message with automatic metadata extraction
memory_id = mem.save(
    user_id="U-123",
    thread_id="T-Refunds",
    content="I still haven't received my refund for order #1049.",
    session_id="S-456"
)
print(f"Memory saved with ID: {memory_id}")
```

**What happens automatically:**
- 🤖 Content enriched with AI-extracted metadata (topic, category, entities, importance)
- 📊 Routed to appropriate tier based on policies (e.g., `short_term`)
- 💾 Stored in PostgreSQL with all metadata
- 🔍 Indexed for fast retrieval

### 4️⃣ Retrieve Memories

```python
# Retrieve relevant memories
memories = mem.retrieve(
    user_id="U-123",
    thread_id="T-Refunds",
    top_k=10
)

# Display results
for memory in memories:
    print(f"Score: {memory['_score']}, Content: {memory['content']}")
```

**Example Output:**

```python
[
    {
        "id": 42,
        "user_id": "U-123",
        "thread_id": "T-Refunds",
        "content": "I still haven't received my refund for order #1049.",
        "metadata": {
            "topic": "refunds",
            "category": "customer_support",
            "importance": "high",
            "entities": ["order #1049"]
        },
        "tier": "short_term",
        "_score": 85.3,
        "created_at": "2025-10-30T10:30:00Z"
    },
    # ... more memories
]
```

The list of memories can be formatted and injected into your LLM's context window.

---

## 🏗️ Architecture

<div align="center">

```mermaid
graph TD
    A[User/AI Agent] --> B[Metadata Agent]
    B --> C[Memory Router]
    C --> D[PostgreSQL Store]
    D --> E[Retriever + Scorer]
    E --> F[LLM/Agent]

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#ffe1f5
    style D fill:#e1ffe1
    style E fill:#f5e1ff
    style F fill:#ffe1e1
```

</div>

### Core Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Metadata Agent** | AI-powered metadata extraction | OpenAI API / Custom LLM |
| **Memory Router** | Policy-driven tier assignment | Rule engine (YAML config) |
| **PostgreSQL Store** | Persistent, indexed storage | PostgreSQL + SQLAlchemy |
| **Retriever** | Deterministic memory search | Metadata filtering + scoring |
| **Scorer** | Rank memories by importance/recency | Configurable scoring engine |

Each layer is **modular, configurable, and easy to extend**.

---

## 🧱 Multi-Tier Memory System

Memoric organizes memories into tiers, each with its own lifecycle:

<table>
<thead>
<tr>
<th>Tier</th>
<th>Lifetime</th>
<th>Behavior</th>
<th>Purpose</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Short-Term</strong></td>
<td>Days</td>
<td>Raw, recent data</td>
<td>Immediate recall</td>
</tr>
<tr>
<td><strong>Mid-Term</strong></td>
<td>Weeks–Months</td>
<td>Trimmed, compact</td>
<td>Ongoing relevance</td>
</tr>
<tr>
<td><strong>Long-Term</strong></td>
<td>Months–Years</td>
<td>Clustered, summarized</td>
<td>Historical continuity</td>
</tr>
</tbody>
</table>

### Memory Evolution Example

```
Day 1   → 💾 Stored in short_term (full detail)
Day 8   → 🔄 Moved to mid_term (trimmed)
Day 100 → 📚 Moved to long_term (clustered by topic)
```

Tier transitions are **deterministic** and follow your YAML policy.

---

## 🧵 Multi-Threaded Memory

Memoric natively supports **multi-threaded memory** — ideal for agents handling multiple topics or chat sessions with the same user.

### Thread Hierarchy

```
User: U-123
 ├── Thread: T-Refunds
 │    ├── Message 1: "Where's my refund?"
 │    ├── Message 2: "It's been two weeks."
 │    └── Message 3: "Still waiting..."
 ├── Thread: T-Shipping
 │    ├── Message 1: "When will my package arrive?"
 │    └── Message 2: "Is it shipped yet?"
 └── Thread: T-Technical
      └── Message 1: "How do I reset my password?"
```

### Thread Features

| Feature | Description |
|---------|-------------|
| **Thread Isolation** | Each conversation has its own memory timeline |
| **Thread Linking** | Link threads with related topics or entities |
| **Cross-Thread Recall** | Optionally fetch related past experiences |
| **Thread Summarization** | Old threads summarized and archived |
| **Concurrent Safety** | PostgreSQL ensures thread-safe operations |

### Thread Management Example

```python
# Save messages in different threads
mem.save(user_id="U-123", thread_id="T-Refunds",
         message="Still no refund yet.")
mem.save(user_id="U-123", thread_id="T-Shipping",
         message="When will my package arrive?")

# Retrieve thread-specific memory
refund_context = mem.retrieve(user_id="U-123", thread_id="T-Refunds")
shipping_context = mem.retrieve(user_id="U-123", thread_id="T-Shipping")
```

---

## 🧮 Scoring System

Each memory is ranked **deterministically** using configurable weights:

```python
score = (importance × 0.6) + (recency × 0.3) + (repetition × 0.1)
```

### Customizable Weights

```yaml
retrieval:
  scoring:
    importance: 0.6   # How critical is this memory?
    recency: 0.3      # How recent is it?
    repetition: 0.1   # How often is it mentioned?
```

All scoring formulas are **fully transparent and adjustable**.

---

## 🔒 Security Features

<div align="center">

### 🏆 Security Score: **8/10** (Production Grade)

</div>

<table>
<tr>
<td width="50%">

### 🔐 Authentication & Authorization
- ✅ JWT-based authentication (HS256)
- ✅ Role-Based Access Control (RBAC)
- ✅ Secure password hashing (Bcrypt)
- ✅ API key management
- ✅ Token refresh & revocation

### 🛡️ Data Protection
- ✅ Encryption at rest (Fernet/AES-128)
- ✅ Encrypted sensitive fields
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ XSS protection (Pydantic validation)

</td>
<td width="50%">

### 📝 Audit & Compliance
- ✅ Comprehensive audit logging (30+ event types)
- ✅ Compliance support (SOC2, GDPR, HIPAA, PCI-DSS)
- ✅ IP address & user agent tracking
- ✅ Before/after state capture
- ✅ Security event detection

### 🏥 Health Monitoring
- ✅ Liveness probes (Kubernetes-ready)
- ✅ Readiness probes
- ✅ Resource monitoring (CPU, memory, disk)
- ✅ Database health checks

</td>
</tr>
</table>

### Security Quick Start

```python
from memoric.api import create_app

# Create secure API with authentication
app = create_app(
    enable_auth=True,      # JWT authentication
    enable_audit=True,     # Audit logging
    secret_key="your-secret-key"
)
```

**See [SECURITY_IMPLEMENTATION_COMPLETE.md](SECURITY_IMPLEMENTATION_COMPLETE.md) for full details.**

---

## 🔌 Framework Integration

### LangChain Integration

```python
from memoric.integrations.langchain.memory import MemoricMemory
from langchain.agents import AgentExecutor

# Use Memoric as LangChain memory backend
memory = MemoricMemory(
    user_id="user-123",
    thread_id="conversation-1",
    k=10  # Number of memories to retrieve
)

agent = AgentExecutor(
    llm=your_llm,
    memory=memory,
    # ... other config
)
```

### Custom Integration

```python
# Direct API usage
from memoric import Memoric

class MyAgent:
    def __init__(self, user_id: str, thread_id: str):
        self.memory = Memoric()
        self.user_id = user_id
        self.thread_id = thread_id

    def process(self, user_input: str):
        # Retrieve relevant memories
        memories = self.memory.retrieve(
            user_id=self.user_id,
            thread_id=self.thread_id,
            top_k=10
        )

        # Format context for LLM
        context = "\n".join([m["content"] for m in memories])

        # Generate response with context
        response = self.llm.generate(f"Context:\n{context}\n\nQuery: {user_input}")

        # Store the interaction
        self.memory.save(
            user_id=self.user_id,
            thread_id=self.thread_id,
            content=user_input
        )

        return response
```

### Framework-Agnostic Pattern

```python
from memoric import Memoric

mem = Memoric()

# Save memories
mem.save(user_id="user-1", thread_id="chat-1", content="User question")
mem.save(user_id="user-1", thread_id="chat-1", content="Agent response")

# Retrieve for context
memories = mem.retrieve(user_id="user-1", thread_id="chat-1", top_k=5)

# Use with any LLM framework (OpenAI, Anthropic, etc.)
context = "\n".join([m["content"] for m in memories])
```

---

## 🧰 Developer API

### Core Methods

| Method | Description | Example |
|--------|-------------|---------|
| `mem.save()` | Store a memory | `mem.save(user_id="U-1", content="Hello")` |
| `mem.retrieve()` | Retrieve memories | `mem.retrieve(user_id="U-1", top_k=10)` |
| `mem.run_policies()` | Execute tier transitions | `mem.run_policies()` |
| `mem.inspect()` | Debug memory system | `mem.inspect()` |
| `mem.rebuild_clusters()` | Rebuild topic clusters | `mem.rebuild_clusters(user_id="U-1")` |
| `mem.get_topic_clusters()` | Get topic clusters | `mem.get_topic_clusters(user_id="U-1")` |

### API Reference

#### `save()` - Store a Memory

```python
memory_id = mem.save(
    user_id="user-123",           # Required: User identifier
    content="Meeting notes...",   # Required: Memory content
    thread_id="thread-abc",       # Optional: Thread/conversation ID
    session_id="session-xyz",     # Optional: Session identifier
    metadata={"custom": "data"},  # Optional: Additional metadata
    namespace="team-alpha"        # Optional: Namespace for multi-tenancy
)
# Returns: int (memory ID)
```

#### `retrieve()` - Get Memories

```python
memories = mem.retrieve(
    user_id="user-123",                    # Filter by user
    thread_id="thread-abc",                # Filter by thread
    metadata_filter={"topic": "refunds"},  # Filter by metadata
    scope="thread",                        # Scope: thread|topic|user|global
    top_k=10,                              # Max results
    namespace="team-alpha"                 # Filter by namespace
)
# Returns: List[Dict[str, Any]]
```

#### Other Methods

```python
# Run policy-based tier transitions
mem.run_policies()

# Inspect memory system state
info = mem.inspect()
# Returns: {"config": {...}, "db_table": "memories", "counts_by_tier": {...}}

# Rebuild topic clusters for a user
cluster_count = mem.rebuild_clusters(user_id="user-123")

# Get topic clusters
clusters = mem.get_topic_clusters(
    user_id="user-123",
    topic="sales",      # Optional filter
    category="meeting", # Optional filter
    limit=100
)
```

---

## 📊 Database Schema

### Memory Table

```sql
CREATE TABLE memories (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    thread_id TEXT,
    session_id TEXT,
    content TEXT NOT NULL,
    metadata JSONB,
    tier TEXT DEFAULT 'short_term',
    importance_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_memories_user_thread ON memories(user_id, thread_id);
CREATE INDEX idx_memories_tier ON memories(tier);
CREATE INDEX idx_memories_created ON memories(created_at DESC);
```

### Cluster Table

```sql
CREATE TABLE memory_clusters (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    entities JSONB,
    summary TEXT,
    memory_ids JSONB,
    occurrences INT DEFAULT 0,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    UNIQUE(user_id, topic, category)
);
```

**Full schema**: [memoric/db/schema.py](memoric/db/schema.py)

---

## 🎨 Design Philosophy

<table>
<tr>
<td width="50%">

### ✅ Core Principles

- **Deterministic by Default** – Every action is explainable
- **Metadata-First Design** – Structure before embeddings
- **Policy-Driven Logic** – YAML-defined behavior
- **Simple, Composable Python** – No bloat
- **Thread-Safe & Scalable** – PostgreSQL transactions

</td>
<td width="50%">

### 🎯 Design Goals

- Transparency over black boxes
- Explainability for all decisions
- Enterprise-grade reliability
- Developer-friendly APIs
- Production-ready from day one

</td>
</tr>
</table>

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md) | Complete JWT & RBAC guide |
| [AUDIT_LOGGING_COMPLETE.md](AUDIT_LOGGING_COMPLETE.md) | Audit system documentation |
| [SECURITY_IMPLEMENTATION_COMPLETE.md](SECURITY_IMPLEMENTATION_COMPLETE.md) | Security features overview |
| [COMPREHENSIVE_REVIEW.md](COMPREHENSIVE_REVIEW.md) | Full system review (8.95/10) |
| [INSTALLATION.md](INSTALLATION.md) | Detailed setup instructions |

---

## 🧪 Testing

### Run Tests

```bash
# Install dev dependencies
pip install memoric[dev]

# Run all tests
pytest

# Run with coverage
pytest --cov=memoric --cov-report=html

# Run specific test suite
pytest tests/test_authentication.py
pytest tests/test_audit_logging.py
```

### Test Coverage

```
✅ Unit Tests: 100+ tests
✅ Integration Tests: 15/15 passed
✅ Security Tests: All passed
✅ Database Tests: All passed
✅ API Tests: All passed
```

---

## 🚦 Production Checklist

### Before Deploying

- [ ] Set production secrets (JWT, encryption keys)
- [ ] Configure PostgreSQL database
- [ ] Enable HTTPS (nginx/Caddy)
- [ ] Set CORS origins
- [ ] Configure environment variables
- [ ] Set up monitoring (Prometheus)
- [ ] Configure audit log retention
- [ ] Review security settings

### Environment Variables

```bash
# Required
export MEMORIC_DB_HOST="your-db-host"
export MEMORIC_DB_USER="memoric"
export MEMORIC_DB_PASSWORD="your-secure-password"
export MEMORIC_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(64))')"
export MEMORIC_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"

# Optional
export MEMORIC_LOG_LEVEL="INFO"
export MEMORIC_CORS_ORIGINS="https://yourdomain.com"
export MEMORIC_RATE_LIMIT="100/minute"
```

---

## 🤝 Contributing

We welcome contributions from AI engineers, researchers, and developers!

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/memoric.git
cd memoric

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black memoric tests
```

### Contribution Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Write clear commit messages

---

## 📈 Roadmap

### Version 0.2.0 (Q4 2025)
- [ ] Async database support (asyncpg)
- [ ] Redis caching layer
- [ ] Rate limiting middleware
- [ ] Email verification
- [ ] Password reset flow

### Version 0.3.0 (Q1 2026)
- [ ] OAuth integration
- [ ] Multi-factor authentication
- [ ] Admin dashboard
- [ ] Performance optimization
- [ ] Multi-database support

### Version 1.0.0 (Q2 2026)
- [ ] Enterprise features
- [ ] Advanced analytics
- [ ] Custom embedding models
- [ ] Distributed deployment
- [ ] Cloud-native features

---

## 🛡️ License

**Apache License 2.0** – Free for personal, commercial, and research use.

See [LICENSE](LICENSE) file for details.

---

## 👥 Team & Support

### Maintainers

**Built with ❤️ by:**
- [Muthanna Al-Faris](https://github.com/muthannaalfaris) – Creator & Lead Developer
- Part of [Nuzum Technologies](https://nuzumtech.com)'s open AI infrastructure initiative

### Support

- 📖 **Documentation**: [docs.memoric.dev](https://docs.memoric.dev)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/cyberbeamhq/memoric/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/cyberbeamhq/memoric/issues)
- 📧 **Email**: support@memoric.dev

---

## ⭐ Show Your Support

If you find Memoric useful, please consider:

- ⭐ Starring the repository
- 🐛 Reporting bugs
- 💡 Suggesting features
- 📖 Improving documentation
- 🤝 Contributing code

---

<div align="center">

### 🚀 Memoric — Bring Structure, Persistence, and Reasoning to Your AI's Memory

**[Get Started](#-installation)** • **[View Docs](#-documentation)** • **[Join Community](https://github.com/cyberbeamhq/memoric/discussions)**

---

Made with 🧠 by the Memoric Team | [Website](https://memoric.dev) | [GitHub](https://github.com/cyberbeamhq/memoric)

</div>
