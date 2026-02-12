# Scraper Consolidation into FastAPI App

## TL;DR

> **Quick Summary**: Move all scraper code into `app/scraper/`, switch config source from YAML files to DB tables (via ConfigService), consolidate storage pools, seed DB with existing YAML data, then delete old directories (scraper/, tests/, config/, data/, scripts/, logs/).
> 
> **Deliverables**:
> - All scraper code lives under `app/scraper/` with updated imports
> - Orchestrator + Matcher read config from DB instead of YAML files
> - ConfigService fixed (column name bugs) + `get_match_rules()` added
> - DB seeded with sites, keywords, match rules from current YAML
> - Single shared SupabaseStorage pool (was 2)
> - Old directories deleted, pyproject.toml + Dockerfile updated
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 5 → Task 6 → Task 8 → Task 9

---

## Context

### Original Request
用户要求：重构后端，把 scraper 的全部功能移植到 fastapi app 里，改由 fastapi 定时爬取，爬虫配置都由 fastapi 后台管理，不再保留 scraper、tests、data、scripts、logs、config 目录。

### Interview Summary
**Key Discussions**:
- Tests: Delete all 574 tests entirely, no migration
- Config: Refactor orchestrator+matcher to read from DB (ConfigService) instead of YAML files

**Research Findings**:
- Scraper module is self-contained (13 files), only 2 app files import from it
- ConfigService has critical bugs: queries `config_json` (column is `extra_config`), queries `keyword_configs.enabled` (column doesn't exist)
- DB tables (site_configs, keyword_configs, match_rules) are all EMPTY — need seeding before YAML deletion
- No `get_match_rules()` in ConfigService — Matcher needs this
- Scheduler creates ad-hoc 3rd asyncpg pool in notification check

### Metis Review
**Identified Gaps** (addressed):
- ConfigService column name mismatches → Task 3 fixes
- Empty DB tables → Task 4 seeds data
- Missing `get_match_rules()` → Task 3 adds it
- `_load_valid_sources()` asyncio.run() crash → Task 2 fixes
- Adapter config shape (extra_config JSONB must be merged into flat dict) → Task 5 handles
- Scheduler ad-hoc pool → Task 7 fixes
- `keyword_configs.enabled` column missing → Task 3 adds via migration

---

## Work Objectives

### Core Objective
Consolidate all scraper functionality into the FastAPI app, making it the single codebase. All configuration managed via DB. Old directories completely removed.

### Concrete Deliverables
- `app/scraper/` directory with all adapter, matcher, dedup, orchestrator, models code
- Fixed ConfigService with correct column names and new `get_match_rules()` method
- DB migration `004_add_keyword_enabled.sql` adding `enabled` column to keyword_configs
- Seed script output: site_configs, keyword_configs, match_rules populated from YAML
- Refactored Orchestrator accepting config dicts (not YAML paths)
- Refactored Matcher accepting keyword/rule dicts (not YAML paths)
- Single shared asyncpg pool across all services
- Updated Dockerfile.backend, pyproject.toml, CLAUDE.md

### Definition of Done
- [x] `uvicorn app.main:app` starts without errors or warnings
- [x] `POST /api/scrape {"sites": ["eleduck"]}` completes successfully with data in DB
- [x] `GET /api/scheduler/status` shows scheduler running
- [x] No `scraper/`, `tests/`, `config/`, `data/`, `scripts/`, `logs/` directories exist
- [x] `python -c "from app.scraper.orchestrator import ScraperOrchestrator"` succeeds
- [x] Only 1 "asyncpg connection pool created" message in startup logs

### Must Have
- Zero adapter logic changes (only import paths change)
- Config loaded from DB tables, not YAML files
- All 7 adapters work identically after migration
- Scheduled scraping continues to function

### Must NOT Have (Guardrails)
- ❌ DO NOT modify adapter logic (scraper/adapters/*.py content — only imports change)
- ❌ DO NOT modify DedupManager logic (scraper/utils/dedup.py content — only imports change)
- ❌ DO NOT introduce FastAPI `Depends()` DI for storage (keep singleton pattern)
- ❌ DO NOT add new tests (test recreation is out of scope)
- ❌ DO NOT touch frontend/ directory
- ❌ DO NOT redesign ConfigService API (minimal fixes only)
- ❌ DO NOT add config CRUD UI features
- ❌ DO NOT modify scraper/models.py beyond fixing `_load_valid_sources()` and import paths

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.

### Test Decision
- **Infrastructure exists**: YES (pytest configured)
- **Automated tests**: None (all tests deleted per user decision)
- **Framework**: N/A

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

Every task includes QA scenarios. The executing agent verifies deliverables by running commands, starting servers, and checking outputs directly.

**Verification Tool by Deliverable Type:**

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| Import integrity | Bash (python -c) | Import module, check no errors |
| Server startup | Bash (uvicorn + curl) | Start server, health check |
| DB operations | Bash (python script) | Query DB, assert results |
| File operations | Bash (ls, test) | Check files exist/don't exist |
| API endpoints | Bash (curl) | Send requests, check responses |

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Move scraper/ → app/scraper/ + fix imports
├── Task 3: Fix ConfigService + add get_match_rules() + DB migration
└── Task 4: Seed DB tables from YAML files

Wave 2 (After Wave 1):
├── Task 2: Fix JobPosting _load_valid_sources() + consolidate models
├── Task 5: Refactor Orchestrator (YAML→DB config)
└── Task 6: Refactor Matcher (YAML→DB config)

Wave 3 (After Wave 2):
├── Task 7: Consolidate storage pools + fix scheduler
├── Task 8: Update Dockerfile, pyproject.toml, CLAUDE.md
└── Task 9: Delete old directories + final verification
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 5, 6 | 3, 4 |
| 2 | 1 | 5, 6, 7 | 5, 6 (after 1 done) |
| 3 | None | 5, 6 | 1, 4 |
| 4 | None | 5, 6, 9 | 1, 3 |
| 5 | 1, 3, 4 | 7, 9 | 6 |
| 6 | 1, 3, 4 | 7, 9 | 5 |
| 7 | 2, 5, 6 | 9 | 8 |
| 8 | 1 | 9 | 7 |
| 9 | 5, 6, 7, 8 | None | None (final) |

---

## TODOs

- [x] 1. Move scraper/ → app/scraper/ and bulk-update imports

  **What to do**:
  - Copy entire `scraper/` directory to `app/scraper/`
  - Ensure all `__init__.py` files exist in `app/scraper/`, `app/scraper/adapters/`, `app/scraper/utils/`
  - Bulk-replace all `from scraper.` → `from app.scraper.` across the ENTIRE codebase (both in app/scraper/ internal imports AND in app/services/ consumer imports)
  - Specifically update these import locations:
    - `app/scraper/orchestrator.py`: imports from scraper.adapters.*, scraper.models, scraper.utils.*
    - `app/scraper/adapters/base.py`: from scraper.models
    - `app/scraper/adapters/api.py`: from scraper.adapters.base, from scraper.models
    - `app/scraper/adapters/rss.py`: from scraper.adapters.base, from scraper.models
    - `app/scraper/adapters/browser.py`: from scraper.adapters.base, from scraper.models
    - `app/scraper/adapters/hybrid.py`: from scraper.adapters.base, from scraper.models
    - `app/scraper/adapters/html.py`: from scraper.adapters.base, from scraper.models
    - `app/scraper/utils/dedup.py`: from scraper.models
    - `app/scraper/utils/matcher.py`: no scraper imports (reads YAML directly)
    - `app/scraper/models.py`: from app.config.settings (already correct)
    - `app/services/scraper_service.py`: from scraper.orchestrator → from app.scraper.orchestrator
    - `app/services/storage.py`: from scraper.models → from app.scraper.models
  - Do NOT delete original `scraper/` yet (Task 9 handles that)
  - Do NOT change any logic — ONLY import paths

  **Must NOT do**:
  - Do NOT modify adapter logic, matcher logic, dedup logic, or model fields
  - Do NOT use relative imports — always absolute `from app.scraper.X`
  - Do NOT delete original scraper/ directory yet

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - No special skills needed — file copy + bulk import replacement
  - **Skills Evaluated but Omitted**:
    - `git-master`: Not needed — no commits in this task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 3, 4)
  - **Blocks**: Tasks 2, 5, 6
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `scraper/orchestrator.py:1-18` — All imports that need `scraper.` → `app.scraper.` prefix
  - `scraper/adapters/api.py:1-15` — Adapter import pattern (base + models)
  - `app/services/scraper_service.py:11` — `from scraper.orchestrator import ScraperOrchestrator`
  - `app/services/storage.py:10` — `from scraper.models import JobPosting`

  **Acceptance Criteria**:

  Agent-Executed QA Scenarios:

  ```
  Scenario: All app.scraper imports resolve
    Tool: Bash (python -c)
    Preconditions: app/scraper/ directory exists with all files
    Steps:
      1. python -c "from app.scraper.orchestrator import ScraperOrchestrator; print('OK')"
      2. python -c "from app.scraper.models import JobPosting; print('OK')"
      3. python -c "from app.scraper.adapters.api import RemoteOKAdapter, EleduckAdapter, WorkGoAdapter; print('OK')"
      4. python -c "from app.scraper.adapters.rss import WeWorkRemotelyAdapter; print('OK')"
      5. python -c "from app.scraper.adapters.browser import ArcDevAdapter; print('OK')"
      6. python -c "from app.scraper.adapters.hybrid import V2EXAdapter; print('OK')"
      7. python -c "from app.scraper.adapters.html import YuanchengAdapter; print('OK')"
      8. python -c "from app.scraper.utils.matcher import KeywordMatcher; print('OK')"
      9. python -c "from app.scraper.utils.dedup import DedupManager; print('OK')"
    Expected Result: All print "OK", no ImportError
    Evidence: Terminal output captured

  Scenario: No stale scraper. imports remain in app/
    Tool: Bash (grep)
    Steps:
      1. grep -rn "from scraper\." app/ --include="*.py" | grep -v "from app.scraper" | grep -v "__pycache__"
      2. grep -rn "import scraper\." app/ --include="*.py" | grep -v "import app.scraper" | grep -v "__pycache__"
    Expected Result: Both commands return empty (no matches)
    Evidence: Terminal output (empty = pass)
  ```

  **Commit**: YES
  - Message: `refactor: move scraper/ to app/scraper/ and update all imports`
  - Files: `app/scraper/**`, `app/services/scraper_service.py`, `app/services/storage.py`

---

- [x] 2. Fix JobPosting `_load_valid_sources()` crash

  **What to do**:
  - In `app/scraper/models.py`, remove the entire `_load_valid_sources()` function and its `asyncio.run()` call at module level
  - Replace `VALID_SOURCES = _load_valid_sources()` with a simple hardcoded set:
    ```python
    VALID_SOURCES = {"remoteok", "eleduck", "weworkremotely", "workgo", "v2ex", "arcdev", "yuancheng"}
    ```
  - Remove the `from app.config.settings import settings` import (no longer needed in models)
  - Remove the `import asyncio` and `import asyncpg` imports from the function
  - Keep the `field_validator("source")` that uses `VALID_SOURCES` — it still validates source values
  - Also remove `to_db_dict()` and `from_db_row()` methods (SQLite legacy, no longer used) — keep only `to_pg_dict()` and `from_pg_row()`

  **Must NOT do**:
  - Do NOT change JobPosting fields or `generate_id()` logic
  - Do NOT remove `to_pg_dict()` or `from_pg_row()` (used by SupabaseStorage)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocks**: Tasks 7
  - **Blocked By**: Task 1

  **References**:
  - `app/scraper/models.py:14-46` — `_load_valid_sources()` function to remove (after Task 1 moves file)
  - `app/scraper/models.py:49` — `VALID_SOURCES = _load_valid_sources()` line to replace
  - `app/services/storage.py:148-163` — `_job_to_params()` uses `to_pg_dict()` pattern — verify NOT broken

  **Acceptance Criteria**:

  ```
  Scenario: No RuntimeWarning on import
    Tool: Bash (python -W error)
    Steps:
      1. python -W error -c "from app.scraper.models import JobPosting; print(f'VALID_SOURCES={JobPosting.__fields__}')"
    Expected Result: No RuntimeWarning, no RuntimeError
    Evidence: Clean output without warnings

  Scenario: Source validation still works
    Tool: Bash (python -c)
    Steps:
      1. python -c "
         from app.scraper.models import JobPosting
         try:
             JobPosting(title='x', company='y', url='http://x', source='INVALID')
             print('FAIL: should have raised')
         except Exception as e:
             print(f'OK: {e}')
         "
    Expected Result: Validation error for invalid source
    Evidence: "OK:" prefix in output
  ```

  **Commit**: YES (groups with Task 1)
  - Message: `fix: remove asyncio.run() from JobPosting module-level init`
  - Files: `app/scraper/models.py`

---

- [x] 3. Fix ConfigService bugs + add DB migration + add `get_match_rules()`

  **What to do**:
  - **Fix column name bug**: In `app/services/config_service.py`, replace ALL occurrences of `config_json` with `extra_config` in SQL queries and dict construction (lines 34, 47, 57, 72, 85)
  - **Add `site_key` to queries**: Add `site_key` to the SELECT in `get_site_configs()` and `get_site_config_by_id()`, include it in returned dicts
  - **Create DB migration** `supabase/migrations/004_add_keyword_enabled.sql`:
    ```sql
    ALTER TABLE keyword_configs ADD COLUMN IF NOT EXISTS enabled boolean NOT NULL DEFAULT true;
    ```
  - **Add `get_match_rules()` method** to ConfigService:
    ```python
    async def get_match_rules(self) -> list[dict]:
        rows = await self._pool.fetch(
            "SELECT id, rule_name, expression, skip_location_for "
            "FROM match_rules ORDER BY id"
        )
        return [
            {
                "rule_name": r["rule_name"],
                "expression": r["expression"],
                "skip_location_for": list(r["skip_location_for"]),
            }
            for r in rows
        ]
    ```
  - **Run migration 004** against the live Supabase DB

  **Must NOT do**:
  - Do NOT redesign ConfigService API
  - Do NOT add update/create methods for match_rules (read-only is enough)
  - Do NOT add caching for match_rules (low frequency reads)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 4)
  - **Blocks**: Tasks 5, 6
  - **Blocked By**: None

  **References**:
  - `app/services/config_service.py:32-52` — `get_site_configs()` with wrong column name `config_json`
  - `app/services/config_service.py:54-73` — `get_site_config_by_id()` with wrong column name
  - `app/services/config_service.py:75-106` — `update_site_config()` with wrong column name in field_map
  - `app/services/config_service.py:108-126` — `get_keyword_configs()` queries `enabled` (column to be added)
  - `supabase/migrations/001_initial_schema.sql:63-72` — keyword_configs schema (no `enabled` column currently)
  - `supabase/migrations/001_initial_schema.sql:77-84` — match_rules schema

  **Acceptance Criteria**:

  ```
  Scenario: ConfigService queries work against real DB
    Tool: Bash (python script)
    Preconditions: Migration 004 applied, DB seeded (Task 4)
    Steps:
      1. Run python script that:
         a. Creates asyncpg pool
         b. Creates ConfigService(pool=pool)
         c. Calls get_site_configs() — assert returns list with site_key field
         d. Calls get_keyword_configs() — assert returns list with enabled field
         e. Calls get_match_rules() — assert returns list with expression field
      2. Assert no SQL errors
    Expected Result: All 3 methods return valid data
    Evidence: Terminal output with row counts

  Scenario: Migration 004 is idempotent
    Tool: Bash (python asyncpg)
    Steps:
      1. Run migration 004 SQL twice
      2. Assert no error on second run (IF NOT EXISTS)
    Expected Result: Both runs succeed
    Evidence: "OK" output
  ```

  **Commit**: YES
  - Message: `fix(config): correct column names in ConfigService, add keyword enabled column and match rules reader`
  - Files: `app/services/config_service.py`, `supabase/migrations/004_add_keyword_enabled.sql`

---

- [x] 4. Seed DB tables from YAML files

  **What to do**:
  - Write a one-time Python seed script (inline, not a file) that reads `config/sites.yaml` and `config/keywords.yaml` and INSERTs into the DB tables
  - **Seed `site_configs`** from sites.yaml:
    - For each site entry: INSERT `site_key`, `name`, `url`, `adapter`, `enabled`, `skip_location_match`, `rate_limit_seconds`, `max_pages`, `extra_config` (JSONB with params, headers, api_url, api_base, clerk_base, page_size, etc.)
    - Use `ON CONFLICT (site_key) DO NOTHING` for idempotency
  - **Seed `keyword_configs`** from keywords.yaml:
    - For each keyword group → keyword: INSERT `group_name`, `keyword`, `enabled=true`
    - Use `ON CONFLICT (group_name, keyword) DO NOTHING`
  - **Seed `match_rules`** from keywords.yaml:
    - INSERT `rule_name='default'`, `expression` from match_rules.default, `skip_location_for` array
    - Use `ON CONFLICT (rule_name) DO NOTHING`
  - Verify data by querying counts after seed

  YAML → DB mapping for site_configs:
  ```
  YAML top-level keys (remoteok, eleduck, etc.) → site_key
  name → name
  url → url
  adapter → adapter
  enabled → enabled
  skip_location_match → skip_location_match (default false)
  rate_limit_seconds → rate_limit_seconds (default 2)
  max_pages → max_pages (nullable)
  Everything else (params, headers, api_url, api_base, clerk_base, page_size) → extra_config JSONB
  ```

  **Must NOT do**:
  - Do NOT create a permanent script file (run inline, this is one-time)
  - Do NOT modify the YAML files
  - Do NOT skip any sites or keywords

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Tasks 5, 6, 9
  - **Blocked By**: None (reads existing YAML files, writes to DB)

  **References**:
  - `config/sites.yaml:1-80` — Full sites configuration with all 7 sites and their params
  - `config/keywords.yaml` — Keywords and match rules (read to identify structure)
  - `supabase/migrations/001_initial_schema.sql:43-56` — site_configs table schema
  - `supabase/migrations/001_initial_schema.sql:63-72` — keyword_configs table schema
  - `supabase/migrations/001_initial_schema.sql:77-84` — match_rules table schema

  **Acceptance Criteria**:

  ```
  Scenario: All sites seeded correctly
    Tool: Bash (python asyncpg)
    Steps:
      1. SELECT COUNT(*) FROM site_configs → assert >= 7
      2. SELECT site_key FROM site_configs → assert contains 'remoteok', 'eleduck', 'weworkremotely', 'v2ex', 'arcdev', 'workgo', 'yuancheng'
      3. SELECT extra_config FROM site_configs WHERE site_key = 'eleduck' → assert contains 'category' key
    Expected Result: 7 sites with correct data
    Evidence: Query output

  Scenario: All keywords seeded correctly
    Tool: Bash (python asyncpg)
    Steps:
      1. SELECT COUNT(*) FROM keyword_configs → assert > 0
      2. SELECT DISTINCT group_name FROM keyword_configs → assert contains 'location', 'technology'
    Expected Result: Keywords grouped correctly
    Evidence: Query output

  Scenario: Match rules seeded
    Tool: Bash (python asyncpg)
    Steps:
      1. SELECT * FROM match_rules WHERE rule_name = 'default'
      2. Assert expression contains 'AND'
      3. Assert skip_location_for array is non-empty
    Expected Result: Default rule with correct expression and skip list
    Evidence: Query output
  ```

  **Commit**: NO (one-time DB operation, no code changes)

---

- [x] 5. Refactor Orchestrator: YAML → DB config

  **What to do**:
  - Modify `app/scraper/orchestrator.py`:
    - Remove `import yaml` and YAML file reading from `__init__`
    - Remove `sites_config_path` and `keywords_config_path` parameters from `__init__`
    - Accept `sites_config: dict` and `keywords_config: dict` (keyword groups + match rules) as constructor args
    - `sites_config` format: `{site_key: {name, url, adapter, enabled, skip_location_match, rate_limit_seconds, max_pages, ...extra_config_flattened}, ...}` — same shape adapters expect
    - Create `KeywordMatcher` from the keywords_config dict (see Task 6)
    - Keep `_ADAPTER_MAP`, `_resolve_sites()`, `_create_adapter()`, `_scrape_site()`, `run()` logic identical
  - Modify `app/services/scraper_service.py`:
    - In `ScraperService.__init__()` or in `_run_scrape()`, fetch config from DB via ConfigService before creating Orchestrator
    - Add a `_build_sites_config(rows: list[dict]) -> dict` helper that transforms ConfigService rows into the dict shape the orchestrator expects (merging DB columns + `extra_config` JSONB into flat dict per site)
    - Add a `_build_keywords_config(keywords: list[dict], rules: list[dict]) -> dict` helper that transforms keyword rows + match rule rows into the dict shape the matcher expects
    - ConfigService needs an asyncpg pool — use the shared pool (from Task 7's pool consolidation, or pass the existing scraper storage pool for now)
  - The key transformation for `_build_sites_config()`:
    ```python
    def _build_sites_config(site_rows: list[dict]) -> dict:
        result = {}
        for row in site_rows:
            cfg = {
                "name": row["name"],
                "url": row["url"],
                "adapter": row["adapter"],
                "enabled": row["enabled"],
                "skip_location_match": row["skip_location_match"],
                "rate_limit_seconds": row["rate_limit_seconds"],
                "max_pages": row["max_pages"],
            }
            # Merge extra_config JSONB into flat dict (params, headers, api_url, etc.)
            extra = row.get("extra_config") or {}
            if isinstance(extra, str):
                extra = json.loads(extra)
            cfg.update(extra)
            result[row["site_key"]] = cfg
        return result
    ```

  **Must NOT do**:
  - Do NOT modify adapter code
  - Do NOT change the pipeline logic (fetch → match → dedup → store)
  - Do NOT change `_ADAPTER_MAP` registry
  - Do NOT change `run()` return value format

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
    - Complex refactoring with config shape transformation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 6)
  - **Blocks**: Tasks 7, 9
  - **Blocked By**: Tasks 1, 3, 4

  **References**:
  - `app/scraper/orchestrator.py:32-57` — Current `__init__` with YAML loading (after Task 1 moves it)
  - `app/scraper/orchestrator.py:160-184` — `_resolve_sites()` and `_create_adapter()` logic
  - `app/services/scraper_service.py:30-33` — Current `ScraperService.__init__` creates orchestrator
  - `app/services/config_service.py:28-52` — `get_site_configs()` returns list[dict] (after Task 3 fixes)
  - `config/sites.yaml:1-80` — YAML shape that adapters currently expect (the target output shape for `_build_sites_config`)
  - `app/scraper/adapters/api.py:150-210` — EleduckAdapter uses `self.config.get("max_pages")`, `self.config.get("params")` — these keys must exist in built config

  **Acceptance Criteria**:

  ```
  Scenario: Orchestrator accepts dict config (no YAML)
    Tool: Bash (python -c)
    Steps:
      1. python -c "
         from app.scraper.orchestrator import ScraperOrchestrator
         import inspect
         sig = inspect.signature(ScraperOrchestrator.__init__)
         params = list(sig.parameters.keys())
         assert 'sites_config_path' not in params, 'Still has YAML path param'
         assert 'sites_config' in params or len(params) >= 2, 'Missing config dict param'
         print('OK: no YAML path params')
         "
    Expected Result: Constructor no longer accepts YAML paths
    Evidence: "OK" output

  Scenario: End-to-end scrape with DB config (dry run)
    Tool: Bash (uvicorn + curl)
    Preconditions: DB seeded (Task 4), ConfigService fixed (Task 3), server started
    Steps:
      1. Start server: uvicorn app.main:app --port 8000 &
      2. Wait 10s for startup
      3. curl -s -X POST http://127.0.0.1:8000/api/scrape -H "Content-Type: application/json" -d '{"sites":["eleduck"],"dry_run":true}'
      4. Capture run_id from response
      5. Wait 30s
      6. curl -s http://127.0.0.1:8000/api/scrape/status/{run_id}
      7. Assert status is "completed" (not "failed")
    Expected Result: Scrape completes using DB config
    Evidence: Status response JSON

  Scenario: No yaml import in orchestrator
    Tool: Bash (grep)
    Steps:
      1. grep -n "import yaml" app/scraper/orchestrator.py
    Expected Result: No matches (yaml import removed)
    Evidence: Empty output
  ```

  **Commit**: YES
  - Message: `refactor(orchestrator): switch from YAML files to DB-backed config via ConfigService`
  - Files: `app/scraper/orchestrator.py`, `app/services/scraper_service.py`

---

- [x] 6. Refactor Matcher: YAML → dict config

  **What to do**:
  - Modify `app/scraper/utils/matcher.py`:
    - Remove `import yaml` and YAML file reading from `__init__`
    - Remove `config_path` parameter
    - Accept `keyword_groups: dict[str, list[str]]` and `match_rules: dict` as constructor args
    - `keyword_groups` shape: `{"location": ["remote", "远程", ...], "technology": ["AI", "LLM", ...]}`
    - `match_rules` shape: `{"default": "location AND technology", "skip_location_for": ["remoteok", "weworkremotely"]}`
    - Keep all matching logic (regex compilation, CJK handling, AND/OR logic) identical
    - The `_compile_patterns()` method stays the same — it works on `self.keyword_groups` dict which is the same shape from YAML or DB
  - The `_build_keywords_config()` in scraper_service.py (Task 5) builds these dicts from DB rows:
    ```python
    def _build_keywords_config(keyword_rows, rule_rows):
        groups = {}
        for row in keyword_rows:
            if row.get("enabled", True):
                groups.setdefault(row["group_name"], []).append(row["keyword"])
        
        rules = {"default": "location AND technology", "skip_location_for": []}
        if rule_rows:
            rule = rule_rows[0]  # use first/default rule
            rules["default"] = rule["expression"]
            rules["skip_location_for"] = rule.get("skip_location_for", [])
        
        return {"keyword_groups": groups, "match_rules": rules}
    ```

  **Must NOT do**:
  - Do NOT change keyword matching logic (regex, CJK, word-boundary)
  - Do NOT change `match_job()` or `match_group()` behavior
  - Do NOT add/remove keyword groups or rules

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 5)
  - **Blocks**: Tasks 7, 9
  - **Blocked By**: Tasks 1, 3, 4

  **References**:
  - `app/scraper/utils/matcher.py` — Full file (after Task 1 moves it) — KeywordMatcher.__init__ reads YAML
  - `config/keywords.yaml` — Current YAML structure that defines the dict shape to accept
  - `app/services/scraper_service.py` — Where _build_keywords_config() helper goes (Task 5 file)

  **Acceptance Criteria**:

  ```
  Scenario: Matcher accepts dict config (no YAML)
    Tool: Bash (python -c)
    Steps:
      1. python -c "
         from app.scraper.utils.matcher import KeywordMatcher
         m = KeywordMatcher(
             keyword_groups={'technology': ['AI', 'LLM']},
             match_rules={'default': 'technology', 'skip_location_for': []}
         )
         result = m.match_job({'title': 'AI Engineer', 'description': '', 'tags': []}, 'test')
         assert result is True, 'Should match AI'
         result2 = m.match_job({'title': 'Plumber', 'description': '', 'tags': []}, 'test')
         assert result2 is False, 'Should not match Plumber'
         print('OK: matcher works with dict config')
         "
    Expected Result: Matcher correctly matches/rejects
    Evidence: "OK" output

  Scenario: No yaml import in matcher
    Tool: Bash (grep)
    Steps:
      1. grep -n "import yaml" app/scraper/utils/matcher.py
    Expected Result: No matches
    Evidence: Empty output
  ```

  **Commit**: YES (groups with Task 5)
  - Message: `refactor(matcher): accept dict config instead of YAML file path`
  - Files: `app/scraper/utils/matcher.py`

---

- [x] 7. Consolidate storage pools + fix scheduler ad-hoc pool

  **What to do**:
  - **Consolidate to 1 pool**: Currently `scraper_service.py` and `job_service.py` each create their own `SupabaseStorage` with separate asyncpg pools
    - Create a single shared pool in `app/services/storage.py` at module level:
      ```python
      _shared_storage: SupabaseStorage | None = None
      
      async def init_storage() -> None:
          global _shared_storage
          _shared_storage = SupabaseStorage()
          await _shared_storage.init_pool()
      
      async def close_storage() -> None:
          global _shared_storage
          if _shared_storage:
              await _shared_storage.close_pool()
              _shared_storage = None
      
      def get_storage() -> SupabaseStorage:
          assert _shared_storage is not None, "Storage not initialized"
          return _shared_storage
      ```
    - Remove `init_scraper_storage()` / `close_scraper_storage()` from `scraper_service.py`
    - Remove `init_job_storage()` / `close_job_storage()` from `job_service.py`
    - Update `app/main.py` lifespan: call `init_storage()` once, `close_storage()` once
    - Update `scraper_service.py`: use `get_storage()` instead of module-level `_storage`
    - Update `job_service.py`: use `get_storage()` instead of module-level `_storage`
  - **Fix scheduler ad-hoc pool**: In `app/services/scheduler.py` `_check_notifications_after_scrape()`:
    - Remove `asyncpg.create_pool()` call (lines 105-108)
    - Use `get_storage()._pool` to get the shared pool
    - Pass `pool=get_storage()._pool` to `NotificationService(pool=pool)`
  - **Increase pool size**: Change `SupabaseStorage.init_pool()` to `min_size=2, max_size=10` (was 1/5, now serving all services)
  - Update `ConfigService` init in any router that creates it to use the shared pool

  **Must NOT do**:
  - Do NOT introduce FastAPI `Depends()` DI pattern
  - Do NOT change SupabaseStorage SQL queries
  - Do NOT refactor NotificationService

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 8)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 2, 5, 6

  **References**:
  - `app/services/storage.py:52-66` — Current SupabaseStorage with pool init (min_size to increase)
  - `app/services/scraper_service.py:13-27` — `init_scraper_storage()` / `close_scraper_storage()` to remove
  - `app/services/job_service.py` — `init_job_storage()` / `close_job_storage()` to remove (find the exact function names)
  - `app/main.py:22-31` — Lifespan with 2 pool inits → replace with 1
  - `app/services/scheduler.py:103-134` — `_check_notifications_after_scrape()` with ad-hoc pool to fix
  - `app/routers/config.py` — May create ConfigService with pool — verify it uses shared pool

  **Acceptance Criteria**:

  ```
  Scenario: Single pool on startup
    Tool: Bash (uvicorn + grep)
    Steps:
      1. Start server: nohup uvicorn app.main:app --port 8000 > /tmp/server.log 2>&1 &
      2. Wait 10s
      3. grep -c "asyncpg connection pool created" /tmp/server.log
    Expected Result: Count is exactly 1
    Evidence: "1" output

  Scenario: All services work with shared pool
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. curl -s http://127.0.0.1:8000/api/health → assert status healthy
      2. curl -s http://127.0.0.1:8000/api/stats → assert returns total count
      3. curl -s http://127.0.0.1:8000/api/jobs?limit=1 → assert returns data array
      4. curl -s http://127.0.0.1:8000/api/scheduler/status → assert is_running true
    Expected Result: All endpoints respond correctly
    Evidence: Response bodies
  ```

  **Commit**: YES
  - Message: `refactor(storage): consolidate to single shared asyncpg pool`
  - Files: `app/services/storage.py`, `app/services/scraper_service.py`, `app/services/job_service.py`, `app/services/scheduler.py`, `app/main.py`

---

- [x] 8. Update Dockerfile, pyproject.toml, CLAUDE.md

  **What to do**:
  - **Dockerfile.backend**:
    - Remove: `COPY scraper/ ./scraper/` (if still present)
    - Remove: `COPY config/ ./config/` (if present)
    - Ensure `COPY app/ ./app/` covers app/scraper/ automatically
    - Remove any `COPY tests/`, `COPY data/`, `COPY scripts/` lines
  - **pyproject.toml**:
    - Remove `pyyaml` from dependencies (no longer needed)
    - Remove `aiosqlite` if still present
    - Update `packages` list: remove `"scraper"` entries, ensure `"app"` subtree covers `app.scraper`
    - Verify packages list includes: `app`, `app.config`, `app.models`, `app.routers`, `app.services`, `app.scraper`, `app.scraper.adapters`, `app.scraper.utils`
  - **CLAUDE.md**:
    - Update Architecture section: `app/scraper/` instead of `scraper/`
    - Update "Config" section: DB-backed config, no YAML files
    - Remove references to `config/sites.yaml`, `config/keywords.yaml`
    - Remove references to `tests/` directory
    - Update project structure diagram
    - Note: single shared storage pool
  - **docker-compose.override.yml** (if present):
    - Remove any volume mounts for `scraper/`, `config/`, `tests/`

  **Must NOT do**:
  - Do NOT update README.md (already outdated, out of scope)
  - Do NOT modify any Python code

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 7)
  - **Blocks**: Task 9
  - **Blocked By**: Task 1

  **References**:
  - `Dockerfile.backend` — Current COPY commands
  - `pyproject.toml` — Dependencies and packages list
  - `CLAUDE.md` — Architecture docs
  - `docker-compose.override.yml` — Volume mounts

  **Acceptance Criteria**:

  ```
  Scenario: pyproject.toml has no yaml/aiosqlite deps
    Tool: Bash (grep)
    Steps:
      1. grep -i "pyyaml\|aiosqlite" pyproject.toml
    Expected Result: No matches
    Evidence: Empty output

  Scenario: Dockerfile has no scraper/config COPY
    Tool: Bash (grep)
    Steps:
      1. grep -i "COPY scraper\|COPY config\|COPY tests" Dockerfile.backend
    Expected Result: No matches
    Evidence: Empty output
  ```

  **Commit**: YES
  - Message: `chore: update Dockerfile, pyproject.toml, CLAUDE.md for consolidated structure`
  - Files: `Dockerfile.backend`, `pyproject.toml`, `CLAUDE.md`, `docker-compose.override.yml`

---

- [x] 9. Delete old directories + final end-to-end verification

  **What to do**:
  - Delete these directories entirely:
    - `scraper/` (code moved to app/scraper/)
    - `tests/` (deleted per user decision)
    - `config/` (config now in DB)
    - `data/` (SQLite era, no longer used)
    - `scripts/` (one-time migration scripts, done)
    - `logs/` (if exists)
    - `main.py` (old CLI, if still exists)
  - Run full end-to-end verification:
    1. Server starts clean
    2. Eleduck scrape works (live, not dry-run)
    3. Stats endpoint returns data
    4. Scheduler is running
    5. No stale imports anywhere
  - Verify no Python file in the repo imports from `scraper.` (without `app.` prefix)

  **Must NOT do**:
  - Do NOT delete `app/`, `frontend/`, `supabase/`, `.sisyphus/`, `.git/`, `Dockerfile.*`, `docker-compose.*`
  - Do NOT run this task until ALL prior tasks are complete

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
    - Needs to run server, curl endpoints, verify pipeline end-to-end

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final task)
  - **Blocks**: None (last task)
  - **Blocked By**: Tasks 5, 6, 7, 8

  **References**:
  - All prior tasks — this is the integration verification step
  - `app/main.py` — Server entry point
  - `app/scraper/orchestrator.py` — Orchestrator (after refactoring)

  **Acceptance Criteria**:

  ```
  Scenario: Old directories fully removed
    Tool: Bash (test)
    Steps:
      1. test -d scraper && echo "FAIL: scraper/ exists" || echo "OK"
      2. test -d tests && echo "FAIL: tests/ exists" || echo "OK"
      3. test -d config && echo "FAIL: config/ exists" || echo "OK"
      4. test -d data && echo "FAIL: data/ exists" || echo "OK"
      5. test -d scripts && echo "FAIL: scripts/ exists" || echo "OK"
      6. test -d logs && echo "FAIL: logs/ exists" || echo "OK"
      7. test -f main.py && echo "FAIL: main.py exists" || echo "OK"
    Expected Result: All print "OK"
    Evidence: Terminal output

  Scenario: No stale scraper imports in codebase
    Tool: Bash (grep)
    Steps:
      1. grep -rn "from scraper\." --include="*.py" . | grep -v __pycache__ | grep -v ".sisyphus" | grep -v "app/scraper"
      2. grep -rn "import scraper\b" --include="*.py" . | grep -v __pycache__ | grep -v ".sisyphus"
    Expected Result: Both empty
    Evidence: Empty output

  Scenario: Server starts cleanly
    Tool: Bash (uvicorn + curl)
    Steps:
      1. Start: nohup uvicorn app.main:app --port 8000 > /tmp/final.log 2>&1 &
      2. Wait 12s
      3. Assert: grep "Application startup complete" /tmp/final.log
      4. Assert: NO "RuntimeWarning" in /tmp/final.log
      5. Assert: grep -c "asyncpg connection pool created" /tmp/final.log == 1
      6. curl -s http://127.0.0.1:8000/api/health | assert "healthy"
    Expected Result: Clean startup, single pool, healthy
    Evidence: Log file + health response

  Scenario: Live Eleduck scrape end-to-end
    Tool: Bash (curl)
    Preconditions: Server running on port 8000
    Steps:
      1. curl -s -X POST http://127.0.0.1:8000/api/scrape -H "Content-Type: application/json" -d '{"sites":["eleduck"],"dry_run":false}'
      2. Capture run_id
      3. Wait 45s (5 pages × rate limiting)
      4. curl -s http://127.0.0.1:8000/api/scrape/status/{run_id}
      5. Assert status == "completed"
      6. Assert new > 0 OR updated > 0
      7. curl -s http://127.0.0.1:8000/api/stats
      8. Assert by_source.eleduck > 0
    Expected Result: Scrape completes, data in DB
    Evidence: Status + stats response JSON

  Scenario: Scheduler active
    Tool: Bash (curl)
    Steps:
      1. curl -s http://127.0.0.1:8000/api/scheduler/status
      2. Assert is_running == true
      3. Assert next_run_time is not null
    Expected Result: Scheduler running with next fire time
    Evidence: Response JSON
  ```

  **Commit**: YES
  - Message: `chore: remove old scraper/, tests/, config/, data/ directories`
  - Files: deleted directories

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `refactor: move scraper/ to app/scraper/ and update all imports` | app/scraper/**, app/services/* | python -c imports |
| 2 | `fix: remove asyncio.run() from JobPosting module-level init` | app/scraper/models.py | python -W error import |
| 3 | `fix(config): correct column names, add keyword enabled column and match rules reader` | app/services/config_service.py, supabase/migrations/004* | DB query test |
| 5+6 | `refactor(orchestrator,matcher): switch from YAML to DB-backed config` | app/scraper/orchestrator.py, app/scraper/utils/matcher.py, app/services/scraper_service.py | dry-run scrape |
| 7 | `refactor(storage): consolidate to single shared asyncpg pool` | app/services/*.py, app/main.py | pool count check |
| 8 | `chore: update Dockerfile, pyproject.toml, CLAUDE.md` | Dockerfile.backend, pyproject.toml, CLAUDE.md | grep checks |
| 9 | `chore: remove old scraper/, tests/, config/, data/ directories` | deleted dirs | full E2E |

---

## Success Criteria

### Verification Commands
```bash
# Server starts clean (no warnings, single pool)
uvicorn app.main:app --port 8000 2>&1 | head -15
# Expected: 1x "asyncpg connection pool created", no RuntimeWarning

# Import integrity
python -c "from app.scraper.orchestrator import ScraperOrchestrator; print('OK')"
# Expected: OK

# Scrape works
curl -s -X POST http://localhost:8000/api/scrape -H "Content-Type: application/json" -d '{"sites":["eleduck"],"dry_run":true}'
# Expected: {"run_id":"...","status":"started"}

# No old directories
ls scraper/ tests/ config/ data/ 2>&1
# Expected: all "No such file or directory"

# No yaml dependency
grep -i pyyaml pyproject.toml
# Expected: empty
```

### Final Checklist
- [x] All scraper code in app/scraper/ with correct imports
- [x] Orchestrator + Matcher read config from DB (no YAML)
- [x] Single shared asyncpg pool (1 init in startup logs)
- [x] No RuntimeWarning from models.py
- [x] ConfigService works (correct column names, match_rules reader)
- [x] DB seeded with all sites, keywords, match rules
- [x] Old directories deleted (scraper/, tests/, config/, data/, scripts/, logs/)
- [x] Dockerfile + pyproject.toml updated
- [x] CLAUDE.md reflects new architecture
- [x] Live Eleduck scrape completes successfully
