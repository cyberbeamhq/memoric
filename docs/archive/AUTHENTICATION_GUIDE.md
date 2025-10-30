# Authentication & Authorization Guide

**Version**: 0.1.0
**Date**: October 29, 2025

## Overview

Memoric now includes comprehensive JWT-based authentication and role-based access control (RBAC) to secure your memory management system. This guide covers setup, usage, and best practices.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication Flow](#authentication-flow)
3. [API Endpoints](#api-endpoints)
4. [Roles & Permissions](#roles--permissions)
5. [Configuration](#configuration)
6. [Code Examples](#code-examples)
7. [Security Best Practices](#security-best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Set Environment Variables

```bash
# Generate JWT secret key
python -c "from memoric.utils.auth import AuthService; print(AuthService.generate_secret_key())"

# Set environment variable
export MEMORIC_JWT_SECRET="your_generated_secret_key_here"

# Optional: Set encryption key for data at rest
python -c "from memoric.utils.encryption import generate_encryption_key; print(generate_encryption_key())"
export MEMORIC_ENCRYPTION_KEY="your_encryption_key_here"
```

### 2. Start API Server with Authentication

```python
from memoric.api.server import create_app
import uvicorn

# Create app with authentication enabled
app = create_app(enable_auth=True)

# Run server
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3. Register a User

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "SecurePassword123"
  }'
```

### 4. Login and Get Token

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "SecurePassword123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "roles": ["user"]
  }
}
```

### 5. Make Authenticated Requests

```bash
export TOKEN="your_access_token_here"

# Create a memory
curl -X POST "http://localhost:8000/memories" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Important meeting notes",
    "metadata": {"topic": "meetings"}
  }'

# List memories
curl -X GET "http://localhost:8000/memories" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Authentication Flow

```
┌──────────┐                                    ┌──────────┐
│  Client  │                                    │   API    │
└────┬─────┘                                    └────┬─────┘
     │                                                │
     │  1. POST /auth/register                       │
     │  {username, email, password}                  │
     ├──────────────────────────────────────────────>│
     │                                                │
     │  2. 201 Created                                │
     │  {user profile}                                │
     │<──────────────────────────────────────────────┤
     │                                                │
     │  3. POST /auth/login                           │
     │  {username, password}                          │
     ├──────────────────────────────────────────────>│
     │                                                │
     │  4. 200 OK                                     │
     │  {access_token, user}                          │
     │<──────────────────────────────────────────────┤
     │                                                │
     │  5. POST /memories                             │
     │  Authorization: Bearer <token>                 │
     ├──────────────────────────────────────────────>│
     │                                                │
     │  6. Verify JWT token                           │
     │  7. Check permissions                          │
     │  8. Execute operation                          │
     │                                                │
     │  9. 200 OK                                     │
     │  {memory_id}                                   │
     │<──────────────────────────────────────────────┤
```

---

## API Endpoints

### Authentication Endpoints

#### Register New User

```http
POST /auth/register
Content-Type: application/json

{
  "username": "alice",
  "email": "alice@example.com",
  "password": "SecurePass123",
  "full_name": "Alice Smith",
  "namespace": "company_a"
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "full_name": "Alice Smith",
  "namespace": "company_a",
  "roles": ["user"],
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-10-29T10:00:00Z"
}
```

#### Login

```http
POST /auth/login
Content-Type: application/json

{
  "username": "alice",
  "password": "SecurePass123"
}
```

**Response**: `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "roles": ["user"]
  }
}
```

#### Get Current User Profile

```http
GET /auth/me
Authorization: Bearer <token>
```

**Response**: `200 OK`
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "full_name": "Alice Smith",
  "roles": ["user"],
  "is_active": true,
  "last_login_at": "2025-10-29T10:00:00Z"
}
```

#### Change Password

```http
POST /auth/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
  "old_password": "SecurePass123",
  "new_password": "NewSecurePass456"
}
```

**Response**: `200 OK`
```json
{
  "message": "Password changed successfully"
}
```

#### Logout

```http
POST /auth/logout
Authorization: Bearer <token>
```

**Response**: `200 OK`
```json
{
  "message": "Logged out successfully",
  "note": "Discard your token on the client side"
}
```

### Protected Endpoints

All memory and cluster endpoints require authentication when `enable_auth=True`.

#### Create Memory

```http
POST /memories
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Meeting notes from Q4 planning",
  "thread_id": "thread_123",
  "metadata": {"topic": "planning", "priority": "high"}
}
```

#### List Memories

```http
GET /memories?thread_id=thread_123&top_k=20
Authorization: Bearer <token>
```

#### List Clusters

```http
GET /clusters?topic=planning&limit=50
Authorization: Bearer <token>
```

#### Run Policies (Admin Only)

```http
POST /policies/run
Authorization: Bearer <token>
```

---

## Roles & Permissions

### Roles

| Role | Description | Default Permissions |
|------|-------------|---------------------|
| **ADMIN** | Full system access | All permissions (`admin:*`) |
| **USER** | Standard user | Read/write own data, execute policies |
| **READ_ONLY** | Read-only access | Read own data only |

### Permissions

| Permission | Description | Required Role |
|------------|-------------|---------------|
| `memories:read` | Read memories | USER, ADMIN |
| `memories:write` | Create/update memories | USER, ADMIN |
| `memories:delete` | Delete memories | USER, ADMIN |
| `clusters:read` | Read clusters | USER, ADMIN |
| `clusters:write` | Manage clusters | USER, ADMIN |
| `policies:execute` | Run policies | ADMIN only |
| `admin:*` | Administrative access | ADMIN only |

### Permission Enforcement

```python
from memoric.utils.auth import AuthService, Role, Permission

