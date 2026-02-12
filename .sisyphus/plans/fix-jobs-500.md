# Fix GET /api/jobs 500 Error

## TL;DR

> **Quick Summary**: Fix 500 error / 51-second timeout on `GET /api/jobs` caused by asyncpg prepared statement caching incompatibility with Supabase PGBouncer transaction-mode pooler.
> 
> **Deliverables**: 
> - One-line fix in `app/services/storage.py`
> 
> **Estimated Effort**: Quick (1 minute)
> **Parallel Execution**: NO - single task
> **Critical Path**: Task 1 only

---

## Context

### Original Request
User reported: `GET /api/jobs 500 51626.7ms` — the jobs endpoint returns 500 after ~51 seconds.

### Root Cause
The project connects to Supabase via **PGBouncer transaction-mode pooler** (`pooler.supabase.com:5432`). asyncpg caches prepared statements by default (`statement_cache_size=16`), which is **incompatible** with PGBouncer in transaction mode. PGBouncer routes successive queries to different PostgreSQL backends, but cached prepared statements are per-backend — causing hangs/timeouts when asyncpg tries to reuse a statement on a different backend.

---

## Work Objectives

### Core Objective
Add `statement_cache_size=0` to `asyncpg.create_pool()` to disable prepared statement caching.

### Must Have
- `statement_cache_size=0` parameter in `asyncpg.create_pool()` call

### Must NOT Have (Guardrails)
- ❌ DO NOT change any other pool parameters (min_size, max_size)
- ❌ DO NOT change the connection string or database URL
- ❌ DO NOT modify any other files

---

## Verification Strategy

### Agent-Executed QA Scenarios

```
Scenario: Jobs endpoint returns 200
  Tool: Bash (curl)
  Preconditions: Server running on localhost:8000
  Steps:
    1. Start server: uvicorn app.main:app --port 8000
    2. curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/jobs?page=1&per_page=20
    3. Assert: HTTP status is 200 (not 500)
    4. Assert: Response time < 5 seconds (not 51 seconds)
  Expected Result: 200 OK with job data
  Evidence: curl output

Scenario: Health endpoint works
  Tool: Bash (curl)
  Steps:
    1. curl -s http://localhost:8000/api/health
    2. Assert: HTTP status is 200
  Expected Result: Health check passes

Scenario: Stats endpoint works
  Tool: Bash (curl)
  Steps:
    1. curl -s http://localhost:8000/api/stats
    2. Assert: HTTP status is 200
  Expected Result: Stats returned
```

---

## TODOs

- [x] 1. Add `statement_cache_size=0` to asyncpg pool initialization

  **What to do**:
  - Edit `app/services/storage.py`, method `init_pool()` (line 83-86)
  - Change:
    ```python
    self._pool = await asyncpg.create_pool(
        self._database_url, min_size=2, max_size=10,
    )
    ```
  - To:
    ```python
    self._pool = await asyncpg.create_pool(
        self._database_url,
        min_size=2,
        max_size=10,
        statement_cache_size=0,
    )
    ```

  **Must NOT do**:
  - Change any other parameters or methods
  - Modify any other files

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (single task)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `app/services/storage.py:83-86` — The `init_pool()` method with `asyncpg.create_pool()` call
  - Supabase docs: PGBouncer requires `statement_cache_size=0` for asyncpg
  - asyncpg docs: `statement_cache_size` controls prepared statement caching

  **Acceptance Criteria**:
  - [ ] `statement_cache_size=0` present in `asyncpg.create_pool()` call
  - [ ] `GET /api/jobs?page=1&per_page=20` returns 200 (not 500)
  - [ ] Response time < 5 seconds (not 51 seconds)
  - [ ] `GET /api/health` returns 200
  - [ ] `GET /api/stats` returns 200

  **Commit**: YES
  - Message: `fix(storage): disable asyncpg statement caching for Supabase PGBouncer compatibility`
  - Files: `app/services/storage.py`

---

## Success Criteria

### Verification Commands
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/jobs?page=1&per_page=20  # Expected: 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health                    # Expected: 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/stats                     # Expected: 200
```

### Final Checklist
- [ ] `statement_cache_size=0` added to pool creation
- [ ] Jobs endpoint returns 200 with data
- [ ] No 51-second timeouts
