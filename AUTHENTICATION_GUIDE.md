# Memoric Authentication & Security Guide

This guide covers authentication, authorization, and security features in Memoric.

---

## Overview

Memoric provides enterprise-grade security features:

- **JWT Authentication** - Token-based authentication (HS256)
- **Role-Based Access Control (RBAC)** - User roles and permissions
- **API Key Management** - Alternative authentication method
- **Audit Logging** - Track all security events
- **Encryption at Rest** - Optional content encryption
- **User Isolation** - Strict data separation between users

---

## Quick Start: Secure API

```python
from memoric.api import create_app
import uvicorn

# Create API with authentication enabled
app = create_app(
    enable_auth=True,      # Enable JWT authentication
    enable_audit=True,     # Enable audit logging
)

# Run server
uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Important:** Set your JWT secret key:

```bash
export MEMORIC_JWT_SECRET="your-secret-key-here"
```

Generate a secure secret:

```bash
python -c 'import secrets; print(secrets.token_hex(64))'
```

---

## User Management

### Creating Users

```python
from memoric.api import create_app

app = create_app(enable_auth=True)
user_manager = app.state.user_manager

# Create admin user
user_manager.create_user(
    username="admin",
    password="secure_password_123",
    email="admin@example.com",
    roles=["admin"]
)

# Create regular user
user_manager.create_user(
    username="user1",
    password="user_password_456",
    email="user1@example.com",
    roles=["user"]
)
```

### User Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full access - can read/write all memories, execute policies, manage users |
| **user** | Standard access - can read/write own memories only |
| **readonly** | Read-only access - can retrieve own memories, cannot create/modify |

---

## Authentication Methods

### Method 1: JWT Tokens (Recommended)

1. **Login to get token:**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user1", "password": "user_password_456"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

2. **Use token in requests:**

```bash
curl http://localhost:8000/memories \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### Method 2: API Keys

1. **Generate API key:**

```python
api_key = user_manager.create_api_key(
    user_id="user-123",
    name="production-api-key",
    expires_days=90
)
print(f"API Key: {api_key}")
```

2. **Use in requests:**

```bash
curl http://localhost:8000/memories \
  -H "X-API-Key: your-api-key-here"
```

---

## Token Management

### Token Refresh

JWT tokens expire after 1 hour by default. Use refresh tokens for long-lived sessions:

```bash
# Get refresh token during login
curl -X POST http://localhost:8000/auth/login \
  -d '{"username": "user1", "password": "password"}'

# Use refresh token to get new access token
curl -X POST http://localhost:8000/auth/refresh \
  -H "Authorization: Bearer <refresh_token>"
```

### Token Revocation

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

---

## Encryption at Rest

Enable content encryption for sensitive data:

1. **Generate encryption key:**

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

2. **Set environment variable:**

```bash
export MEMORIC_ENCRYPTION_KEY="your-encryption-key-here"
```

3. **Enable in configuration:**

```yaml
privacy:
  encrypt_content: true
```

4. **Use in code:**

```python
from memoric.db import PostgresConnector

db = PostgresConnector(
    dsn="postgresql://...",
    encryption_key=os.getenv("MEMORIC_ENCRYPTION_KEY"),
    encrypt_content=True
)
```

**Note:** Encryption/decryption happens automatically. Content is encrypted before storage and decrypted on retrieval.

---

## User Isolation

Memoric enforces strict user isolation by default:

```yaml
privacy:
  user_isolation: true           # Enforce user data separation
  allow_global_scope: false      # Prevent cross-user queries
```

Users can **only access their own memories** unless they have admin role.

---

## Audit Logging

Track all security events:

```python
app = create_app(
    enable_auth=True,
    enable_audit=True
)
```

### Audited Events

- User login/logout
- Failed authentication attempts
- Memory creation/retrieval
- Policy execution
- Authorization failures
- API key usage

### Querying Audit Logs

```bash
# Get recent audit logs (admin only)
curl http://localhost:8000/audit/logs?limit=50 \
  -H "Authorization: Bearer <admin_token>"
```

