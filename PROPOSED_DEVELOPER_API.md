# Proposed Developer-Friendly API

This document shows side-by-side comparison of **current API** vs **proposed improved API** for common use cases.

---

## Use Case 1: Building a Chatbot

### ❌ Current Way (Verbose)

```python
from memoric import Memoric
from openai import OpenAI

# Initialize
memory = Memoric()
openai_client = OpenAI()

def chat(customer_id: str, conversation_id: str, user_message: str):
    # 1. Save user message
    memory.save(
        user_id=customer_id,
        thread_id=conversation_id,
        content=user_message,
        role="user"
    )

    # 2. Retrieve conversation history
    memories = memory.retrieve(
        user_id=customer_id,
        thread_id=conversation_id,
        scope="thread",
        top_k=20
    )

    # 3. Format for OpenAI
    messages = [{"role": "system", "content": "You are helpful"}]
    for mem in memories:
        role = mem.get("metadata", {}).get("role", "user")
        content = mem.get("content", "")
        messages.append({
            "role": "assistant" if role == "assistant" else "user",
            "content": content
        })

    # 4. Call OpenAI
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )

    assistant_message = response.choices[0].message.content

    # 5. Save assistant response
    memory.save(
        user_id=customer_id,
        thread_id=conversation_id,
        content=assistant_message,
        role="assistant"
    )

    return assistant_message
```

**Problems:**
- 40+ lines for simple chat
- Manual message formatting
- Easy to forget saving response
- Have to manage OpenAI format manually

---

### ✅ Proposed Way (Simple)

```python
from memoric import SimpleAgent
from openai import OpenAI

# Initialize once
agent = SimpleAgent(
    memory=Memoric(),
    llm=OpenAI(),
    system_prompt="You are helpful"
)

def chat(customer_id: str, conversation_id: str, user_message: str):
    # One line does everything!
    return agent.chat(
        user_id=customer_id,
        conversation_id=conversation_id,
        message=user_message
    )
```

**Benefits:**
- 90% less code
- Auto-saves messages
- Auto-formats for LLM
- Auto-retrieves context
- Less error-prone

---

## Use Case 2: Customer Support with Context

### ❌ Current Way

```python
def handle_support_request(customer_id: str, message: str):
    # Get current conversation
    current_conv = memory.retrieve(
        user_id=customer_id,
        thread_id="current",
        scope="thread",
        top_k=10
    )

    # Get customer history
    history = memory.retrieve(
        user_id=customer_id,
        scope="user",
        top_k=50
    )

    # Get topic clusters
    clusters = memory.get_topic_clusters(
        user_id=customer_id,
        limit=5
    )

    # Manually build context
    context = "Conversation:\n"
    for mem in current_conv:
        context += f"- {mem['content']}\n"

    context += "\nCustomer History:\n"
    for mem in history[:5]:
        context += f"- {mem['content'][:50]}\n"

    context += "\nCommon Topics:\n"
    for cluster in clusters:
        context += f"- {cluster['topic']}\n"

    # Use context...
    return context
```

---

### ✅ Proposed Way

```python
def handle_support_request(customer_id: str, message: str):
    # Get full context automatically formatted
    context = memory.get_full_context(
        user_id=customer_id,
        include_conversation=True,
        include_history=True,
        include_patterns=True,
        format="llm_prompt"  # or "json", "markdown"
    )

    # Or even simpler with ConversationManager
    conversation = ConversationManager(
        memory=memory,
        customer_id=customer_id
    )

    return conversation.get_context(include_profile=True)
```

---

## Use Case 3: Searching Memories

### ❌ Current Way (Confusing)

```python
# Search for refund-related memories
memories = memory.retrieve(
    user_id="user-123",
    metadata_filter={
        "topic": "refunds",
        "importance": "high"
    },
    scope="user",
    top_k=20
)

# Complex filtering - unclear syntax
memories = memory.retrieve(
    user_id="user-123",
    metadata_filter={
        "metadata": {
            "topic": {"$in": ["refunds", "complaints"]},
            "created_at": {"$gte": "2024-01-01"}
        }
    }
)
```

