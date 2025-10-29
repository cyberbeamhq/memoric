# Installation & Import Guide - Memoric

**Getting Started with Clean Imports and Centralized Configuration**

---

## Installation

### Option 1: Install from Source (Development)

```bash
# Clone the repository
git clone https://github.com/cyberbeamhq/memoric.git
cd memoric

# Install in editable mode
pip install -e .

# With optional dependencies
pip install -e ".[llm]"  # For LLM-based summarization
pip install -e ".[dev]"  # For development tools
```

### Option 2: Install from PyPI (When Published)

```bash
pip install memoric

# With optional dependencies
pip install memoric[llm]  # For LLM support
```

###  Option 3: Install from GitHub

```bash
pip install git+https://github.com/cyberbeamhq/memoric.git
```

---

## Import Patterns

Memoric supports two import styles: **Legacy** (for backward compatibility) and **Modern** (recommended).

### Modern Imports (Recommended)

```python
# Core components
from memoric.core import MemoryManager, Retriever, PolicyExecutor

# Database connectors
from memoric.db import PostgresConnector

# Agents
from memoric.agents import MetadataAgent

# Text processing
from memoric.utils import (
    TextTrimmer,
    TextSummarizer,
    LLMSummarizer,
    create_trimmer,
    create_summarizer,
)

# Scoring utilities
from memoric.utils import (
    ScoringEngine,
    ScoringWeights,
    create_topic_boost_rule,
)
```

### Legacy Imports (Backward Compatibility)

```python
# Old style - still works
from memoric import Memoric

m = Memoric()
```

### Top-Level Imports

```python
# Import from top level for convenience
from memoric import (
    MemoryManager,
    Retriever,
    PostgresConnector,
    MetadataAgent,
    LLMSummarizer,
)
```

---

## Configuration

### Quick Start (No Configuration)

```python
from memoric.core import MemoryManager

# Uses default configuration (SQLite database)
m = MemoryManager()
```

### Using the Default Config File

```python
from memoric.core import MemoryManager

# Use the provided default configuration
m = MemoryManager(config_path="config/default_config.yaml")
```

### Creating Your Own Configuration

```bash
# Copy the default config
cp config/default_config.yaml my_config.yaml

# Edit my_config.yaml with your settings
# Then use it:
```

```python
from memoric.core import MemoryManager

m = MemoryManager(config_path="my_config.yaml")
```

### Using a Dictionary Configuration

```python
from memoric.core import MemoryManager

config = {
    "database": {
        "dsn": "postgresql://user:pass@localhost:5432/memoric"
    },
    "text_processing": {
        "trimmer": {"type": "noop"},      # Preserve data
        "summarizer": {"type": "llm"}     # Use LLM
    },
    "storage": {
        "tiers": [
            {"name": "short_term", "expiry_days": 7},
            {"name": "mid_term", "expiry_days": 30},
            {"name": "long_term"}
        ]
    }
}

m = MemoryManager(config=config)
```

---

## Configuration File Location

### Default Locations (Searched in Order)

1. Path specified via `config_path` parameter
2. `./config.yaml` (current directory)
3. `./memoric.yaml`
4. `~/.memoric/config.yaml` (home directory)
5. `/etc/memoric/config.yaml` (system-wide)
6. `config/default_config.yaml` (package default)

### Environment Variable Override

```bash
export MEMORIC_CONFIG=/path/to/your/config.yaml
```

```python
from memoric.core import MemoryManager

# Will use MEMORIC_CONFIG environment variable
m = MemoryManager()
```

---

## Common Configuration Patterns

### Pattern 1: Prevent Data Loss

```yaml
# my_config.yaml
text_processing:
  trimmer:
    type: noop  # Never trim
  summarizer:
    type: noop  # Never summarize

# All data is preserved
```

### Pattern 2: Production with LLM