---

## Security Best Practices

### Production Checklist

- [ ] Set strong `MEMORIC_JWT_SECRET` (minimum 64 characters)
- [ ] Enable HTTPS (use nginx/Caddy reverse proxy)
- [ ] Set secure `MEMORIC_ENCRYPTION_KEY` if using encryption
- [ ] Use PostgreSQL with SSL connections
- [ ] Enable audit logging
- [ ] Set up rate limiting at reverse proxy level
- [ ] Regularly rotate API keys
- [ ] Review audit logs for suspicious activity
- [ ] Use strong password policies
- [ ] Restrict CORS origins to your domains

### Environment Variables

```bash
# Required for production
export MEMORIC_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(64))')"

# Optional but recommended
export MEMORIC_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
export MEMORIC_DB_PASSWORD="strong_db_password"
export MEMORIC_CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

### Configuration

```yaml
# config.yaml
privacy:
  user_isolation: true
  encrypt_content: true

observability:
  logging:
    enabled: true
    level: INFO

  metrics:
    enabled: true
```

---

## CORS Configuration

Control which domains can access your API:

```python
app = create_app(
    enable_auth=True,
    enable_cors=True,
    allowed_origins=[
        "https://yourdomain.com",
        "https://app.yourdomain.com",
    ]
)
```

---

## Health Checks

Memoric provides Kubernetes-ready health endpoints:

- **`/health`** - Liveness probe (is service running?)
- **`/ready`** - Readiness probe (can handle traffic?)
- **`/health/detailed`** - Full diagnostic info

These endpoints **do not require authentication** for K8s to use them.

---

## Example: Secure Production Setup

```python
import os
from memoric.api import create_app
import uvicorn

# Ensure secrets are set
assert os.getenv("MEMORIC_JWT_SECRET"), "Set MEMORIC_JWT_SECRET"
assert os.getenv("MEMORIC_ENCRYPTION_KEY"), "Set MEMORIC_ENCRYPTION_KEY"

# Create secure API
app = create_app(
    enable_auth=True,
    enable_audit=True,
    enable_cors=True,
    enable_metrics=True,
    allowed_origins=[
        os.getenv("CORS_ORIGIN", "https://yourdomain.com")
    ],
)

# Create admin user (first time only)
if os.getenv("CREATE_ADMIN"):
    user_manager = app.state.user_manager
    user_manager.create_user(
        username=os.getenv("ADMIN_USERNAME"),
        password=os.getenv("ADMIN_PASSWORD"),
        email=os.getenv("ADMIN_EMAIL"),
        roles=["admin"]
    )

# Run with HTTPS (use nginx/Caddy reverse proxy)
uvicorn.run(
    app,
    host="127.0.0.1",  # Bind to localhost, use reverse proxy
    port=8000,
    log_level="info"
)
```

---

## Compliance

Memoric's security features support compliance with:

- **SOC 2** - Audit logging, access controls
- **GDPR** - Data encryption, user isolation, audit trails
- **HIPAA** - Encryption at rest, access logging, user authentication
- **PCI-DSS** - Secure credential storage, audit logging

---

## Troubleshooting

### Authentication Errors

**"Invalid credentials"**
- Verify username and password
- Check user exists: `user_manager.get_user(username="user1")`

**"Token expired"**
- Use refresh token to get new access token
- Adjust token expiry in AuthService if needed

**"Insufficient permissions"**
- Check user roles
- Ensure endpoint allows user's role

### Encryption Errors

**"Decryption failed"**
- Ensure MEMORIC_ENCRYPTION_KEY matches key used for encryption
- Key must be consistent across all instances

---

## API Reference

See `memoric/api/server.py` for full API specification and `memoric/utils/auth.py` for authentication implementation details.

---

## Support

- **Security Issues:** Report privately to security@memoric.dev
- **General Questions:** https://github.com/cyberbeamhq/memoric/discussions
- **Bug Reports:** https://github.com/cyberbeamhq/memoric/issues