**Problems:**
- Unclear what `metadata_filter` supports
- No type hints
- No autocomplete
- Easy to make mistakes

---

### ✅ Proposed Way (Intuitive)

```python
from memoric.query import Q

# Simple search
memories = memory.search(
    user_id="user-123",
    text="refund",
    topics=["refunds", "complaints"],
    min_score=70
)

# Query builder with autocomplete
memories = memory.retrieve(
    user_id="user-123",
    query=Q()
        .with_topic("refunds")
        .with_importance("high")
        .created_after("2024-01-01")
        .limit(20)
)

# Or fluent API
memories = (memory
    .for_user("user-123")
    .in_topics(["refunds", "complaints"])
    .with_high_importance()
    .recent(days=30)
    .limit(20)
    .fetch()
)
```

**Benefits:**
- Type-safe
- Autocomplete works
- Self-documenting
- Chainable

---

## Use Case 4: Batch Import

### ❌ Current Way (Manual Loop)

```python
# Import 1000 historical messages
conversations = load_from_csv("conversations.csv")

for msg in conversations:
    memory.save(
        user_id=msg["user_id"],
        thread_id=msg["thread_id"],
        content=msg["content"],
        role=msg["role"],
        metadata={"timestamp": msg["timestamp"]}
    )
    # This is SLOW - 1000 DB calls!
```

**Problems:**
- Slow (N database calls)
- No progress tracking
- No error handling
- No rollback on failure

---

### ✅ Proposed Way (Batch)

```python
# Import 1000 messages efficiently
conversations = load_from_csv("conversations.csv")

# Batch import with progress
memory_ids = memory.import_batch(
    conversations,
    batch_size=100,  # 10 DB calls instead of 1000
    show_progress=True
)

# Or use migration helper
from memoric.migrations import Migrator

migrator = Migrator.from_csv("conversations.csv")
migrator.migrate_to(
    memory,
    batch_size=100,
    on_error="skip"  # or "stop", "log"
)
```

**Benefits:**
- 10x faster
- Progress bar
- Error handling
- Transaction safety

---

## Use Case 5: Testing

### ❌ Current Way (No Helpers)

```python
import pytest

def test_my_chatbot():
    # Have to manually set up test data
    memory = Memoric()

    # Manually create test conversation
    memory.save(user_id="test", thread_id="test", content="Hello", role="user")
    memory.save(user_id="test", thread_id="test", content="Hi!", role="assistant")

    # Test
    result = chatbot.respond(memory, "test", "test", "How are you?")
    assert "good" in result.lower()

    # Manual cleanup
    # (actually - no way to delete memories!)
```

**Problems:**
- No test fixtures
- Manual setup/teardown
- Can't clean up test data
- Slow (real DB)

---

### ✅ Proposed Way (Test Utils)

```python
from memoric.testing import MemoryFixture, MockMemory

def test_my_chatbot(memory_fixture):
    # Pre-populated with test data
    memory = memory_fixture.with_conversation(
        user_id="test-user",
        messages=[
            ("user", "Hello"),
            ("assistant", "Hi there!"),
            ("user", "How are you?"),
            ("assistant", "I'm great!")
        ]
    )

    # Test
    result = chatbot.respond(memory, "test-user", "test-conv", "Tell me a joke")
    assert len(result) > 0

    # Auto-cleanup!

# Or use mock for unit tests (no DB)
def test_fast():
    memory = MockMemory()  # In-memory, fast
    # ... tests ...
```

**Benefits:**
- Fast test fixtures
- No DB setup needed
- Auto-cleanup
- Realistic test data

---

## Use Case 6: Monitoring

### ❌ Current Way (Only Prometheus)

```python
# Current: only Prometheus metrics
# No easy way to:
# - See memory usage
# - View conversations
# - Debug issues
# - Analyze patterns

# Have to write SQL queries manually
from memoric.db import PostgresConnector
db = PostgresConnector(dsn="...")
with db.engine.connect() as conn:
    result = conn.execute("SELECT COUNT(*) FROM memories WHERE user_id = %s", ["user-123"])
```

---

### ✅ Proposed Way (Dashboard + CLI)

