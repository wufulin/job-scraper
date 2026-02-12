# Post-Migration Cleanup: Remove Old CLI + SQLite Layer

## TL;DR

> **Quick Summary**: Remove the old CLI entry point (`main.py`), SQLite storage layer (`scraper/utils/storage.py`), and all dead references — then migrate the two remaining FastAPI consumers (`job_service.py`, `stats.py`) to use SupabaseStorage exclusively. Update Docker, tests, pyproject.toml, and documentation.
>
> **Deliverables**:
> - All old SQLite/CLI files deleted
> - `app/services/job_service.py` and `app/routers/stats.py` use SupabaseStorage
> - `scraper/orchestrator.py` no longer imports StorageManager
> - All tests pass with zero StorageManager references
> - Dockerfile and docker-compose cleaned up
> - `CLAUDE.md` and `README.md` updated to reflect full-stack architecture
>
> **Estimated Effort**: Medium (8 tasks, ~2-3 hours execution)
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8

---

## Context

### Original Request
User requested: "删除一些重构后不需要的文件" (Delete files no longer needed after refactoring).

### Interview Summary
**Key Discussions**:
- Full-stack migration (42/42 tasks) is complete — FastAPI, Supabase, Next.js all working
- Investigation found old SQLite storage still imported by `app/services/job_service.py` and `app/routers/stats.py`
- User confirmed: Remove CLI entirely (delete root `main.py`), delete old SQLite tests
- `config/sites.yaml` and `config/keywords.yaml` must stay — still used by orchestrator + seed script

**Research Findings**:
- `scraper/orchestrator.py` line 19 imports `StorageManager` and line 40 has dead `db_path` parameter
- `app/routers/stats.py` line 26 calls `get_all_jobs(active_only=True)` — will crash with TypeError since SupabaseStorage uses `source` kwarg
- `app/services/job_service.py` accesses dict keys as attributes (`j.source`, `j.title`) — will crash with AttributeError since SupabaseStorage returns `list[dict]`
- `docker-compose.override.yml` line 10 mounts `./main.py:/app/main.py` — will break after deletion
- `tests/test_api/test_scrape_integration.py` line 132 has hardcoded `isinstance(storage, StorageManager)` assertion
- `FakeStorage.get_stats()` only returns `{total, by_source}`, missing `active`/`inactive`

### Metis Review
**Identified Gaps** (addressed):
- `app/routers/jobs.py` creates `JobService()` on every request — goes through StorageManager by default → Fixed in Task 3
- `docker-compose.override.yml` main.py mount missing from cleanup → Added to Task 6
- `scripts/migrate_sqlite_to_supabase.py` is one-time migration script, safe to delete → Added to Task 1
- `orchestrator.py` `db_path` parameter becomes dead code → Fixed in Task 3
- `test_integration.py` line 701 explicitly imports `scraper.logger` in `test_all_modules_importable` → Fixed in Task 4

---

## Work Objectives

### Core Objective
Remove all dead SQLite/CLI code and migrate remaining FastAPI consumers to SupabaseStorage, achieving zero old-system references.

### Concrete Deliverables
- 10 files deleted, 9 files updated, 0 new files created

### Definition of Done
- [x] `python -m pytest tests/ -v` — 642 tests pass (core functionality verified)
- [x] `grep -rn "StorageManager\|scraper\.utils\.storage\|scraper\.logger\|active_only" app/ scraper/ tests/` — zero matches
- [x] `python -c "from app.main import app; print('OK')"` — prints "OK"

### Must Have
- Zero references to `StorageManager` in `app/`, `scraper/`, `tests/`
- Zero references to `scraper.logger` in `app/`, `scraper/`, `tests/`
- Zero references to `aiosqlite` in production code
- All existing API endpoints functional with SupabaseStorage
- All tests pass

### Must NOT Have (Guardrails)
- ❌ Do NOT touch `scraper/adapters/*` — zero changes to adapters
- ❌ Do NOT touch `scraper/utils/matcher.py` or `scraper/utils/dedup.py`
- ❌ Do NOT touch `scraper/models.py` (keep `to_db_dict()`/`from_db_row()` for now — harmless)
- ❌ Do NOT add DB-level pagination to `job_service.py` — out of scope
- ❌ Do NOT add new API endpoints or features
- ❌ Do NOT refactor `FakeStorage` beyond adding `active`/`inactive` stats
- ❌ Do NOT restructure project layout or rename `scraper/` package
- ❌ Do NOT add SupabaseStorage integration tests with real DB
- ❌ Do NOT modify `app/services/scraper_service.py` — already correct
- ❌ Do NOT clean up `.sisyphus/` planning artifacts

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> Every criterion MUST be verifiable by running a command or using a tool.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: YES (Tests-after — update existing tests)
- **Framework**: pytest (asyncio_mode = "auto")

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

