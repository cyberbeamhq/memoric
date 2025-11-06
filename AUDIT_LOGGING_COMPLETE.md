# Audit Logging - Complete Documentation

Memoric includes comprehensive audit logging for security, compliance, and debugging.

---

## Overview

The audit logging system tracks:
- Authentication events (login, logout, failures)
- Authorization events (permission checks, access denials)
- Memory operations (create, read, update, delete)
- Policy execution (migrations, trimming, summarization)
- System events (startup, shutdown, errors)

**Implementation:** `memoric/utils/audit_logger.py` and `memoric/db/audit_schema.py`

---

## Quick Start

```python
from memoric.api import create_app

# Enable audit logging
app = create_app(enable_audit=True)
```

---

## Audit Event Types

All event types are defined in `memoric/db/audit_schema.py`:

```python
class AuditEventType:
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"

    # Authorization
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"

    # Memory operations
    MEMORY_CREATED = "memory_created"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_DELETED = "memory_deleted"

    # Cluster operations
    CLUSTER_CREATED = "cluster_created"
    CLUSTER_RETRIEVED = "cluster_retrieved"

    # Policy operations
    POLICY_EXECUTED = "policy_executed"
    POLICY_FAILED = "policy_failed"
```

---

## Audit Log Schema

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    user_id VARCHAR(128),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Resource info
    resource_type VARCHAR(64),
    resource_id VARCHAR(128),

    -- Action details
    action VARCHAR(64),
    success BOOLEAN,
    error_message TEXT,

    -- Context
    ip_address VARCHAR(45),
    user_agent TEXT,

    -- State tracking
    before_state JSONB,
    after_state JSONB,
    metadata JSONB,

    -- Security
    severity VARCHAR(20),
    tags TEXT[]
);
```

---

## Usage Examples

### Querying Audit Logs

```bash
# Get recent logs (admin only)
curl http://localhost:8000/audit/logs?limit=100 \
  -H "Authorization: Bearer <admin_token>"

# Filter by user
curl "http://localhost:8000/audit/logs?user_id=user-123&limit=50" \
  -H "Authorization: Bearer <admin_token>"

# Filter by event type
curl "http://localhost:8000/audit/logs?event_type=login_failed" \
  -H "Authorization: Bearer <admin_token>"
```

### Programmatic Access

```python
from memoric.api import create_app

app = create_app(enable_audit=True)
audit_logger = app.state.audit_logger

# Get recent failed logins
failed_logins = audit_logger.query_logs(
    event_type="login_failed",
    limit=50
)

# Get user's activity
user_activity = audit_logger.query_logs(
    user_id="user-123",
    limit=100
)
```

---

## Compliance Support

### SOC 2 Requirements

✅ Access logging - All API requests logged
✅ Authentication tracking - Login/logout events
✅ Change tracking - Before/after states captured
✅ Failure logging - All errors recorded

### GDPR Requirements

✅ Data access audit - Who accessed what data
✅ Deletion tracking - Audit trail of deletions
✅ Consent tracking - Can log consent events

### HIPAA Requirements

✅ Access logs - PHI access tracked
✅ Audit trail - All operations logged
✅ Security events - Failed auth attempts tracked

---

## Log Retention

Configure retention in your database:

```sql
-- Example: Delete logs older than 90 days
DELETE FROM audit_logs
WHERE timestamp < NOW() - INTERVAL '90 days';
```

Or use a cron job:

```bash
# /etc/cron.daily/cleanup-audit-logs
psql -d memoric -c "DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '90 days';"
```

---

## Monitoring & Alerts

### Failed Login Monitoring

```python
# Example: Alert on multiple failed logins
failed_logins = audit_logger.query_logs(
    event_type="login_failed",
    limit=10,
    since=datetime.now() - timedelta(minutes=5)
)

if len(failed_logins) >= 5:
    send_alert("Multiple failed login attempts detected")
```

### Suspicious Activity Detection

```python
# Example: Detect unusual access patterns
recent_access = audit_logger.query_logs(
    user_id="user-123",
    event_type="memory_retrieved",
    limit=100,
    since=datetime.now() - timedelta(hours=1)
)

if len(recent_access) > 50:
    send_alert("Unusual access pattern detected")
```

---

## Performance Considerations

Audit logging adds minimal overhead:
- Asynchronous writes (non-blocking)
- Batched inserts for high-volume scenarios
- Indexed timestamp and user_id columns

For very high-volume systems, consider:
1. Using separate database for audit logs
2. Implementing log rotation
3. Archiving old logs to cold storage

---

## Security Best Practices

1. **Restrict Access** - Only admins should read audit logs
2. **Immutable Logs** - Never delete logs (archive instead)
3. **Monitor Alerts** - Set up alerts for security events
4. **Regular Reviews** - Review logs for suspicious activity
5. **Backup Logs** - Include audit logs in backups

---

## See Also

- `memoric/utils/audit_logger.py` - Implementation
- `memoric/db/audit_schema.py` - Schema definition
- `memoric/api/audit_routes.py` - API endpoints
- [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md) - Security setup