```bash
# View stats in terminal
$ memoric stats --user user-123
User: user-123
Total Memories: 1,234
Conversations: 45
Most Common Topics: refunds (23%), orders (18%), delivery (15%)
Average Importance: 6.5/10

# Launch web dashboard
$ memoric dashboard --port 8080
Dashboard running at http://localhost:8080

# Search from CLI
$ memoric search --user user-123 --query "refund"
Found 15 memories:
1. [2024-11-01] "I need a refund for order #123" (score: 85)
2. [2024-10-28] "Refund processed successfully" (score: 78)
...

# Export data
$ memoric export --user user-123 --format json > backup.json
```

```python
# Or programmatic dashboard
from memoric.dashboard import Dashboard

dashboard = Dashboard(memory)
dashboard.run(port=8080)

# Access at http://localhost:8080
# - View memory usage by tier
# - Browse conversations
# - Search memories
# - View topic clusters
# - Analyze patterns
```

---

## Use Case 7: Integration with Tools

### ❌ Current Way (Manual)

```python
from langchain.agents import create_openai_functions_agent
from memoric.integrations.langchain.memory import MemoricMemory

# Complex setup
memory_obj = MemoricMemory(
    user_id="user-123",
    thread_id="conv-456",
    k=20
)

# Have to know LangChain internals
agent = create_openai_functions_agent(
    llm=ChatOpenAI(),
    tools=[tool1, tool2],
    prompt=complex_prompt_template
)

executor = AgentExecutor(
    agent=agent,
    tools=[tool1, tool2],
    memory=memory_obj,
    verbose=True
)
```

---

### ✅ Proposed Way (Simple)

```python
from memoric import ToolAgent

# Simple tool integration
agent = ToolAgent(
    memory=memory,
    system_prompt="You are helpful",
    tools=[
        get_order_status,
        cancel_order,
        process_refund
    ]
)

# Automatic tool calling + memory management
response = agent.chat(
    user_id="user-123",
    conversation_id="conv-456",
    message="Cancel my order #123"
)
# Response: "I've cancelled order #123. You'll receive a refund in 3-5 days."
```

---

## Summary: What's Missing

| Feature | Current | Proposed | Priority |
|---------|---------|----------|----------|
| **Simple chat wrapper** | ❌ Manual | ✅ SimpleAgent | 🔴 Critical |
| **Conversation manager** | ❌ No | ✅ ConversationManager | 🔴 Critical |
| **Batch operations** | ❌ Loop manually | ✅ Batch methods | 🔴 Critical |
| **Query builder** | ❌ Dict syntax | ✅ Fluent API | 🟠 High |
| **Testing utilities** | ❌ No | ✅ Fixtures + Mocks | 🟠 High |
| **Migration tools** | ❌ No | ✅ Migrator class | 🟠 High |
| **Dashboard** | ❌ No | ✅ Web UI | 🟡 Medium |
| **Better CLI** | ⚠️ Basic | ✅ Full-featured | 🟡 Medium |
| **Tool integration** | ⚠️ LangChain only | ✅ Built-in | 🟡 Medium |

---

## Recommended Implementation Order

### Phase 1: Quick Wins (v0.1.1 - 2 weeks)
```python
# Add these as convenience wrappers (no breaking changes)

class ConversationManager:
    """Simple wrapper around Memoric for chat use cases."""
    def __init__(self, memory, customer_id, conversation_id):
        self.memory = memory
        self.customer_id = customer_id
        self.conversation_id = conversation_id

    def add_message(self, content, role="user"):
        return self.memory.save(
            user_id=self.customer_id,
            thread_id=self.conversation_id,
            content=content,
            role=role
        )

    def get_history(self, limit=20):
        return self.memory.retrieve(
            user_id=self.customer_id,
            thread_id=self.conversation_id,
            scope="thread",
            top_k=limit
        )
```

### Phase 2: Core Features (v0.2.0 - 2 months)
- SimpleAgent class
- Batch operations
- Query builder
- Testing utilities

### Phase 3: Advanced (v0.3.0 - 4 months)
- Dashboard
- Migration tools
- Advanced CLI
- More integrations

---

This shows exactly what developers want vs what they currently have to do! 🎯
