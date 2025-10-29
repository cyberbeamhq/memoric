# Memoric Quick Start Guide

Get started with Memoric in 5 minutes!

## Installation

```bash
# Clone the repository
git clone https://github.com/cyberbeamhq/memoric.git
cd memoric

# Install the package
pip install -e .

# Optional: Install with LLM support
pip install -e ".[llm]"
```

## Basic Usage

### 1. Create Your Configuration

```bash
# Copy the default configuration
cp config/default_config.yaml my_config.yaml

# Edit the configuration (IMPORTANT: Review text processing settings!)
vim my_config.yaml
```

**Key Configuration Section** (Prevent Data Loss!):

```yaml
text_processing:
  trimmer:
    type: noop  # ← Set to 'noop' to preserve all data
  summarizer:
    type: noop  # ← Set to 'noop' to prevent summarization
```

### 2. Use Memoric in Your Code

```python
from core.memory_manager import Memoric

# Initialize with your config
m = Memoric(config_path="my_config.yaml")

# Save a memory
m.save(
    user_id="user123",
    thread_id="conversation_1",
    content="Important meeting notes: Discussed Q4 roadmap and priorities.",
    metadata={"topic": "planning", "importance": "high"}
)

# Retrieve memories
results = m.retrieve(
    user_id="user123",
    query="roadmap",
    top_k=5
)

for memory in results:
    print(f"Score: {memory['_score']:.2f}")
    print(f"Content: {memory['content']}")
    print(f"Tier: {memory['tier']}")
    print("---")
```

### 3. Using LLM-Powered Features

```python
from core.memory_manager import Memoric
import os

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "sk-..."

# Configure for LLM usage
config = {
    "database": {"dsn": "sqlite:///./memoric.db"},
    "text_processing": {
        "trimmer": {"type": "noop"},  # Still preserve data
        "summarizer": {
            "type": "llm",  # Use LLM for summarization
            "model": "gpt-4o-mini"
        }
    },
    "metadata": {
        "enrichment": {
            "enabled": True,
            "model": "gpt-4o-mini"
        }
    }
}

m = Memoric(config=config)

# Automatic metadata extraction!
m.save(
    user_id="user123",
    content="We need to fix the authentication bug by Friday. John will handle it."
)
# → Automatically extracts: topic, category, entities, importance
```

## Import Patterns

Memoric supports multiple import patterns:

```python
# Direct imports (currently recommended)
from core.memory_manager import Memoric
from core.retriever import Retriever
from utils.text_processors import LLMSummarizer

# Using package modules
from core import MemoryManager, Retriever
from utils import LLMSummarizer, ScoringEngine
```

## Configuration Sections

Your config file controls everything. Key sections:

### Database
```yaml
database:
  dsn: "sqlite:///./memoric.db"  # or postgresql://...
```

### Text Processing (IMPORTANT!)
```yaml
text_processing:
  trimmer:
    type: noop  # Options: noop, simple
  summarizer:
    type: noop  # Options: noop, simple, llm
```

### Storage Tiers
```yaml
storage:
  tiers:
    - name: short_term
      expiry_days: 7
    - name: mid_term
      expiry_days: 30
    - name: long_term
      # No expiry - permanent storage
```

### Memory Policies
```yaml
policies:
  write_policies:
    - when: "score >= 0.8"
      to: [long_term]
    - when: "score >= 0.5"
      to: [mid_term]
    - when: "score < 0.5"
      to: [short_term]
```

## Custom Text Processing

Create your own processing logic:

```python
from utils.text_processors import TextSummarizer
from core import PolicyExecutor

class MySummarizer(TextSummarizer):
    """Your custom ML model or logic"""
    def summarize(self, text: str, target_chars: int) -> str:
        # Your implementation here
        return your_ml_model.summarize(text)

# Use your custom processor
from db.postgres_connector import PostgresConnector

db = PostgresConnector(dsn="sqlite:///./memoric.db")
executor = PolicyExecutor(
    db=db,
    config=config,
    summarizer=MySummarizer()  # Inject your custom processor!
)
```

## Common Operations

### Save Memory
```python
m.save(
    user_id="user123",
    thread_id="conv_1",
    content="Memory content here",
    metadata={"topic": "meetings", "importance": "high"}
)
```

### Retrieve Memories
```python
# By query
results = m.retrieve(
    user_id="user123",
    query="project deadline",
    top_k=10
)

# By thread
results = m.retrieve(
    user_id="user123",
    thread_id="conv_1",
    top_k=5
)

# By topic
results = m.retrieve(
    user_id="user123",
    topic="meetings",
    top_k=10
)
```

### Run Policies
```python
# Execute policies (migration, trimming, etc.)
result = m.run_policies()
print(f"Migrated: {result['migrated']}")
print(f"Trimmed: {result['trimmed']}")
print(f"Summarized: {result['summarized']}")
```

### Inspect System
```python
# Get system information
info = m.inspect()
print(f"Total memories: {info['total_records']}")
print(f"By tier: {info['tier_counts']}")
print(f"Clusters: {len(info['clusters'])}")
```

## Validation

Check that your configuration is consistent:

```bash
python scripts/check_version_consistency.py
```

**Expected output**:
```
✓ All versions are consistent: 0.1.0
✓ Dependencies are consistent
✓ Optional dependencies consistent
✓ All checks passed!
```

## Examples

Check the `examples/` directory for complete examples:

- `examples/quickstart_sdk.py` - Basic usage
- `examples/demo_basic.py` - Core features
- `examples/demo_multi_tier.py` - Multi-tier demonstration
- `examples/custom_text_processing.py` - Custom processors (5 examples!)
- `examples/policy_driven.py` - Policy configuration
- `examples/langchain_integration.py` - LangChain integration

Run an example:
```bash
python examples/quickstart_sdk.py
```

## Documentation

For detailed information, see:

- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - Complete configuration reference (400+ lines)
- **[TEXT_PROCESSING_GUIDE.md](TEXT_PROCESSING_GUIDE.md)** - Text processing documentation (600+ lines)
- **[INSTALLATION_AND_IMPORTS.md](INSTALLATION_AND_IMPORTS.md)** - Installation instructions
- **[CONFIGURATION_STATUS.md](CONFIGURATION_STATUS.md)** - Current status and known issues

## Troubleshooting

### Import Errors

If you see `ImportError`, ensure the package is installed:

```bash
pip install -e .
```

And use direct imports:

```python
from core.memory_manager import Memoric  # ✅ Works
# Instead of:
# from memoric import Memoric  # ⚠️ May have issues
```

### Configuration Not Loading

Use an absolute path:

```python
from pathlib import Path

config_path = Path(__file__).parent / "my_config.yaml"
m = Memoric(config_path=str(config_path))
```

### Database Connection Issues

For PostgreSQL, ensure the connection string is correct:

```yaml
database:
  dsn: "postgresql://user:password@localhost:5432/memoric"
```

For SQLite (development):

```yaml
database:
  dsn: "sqlite:///./memoric.db"
```

## Support

- **Issues**: https://github.com/cyberbeamhq/memoric/issues
- **Documentation**: See the guides listed above
- **Email**: ceo@cyberbeam.ie

## Version

Current version: **0.1.0**

Check version:
```bash
pip show memoric | grep Version
```

---

**Ready to build?** Start with `examples/quickstart_sdk.py` and customize from there!