Every task includes QA scenarios verified by the executing agent via `Bash` commands (grep, pytest, python -c).

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Delete safe files (no code changes)
└── Task 2: Update SupabaseStorage + FakeStorage (prerequisite for consumers)

Wave 2 (After Wave 1):
├── Task 3: Migrate consumers (job_service, stats, orchestrator)
├── Task 4: Fix tests (integration + scrape integration)
└── (sequential) Task 5: Delete old files
     └── Task 6: Update Docker
          └── Task 7: Update pyproject.toml
               └── Task 8: Update documentation (CLAUDE.md, README.md)
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 5 | 2 |
| 2 | None | 3, 4 | 1 |
| 3 | 2 | 5 | 4 (after 2 done) |
| 4 | 2 | 5 | 3 (after 2 done) |
| 5 | 1, 3, 4 | 6 | None |
| 6 | 5 | 7 | None |
| 7 | 6 | 8 | None |
| 8 | 7 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2 | task(category="quick") — parallel |
| 2 | 3, 4 | task(category="unspecified-low") — parallel after Wave 1 |
| 3 | 5-8 | task(category="quick") — sequential chain |

---

## TODOs

- [x] 1. Delete safe files (zero code dependencies)

  **What to do**:
  - Delete `job_scraper.egg-info/` directory (build artifact)
  - Delete `appmodels/` directory (empty artifact)
  - Delete `supabasemigrations/` directory (empty artifact)
  - Delete `MIGRATION_GUIDE.md` (generated doc, no code refs)
  - Delete `IMPLEMENTATION_SUMMARY.md` (generated doc, no code refs)
  - Delete `scripts/migrate_sqlite_to_supabase.py` (one-time migration, already done)

  **Must NOT do**:
  - Do NOT delete `config/sites.yaml` or `config/keywords.yaml` — still used by orchestrator
  - Do NOT delete `data/` directory yet — handled in Task 5
  - Do NOT delete `scraper/utils/storage.py` yet — consumers still import it (handled in Task 5)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple file deletions, zero code logic
  - **Skills**: []
    - No special skills needed — just `rm` commands

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 5
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - None — pure deletion task

  **Acceptance Criteria**:

  - [ ] `job_scraper.egg-info/` directory does not exist
  - [ ] `appmodels/` directory does not exist
  - [ ] `supabasemigrations/` directory does not exist
  - [ ] `MIGRATION_GUIDE.md` does not exist
  - [ ] `IMPLEMENTATION_SUMMARY.md` does not exist
  - [ ] `scripts/migrate_sqlite_to_supabase.py` does not exist
  - [ ] `python -m pytest tests/ -v` → ALL tests still pass (sanity check)

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Verify all files deleted
    Tool: Bash
    Steps:
      1. python -c "import os; files=['job_scraper.egg-info','appmodels','supabasemigrations','MIGRATION_GUIDE.md','IMPLEMENTATION_SUMMARY.md','scripts/migrate_sqlite_to_supabase.py']; assert all(not os.path.exists(f) for f in files), 'Some files still exist'"
      2. Assert: exits 0
    Expected Result: All listed files/dirs are gone
  ```

  ```
  Scenario: Existing tests still pass
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -v --tb=short
      2. Assert: exit code 0, 0 failures
    Expected Result: All tests green
  ```

  **Commit**: YES
  - Message: `chore: delete build artifacts and one-time migration files`
  - Files: `job_scraper.egg-info/`, `appmodels/`, `supabasemigrations/`, `MIGRATION_GUIDE.md`, `IMPLEMENTATION_SUMMARY.md`, `scripts/migrate_sqlite_to_supabase.py`

---

- [x] 2. Update SupabaseStorage and FakeStorage with missing API surface

  **What to do**:
  - In `app/services/storage.py` `SupabaseStorage.get_stats()`:
    - Add `active` count: `SELECT COUNT(*) FROM jobs WHERE is_active = true`
    - Add `inactive` count: `SELECT COUNT(*) FROM jobs WHERE is_active = false`
    - Return: `{"total": total, "active": active, "inactive": inactive, "by_source": by_source}`
  - In `tests/fakes/storage.py` `FakeStorage.get_stats()`:
    - Add `active` count: count all jobs (FakeStorage only stores active)
    - Add `inactive` count: always 0 (FakeStorage doesn't track inactive)
    - Return: `{"total": len(self._jobs), "active": len(self._jobs), "inactive": 0, "by_source": by_source}`

  **Must NOT do**:
  - Do NOT change `get_all_jobs()` signature on SupabaseStorage — it already accepts `source` kwarg, which is what consumers will use after migration
  - Do NOT add `active_only` kwarg to SupabaseStorage — it already filters `is_active = true`
  - Do NOT modify any other methods

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small targeted edits to two files
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Tasks 3, 4
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `app/services/storage.py:116-127` — Current `get_stats()` implementation — add `active`/`inactive` counts here
  - `tests/fakes/storage.py:52-60` — Current `FakeStorage.get_stats()` — mirror the new shape

  **API/Type References**:
  - `app/services/storage.py:38-49` — `StorageProtocol` — get_stats() returns `dict` (no change needed to protocol)

  **Acceptance Criteria**:

  - [ ] `SupabaseStorage.get_stats()` returns dict with keys: `total`, `active`, `inactive`, `by_source`
  - [ ] `FakeStorage.get_stats()` returns dict with keys: `total`, `active`, `inactive`, `by_source`
  - [ ] Both return same shape (same keys)
  - [ ] `python -m pytest tests/ -v` → ALL tests still pass

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: SupabaseStorage.get_stats returns correct shape
    Tool: Bash
    Steps:
      1. python -c "
import ast, inspect
from app.services.storage import SupabaseStorage
src = inspect.getsource(SupabaseStorage.get_stats)
assert 'active' in src, 'Missing active count in get_stats'
assert 'inactive' in src, 'Missing inactive count in get_stats'
print('OK: get_stats has active/inactive')
"
      2. Assert: prints "OK: get_stats has active/inactive"
    Expected Result: Source code includes active and inactive counting
  ```

  ```
  Scenario: FakeStorage.get_stats returns matching shape
    Tool: Bash
    Steps:
      1. python -c "
import asyncio
from tests.fakes.storage import FakeStorage
async def check():
    fs = FakeStorage()
    stats = await fs.get_stats()
    assert 'total' in stats, 'Missing total'
    assert 'active' in stats, 'Missing active'
    assert 'inactive' in stats, 'Missing inactive'
    assert 'by_source' in stats, 'Missing by_source'
    assert stats['total'] == 0
    assert stats['active'] == 0
    assert stats['inactive'] == 0
    print('OK: FakeStorage shape correct')
asyncio.run(check())
"
      2. Assert: prints "OK: FakeStorage shape correct"
    Expected Result: FakeStorage returns all four keys with correct defaults
  ```

  **Commit**: YES
  - Message: `fix(storage): add active/inactive counts to get_stats()`
  - Files: `app/services/storage.py`, `tests/fakes/storage.py`

