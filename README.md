🧠 Memoric

Policy-driven, deterministic memory framework for AI agents

“Memoric gives your AI agents structured, explainable, and persistent memory — without the black box.”

📖 Overview

Memoric is an open-source Python framework that provides a robust, deterministic memory layer for AI agents.
It helps AI teams deploy agents with long-term, rule-based memory, structured by metadata, organized by tiers, and retrievable through policy-driven scoring.

Instead of relying solely on vector embeddings or opaque similarity searches, Memoric focuses on structure, transparency, and control.
Every stored memory is traceable, explainable, and policy-governed — enabling predictable, high-relevance recall for any AI system.

✨ Key Features

✅ Deterministic, Rule-Based Retrieval
Retrieve memories using metadata, recency, and importance — not fuzzy vector magic.

✅ Multi-Tier Memory Architecture
Short-term, mid-term, and long-term tiers evolve your memory over time automatically.

✅ Multi-Threaded Memory Isolation
Maintain separate memory threads (e.g., different chat topics) under one user while preserving cross-thread relevance when needed.

✅ Metadata Enrichment via Metadata Agent
AI-powered metadata extraction (topics, categories, entities, and importance).

✅ Policy-Driven YAML Configuration
Define memory rules, expiry, routing, and scoring in one clean YAML file.

✅ PostgreSQL Backend
Proven, efficient, and enterprise-grade — with ready-to-use schemas and indexes.

✅ Clustered Long-Term Summaries
Automatically condense repeated information into structured knowledge clusters.

✅ Framework-Agnostic Integration
Works with LangChain, LlamaIndex, or any custom LLM pipeline.

🧩 Core Architecture
User or AI Agent
   ↓
Metadata Agent (adds metadata)
   ↓
Memory Router (applies tier & thread policies)
   ↓
PostgreSQL Memory Store
   ↓
Retriever + Scorer (finds relevant memories)
   ↓
Context Assembler (returns structured context)
   ↓
LLM / Agent


Each layer is modular, configurable, and easy to extend.

🧱 Installation
pip install memoric


(Coming soon — currently in early development stage.)

⚙️ Quick Start
1️⃣ Create a Config File (config.yaml)
database:
  engine: postgres
  host: localhost
  user: memoric
  password: secret
  db: memoric_db

metadata_agent:
  model: gpt-4o-mini
  extract_fields: [topic, category, entities, sentiment, importance]

tiers:
  short_term:
    expiry_days: 7
  mid_term:
    expiry_days: 90
    trim: true
  long_term:
    expiry_days: 365
    cluster_by: ["topic", "entities"]

retrieval:
  scope: thread  # options: thread | topic | user | global
  fallback: topic
  scoring:
    importance: 0.6
    recency: 0.3
    repetition: 0.1

2️⃣ Initialize Memoric
from memoric import Memoric

mem = Memoric(config_path="config.yaml")

3️⃣ Store a New Memory
mem.save(
    user_id="U-123",
    thread_id="T-Refunds",
    session_id="S-456",
    message="I still haven’t received my refund for order #1049.",
    role="user"
)


Memoric automatically:

Enriches the message with metadata via the Metadata Agent

Routes it to the appropriate tier (e.g., short_term)

Stores it in PostgreSQL with all relevant metadata

4️⃣ Retrieve Context
context = mem.retrieve(
    user_id="U-123",
    thread_id="T-Refunds",
    query="refund status",
    max_results=10
)

print(context)


Example output:

{
  "thread_context": [
    "User: I still haven’t received my refund for order #1049.",
    "Agent: We’ve escalated your case to finance.",
    "User: It’s been two weeks now, any updates?"
  ],
  "related_history": [
    "User had similar refund issues in Jan 2024 (Order #1082)."
  ],
  "metadata": {
    "topic": "refunds",
    "category": "customer_support",
    "importance": "high",
    "thread_id": "T-Refunds",
    "user_id": "U-123"
  }
}


This JSON can be injected directly into your LLM’s context window.

🧠 Multi-Tier Memory System

Memoric organizes memories into tiers, each with its own lifecycle and transformation rules.

Tier	Lifetime	Behavior	Purpose
short_term	Days	Raw, recent data	Immediate recall
mid_term	Weeks–Months	Trimmed, compact	Ongoing relevance
long_term	Months–Years	Clustered, summarized	Historical continuity