auth = AuthService(secret_key="your_secret")

# Create token with specific roles
token = auth.create_token(
    user_id="user123",
    roles=[Role.USER]
)

# Verify and check permissions
payload = auth.verify_token(token)

# Check permission
if auth.has_permission(payload, Permission.MEMORIES_WRITE):
    # Allow operation
    pass

# Check resource ownership
if auth.check_resource_access(payload, memory["user_id"]):
    # User owns this memory
    pass
```

---

## Configuration

### Environment Variables

```bash
# Required for authentication
export MEMORIC_JWT_SECRET="your_secret_key"

# Optional: Token expiration (seconds)
export MEMORIC_JWT_EXPIRY=3600

# Optional: Encryption at rest
export MEMORIC_ENCRYPTION_KEY="your_encryption_key"

# Optional: Database
export DATABASE_URL="postgresql://user:pass@host:5432/memoric"
```

### Application Configuration

```python
from memoric.api.server import create_app

app = create_app(
    enable_auth=True,           # Enable JWT authentication
    enable_cors=True,           # Enable CORS
    allowed_origins=[           # Allowed CORS origins
        "https://yourdomain.com",
        "http://localhost:3000"
    ],
    enable_metrics=True         # Enable Prometheus metrics
)
```

### Config File (config.yaml)

```yaml
security:
  jwt_secret: "${MEMORIC_JWT_SECRET}"
  token_expiry_seconds: 3600

  # Password policy
  min_password_length: 8
  require_uppercase: true
  require_lowercase: true
  require_digit: true
  require_special_char: false

privacy:
  # Enable encryption at rest
  encrypt_content: true
  encryption_key: "${MEMORIC_ENCRYPTION_KEY}"

  # User isolation
  user_isolation: true
  allow_global_scope: false

  # Multi-tenancy
  require_namespace: true

cors:
  enabled: true
  allowed_origins:
    - "https://yourdomain.com"
    - "http://localhost:3000"
  allow_credentials: true
  allowed_methods: ["GET", "POST", "PUT", "DELETE"]
```

---

## Code Examples

### Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

class MemoricClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None

    def register(self, username: str, email: str, password: str):
        """Register a new user."""
        response = requests.post(
            f"{self.base_url}/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password
            }
        )
        response.raise_for_status()
        return response.json()

    def login(self, username: str, password: str):
        """Login and store token."""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return data

    def create_memory(self, content: str, metadata: dict = None):
        """Create a memory."""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/memories",
            json={"content": content, "metadata": metadata},
            headers=headers
        )
        response.raise_for_status()
        return response.json()

    def list_memories(self, thread_id: str = None, top_k: int = 20):
        """List memories."""
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"top_k": top_k}
        if thread_id:
            params["thread_id"] = thread_id

        response = requests.get(
            f"{self.base_url}/memories",
            params=params,
            headers=headers
        )
        response.raise_for_status()
        return response.json()

# Usage
client = MemoricClient(BASE_URL)

# Register
client.register("alice", "alice@example.com", "SecurePass123")

# Login
client.login("alice", "SecurePass123")

# Create memory
memory_id = client.create_memory(
    "Meeting with Bob about Q4 goals",
    metadata={"topic": "meetings", "priority": "high"}
)

# List memories
memories = client.list_memories(top_k=10)
```

