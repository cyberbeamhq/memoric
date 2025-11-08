# 🧠 Memoric

### *Simple Memory Management for AI Agents*

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

**Give your AI agents memory in 3 lines of code.**

Save what users say. Recall relevant context. Make your AI smarter.

---

## 🚀 Quick Start

```bash
pip install memoric
```

```python
from memoric import Memory

# Initialize
memory = Memory(user_id="chatbot")

# Save memories
memory.add("User loves pizza")
memory.add("User's birthday is March 15th")

# Search by meaning (not exact keywords!)
results = memory.search("What does the user like to eat?")
print(results[0]['content'])  # "User loves pizza"

# Get context for your AI
context = memory.get_context("User asked about food preferences")
# Pass this to your LLM as system message
```

That's it. Your AI now has memory.

---

## 💡 Core Concept

**What Memoric Does:**
1. **Save** what users say (text → database + vector embedding)
2. **Search** by meaning (semantic similarity, not just keywords)
3. **Recall** relevant context for AI responses

**What it's NOT:**
- Not a chatbot (bring your own LLM)
- Not a vector database (but integrates with Pinecone/Qdrant)
- Not complicated (one class, simple API)

---

## 📖 API Reference

### `Memory(user_id, **config)`

Initialize memory for a user/agent.

```python
# Development (uses local SQLite + in-memory vectors)
memory = Memory(user_id="bot_123")

# Production (uses Pinecone for scale)
memory = Memory(
    user_id="bot_123",
    vector_store="pinecone",
    vector_store_config={
        "api_key": "your-key",
        "index_name": "memories"
    }
)
```

### `memory.add(content, **metadata)`

Save a memory.

```python
memory.add(
    "User reported a bug in the mobile app",
    thread_id="ticket_456",
    importance="high"
)
```

### `memory.search(query, limit=5)`

Search memories by meaning.

```python
results = memory.search("What bugs did user report?", limit=3)
for result in results:
    print(f"[{result['_score']:.2f}] {result['content']}")
```

### `memory.get_context(query, format="text")`

Get formatted context for AI consumption.

```python
# Get as text (for LLM system message)
context = memory.get_context("User asking about their bug report")

# Get as JSON (for custom formatting)
context = memory.get_context("...", format="json")
```

### `memory.get_thread(thread_id)`

Get full conversation thread in chronological order.

```python
history = memory.get_thread("conv_123")
for msg in history:
    print(f"{msg['metadata']['role']}: {msg['content']}")
```

### `memory.stats()`

Get usage statistics.

```python
stats = memory.stats()
print(f"Total memories: {stats['total_memories']}")
print(f"Vector store: {stats['vector_store']}")
```

---

## 🎯 Use Cases

### Customer Support Bot
```python
from memoric import Memory

memory = Memory(user_id="support_bot")

# Save customer interactions
memory.add(
    "Customer complained about slow checkout",
    thread_id="ticket_789",
    importance="high"
)

# When customer returns
context = memory.get_context(
    "Customer is asking about their issue",
    thread_id="ticket_789"
)

# Your bot now remembers the previous conversation!
```

### Personal Assistant
```python
memory = Memory(user_id="user_alice")

# Throughout the day
memory.add("I need to buy groceries after work", importance="high")
memory.add("Meeting with Bob at 3pm tomorrow")
memory.add("Favorite restaurant is Olive Garden")

# Later
results = memory.search("What do I need to do today?")
# Returns: "I need to buy groceries after work"
```

### Document Q&A
```python
memory = Memory(user_id="doc_qa_bot")

# Index your documents
with open("manual.pdf") as f:
    for page in extract_pages(f):
        memory.add(page.text, metadata={"source": "manual.pdf"})

# Answer questions
results = memory.search("How do I reset my password?")
context = memory.get_context("User asking about password reset")
# Pass to your LLM
```

---

## 🔧 Production Setup

### With Pinecone (Recommended for scale)

```python
from memoric import Memory
import os

memory = Memory(
    user_id="production_bot",
    vector_store="pinecone",
    vector_store_config={
        "api_key": os.environ["PINECONE_API_KEY"],
        "environment": "us-east-1",
        "index_name": "memories",
        "dimension": 1536,  # OpenAI ada-002
    }
)
```

**Requirements:**
- `pip install pinecone-client`
- `OPENAI_API_KEY` environment variable (for embeddings)
- `PINECONE_API_KEY` environment variable

### With Qdrant

```python
memory = Memory(
    user_id="bot",
    vector_store="qdrant",
    vector_store_config={
        "url": "http://localhost:6333",
        "collection_name": "memories"
    }
)
```

**Requirements:**
- `pip install qdrant-client`
- Running Qdrant instance

---

## 🧪 How It Works

```
User says: "I love Italian food"
           ↓
    Save to database (PostgreSQL/SQLite)
           ↓
    Generate embedding (OpenAI ada-002)
           ↓
    Store in vector store (Pinecone/Qdrant/In-Memory)
           ↓
Later: Search "What does user like to eat?"
           ↓
    Generate query embedding
           ↓
    Vector similarity search (semantic)
           ↓
    Combine with keyword + recency scoring
           ↓
    Return: "I love Italian food" (0.89 relevance)
```

**Hybrid Search:**
- 60% semantic similarity (meaning)
- 30% keyword matching (exact terms)
- 10% recency (recent = more relevant)

---

## 📚 Examples

See `examples/` directory:

- **`simple.py`** - Simplest possible usage (10 lines)
- **`chatbot.py`** - Build a chatbot with memory
- **`production_simple.py`** - Production setup with Pinecone

---

## 🤔 FAQ

**Q: Do I need OpenAI API key?**
A: For best results, yes (for embeddings). Without it, we fall back to local embeddings (lower quality).

**Q: Do I need Pinecone/Qdrant?**
A: Not for development. In-memory works fine. For production with >10k memories, use Pinecone or Qdrant.

**Q: How is this different from LangChain memory?**
A: We're more focused and simpler. LangChain has 10 memory types - we have one that works well.

**Q: Can I use this with LangChain/LlamaIndex?**
A: Yes! Just pass `memory.get_context()` as a system message.

**Q: What about privacy/encryption?**
A: Memories are stored unencrypted by default. For encryption, see advanced config.

**Q: Can I delete memories?**
A: Yes: `memory.delete(memory_id)` or `memory.clear(thread_id="...")`

---

## 🛣️ Roadmap

- [ ] Automatic conversation summarization (compress old messages)
- [ ] Multi-modal memory (images, audio)
- [ ] Federated memory (share across agents)
- [ ] Memory decay (forget old/irrelevant memories)
- [ ] Memory consolidation (merge similar memories)

---

## 🤝 Contributing

We're open source! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Quick ways to help:**
- ⭐ Star the repo
- 🐛 Report bugs
- 💡 Suggest features
- 📖 Improve docs
- 🧪 Add examples

---

## 📄 License

Apache 2.0 - see [LICENSE](LICENSE)

---

## 🙏 Credits

Built with:
- PostgreSQL (database)
- OpenAI (embeddings)
- Pinecone/Qdrant (vector stores)
- Love ❤️

---

**Made by the Memoric team** | [GitHub](https://github.com/cyberbeamhq/memoric) | [Issues](https://github.com/cyberbeamhq/memoric/issues)