Example evolution:

Day 1   → Stored in short_term  
Day 8   → Moves to mid_term (trimmed)  
Day 100 → Moves to long_term (clustered by topic)


Tier transitions are deterministic and follow your YAML policy.

🧵 Threaded Memory and Context Isolation

Memoric natively supports multi-threaded memory — ideal for agents that handle multiple topics or chat sessions with the same user.

🧩 How It Works

Each message includes a thread_id, letting Memoric isolate and retrieve context per thread while optionally pulling related memories when relevant.

Example:

User 123
 ├── Thread: Refunds
 │    ├── Message 1
 │    ├── Message 2
 ├── Thread: Shipping
 │    ├── Message 1
 │    ├── Message 2


Retrieving refund-related context will only fetch messages from that thread unless your retrieval policy allows topic-based fallback.

🧩 YAML Policy
retrieval:
  scope: thread      # Restrict to the active thread
  fallback: topic    # Fall back to similar-topic history if needed

🧩 Advanced Thread Management
Feature	Description
Thread Isolation	Each conversation thread has its own memory timeline
Thread Linking	Link threads with related topics or entities
Cross-Thread Recall	Optionally fetch related past experiences
Hierarchical Threads	Nested or related threads (e.g., “Refund #1049” related to “Refund #1082”)
Thread Summarization	Old threads are summarized and stored in long-term memory
Concurrent Thread Safety	PostgreSQL ensures thread-safe writes for multi-agent use
🧩 Example Usage
# Save messages in different threads
mem.save(user_id="U-123", thread_id="T-Refunds", message="Still no refund yet.")
mem.save(user_id="U-123", thread_id="T-Shipping", message="When will my package arrive?")

# Retrieve thread-specific memory
refund_context = mem.retrieve(user_id="U-123", thread_id="T-Refunds")
shipping_context = mem.retrieve(user_id="U-123", thread_id="T-Shipping")


Each retrieval yields isolated thread context plus optional related context via metadata-based linking.

🧮 Scoring System

Each memory (or cluster) is ranked deterministically:

score = (importance * 0.6) + (recency * 0.3) + (repetition * 0.1)


Weights and formulas are fully configurable.

🧰 Developer API
Method	Description
mem.save()	Store a message or event
mem.retrieve()	Retrieve relevant context
mem.run_policies()	Execute tier transitions
mem.add_metadata_agent()	Register or override metadata model
mem.inspect()	Debug memory tiers and scoring
mem.promote_tier()	Manually promote memories between tiers
🔌 Integration with AI Frameworks

Memoric works as a universal memory backend for any AI framework.

Example: LangChain Integration
from memoric import MemoricMemory
from langchain.agents import AgentExecutor

memory = MemoricMemory(config_path="config.yaml")

agent = AgentExecutor(
    model="gpt-4o",
    memory=memory
)


Now your LangChain agent benefits from:

Structured, tiered memory

Thread-aware context recall

Explainable, rule-based memory evolution

🧩 Example Database Schema
CREATE TABLE memories (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    thread_id TEXT,
    session_id TEXT,
    content TEXT,
    metadata JSONB,
    tier TEXT DEFAULT 'short_term',
    importance_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE clusters (
    id SERIAL PRIMARY KEY,
    topic TEXT,
    entities JSONB,
    summary TEXT,
    occurrences INT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
);

🧠 Design Philosophy
Principle	Description
Deterministic by default	Every action is explainable and repeatable
Metadata-first design	Structure and clarity before embeddings
Policy-driven logic	YAML-defined behavior for full transparency
Simple, Composable Python	Modular imports, no bloat
Thread-safe and scalable	Built on PostgreSQL transactions
🤝 Contributing

We welcome contributions from AI engineers, researchers, and open-source developers.

Fork the repo

Create a feature branch (git checkout -b feature/new-idea)

Commit your changes

Submit a PR

Follow the existing structure and commit conventions.

🛡️ License

Apache 2.0 — free for personal, commercial, and research use.

👥 Maintainers

Built with ❤️ by Muthanna Al-Faris and contributors.
Part of Nuzum Technologies’ initiative to build open, explainable AI infrastructure.

🚀 Tagline

Memoric — Bring structure, persistence, and reasoning to your AI’s memory.