### JavaScript/TypeScript Client

```typescript
class MemoricClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async register(username: string, email: string, password: string) {
    const response = await fetch(`${this.baseUrl}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });
    return response.json();
  }

  async login(username: string, password: string) {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    this.token = data.access_token;

    // Store token in localStorage
    localStorage.setItem('memoric_token', this.token);

    return data;
  }

  async createMemory(content: string, metadata?: object) {
    const response = await fetch(`${this.baseUrl}/memories`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ content, metadata })
    });
    return response.json();
  }

  async listMemories(threadId?: string, topK: number = 20) {
    const params = new URLSearchParams({ top_k: topK.toString() });
    if (threadId) params.append('thread_id', threadId);

    const response = await fetch(
      `${this.baseUrl}/memories?${params}`,
      {
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    );
    return response.json();
  }

  logout() {
    this.token = null;
    localStorage.removeItem('memoric_token');
  }
}

// Usage
const client = new MemoricClient('http://localhost:8000');

// Register and login
await client.register('alice', 'alice@example.com', 'SecurePass123');
await client.login('alice', 'SecurePass123');

// Create memory
const memory = await client.createMemory(
  'Important meeting notes',
  { topic: 'planning' }
);

// List memories
const memories = await client.listMemories();
```

---

## Security Best Practices

### 1. Strong Secret Keys

```bash
# Generate cryptographically secure keys
python -c "from memoric.utils.auth import AuthService; print(AuthService.generate_secret_key())"

# NEVER use default or weak secrets in production
# NEVER commit secrets to version control
```

### 2. HTTPS Only in Production

```python
# Use HTTPS in production
if not app.debug:
    @app.middleware("http")
    async def https_only(request, call_next):
        if request.url.scheme != "https":
            return Response("HTTPS required", status_code=400)
        return await call_next(request)
```

### 3. Token Storage

**Client-side best practices**:
- ✅ Store in memory for SPAs
- ✅ Use httpOnly cookies for web apps
- ❌ Don't store in localStorage (XSS vulnerable)
- ❌ Don't store in sessionStorage

### 4. Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- Consider requiring special characters

### 5. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(...):
    ...
```

### 6. Token Expiration

- Set reasonable token expiry (default: 1 hour)
- Implement refresh tokens for long-lived sessions
- Force re-authentication for sensitive operations

### 7. Audit Logging

Log all authentication events:
- Successful logins
- Failed login attempts
- Password changes
- Permission denials

---

## Troubleshooting

### "Missing authentication credentials"

**Problem**: Request missing Authorization header

**Solution**:
```bash
# Include Authorization header
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/memories
```

### "Token has expired"

**Problem**: JWT token expired (default: 1 hour)

**Solution**: Login again to get a new token

### "Invalid authentication credentials"

**Problem**: Token is malformed or signed with wrong key

**Solutions**:
- Check `MEMORIC_JWT_SECRET` is set correctly
- Ensure token hasn't been modified
- Login again to get fresh token

### "Insufficient permissions"

**Problem**: User role lacks required permission

**Solution**: Contact admin to upgrade role or check endpoint requirements

### "Can only access your own memories"

**Problem**: Regular users trying to access other users' data

**Solution**: Only admins can access cross-user data

---

## Next Steps

1. **Set Up Production Deployment**:
   - Use HTTPS
   - Set strong JWT secret
   - Enable encryption at rest
   - Configure CORS properly
   - Set up monitoring

2. **Implement Refresh Tokens** (Optional):
   - Extend token lifetime
   - Add token rotation
   - Implement blacklist

3. **Add OAuth/SSO** (Optional):
   - Google OAuth
   - GitHub OAuth
   - SAML for enterprise

4. **Enable Audit Logging**:
   - Track all authentication events
   - Monitor failed login attempts
   - Alert on suspicious activity

5. **Add Multi-Factor Authentication** (Optional):
   - TOTP (Google Authenticator)
   - SMS verification
   - Email verification

---

**For questions or issues, see:**
- [Security Implementation Status](SECURITY_IMPLEMENTATION_STATUS.md)
- [Production Readiness Assessment](PRODUCTION_READINESS_ASSESSMENT.md)
- GitHub Issues: https://github.com/cyberbeamhq/memoric/issues
