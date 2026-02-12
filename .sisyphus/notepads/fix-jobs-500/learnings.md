# Learnings from fix-jobs-500

## Problem
GET /api/jobs returned 500 after ~51 seconds timeout.

## Root Cause
asyncpg's prepared statement caching (`statement_cache_size=16` by default) is incompatible with Supabase's PGBouncer transaction-mode pooler. When PGBouncer routes queries to different PostgreSQL backends, asyncpg tries to reuse cached prepared statements that don't exist on the new backend, causing hangs/timeouts.

## Solution
Add `statement_cache_size=0` to `asyncpg.create_pool()` to disable prepared statement caching.

```python
self._pool = await asyncpg.create_pool(
    self._database_url,
    min_size=2,
    max_size=10,
    statement_cache_size=0,  # Required for PGBouncer transaction mode
)
```

## Reference
- Supabase connection string: `pooler.supabase.com:5432` = transaction mode PGBouncer
- asyncpg docs: `statement_cache_size` controls prepared statement caching
- Standard practice: Always use `statement_cache_size=0` with PGBouncer transaction mode

## Files Modified
- `app/services/storage.py` (line 88)

## Commit
`fb8274f` - fix(storage): disable asyncpg statement caching for Supabase PGBouncer compatibility
