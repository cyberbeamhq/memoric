# Memoric Installation Guide

This guide covers installation and initial setup of Memoric.

---

## Prerequisites

- **Python 3.9 or higher**
- **pip** package manager
- **PostgreSQL 12+** (recommended for production) or **SQLite** (for development)

---

## Installation Methods

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

### Option 3: Install with Optional Dependencies

```bash
# All optional dependencies
pip install memoric[all]

# Specific extras
pip install memoric[llm]      # OpenAI integration for metadata extraction
pip install memoric[metrics]  # Prometheus metrics
pip install memoric[dev]      # Development tools (pytest, black, mypy)
```

---

## Quick Start

### 1. Basic Setup (No Configuration Required)

Memoric works out of the box with SQLite:

```python
from memoric import Memoric

# Initialize with defaults
m = Memoric()

# Save a memory
memory_id = m.save(
    user_id="user-123",
    thread_id="conversation-1",
    content="Remember to follow up on the customer refund request"
)

# Retrieve memories
memories = m.retrieve(
    user_id="user-123",
    thread_id="conversation-1",
    top_k=10
)

print(memories)
```

### 2. With Configuration File

For more control, create a configuration file:

```bash
# Copy the quickstart config template
memoric init-config -o my_config.yaml
```

Then use it in your code:

```python
from memoric import Memoric

m = Memoric(config_path="my_config.yaml")
```

---

## Database Setup

### SQLite (Development)

No setup required! Memoric will create a database file automatically:

```python
from memoric import Memoric

m = Memoric()  # Creates memoric.db in current directory
```

### PostgreSQL (Production)

1. **Create Database:**

```bash
createdb memoric
```

2. **Set Environment Variables:**

```bash
export MEMORIC_DB_HOST="localhost"
export MEMORIC_DB_USER="your_username"
export MEMORIC_DB_PASSWORD="your_password"
export MEMORIC_DB_NAME="memoric"
```

3. **Or Use Configuration File:**

```yaml
# config.yaml
database:
  dsn: "postgresql://user:pass@localhost:5432/memoric"
```

4. **Initialize Schema:**

```python
from memoric import Memoric

m = Memoric(config_path="config.yaml")
m.initialize()  # Creates tables
```

---

## Optional: OpenAI Integration

For AI-powered metadata extraction:

1. **Install OpenAI package:**

```bash
pip install memoric[llm]
```

2. **Set API Key:**

```bash
export OPENAI_API_KEY="sk-..."
```

3. **Enable in Configuration:**

```yaml
metadata:
  enrichment:
    enabled: true
    model: gpt-4o-mini
```

**Note:** Memoric works without OpenAI - it falls back to simple heuristics for metadata extraction.

---

## Verification

Test your installation:

```bash
# Check version
memoric version

# Run basic test
python -c "from memoric import Memoric; m = Memoric(); print('✓ Installation successful!')"
```

---

## Docker Installation (Optional)

Coming soon! We're working on official Docker images.

---

## Troubleshooting

### ImportError: No module named 'memoric'

Make sure you've installed the package:
```bash
pip install memoric
```

### Database Connection Errors

For PostgreSQL, verify:
- PostgreSQL is running: `pg_isready`
- Database exists: `psql -l | grep memoric`
- Connection string is correct in config

### Permission Errors

If using SQLite, ensure you have write permissions in the current directory:
```bash
touch test.db  # Test write permission
rm test.db
```

---

## Next Steps

- Read the [README](README.md) for feature overview
- Check [examples/](examples/) for code examples
- See [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md) for security setup
- Review [quickstart_config.yaml](memoric/config/quickstart_config.yaml) for configuration options

---

## Upgrading

```bash
pip install --upgrade memoric
```

Check the [CHANGELOG](https://github.com/cyberbeamhq/memoric/releases) for breaking changes.

---

## Support

- **Issues:** https://github.com/cyberbeamhq/memoric/issues
- **Discussions:** https://github.com/cyberbeamhq/memoric/discussions
- **Email:** support@memoric.dev
