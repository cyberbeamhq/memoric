# Memoric Database Migration Guide

## Overview

This guide covers database setup, migrations, and best practices for the Memoric memory management system.

## Quick Start

### New Installation

```bash
# 1. Install dependencies
pip install -e .

# 2. Set database URL (PostgreSQL recommended)
export MEMORIC_DATABASE_URL="postgresql://user:pass@localhost/memoric"

# 3. Initialize database with migrations
memoric init-db --migrate

# 4. Verify setup
memoric db-migrate current
# Expected output: 20250115_0001_initial_schema (head)
```

### Development Setup (SQLite)

```bash
# 1. Install dependencies
pip install -e .

# 2. Use SQLite (development only)
export MEMORIC_DATABASE_URL="sqlite:///memoric_dev.db"

# 3. Initialize database
memoric init-db --migrate

# Note: You'll see a warning about SQLite being for dev/testing only
```

## Database Backends

### PostgreSQL (Production)

**Recommended for**:
- Production deployments
- >10,000 memories
- Multi-user systems
- High-query workloads

**Connection String**:
```bash
export MEMORIC_DATABASE_URL="postgresql://user:password@host:5432/database"
```

**Features**:
- Native JSONB support with GIN indexes
- 10-100x faster metadata queries
- Optimized for concurrent access
- Full-text search capabilities

**Performance**:
- Metadata query: ~8ms (with GIN index)
- Thread retrieval: ~5ms
- Cluster lookup: ~2ms

### SQLite (Development)

**Recommended for**:
- Local development
- Testing
- Small datasets (<10k records)
- Single-user demos

**Connection String**:
```bash
export MEMORIC_DATABASE_URL="sqlite:///path/to/memoric.db"
```

**Limitations**:
- Python-level JSON containment (slower)
- No GIN indexes
- Single-writer limitation
- Not recommended for production

**Performance**:
- Metadata query: ~150ms (Python filter)
- Thread retrieval: ~45ms
- Cluster lookup: ~25ms

## Migration Commands

### Check Status

```bash
# View current migration version
memoric db-migrate current

# View all migrations
memoric db-migrate history
```

### Apply Migrations

```bash
# Apply all pending migrations
memoric db-migrate upgrade head

# Apply next migration only
memoric db-migrate upgrade +1

# Upgrade to specific version
memoric db-migrate upgrade <revision_id>
```

### Rollback Migrations

```bash
# Rollback last migration
memoric db-migrate downgrade -1

# Rollback all migrations
memoric db-migrate downgrade base

# Rollback to specific version
memoric db-migrate downgrade <revision_id>
```

### Create Migrations

```bash
# Create new migration (auto-detect changes)
memoric db-migrate revision -m "Add new column"

# View what would be generated (dry-run)
alembic revision --autogenerate -m "Add new column" --sql
```

## Indexes

### PostgreSQL GIN Indexes

**Created On**:
- `memories.metadata` - Fast JSONB containment queries
- `memories.related_threads` - Multi-thread retrieval

**Usage**:
```python
# These queries use GIN indexes:
mem.db.get_memories(where_metadata={"topic": "billing"})
mem.db.get_memories(where_metadata={"priority": "high", "category": "support"})
```

**Performance**: ~10-100x faster than sequential scan

### Composite Indexes

**Created On**:
1. `(user_id, thread_id)` - Thread-specific queries
2. `(user_id, tier)` - Per-user tier statistics
3. `(tier, updated_at)` - Policy execution
4. `(user_id, tier, updated_at)` - User-specific policies

**Usage**:
```python
# These queries use composite indexes:
mem.db.get_memories(user_id="user1", thread_id="thread123")
mem.db.count_by_tier(user_id="user1")
```

### Index Maintenance

```sql
-- Check index usage (PostgreSQL)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Rebuild indexes
REINDEX TABLE memories;

-- Update statistics
ANALYZE memories;
```

## Common Workflows

### Production Deployment

```bash
# 1. Backup existing database
pg_dump memoric > backup_$(date +%Y%m%d).sql

# 2. Pull latest code
git pull origin main

# 3. Check for pending migrations
memoric db-migrate history

# 4. Apply migrations
memoric db-migrate upgrade head

# 5. Verify application
memoric stats

# 6. Monitor logs for errors
tail -f /var/log/memoric.log
```

### Development Workflow

```bash
# 1. Make schema changes in db/postgres_connector.py
# Example: Add new column to memories table

# 2. Generate migration
memoric db-migrate revision -m "Add sentiment column"

# 3. Review generated migration
cat alembic/versions/$(ls -t alembic/versions | head -1)

# 4. Test migration
memoric db-migrate upgrade +1  # Apply
memoric stats                   # Verify
memoric db-migrate downgrade -1 # Rollback test
memoric db-migrate upgrade +1   # Re-apply

# 5. Commit changes
git add alembic/versions/
git commit -m "Add sentiment column migration"
```

### Migrating from SQLite to PostgreSQL