```yaml
# prod_config.yaml
database:
  dsn: postgresql://user:pass@prod-db:5432/memoric
  pool:
    size: 20
    max_overflow: 40

text_processing:
  trimmer:
    type: noop  # Don't trim
  summarizer:
    type: llm
    model: gpt-4o-mini

metadata:
  enrichment:
    enabled: true
    model: gpt-4o-mini

observability:
  logging:
    enabled: true
    level: INFO
  metrics:
    enabled: true
    port: 9090
```

### Pattern 3: Development / Testing

```yaml
# dev_config.yaml
database:
  dsn: sqlite:///./test.db

text_processing:
  trimmer:
    type: simple
  summarizer:
    type: simple

developer:
  debug: true
  profile: true

observability:
  logging:
    level: DEBUG
```

---

## Complete Usage Example

```python
"""
Complete example showing modern imports and configuration.
"""

# Import using modern style
from memoric.core import MemoryManager, Retriever
from memoric.utils import LLMSummarizer, create_trimmer
from memoric.db import PostgresConnector

# Option 1: Use config file
m = MemoryManager(config_path="my_config.yaml")

# Option 2: Use dict config
config = {
    "database": {"dsn": "sqlite:///./memories.db"},
    "text_processing": {
        "trimmer": {"type": "noop"},
        "summarizer": {"type": "llm", "model": "gpt-4o-mini"}
    }
}
m = MemoryManager(config=config)

# Save a memory
mem_id = m.save(
    user_id="user123",
    thread_id="conversation_1",
    content="Important meeting notes about Q4 planning..."
)

# Retrieve memories
results = m.retrieve(
    user_id="user123",
    query="Q4 planning",
    scope="user",
    top_k=5
)

# Access advanced components
retriever = m.retriever        # Access the retriever
db = m.db                      # Access the database connector
agent = m.metadata_agent       # Access the metadata agent

# Run policies
policy_results = m.run_policies()
print(f"Policies executed: {policy_results}")

# Rebuild clusters
cluster_count = m.rebuild_clusters(user_id="user123")
print(f"Created {cluster_count} clusters")
```

---

## IDE Setup (Fix Import Resolution)

### Problem: "Import 'memoric' could not be resolved"

This happens when the package isn't installed or isn't in your Python path.

### Solution 1: Install the Package

```bash
# Install in editable mode (recommended for development)
pip install -e .

# Now imports will work
```

### Solution 2: Add to PYTHONPATH

```bash
# Add project root to PYTHONPATH
export PYTHONPATH="/Users/user/Desktop/memoric:$PYTHONPATH"
```

### Solution 3: Use VSCode/PyCharm Settings

**VSCode** (`settings.json`):
```json
{
    "python.analysis.extraPaths": [
        "/Users/user/Desktop/memoric"
    ]
}
```

**PyCharm**:
1. Right-click project root → Mark Directory As → Sources Root

### Solution 4: For Examples (When Running as Scripts)

Examples already include path manipulation:

```python
import sys
from pathlib import Path

# Add parent directory to path for imports when running as script
sys.path.insert(0, str(Path(__file__).parent.parent))

# Now you can import
from memoric.core import MemoryManager
```

---

## Package Structure

```
memoric/
├── __init__.py           # Main package exports
├── core/
│   ├── __init__.py       # Core component exports
│   ├── memory_manager.py # MemoryManager class
│   ├── retriever.py      # Retriever class
│   ├── policy_executor.py# PolicyExecutor class
│   └── clustering.py     # Clustering utilities
├── db/
│   ├── __init__.py       # Database exports
│   └── postgres_connector.py
├── agents/
│   ├── __init__.py       # Agent exports
│   └── metadata_agent.py
├── utils/
│   ├── __init__.py       # Utility exports
│   ├── text_processors.py
│   ├── scoring.py
│   ├── logger.py
│   └── metrics.py
├── config/
│   ├── __init__.py
│   └── default_config.yaml  # ⭐ Main configuration file
├── examples/
│   └── *.py              # Usage examples
└── tests/
    └── *.py              # Test files
```