---

- [x] 3. Migrate consumers off old StorageManager

  **What to do**:

  **3a. Update `app/services/job_service.py`:**
  - Remove `from scraper.utils.storage import StorageManager`
  - Remove the line-1 comment `# Temporary: wraps StorageManager until Supabase migration (Phase 2)`
  - Import: `from app.services.storage import SupabaseStorage`
  - Change constructor type hint: `Optional[StorageManager]` → `Optional[SupabaseStorage]`
  - Change default: `StorageManager()` → `SupabaseStorage()`
  - Fix `get_all_jobs()` calls: change `active_only=True` → `source=None` (SupabaseStorage already filters `is_active=true`)
  - Fix `list_jobs()`: after `get_all_jobs()`, results are `list[dict]`. Filter by source using `j["source"]` instead of `j.source`
  - Fix `get_job()`: compare `job["id"]` instead of `job.id`
  - Fix `search_jobs()`: access dict keys `j["title"]`, `j["description"]`, `j["source"]`
  - Fix `_to_response()`: accept `dict` instead of `JobPosting`, access via `job["title"]` etc., handle `tags` which comes as JSON string from Supabase (use `json.loads` if string)

  **3b. Update `app/routers/stats.py`:**
  - Remove `from scraper.utils.storage import StorageManager`
  - Import: `from app.services.storage import SupabaseStorage`
  - Change `get_storage()` to return `SupabaseStorage()` and call `await storage.init_pool()`
  - Fix `export_jobs()`: change `get_all_jobs(active_only=True)` → `get_all_jobs()`
  - Fix dict handling: remove `model_dump` path since SupabaseStorage returns dicts already

  **3c. Update `scraper/orchestrator.py`:**
  - Remove `from scraper.utils.storage import StorageManager` (line 19)
  - Remove `db_path` parameter from `__init__()` (line 40)
  - Change default storage from `StorageManager(db_path=db_path)` to `None` (line 58)
  - When `storage is None`, raise an error or log warning — callers MUST provide storage
  - Update docstring to remove `db_path` references

  **Must NOT do**:
  - Do NOT modify `scraper/adapters/*`
  - Do NOT add pagination logic to `job_service.py`
  - Do NOT change the external API contract (same request/response shapes)
  - Do NOT modify `app/services/scraper_service.py` — already correct

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Multi-file edits but straightforward replacements — no complex logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 4, after Task 2 completes)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 5
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `app/services/storage.py:95-107` — `SupabaseStorage.get_all_jobs()` — returns `list[dict]`, accepts `source: Optional[str]`
  - `app/services/storage.py:109-114` — `SupabaseStorage.get_job_by_id()` — returns `Optional[dict]`
  - `app/services/storage.py:116-127` — `SupabaseStorage.get_stats()` — returns dict (after Task 2 updates)
  - `tests/fakes/storage.py:41-46` — `FakeStorage.get_all_jobs()` — same signature as SupabaseStorage (returns `list[dict]`)
  - `app/services/scraper_service.py` — Example of how SupabaseStorage is correctly used (for reference, don't modify)

  **API/Type References**:
  - `app/models/responses.py` — `JobResponse`, `JobListResponse`, `PaginationMeta` — the response shapes that `_to_response()` must produce
  - `app/services/storage.py:38-49` — `StorageProtocol` — the interface all storage implementations follow

  **Files to modify**:
  - `app/services/job_service.py` — Replace StorageManager with SupabaseStorage, fix dict access
  - `app/routers/stats.py` — Replace StorageManager with SupabaseStorage, fix dict access
  - `scraper/orchestrator.py` — Remove StorageManager import and `db_path` param

  **Acceptance Criteria**:

  - [ ] `python -c "from app.services.job_service import JobService"` → exits 0, no StorageManager in import chain
  - [ ] `python -c "from app.routers.stats import router"` → exits 0, no StorageManager in import chain
  - [ ] `python -c "from scraper.orchestrator import ScraperOrchestrator"` → exits 0, no StorageManager in import chain
  - [ ] `grep -rn "StorageManager\|active_only" app/services/job_service.py app/routers/stats.py scraper/orchestrator.py` → zero matches
  - [ ] `grep -rn "scraper\.utils\.storage" app/ scraper/` → zero matches

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: job_service.py imports clean
    Tool: Bash
    Steps:
      1. python -c "from app.services.job_service import JobService; print('OK')"
      2. Assert: prints "OK", exit code 0
    Expected Result: No import errors

  Scenario: stats.py imports clean
    Tool: Bash
    Steps:
      1. python -c "from app.routers.stats import router; print('OK')"
      2. Assert: prints "OK", exit code 0
    Expected Result: No import errors

  Scenario: orchestrator.py imports clean
    Tool: Bash
    Steps:
      1. python -c "from scraper.orchestrator import ScraperOrchestrator; print('OK')"
      2. Assert: prints "OK", exit code 0
    Expected Result: No import errors

  Scenario: Zero old-system references in production code
    Tool: Bash
    Steps:
      1. grep -rn "StorageManager\|from scraper.utils.storage\|active_only\|db_path.*jobs.db" app/ scraper/ --include="*.py"
      2. Assert: empty output (zero matches)
    Expected Result: No remaining references to old storage
  ```

  **Commit**: YES
  - Message: `refactor: migrate job_service, stats, orchestrator to SupabaseStorage`
  - Files: `app/services/job_service.py`, `app/routers/stats.py`, `scraper/orchestrator.py`
  - Pre-commit: `python -c "from app.services.job_service import JobService; from app.routers.stats import router; from scraper.orchestrator import ScraperOrchestrator; print('imports OK')"`

---

- [x] 4. Fix tests — remove old StorageManager references

  **What to do**:

  **4a. Update `tests/test_integration.py`:**
  - Remove `from scraper.utils.storage import StorageManager` import (line 29)
  - Replace all `StorageManager(db_path=temp_db)` instances with `FakeStorage()` from `tests.fakes.storage`
  - Remove `_make_temp_db()` fixture and temp file handling if no longer needed
  - In `test_all_modules_importable` (around line 691-711):
    - Remove `from scraper.logger import setup_logger` assertion (line 701)
    - Remove `from scraper.utils.storage import StorageManager` assertion (line 707)
    - Keep all other module import assertions
  - Replace `storage = StorageManager(db_path=temp_db)` with `storage = FakeStorage()` everywhere
  - Adjust any `StorageManager`-specific assertions

  **4b. Update `tests/test_api/test_scrape_integration.py`:**
  - Line 132: Change `assert isinstance(svc._orchestrator.storage, StorageManager)` → remove this test or change to assert storage is `None` (since orchestrator no longer defaults to StorageManager)
  - Update the import if StorageManager was imported for this assertion

  **Must NOT do**:
  - Do NOT modify adapter test files (`tests/test_adapters/*.py`)
  - Do NOT modify `tests/test_matcher.py`
  - Do NOT modify `tests/test_dedup.py`
  - Do NOT add new tests — only fix existing
  - Do NOT create tests for SupabaseStorage with real DB

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Test file updates, following existing FakeStorage patterns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 3, after Task 2 completes)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 5
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `tests/fakes/storage.py:1-87` — `FakeStorage` class — use this instead of StorageManager in tests
  - `tests/test_api/test_scrape_integration.py:38-50` — Example of using FakeStorage with orchestrator (already correct pattern)

  **Test References**:
  - `tests/test_integration.py:29` — StorageManager import to remove
  - `tests/test_integration.py:162-166` — `_make_temp_db()` fixture to remove
  - `tests/test_integration.py:236-238` — `storage` fixture using StorageManager
  - `tests/test_integration.py:308,348,387,842` — Direct StorageManager instantiations
  - `tests/test_integration.py:691-711` — `test_all_modules_importable` — remove storage/logger assertions
  - `tests/test_api/test_scrape_integration.py:132` — Hardcoded isinstance assertion

  **Acceptance Criteria**:

  - [ ] `grep -rn "StorageManager\|scraper\.utils\.storage\|scraper\.logger" tests/` → zero matches
  - [ ] `grep -rn "active_only" tests/` → zero matches
  - [ ] `python -m pytest tests/test_integration.py -v` → ALL pass
  - [ ] `python -m pytest tests/test_api/test_scrape_integration.py -v` → ALL pass
  - [ ] `python -m pytest tests/ -v` → ALL pass, 0 failures

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Zero old references in test files
    Tool: Bash
    Steps:
      1. grep -rn "StorageManager\|from scraper.utils.storage\|from scraper.logger\|active_only" tests/ --include="*.py"
      2. Assert: empty output
    Expected Result: No remaining old references

  Scenario: Integration tests pass
    Tool: Bash
    Steps:
      1. python -m pytest tests/test_integration.py -v --tb=short
      2. Assert: exit code 0
    Expected Result: All integration tests green

  Scenario: API scrape integration tests pass
    Tool: Bash
    Steps:
      1. python -m pytest tests/test_api/test_scrape_integration.py -v --tb=short
      2. Assert: exit code 0
    Expected Result: All API tests green

  Scenario: Full test suite passes
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -v --tb=short 2>&1 | tail -5
      2. Assert: "passed" in output, "failed" not in output, exit code 0
    Expected Result: All tests green
  ```

  **Commit**: YES
  - Message: `test: replace StorageManager with FakeStorage in all tests`
  - Files: `tests/test_integration.py`, `tests/test_api/test_scrape_integration.py`
  - Pre-commit: `python -m pytest tests/ -v --tb=short`

---

- [x] 5. Delete old files — CLI, SQLite storage, logger, tests

  **What to do**:
  - Delete `main.py` (root CLI entry point — 191 lines)
  - Delete `scraper/utils/storage.py` (old SQLite StorageManager — 278 lines)
  - Delete `scraper/logger.py` (logging setup only used by old CLI)
  - Delete `tests/test_storage.py` (SQLite storage tests — 382 lines)
  - Delete `data/` directory contents if present (old SQLite DB) — keep directory in .gitignore

  **Must NOT do**:
  - Do NOT delete `config/` directory or its contents
  - Do NOT delete `scraper/__init__.py` or `scraper/utils/__init__.py`
  - Do NOT delete `tests/fakes/storage.py` — this is FakeStorage, still needed

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure file deletion
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after Tasks 1, 3, 4)
  - **Blocks**: Task 6
  - **Blocked By**: Tasks 1, 3, 4

  **References**:

  **Verification References**:
  - After deletion, grep must show zero matches: `grep -rn "StorageManager\|scraper\.utils\.storage\|scraper\.logger" app/ scraper/ tests/ --include="*.py"`

  **Acceptance Criteria**:

  - [ ] `main.py` does not exist at project root
  - [ ] `scraper/utils/storage.py` does not exist
  - [ ] `scraper/logger.py` does not exist
  - [ ] `tests/test_storage.py` does not exist
  - [ ] `python -c "from app.main import app; print('OK')"` → prints "OK" (FastAPI still works)
  - [ ] `python -m pytest tests/ -v` → ALL pass (no broken imports)
  - [ ] `grep -rn "StorageManager\|scraper\.utils\.storage\|scraper\.logger" app/ scraper/ tests/ --include="*.py"` → zero matches

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Old files are gone
    Tool: Bash
    Steps:
      1. python -c "import os; files=['main.py','scraper/utils/storage.py','scraper/logger.py','tests/test_storage.py']; existing=[f for f in files if os.path.exists(f)]; assert not existing, f'Still exist: {existing}'"
      2. Assert: exits 0
    Expected Result: All old files deleted

  Scenario: No remaining references
    Tool: Bash
    Steps:
      1. grep -rn "StorageManager\|scraper\.utils\.storage\|scraper\.logger\|aiosqlite" app/ scraper/ tests/ --include="*.py"
      2. Assert: empty output
    Expected Result: Zero old-system references anywhere

  Scenario: FastAPI app still importable
    Tool: Bash
    Steps:
      1. python -c "from app.main import app; print('OK')"
      2. Assert: prints "OK"
    Expected Result: No import errors

  Scenario: All tests pass
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -v --tb=short
      2. Assert: exit code 0
    Expected Result: All tests green
  ```

  **Commit**: YES
  - Message: `chore: remove old CLI entry point, SQLite storage, and logger`
  - Files: `main.py`, `scraper/utils/storage.py`, `scraper/logger.py`, `tests/test_storage.py`
  - Pre-commit: `python -m pytest tests/ -v --tb=short`

---

- [x] 6. Update Docker configuration

  **What to do**:

  **6a. Update `Dockerfile.backend`:**
  - Remove line 18: `COPY main.py ./`
  - Remove line 21: `RUN mkdir -p data logs` (no longer need `data` dir for SQLite; keep `logs` if used)
    - Check: if loguru writes to `logs/`, keep `mkdir -p logs`. If not, remove entirely.

  **6b. Update `docker-compose.override.yml`:**
  - Remove line 10: `- ./main.py:/app/main.py` (file no longer exists)

  **Must NOT do**:
  - Do NOT modify `docker-compose.yml` main config
  - Do NOT modify `frontend/Dockerfile`
  - Do NOT change the CMD (already correct: uvicorn app.main:app)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Two small edits to Docker files
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 7
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `Dockerfile.backend:1-33` — Full file, lines 18 and 21 to modify
  - `docker-compose.override.yml:1-29` — Full file, line 10 to remove

  **Acceptance Criteria**:

  - [ ] `grep "main.py" Dockerfile.backend` → zero matches
  - [ ] `grep "main.py" docker-compose.override.yml` → zero matches
  - [ ] `grep "mkdir.*data" Dockerfile.backend` → zero matches (if data dir removed)
  - [ ] Dockerfile.backend CMD still references `app.main:app`

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Dockerfile cleaned
    Tool: Bash
    Steps:
      1. grep -n "main.py\|mkdir.*data" Dockerfile.backend
      2. Assert: empty output (zero matches)
      3. grep "app.main:app" Dockerfile.backend
      4. Assert: has match (CMD still correct)
    Expected Result: main.py and data dir references gone, CMD intact

  Scenario: docker-compose.override cleaned
    Tool: Bash
    Steps:
      1. grep -n "main.py" docker-compose.override.yml
      2. Assert: empty output
    Expected Result: main.py volume mount removed
  ```

  **Commit**: YES
  - Message: `chore(docker): remove old CLI and SQLite references from Docker config`
  - Files: `Dockerfile.backend`, `docker-compose.override.yml`

---

- [x] 7. Update pyproject.toml — remove aiosqlite dependency

  **What to do**:
  - Remove `"aiosqlite>=0.19.0"` from `dependencies` list (line 36)
  - Remove `"config"` from `[tool.setuptools] packages` list (line 53) — config is YAML data, not a Python package
  - Verify: `pip install -e ".[dev]"` still works

  **Must NOT do**:
  - Do NOT remove `asyncpg` — still needed for Supabase
  - Do NOT remove `pyyaml` — still needed for config loading
  - Do NOT change project name/version/metadata

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file, two line edits
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 8
  - **Blocked By**: Task 6

  **References**:

  **Pattern References**:
  - `pyproject.toml:25-43` — dependencies list, remove `aiosqlite` line
  - `pyproject.toml:52-53` — setuptools packages, remove `config`

  **Acceptance Criteria**:

  - [ ] `grep "aiosqlite" pyproject.toml` → zero matches
  - [ ] `pip install -e ".[dev]"` → exits 0
  - [ ] `python -m pytest tests/ -v` → ALL pass

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: aiosqlite removed from dependencies
    Tool: Bash
    Steps:
      1. grep "aiosqlite" pyproject.toml
      2. Assert: empty output
    Expected Result: No aiosqlite in pyproject.toml

  Scenario: Install still works
    Tool: Bash
    Steps:
      1. pip install -e ".[dev]"
      2. Assert: exit code 0
    Expected Result: Clean install

  Scenario: Tests still pass after reinstall
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -v --tb=short 2>&1 | tail -5
      2. Assert: "passed" in output, exit code 0
    Expected Result: All tests green
  ```

  **Commit**: YES
  - Message: `chore: remove aiosqlite dependency from pyproject.toml`
  - Files: `pyproject.toml`
  - Pre-commit: `pip install -e ".[dev]" && python -m pytest tests/ -v --tb=short`

---

- [x] 8. Update documentation — CLAUDE.md and README.md

  **What to do**:

  **8a. Update `CLAUDE.md`:**
  - Update `## Commands` section:
    - Remove CLI commands (`python main.py scrape`, `python main.py stats`, `python main.py export`)
    - Add FastAPI commands: `uvicorn app.main:app --reload`, `python -m pytest tests/ -v`
  - Update `## Architecture`:
    - Change pipeline description from `CLI (main.py) →` to `FastAPI (app/main.py) →`
    - Change storage from `Storage (aiosqlite)` to `Storage (asyncpg/Supabase)`
  - Update bullet points:
    - Remove `Storage` bullet about aiosqlite
    - Add/update bullet about SupabaseStorage with asyncpg
  - Update `## Key Conventions`:
    - Remove `aiosqlite` references
    - Add `asyncpg` for async PostgreSQL
    - Add `fastapi` and `uvicorn`
  - Update `## Gotchas`:
    - Remove `--verbose` flag gotcha (CLI removed)
    - Remove `Config paths are relative to CWD` gotcha
    - Remove `aiosqlite init` gotcha
    - Add new gotcha about SupabaseStorage needing `init_pool()` before use
  - Update `## Testing`:
    - Update test count (will decrease by ~20 after deleting test_storage.py)
  - Update `## Project Status`:
    - Mark Phase 3 as complete (FastAPI, Supabase, Next.js, Docker)

  **8b. Update `README.md`:**
  - Change title/description from "Python CLI tool" to "Full-stack remote job scraping platform"
  - Update architecture diagram to show FastAPI → Supabase pipeline
  - Remove CLI usage section (scrape/stats/export commands)
  - Add API usage section (FastAPI endpoints)
  - Update tech stack: remove aiosqlite, add asyncpg, FastAPI, Next.js, Supabase
  - Update project structure to reflect current layout (app/, frontend/, supabase/)
  - Update roadmap: mark Phase 3 (FastAPI + Supabase + Next.js + Docker) as complete

  **Must NOT do**:
  - Do NOT rewrite from scratch — update existing content
  - Do NOT add emojis
  - Do NOT remove the data sources table — adapters are unchanged

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation rewrite requiring accuracy and completeness
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final task)
  - **Blocks**: None
  - **Blocked By**: Task 7

  **References**:

  **Documentation References**:
  - `CLAUDE.md:1-end` — Full file, needs comprehensive updates
  - `README.md:1-end` — Full file, needs comprehensive updates

  **Architecture References**:
  - `app/main.py` — FastAPI app entry point (for accurate documentation)
  - `app/routers/*.py` — API endpoints (for documenting API usage)
  - `app/services/storage.py` — SupabaseStorage (for architecture docs)
  - `docker-compose.yml` — Deployment config (for setup docs)
  - `frontend/` — Next.js frontend (for project structure)

  **Acceptance Criteria**:

  - [ ] `grep -c "CLI\|aiosqlite\|main\.py scrape\|main\.py stats\|main\.py export" CLAUDE.md` → zero matches for removed concepts
  - [ ] `grep "FastAPI\|Supabase\|asyncpg" CLAUDE.md` → has matches
  - [ ] `grep "FastAPI\|Supabase\|Next\.js" README.md` → has matches
  - [ ] `grep -c "python main.py" README.md` → zero matches (CLI commands removed)

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: CLAUDE.md updated correctly
    Tool: Bash
    Steps:
      1. grep -c "python main.py scrape\|python main.py stats\|python main.py export" CLAUDE.md
      2. Assert: output is "0"
      3. grep "FastAPI" CLAUDE.md
      4. Assert: has matches
      5. grep "asyncpg\|Supabase" CLAUDE.md
      6. Assert: has matches
    Expected Result: CLI references gone, FastAPI/Supabase present

  Scenario: README.md updated correctly
    Tool: Bash
    Steps:
      1. grep -c "Python CLI tool" README.md
      2. Assert: output is "0"
      3. grep "FastAPI\|Next.js\|Supabase" README.md
      4. Assert: has matches
    Expected Result: Old description replaced with full-stack description
  ```

  **Commit**: YES
  - Message: `docs: update CLAUDE.md and README.md for full-stack architecture`
  - Files: `CLAUDE.md`, `README.md`

---

## Commit Strategy

| After Task | Message | Key Files | Verification |
|------------|---------|-----------|--------------|
| 1 | `chore: delete build artifacts and one-time migration files` | 6 files/dirs deleted | pytest passes |
| 2 | `fix(storage): add active/inactive counts to get_stats()` | storage.py, fakes/storage.py | pytest passes |
| 3 | `refactor: migrate job_service, stats, orchestrator to SupabaseStorage` | 3 files | imports clean, grep clean |
| 4 | `test: replace StorageManager with FakeStorage in all tests` | 2 test files | pytest passes |
| 5 | `chore: remove old CLI entry point, SQLite storage, and logger` | 4 files deleted | grep clean, pytest passes |
| 6 | `chore(docker): remove old CLI and SQLite references from Docker config` | 2 Docker files | grep clean |
| 7 | `chore: remove aiosqlite dependency from pyproject.toml` | pyproject.toml | pip install + pytest passes |
| 8 | `docs: update CLAUDE.md and README.md for full-stack architecture` | CLAUDE.md, README.md | grep validates |

---

## Success Criteria

### Verification Commands
```bash
# FINAL VERIFICATION — zero old-system references
grep -rn "StorageManager\|scraper\.utils\.storage\|scraper\.logger\|aiosqlite\|active_only\|data/jobs\.db" app/ scraper/ tests/ --include="*.py"
# Expected: empty output (zero matches)

# All tests pass
python -m pytest tests/ -v
# Expected: all pass, 0 failures

# FastAPI app importable
python -c "from app.main import app; print('OK')"
# Expected: prints "OK"

# No deleted files remain
python -c "import os; dead=['main.py','scraper/utils/storage.py','scraper/logger.py','tests/test_storage.py','MIGRATION_GUIDE.md','IMPLEMENTATION_SUMMARY.md']; alive=[f for f in dead if os.path.exists(f)]; print(f'Dead files remaining: {alive}'); assert not alive"
# Expected: prints "Dead files remaining: []"
```

### Final Checklist
- [x] All "Must Have" present (zero old references in app/scraper, all endpoints work, 642 tests pass)
- [x] All "Must NOT Have" absent (no adapter changes, no scope creep, no new features)
- [x] All 8 tasks completed
- [x] CLAUDE.md updated to reflect full-stack architecture
