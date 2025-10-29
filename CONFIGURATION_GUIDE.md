# Memoric Configuration Guide

This guide explains how to configure Memoric for your specific needs.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration File Structure](#configuration-file-structure)
3. [Creating Your Configuration](#creating-your-configuration)
4. [Configuration Sections](#configuration-sections)
5. [Import Patterns](#import-patterns)
6. [Installation Options](#installation-options)
7. [Configuration Validation](#configuration-validation)

---

## Quick Start

### 1. Generate Configuration File

```bash
# Install Memoric
pip install -e .

# Generate your configuration file
memoric init-config                    # Creates memoric_config.yaml
memoric init-config -o my_config.yaml  # Custom filename
memoric init-config --force            # Overwrite existing file
```

### 2. Edit Your Configuration

The generated file contains all available options with comments. Key sections to review:

```yaml
# PREVENT DATA LOSS - Disable trimming and summarization
text_processing:
  trimmer:
    type: noop  # Preserves all data
  summarizer:
    type: noop  # No summarization

# Database connection
database:
  dsn: "sqlite:///./memoric.db"  # Change to PostgreSQL in production

# Memory tiers
storage:
  tiers:
    - name: short_term
      expiry_days: 7
    - name: mid_term
      expiry_days: 30
    - name: long_term
```

### 3. Use Your Configuration

```python
from memoric import Memoric

# Load custom config
m = Memoric(config_path="memoric_config.yaml")

# Or pass config dict directly
config = {
    "database": {"dsn": "postgresql://..."},
    "text_processing": {
        "trimmer": {"type": "noop"},
        "summarizer": {"type": "noop"}
    }
}
m = Memoric(config=config)
```

---

## Configuration File Structure

Memoric uses YAML configuration files with the following structure:

```
config/
├── default_config.yaml    # Package default (DO NOT EDIT)
└── [your config files]    # Your custom configurations
```

### Configuration Priority

When loading configuration, Memoric follows this priority order:

1. **Explicit config dict** passed to `Memoric(config={...})`
2. **Config file path** passed to `Memoric(config_path="...")`
3. **Environment variable** `MEMORIC_CONFIG` pointing to a file
4. **Default config** from package (`config/default_config.yaml`)

---

## Creating Your Configuration

### Method 1: Using CLI (Recommended)

```bash
# Generate with default name
memoric init-config

# Generate with custom name
memoric init-config -o production_config.yaml

# Overwrite existing file
memoric init-config --force
```

The CLI will show you the next steps:

```
✓ Config file created: memoric_config.yaml

Next steps:
  1. Edit the config file to suit your needs
  2. Review the text_processing section (prevent data loss!)
  3. Configure your database connection
  4. Adjust storage tiers and policies

Key sections to review:
  • text_processing - Control trimming and summarization
  • database - Connection settings
  • storage - Memory tier configuration
  • policies - Write, migration, and trimming rules

Load it in your code:
  from memoric import Memoric
  m = Memoric(config_path="memoric_config.yaml")
```

### Method 2: Manual Copy

```bash
# Copy from package installation
cp $(python -c "import memoric; from pathlib import Path; print(Path(memoric.__file__).parent / 'config' / 'default_config.yaml')") my_config.yaml

# Edit the file
vim my_config.yaml
```

### Method 3: Start from Scratch

Create a minimal config with only the settings you need:

```yaml
# minimal_config.yaml
database:
  dsn: "postgresql://user:pass@localhost/memoric"

text_processing:
  trimmer:
    type: noop
  summarizer:
    type: noop

storage:
  tiers:
    - name: short_term
      expiry_days: 7
    - name: long_term
```

---

## Configuration Sections

### 1. Database Configuration

```yaml
database:
  dsn: "postgresql://user:pass@localhost:5432/memoric"

  # Connection pool (PostgreSQL only)
  pool:
    size: 5
    max_overflow: 10
    timeout: 30
```

**Options:**
- **SQLite** (development): `sqlite:///./memoric.db`
- **PostgreSQL** (production): `postgresql://user:pass@host:port/db`

### 2. Text Processing (Critical!)

**⚠️ IMPORTANT**: Default behavior may cause data loss through trimming/summarization.

```yaml
text_processing:
  # Option A: Disable all processing (RECOMMENDED)
  trimmer:
    type: noop    # No trimming - preserves all data
  summarizer:
    type: noop    # No summarization - preserves all data

  # Option B: Simple truncation
  trimmer:
    type: simple  # Truncates at max_chars
  summarizer:
    type: simple  # Naive sentence-based truncation

  # Option C: LLM-powered (requires openai package)
  summarizer:
    type: llm
    model: gpt-4o-mini
    api_key: sk-...  # Optional, uses OPENAI_API_KEY env var
```

**Custom Processors:**

```python
from memoric.utils import TextTrimmer, TextSummarizer

class MyCustomSummarizer(TextSummarizer):
    def summarize(self, text: str, target_chars: int) -> str:
        # Your ML model or custom logic
        return custom_summarization(text, target_chars)

# Use custom processor
from memoric.core import MemoryManager, PolicyExecutor
executor = PolicyExecutor(
    db=db,
    config=config,
    summarizer=MyCustomSummarizer()
)
```

See [TEXT_PROCESSING_GUIDE.md](TEXT_PROCESSING_GUIDE.md) for detailed documentation.

### 3. Storage Tiers

```yaml
storage:
  tiers:
    # Recent memory (high churn)
    - name: short_term
      expiry_days: 7
      trim:
        max_chars: 5000

    # Intermediate memory
    - name: mid_term
      expiry_days: 30
      trim:
        max_chars: 2000

    # Archive (permanent)
    - name: long_term
      # No expiry - stays forever
      trim:
        max_chars: 1000
```

### 4. Memory Policies

```yaml
policies:
  # Where to store new memories
  write_policies:
    - when: "score >= 0.8"
      to: [long_term]
    - when: "score >= 0.5"
      to: [mid_term]
    - when: "score < 0.5"
      to: [short_term]

  # Move memories between tiers
  migration_policies:
    - from: short_term
      to: mid_term
      when: "age_days > 7"
    - from: mid_term
      to: long_term
      when: "age_days > 30"

  # Trim large memories
  trimming_policies:
    - tier: mid_term
      when: "length > 2000"
      action: trim
      max_chars: 2000
```

### 5. Retrieval & Recall

```yaml
recall:
  default_top_k: 10
  default_scope: thread  # thread, topic, user, global
```

**Scopes:**
- `thread`: Single conversation thread
- `topic`: All threads with same topic
- `user`: All memories for a user
- `global`: All memories (⚠️ privacy concern!)

### 6. Scoring & Ranking

```yaml
scoring:
  weights:
    recency: 0.3      # How recent?
    importance: 0.4   # How important?
    frequency: 0.2    # How often accessed?
    relevance: 0.1    # Relevant to context?

  rules:
    - type: topic_boost
      topic: critical
      boost: 20
    - type: entity_match
      entities: [customer, deadline, bug]
      boost: 15
```

### 7. Metadata Enrichment

```yaml
metadata:
  enrichment:
    enabled: true
    model: gpt-4o-mini
    # api_key: sk-...  # Uses OPENAI_API_KEY env var

  fields:
    - topic
    - category
    - entities
    - importance
```

### 8. Privacy & Security

```yaml
privacy:
  user_isolation: true         # Enforce user data isolation
  allow_global_scope: false    # Prevent cross-user retrieval
  encrypt_content: false       # Encrypt at rest
  # encryption_key: "..."      # Required if encrypt_content=true
```

### 9. Observability

```yaml
observability:
  logging:
    enabled: true
    level: INFO  # DEBUG, INFO, WARNING, ERROR
    format: json
    output: stdout

  metrics:
    enabled: true
    exporter: prometheus
    port: 9090
    path: /metrics

  tracing:
    enabled: false
    exporter: jaeger
    endpoint: http://localhost:14268/api/traces
```

### 10. Performance

```yaml
performance:
  batch_size: 100
  max_concurrent: 10

  cache:
    enabled: true
    ttl: 300
    max_size: 1000

  rate_limit:
    enabled: false
    requests_per_minute: 100
```

### 11. Integrations

```yaml
integrations:
  vector_db:
    enabled: false
    provider: pinecone  # pinecone, weaviate, qdrant
    # api_key: "..."
    # index_name: memoric

  apis:
    openai:
      # api_key: sk-...
      timeout: 30
      max_retries: 3
```

---

## Import Patterns

Memoric supports multiple import patterns for flexibility.

### Legacy Pattern (Backward Compatibility)

```python
from memoric import Memoric

m = Memoric(config_path="config.yaml")
m.save(user_id="user1", content="...")
```

### Modern Pattern (Recommended)

```python
from memoric.core import MemoryManager, Retriever, PolicyExecutor
from memoric.utils import LLMSummarizer, TextTrimmer
from memoric.db import PostgresConnector
from memoric.agents import MetadataAgent

# Use MemoryManager instead of Memoric
m = MemoryManager(config_path="config.yaml")
```

### Direct Component Access

```python
from memoric.core import Retriever, PolicyExecutor
from memoric.utils import ScoringEngine, ScoringWeights

# Create custom scoring
scorer = ScoringEngine(
    weights=ScoringWeights(recency=0.5, importance=0.5)
)

# Use retriever directly
retriever = Retriever(db=db, scorer=scorer, config=config)
results = retriever.retrieve(user_id="user1", query="meetings")
```

### Available Imports

```python
# Core
from memoric.core import (
    MemoryManager,
    Retriever,
    PolicyExecutor,
    SimpleClustering,
    Cluster,
)

# Database
from memoric.db import PostgresConnector

# Agents
from memoric.agents import MetadataAgent

# Utilities
from memoric.utils import (
    TextTrimmer,
    TextSummarizer,
    LLMSummarizer,
    ScoringEngine,
    ScoringWeights,
)
```

---

## Installation Options

### Standard Installation

```bash
pip install memoric
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/cyberbeamhq/memoric.git
cd memoric

# Install in editable mode
pip install -e .
```

### Optional Dependencies

```bash
# LLM support (OpenAI)
pip install memoric[llm]

# Metrics/observability
pip install memoric[metrics]

# Development tools
pip install memoric[dev]

# All optional dependencies
pip install memoric[all]
```

---

## Configuration Validation

### Validate Configuration Consistency

Run the version consistency checker to ensure all config files are properly aligned:

```bash
python scripts/check_version_consistency.py
```

This validates:
- ✓ Version numbers match across `__init__.py`, `setup.py`, `pyproject.toml`
- ✓ Dependencies match between `setup.py` and `pyproject.toml`
- ✓ Optional dependencies (extras) are consistent

**Example Output:**

```
============================================================
  Memoric Configuration Consistency Checker
============================================================

Checking version consistency...

  __init__.py          -> 0.1.0
  setup.py             -> 0.1.0
  pyproject.toml       -> 0.1.0

✓ All versions are consistent: 0.1.0

Checking dependency consistency...

  ✓ Dependencies are consistent

Checking optional dependencies...

  ✓ 'llm' is consistent
  ✓ 'metrics' is consistent
  ✓ 'dev' is consistent
  ✓ 'all' is consistent

============================================================
  Summary
============================================================

✓ All checks passed! Configuration is consistent.

  Current version: 0.1.0
```

### Validate Runtime Configuration

```python
from memoric import Memoric

# Load config and validate
m = Memoric(config_path="config.yaml")

# Check loaded configuration
print(m.config)
```

---

## Environment Variables

Memoric respects the following environment variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `MEMORIC_CONFIG` | Default config file path | `export MEMORIC_CONFIG=/path/to/config.yaml` |
| `OPENAI_API_KEY` | OpenAI API key for LLM features | `export OPENAI_API_KEY=sk-...` |
| `DATABASE_URL` | Database connection (overrides config) | `export DATABASE_URL=postgresql://...` |

---

## Common Configuration Scenarios

### Scenario 1: Development (SQLite, No Processing)

```yaml
database:
  dsn: "sqlite:///./memoric_dev.db"

text_processing:
  trimmer:
    type: noop
  summarizer:
    type: noop

developer:
  debug: true
```

### Scenario 2: Production (PostgreSQL, LLM Processing)

```yaml
database:
  dsn: "postgresql://user:pass@prod-host:5432/memoric"
  pool:
    size: 10
    max_overflow: 20

text_processing:
  trimmer:
    type: noop  # Still recommend noop
  summarizer:
    type: llm
    model: gpt-4o-mini

privacy:
  user_isolation: true
  allow_global_scope: false
  encrypt_content: true
  encryption_key: "${ENCRYPTION_KEY}"  # From environment

observability:
  logging:
    enabled: true
    level: INFO
    output: /var/log/memoric/app.log
  metrics:
    enabled: true
    exporter: prometheus
    port: 9090
```

### Scenario 3: Multi-Tenant SaaS

```yaml
database:
  dsn: "postgresql://..."

privacy:
  user_isolation: true        # Critical!
  allow_global_scope: false   # Critical!

performance:
  rate_limit:
    enabled: true
    requests_per_minute: 100

observability:
  metrics:
    enabled: true
  tracing:
    enabled: true
```

---

## Troubleshooting

### Configuration Not Loading

**Issue**: Config file not found or not loading

**Solutions:**
1. Check file path: `ls -la memoric_config.yaml`
2. Use absolute path: `Memoric(config_path="/full/path/to/config.yaml")`
3. Check environment variable: `echo $MEMORIC_CONFIG`
4. Verify YAML syntax: `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`

### Import Errors

**Issue**: `Import "memoric" could not be resolved`

**Solutions:**
1. Install package: `pip install -e .`
2. Check installation: `pip show memoric`
3. Verify Python path: `python -c "import memoric; print(memoric.__file__)"`

### Version Mismatches

**Issue**: Dependencies or versions inconsistent

**Solution:**
```bash
# Run consistency checker
python scripts/check_version_consistency.py

# Fix any issues reported
# Then reinstall
pip install -e . --force-reinstall
```

---

## Best Practices

### 1. Start with NoOp Processing

Always start with `type: noop` for both trimmer and summarizer to prevent data loss:

```yaml
text_processing:
  trimmer:
    type: noop
  summarizer:
    type: noop
```

### 2. Use Environment Variables for Secrets

Never hardcode API keys or passwords in config files:

```yaml
metadata:
  enrichment:
    # DON'T: api_key: sk-abc123...
    # DO: Load from environment
    api_key: ${OPENAI_API_KEY}
```

### 3. Version Control Your Config

Keep your config in version control, but exclude secrets:

```bash
# .gitignore
memoric_config.yaml
*.local.yaml
.env
```

### 4. Validate Before Production

Always run the consistency checker before deploying:

```bash
python scripts/check_version_consistency.py
```

### 5. Monitor Configuration Changes

Log when configuration is loaded:

```python
import logging

m = Memoric(config_path="config.yaml")
logging.info(f"Loaded config from: {config_path}")
logging.info(f"Text processing: trimmer={m.config['text_processing']['trimmer']['type']}")
```

---

## Additional Resources

- [TEXT_PROCESSING_GUIDE.md](TEXT_PROCESSING_GUIDE.md) - Detailed text processing documentation
- [INSTALLATION_AND_IMPORTS.md](INSTALLATION_AND_IMPORTS.md) - Installation and import patterns
- [examples/](examples/) - Configuration examples and demos
- [config/default_config.yaml](config/default_config.yaml) - Complete default configuration

---

## Support

- **Issues**: https://github.com/cyberbeamhq/memoric/issues
- **Documentation**: https://github.com/cyberbeamhq/memoric
- **Email**: ceo@cyberbeam.ie