```bash
# 1. Export data from SQLite
sqlite3 memoric.db .dump > dump.sql

# 2. Set up PostgreSQL database
createdb memoric

# 3. Configure Memoric for PostgreSQL
export MEMORIC_DATABASE_URL="postgresql://localhost/memoric"

# 4. Initialize schema with migrations
memoric init-db --migrate

# 5. Import data (may require conversion)
# Note: SQLite dump format differs from PostgreSQL
# You may need to use a tool like pgloader or custom script

# 6. Verify data
memoric stats
```

### Rollback Procedure

```bash
# 1. Identify problematic migration
memoric db-migrate history

# 2. Restore from backup (if available)
pg_restore -d memoric backup_20250115.sql

# 3. Or rollback migration
memoric db-migrate downgrade -1

# 4. Verify database state
memoric stats
memoric db-migrate current

# 5. Fix migration file if needed
# Edit alembic/versions/<migration>.py

# 6. Re-apply
memoric db-migrate upgrade head
```

## Troubleshooting

### "Relation already exists" Error

**Problem**: Tables created without migration tracking

**Solution**:
```bash
# Stamp database with current version
memoric db-migrate stamp head
```

### Slow Queries on SQLite

**Problem**: Using SQLite with large datasets

**Solution**:
```bash
# 1. Migrate to PostgreSQL (recommended)
export MEMORIC_DATABASE_URL="postgresql://localhost/memoric"
memoric init-db --migrate

# 2. Or reduce dataset size
memoric run-policies  # Run trimming policies
```

### Migration Conflicts

**Problem**: Multiple head revisions from parallel development

**Solution**:
```bash
# Merge migration branches
alembic merge heads -m "Merge parallel migrations"
```

### GIN Index Not Used

**Problem**: PostgreSQL not using GIN index for metadata queries

**Diagnosis**:
```sql
EXPLAIN ANALYZE
SELECT * FROM memories
WHERE metadata @> '{"topic": "billing"}';
```

**Solution**:
```sql
-- Update table statistics
ANALYZE memories;

-- Force index usage (testing only)
SET enable_seqscan = OFF;
```

## Performance Optimization

### Query Optimization

```python
# Good: Uses composite index
mem.db.get_memories(user_id="user1", thread_id="thread1")

# Good: Uses GIN index (PostgreSQL)
mem.db.get_memories(where_metadata={"topic": "billing"})

# Slow: Full table scan
mem.db.get_memories()  # No filters
```

### Bulk Operations

```python
# Good: Batch insert
with mem.db.conn.begin():
    for item in items:
        mem.save(...)

# Slow: Individual transactions
for item in items:
    mem.save(...)  # Separate transaction each time
```

### Index Monitoring

```bash
# Check for unused indexes (PostgreSQL)
SELECT
    schemaname || '.' || tablename AS table,
    indexname AS index,
    idx_scan AS scans,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan < 50
ORDER BY pg_relation_size(indexrelid) DESC;

# Drop unused indexes
DROP INDEX IF EXISTS idx_unused;
```

## Configuration

### alembic.ini

```ini
[alembic]
# Migration location
script_location = alembic

# Migration filename template
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

# Timezone
timezone = UTC
```

### Environment Variables

```bash
# Database connection
export MEMORIC_DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Logging level
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
```

## Best Practices

### Migration Guidelines

1. **Always test migrations on staging first**
2. **Include rollback logic in downgrade()**
3. **Make migrations backward compatible when possible**
4. **Add data migrations separately from schema changes**
5. **Document breaking changes in migration docstring**

### Schema Changes

```python
# Good: Backward compatible
def upgrade():
    # Add nullable column
    op.add_column('memories', sa.Column('new_field', sa.String(), nullable=True))

# Bad: Breaking change without migration path
def upgrade():
    # Remove column without deprecation
    op.drop_column('memories', 'important_field')
```

### Production Checklist

- [ ] Backup database before migration
- [ ] Test migration on staging environment
- [ ] Review migration SQL (dry-run)
- [ ] Schedule downtime for large migrations
- [ ] Monitor migration progress
- [ ] Verify application post-migration
- [ ] Keep rollback plan ready
- [ ] Update documentation

## Additional Resources

- **Phase 4 Summary**: [PHASE4_SUMMARY.md](PHASE4_SUMMARY.md)
- **Alembic Documentation**: https://alembic.sqlalchemy.org/
- **PostgreSQL JSONB**: https://www.postgresql.org/docs/current/datatype-json.html
- **SQLAlchemy**: https://docs.sqlalchemy.org/

## Support

For issues or questions:
1. Check [PHASE4_SUMMARY.md](PHASE4_SUMMARY.md) troubleshooting section
2. Review [tests/test_migrations.py](tests/test_migrations.py) for examples
3. Open an issue on GitHub

## Version History

- **Phase 4** (2025-01-15): Alembic integration, GIN indexes, SQLite fallback
- **Phase 3** (2025-01-14): Clustering enhancements, custom scoring
- **Phase 2** (2025-01-13): Multi-tier memory policies
- **Phase 1** (2025-01-12): Initial release