---

## Verification

### Test Your Installation

```python
# test_installation.py
from memoric.core import MemoryManager
from memoric.utils import LLMSummarizer
from memoric.db import PostgresConnector

print("✓ Imports working!")

m = MemoryManager()
print("✓ MemoryManager initialized!")

mem_id = m.save(user_id="test", content="Test memory")
print(f"✓ Memory saved: {mem_id}")

results = m.retrieve(user_id="test", query="test")
print(f"✓ Retrieval working: {len(results)} results")

print("\n🎉 Installation verified!")
```

### Run the Test

```bash
python test_installation.py
```

Expected output:
```
✓ Imports working!
✓ MemoryManager initialized!
✓ Memory saved: 1
✓ Retrieval working: 1 results

🎉 Installation verified!
```

---

## Migration from Old Imports

### Before (Old Style)

```python
from core.memory_manager import Memoric
from db.postgres_connector import PostgresConnector
from agents.metadata_agent import MetadataAgent
```

### After (New Style)

```python
from memoric.core import MemoryManager
from memoric.db import PostgresConnector
from memoric.agents import MetadataAgent
```

### Alias for Backward Compatibility

```python
# If you want to keep using "Memoric" name
from memoric.core import MemoryManager as Memoric

m = Memoric()  # Works!
```

---

## Troubleshooting

### Issue: ModuleNotFoundError: No module named 'memoric'

**Cause**: Package not installed

**Solution**:
```bash
cd /Users/user/Desktop/memoric
pip install -e .
```

### Issue: ImportError: cannot import name 'MemoryManager'

**Cause**: Package not properly installed or outdated

**Solution**:
```bash
pip uninstall memoric
pip install -e .
```

### Issue: Config file not found

**Cause**: Wrong path to config file

**Solution**:
```python
# Use absolute path
import os
config_path = os.path.join(os.path.dirname(__file__), "config", "default_config.yaml")
m = MemoryManager(config_path=config_path)

# Or use relative to package
from pathlib import Path
import memoric
package_dir = Path(memoric.__file__).parent
config_path = package_dir / "config" / "default_config.yaml"
m = MemoryManager(config_path=str(config_path))
```

### Issue: OpenAI API key not found (when using LLM)

**Cause**: OPENAI_API_KEY environment variable not set

**Solution**:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

Or in config:
```yaml
text_processing:
  summarizer:
    type: llm
    api_key: sk-your-key-here  # Not recommended - use env var instead
```

---

## Environment Variables

Memoric supports these environment variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `MEMORIC_CONFIG` | Path to config file | `/path/to/config.yaml` |
| `MEMORIC_DSN` | Database connection string | `postgresql://...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `MEMORIC_DEBUG` | Enable debug mode | `true` or `false` |
| `MEMORIC_LOG_LEVEL` | Logging level | `DEBUG`, `INFO`, `WARNING` |

---

## Next Steps

1. **Install the package**: `pip install -e .`
2. **Copy config template**: `cp config/default_config.yaml my_config.yaml`
3. **Customize config**: Edit `my_config.yaml` with your settings
4. **Run examples**: `python examples/quickstart_sdk.py`
5. **Read guides**:
   - [TEXT_PROCESSING_GUIDE.md](TEXT_PROCESSING_GUIDE.md)
   - [README.md](README.md)

---

## Quick Reference

```python
# Modern imports (recommended)
from memoric.core import MemoryManager
from memoric.utils import LLMSummarizer
from memoric.db import PostgresConnector

# Configuration (choose one)
m = MemoryManager()                          # Default config
m = MemoryManager(config_path="my_config.yaml")  # File config
m = MemoryManager(config={"database": {...}})    # Dict config

# Common operations
mem_id = m.save(user_id="u1", content="text")
results = m.retrieve(user_id="u1", query="search")
m.run_policies()
m.rebuild_clusters(user_id="u1")
```

---

**Questions?** See [examples/](examples/) directory for complete working examples.
