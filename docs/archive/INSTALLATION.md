# Memoric Installation Guide

This guide covers all installation methods for Memoric.

## Requirements

- Python 3.9 or higher
- PostgreSQL 12+ (for production use)
- pip or poetry for package management

## Installation Methods

### 1. Install from PyPI (Recommended - Coming Soon)

Once published to PyPI, you'll be able to install with:

```bash
pip install memoric
```

### 2. Install from Source

#### Clone and Install in Development Mode

```bash
# Clone the repository
git clone https://github.com/cyberbeamhq/memoric.git
cd memoric

# Install in development mode (editable)
pip install -e .
```

This installs Memoric in "editable" mode, meaning changes to the source code are immediately reflected without reinstalling.

#### Build and Install from Wheel

```bash
# Clone the repository
git clone https://github.com/cyberbeamhq/memoric.git
cd memoric

# Build the distribution packages
python -m build

# Install the wheel
pip install dist/memoric-0.1.0-py3-none-any.whl
```

### 3. Install from GitHub (Latest Development Version)

```bash
pip install git+https://github.com/cyberbeamhq/memoric.git
```

## Optional Dependencies

Memoric comes with optional extras for additional functionality:

### LLM Integration

For OpenAI and other LLM integrations:

```bash
pip install memoric[llm]
```

Includes:
- `openai>=1.0.0`

### Metrics and Monitoring

For Prometheus metrics support:

```bash
pip install memoric[metrics]
```

Includes:
- `prometheus-client>=0.19.0`

### Development Tools

For development, testing, and code quality:

```bash
pip install memoric[dev]
```

Includes:
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `black` - Code formatter
- `flake8` - Linter
- `mypy` - Type checker
- `build` - Build tool

### All Optional Dependencies

To install everything:

```bash
pip install memoric[all]
```

## Core Dependencies

Memoric automatically installs these core dependencies:

- **pyyaml** (>=6.0.1) - Configuration file parsing
- **pydantic** (>=2.8.0) - Data validation
- **pydantic[email]** (>=2.8.0) - Email validation
- **click** (>=8.1.7) - CLI framework
- **rich** (>=13.7.1) - Terminal formatting
- **sqlalchemy** (>=2.0) - Database ORM
- **fastapi** (>=0.112.0) - Web API framework
- **uvicorn** (>=0.30.0) - ASGI server
- **cryptography** (>=41.0.0) - Encryption
- **pyjwt** (>=2.8.0) - JWT authentication
- **passlib** (>=1.7.4) - Password hashing
- **psutil** (>=5.9.0) - System monitoring
- **email-validator** (>=2.0.0) - Email validation

## Database Setup

### PostgreSQL (Recommended for Production)

1. Install PostgreSQL 12 or higher

2. Create a database and user:

```sql
CREATE DATABASE memoric_db;
CREATE USER memoric WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE memoric_db TO memoric;
```

3. Set environment variables or configure in your code:

```bash
export DATABASE_URL="postgresql://memoric:your_password@localhost:5432/memoric_db"
```

### SQLite (For Development/Testing)

SQLite works out of the box with no setup:

```python
from memoric import Memoric

# SQLite in-memory database
mem = Memoric(dsn="sqlite:///:memory:")

# SQLite file-based database
mem = Memoric(dsn="sqlite:///memoric.db")
```

## Environment Variables

### Required for Production

```bash
# JWT Secret for authentication (generate with: python -c 'import secrets; print(secrets.token_hex(64))')
export MEMORIC_JWT_SECRET="your-secret-key-here"

# Encryption key for data at rest (generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
export MEMORIC_ENCRYPTION_KEY="your-encryption-key-here"
```

### Optional

```bash
# Database connection
export DATABASE_URL="postgresql://user:password@localhost:5432/memoric_db"

# API configuration
export MEMORIC_HOST="0.0.0.0"
export MEMORIC_PORT="8000"

# Feature flags
export MEMORIC_ENABLE_AUTH="true"
export MEMORIC_ENABLE_AUDIT="true"
export MEMORIC_ENABLE_METRICS="true"

# OpenAI API key (if using LLM features)
export OPENAI_API_KEY="your-openai-api-key"
```

## Verifying Installation

Test your installation with:

```python
import memoric
from memoric import Memoric
from memoric.api import create_app

print(f"✅ Memoric installed successfully!")
print(f"✅ Version: 0.1.0")

# Test database connection
mem = Memoric(dsn="sqlite:///:memory:")
mem.save(user_id="test", content="Hello, Memoric!")
memories = mem.retrieve(user_id="test")
print(f"✅ Database working! Retrieved {len(memories)} memory")

# Test API
app = create_app(enable_auth=False)
print(f"✅ API ready!")
```

## Quick Start

After installation, create a simple script:

```python
from memoric import Memoric

# Initialize with SQLite for testing
mem = Memoric(dsn="sqlite:///memoric.db")

# Save a memory
memory_id = mem.save(
    user_id="alice",
    content="Meeting notes from Q4 planning session",
    thread_id="planning-2024",
    metadata={"topic": "planning", "importance": "high"}
)

# Retrieve memories
memories = mem.retrieve(
    user_id="alice",
    thread_id="planning-2024",
    top_k=10
)

print(f"Stored {memory_id}, retrieved {len(memories)} memories")
```

## Running the API Server

### Development Mode

```bash
# Using uvicorn directly
uvicorn memoric.api.server:app --reload --host 0.0.0.0 --port 8000

# Or using the API in code
from memoric.api import create_app
import uvicorn

app = create_app(
    enable_auth=True,
    enable_audit=True,
    enable_metrics=True
)

uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Production Mode

```bash
# Using gunicorn with uvicorn workers
pip install gunicorn

gunicorn memoric.api.server:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
```

## Docker Installation (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install memoric
RUN pip install -e .

# Expose API port
EXPOSE 8000

# Run the API server
CMD ["uvicorn", "memoric.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t memoric:latest .
docker run -p 8000:8000 \
    -e MEMORIC_JWT_SECRET="your-secret" \
    -e MEMORIC_ENCRYPTION_KEY="your-key" \
    -e DATABASE_URL="postgresql://..." \
    memoric:latest
```

## Troubleshooting

### Import Errors

If you see import errors:

```bash
# Reinstall with all dependencies
pip install --force-reinstall memoric

# Or install missing dependencies manually
pip install email-validator psutil
```

### Database Connection Issues

```python
# Test database connection
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:password@localhost:5432/memoric_db")
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("✅ Database connection successful!")
```

### Authentication Issues

```bash
# Generate new secrets
python -c "import secrets; print('JWT_SECRET:', secrets.token_hex(64))"
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY:', Fernet.generate_key().decode())"
```

## Upgrading

### From Git

```bash
cd memoric
git pull origin main
pip install -e . --upgrade
```

### From PyPI (When Available)

```bash
pip install --upgrade memoric
```

## Uninstalling

```bash
pip uninstall memoric
```

## Next Steps

- Read the [Authentication Guide](AUTHENTICATION_GUIDE.md) for securing your API
- Check the [Audit Logging Guide](AUDIT_LOGGING_COMPLETE.md) for compliance features
- Review the [Security Implementation](SECURITY_IMPLEMENTATION_COMPLETE.md) for production deployment
- Explore the `examples/` directory for sample code

## Support

- **Documentation**: See the `docs/` directory and `*.md` files in the repository
- **Issues**: https://github.com/cyberbeamhq/memoric/issues
- **Discussions**: https://github.com/cyberbeamhq/memoric/discussions

## License

Apache 2.0 - See [LICENSE](LICENSE) file for details.
