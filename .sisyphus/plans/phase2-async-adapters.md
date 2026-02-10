# Plan: Phase 2 — Async Migration + New Data Sources

> Remote AI Job Scraper — Phase 2
> Depends on: Phase 1 MVP (complete, 128 tests, commit 4062f15)
> Created: 2026-02-10

## TL;DR

> **Quick Summary**: Migrate the entire scraper from synchronous to async (httpx.AsyncClient + aiosqlite), add 4 new data sources (workgo.ai, V2EX, Arc.dev, 远程.work), implement cross-site deduplication, and add pagination support.
>
> **Deliverables**:
> - Async-migrated core (adapters, storage, orchestrator, CLI)
> - 4 new adapters: WorkGoAdapter (Playwright), V2EXAdapter (hybrid HTML+API), ArcDevAdapter (Playwright), YuanchengAdapter (HTML/BS4)
> - Cross-site dedup utility (company+title similarity)
> - Pagination support for adapters that support it
> - All existing + new tests passing
>
> **Estimated Effort**: Large (XL)
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Task 1 (source validator) → Task 2 (async migration) → Tasks 3-8 (parallel adapters + features) → Task 9 (integration)

---

## Context

### Original Request
User requested adding workgo.ai as a new data source. During interview, scope expanded to full Phase 2: async migration + all 4 planned new sources + cross-site dedup + pagination.

### Interview Summary
**Key Discussions**:
- workgo.ai requires Clerk JWT auth → Playwright browser automation chosen
- User has existing workgo.ai account, credentials in .env
- All existing adapters to be migrated from sync to async
- TDD with mocked responses for all new adapters
- Full Phase 2 scope: V2EX, Arc.dev, 远程.work also included

**Research Findings**:
- workgo.ai: React SPA, API at api.workgo.ai, POST /auth/jobs/all (paginated, Clerk JWT required)
- V2EX: HTML list + public API detail, rate limit 600 req/hour
- Arc.dev: Next.js SPA, needs Playwright (selectors TBD — need live investigation)
- 远程.work: WordPress site, shows "0 positions, 0 users" but has listings, possibly unreliable
- Existing codebase: BaseAdapter ABC, 3 sync adapters, SQLite storage, 128 tests

### Metis Review
**Identified Gaps** (addressed):
- **CRITICAL**: `validate_source` in models.py has hardcoded valid sources set → must update to accept new source IDs
- **CRITICAL**: Async migration touches EVERY core file → must be gated before new adapters
- **Scope clarification**: Pagination "for all adapters" is misleading — RemoteOK returns all jobs in one response, WWR RSS has no pagination. Lock scope to "adapters that support it" (Eleduck, WorkGo, V2EX, Arc.dev)
- **Missing**: Playwright dependency installation + browser binary management
- **Missing**: How to handle Playwright in tests (mock vs real browser)
- **Missing**: aiosqlite connection pool strategy
- **Missing**: 远程.work reliability concern (may return empty data)

---

## Work Objectives

### Core Objective
Migrate the scraper to async architecture and expand from 3 to 7 data sources, with cross-site deduplication.

### Concrete Deliverables
- Async core: `scraper/adapters/base.py`, `scraper/utils/storage.py`, `scraper/orchestrator.py`, `main.py` all async
- New file: `scraper/adapters/browser.py` (WorkGoAdapter, ArcDevAdapter)
- New file: `scraper/adapters/hybrid.py` (V2EXAdapter)
- New file: `scraper/adapters/html.py` (YuanchengAdapter)
- New file: `scraper/utils/dedup.py` (cross-site deduplication)
- Updated: `config/sites.yaml` (4 new site entries)
- Updated: `scraper/models.py` (new valid sources)
- Updated: `.env.example` (WORKGO_EMAIL, WORKGO_PASSWORD)
- Updated: `pyproject.toml` (playwright, aiosqlite dependencies)
- New tests for each adapter + dedup + async integration

### Definition of Done
- [x] All existing 128 tests still pass (after async migration)
- [x] All new adapter tests pass
- [x] `python main.py scrape --verbose` fetches from all 7 sources
- [x] `python main.py stats` shows data from all active sources
- [x] Cross-site dedup removes duplicate jobs across sources

### Must Have
- Async migration of ALL existing adapters (not just new ones)
- Playwright-based adapters for workgo.ai and Arc.dev
- Environment variable auth for workgo.ai (WORKGO_EMAIL, WORKGO_PASSWORD)
- TDD for all new adapters
- Backward-compatible CLI interface

### Must NOT Have (Guardrails)
- NO circuit breaker (Phase 3)
- NO notifications (Phase 3)
- NO Docker (Phase 3)
- NO match scoring/ranking (Phase 4)
- NO Notion/Google Sheets integration (Phase 4)
- NO CI/CD setup (out of scope)
- DO NOT copy brainstorm pseudocode verbatim — APIs are incorrect
- DO NOT add sync wrappers for Playwright — use native async
- DO NOT change the CLI interface (scrape/stats/export commands unchanged)
- DO NOT add new CLI subcommands
- DO NOT over-abstract adapter types — concrete classes are fine

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.

### Test Decision
- **Infrastructure exists**: YES (pytest, 128 tests)
- **Automated tests**: YES (TDD for new adapters, tests-after for async migration)
- **Framework**: pytest + pytest-asyncio

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

Verification tools by deliverable type:

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| Async adapters | Bash (pytest) | Run async tests with pytest-asyncio |
| Playwright adapters | Bash (pytest) | Mocked browser tests, no live browser needed in CI |
| CLI | Bash | Run main.py commands, assert output |
| Storage | Bash (pytest) | Async DB tests with temp files |
| Dedup | Bash (pytest) | Unit tests with fixture data |

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — Sequential, must complete first):
├── Task 1: Update source validator + add dependencies
└── Task 2: Async migration of existing codebase

Wave 2 (Expansion — Parallel after Wave 1):
├── Task 3: WorkGo Playwright adapter (TDD)
├── Task 4: V2EX hybrid adapter (TDD)
├── Task 5: 远程.work HTML adapter (TDD)
├── Task 6: Arc.dev Playwright adapter (TDD)
├── Task 7: Cross-site dedup utility (TDD)
└── Task 8: Pagination enhancement

Wave 3 (Integration — After Wave 2):
└── Task 9: Full integration test + verification
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2 | None |
| 2 | 1 | 3,4,5,6,7,8 | None |
| 3 | 2 | 9 | 4,5,6,7,8 |
| 4 | 2 | 9 | 3,5,6,7,8 |
| 5 | 2 | 9 | 3,4,6,7,8 |
| 6 | 2 | 9 | 3,4,5,7,8 |
| 7 | 2 | 9 | 3,4,5,6,8 |
| 8 | 2 | 9 | 3,4,5,6,7 |
| 9 | 3,4,5,6,7,8 | None | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2 | Sequential: task(category="unspecified-high") |
| 2 | 3-8 | Parallel: up to 6 agents simultaneously |
| 3 | 9 | Final: task(category="unspecified-high") |

---

## TODOs

### Task 1: Update Source Validator + Add Dependencies

**What to do**:
- Update `scraper/models.py` `validate_source` field_validator to accept new source IDs: `workgo`, `v2ex`, `arcdev`, `yuancheng` (in addition to existing `remoteok`, `eleduck`, `weworkremotely`)
- Make the validator data-driven: read valid sources from a constant `VALID_SOURCES` set (not hardcoded in the validator body) so future sources don't require code changes
- Update `pyproject.toml` dependencies: add `playwright>=1.40.0`, `aiosqlite>=0.19.0`, `pytest-asyncio>=0.23.0` (dev)
- Update `.env.example`: add `WORKGO_EMAIL=`, `WORKGO_PASSWORD=`
- Update `main.py` CLI `--site` choices to include new sources
- Run `pip install -e ".[dev]"` to install new deps
- Run `playwright install chromium` to install browser binary

**Must NOT do**:
- Do NOT change any adapter logic yet
- Do NOT migrate to async yet — this is a prep task only

**Recommended Agent Profile**:
- **Category**: `quick`
- **Skills**: []
  - Simple config/model changes, no complex logic

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 1 (sequential)
- **Blocks**: Task 2
- **Blocked By**: None

**References**:
- `scraper/models.py:49-53` — `validate_source` field_validator with hardcoded set `{"remoteok", "eleduck", "weworkremotely"}`
- `pyproject.toml:25-34` — current dependencies list
- `pyproject.toml:36-39` — dev dependencies
- `.env.example` — current env template
- `main.py:132-137` — `--site` argparse choices

**Acceptance Criteria**:
- [x] `python -c "from scraper.models import JobPosting; JobPosting(id='x',title='t',url='u',source='workgo',first_seen=...,last_seen=...,last_updated=...)"` → no validation error
- [x] Same for sources: `v2ex`, `arcdev`, `yuancheng`
- [x] `python -m pytest tests/ -v` → all 128 existing tests still pass
- [x] `playwright install chromium` completes without error
- [x] `python -c "import aiosqlite; print('OK')"` → prints OK
- [x] `.env.example` contains WORKGO_EMAIL and WORKGO_PASSWORD lines

**Agent-Executed QA Scenarios**:
```
Scenario: New sources pass validation
  Tool: Bash
  Steps:
    1. python -c "from scraper.models import JobPosting; from datetime import datetime; n=datetime.now(); j=JobPosting(id='test',title='Test',url='http://test.com',source='workgo',first_seen=n,last_seen=n,last_updated=n); print(j.source)"
    2. Assert: output is "workgo"
    3. Repeat for v2ex, arcdev, yuancheng
  Expected Result: All 4 new sources accepted
  Evidence: Terminal output captured

Scenario: Existing tests unbroken
  Tool: Bash
  Steps:
    1. python -m pytest tests/ -v
    2. Assert: 128 passed, 0 failed
  Expected Result: No regressions
  Evidence: pytest output captured
```

**Commit**: YES
- Message: `feat(models): add Phase 2 source IDs and async dependencies`
- Files: `scraper/models.py`, `pyproject.toml`, `.env.example`, `main.py`
- Pre-commit: `python -m pytest tests/ -v`

---

### Task 2: Async Migration of Existing Codebase

**What to do**:
- Migrate `scraper/adapters/base.py`:
  - `BaseAdapter.fetch_jobs()` → `async def fetch_jobs()`
  - `_get_client()` → return `httpx.AsyncClient` context manager
  - `_delay()` → `async def _delay()` using `asyncio.sleep()`
- Migrate `scraper/adapters/api.py`:
  - `RemoteOKAdapter.fetch_jobs()` → `async def fetch_jobs()`
  - `EleduckAdapter.fetch_jobs()` → `async def fetch_jobs()` (paginated with async)
  - All `client.get()` calls → `await client.get()`
  - All `with self._get_client() as client` → `async with self._get_client() as client`
- Migrate `scraper/adapters/rss.py`:
  - `WeWorkRemotelyAdapter.fetch_jobs()` → `async def fetch_jobs()`
  - HTTP fetch async, feedparser still sync (it's CPU-bound parsing, fine to keep sync)
- Migrate `scraper/utils/storage.py`:
  - Replace `import sqlite3` with `import aiosqlite`
  - `StorageManager.__init__()` → lazy connection (async context manager)
  - `upsert_job()` → `async def upsert_job()`
  - `get_all_jobs()` → `async def get_all_jobs()`
  - `get_stats()` → `async def get_stats()`
  - `export_json()` → `async def export_json()`
  - Use `async with aiosqlite.connect(path) as db:` pattern
- Migrate `scraper/orchestrator.py`:
  - `ScraperOrchestrator.run()` → `async def run()`
  - `_scrape_site()` → `async def _scrape_site()`
  - Run adapters with `asyncio.gather()` for parallel fetching (with semaphore for rate limiting)
- Migrate `main.py`:
  - `cmd_scrape()` → use `asyncio.run()` to launch async orchestrator
  - `cmd_export()` → `asyncio.run()` wrapper
  - `cmd_stats()` → `asyncio.run()` wrapper
- Migrate ALL existing tests:
  - Add `@pytest.mark.asyncio` to async test functions
  - Update mock patterns for async context managers
  - Update `conftest.py` or add `pytest.ini` with `asyncio_mode = auto`
- Verify: ALL 128 existing tests pass after migration

**Must NOT do**:
- Do NOT add new adapters yet — pure refactor only
- Do NOT change any business logic (matching, field mapping)
- Do NOT change CLI interface or command names
- Do NOT add new features — this is a mechanical migration
- Do NOT use `sync_to_async` wrappers — migrate properly

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
- **Skills**: []
  - Large refactor touching every core file, needs careful attention to async/await patterns

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 1 (sequential, after Task 1)
- **Blocks**: Tasks 3, 4, 5, 6, 7, 8
- **Blocked By**: Task 1

**References**:
- `scraper/adapters/base.py` — full file, BaseAdapter ABC with `_get_client()`, `_delay()`, `fetch_jobs()`
- `scraper/adapters/api.py` — full file, RemoteOKAdapter + EleduckAdapter with sync httpx
- `scraper/adapters/rss.py` — full file, WeWorkRemotelyAdapter with sync httpx + feedparser
- `scraper/utils/storage.py` — full file, StorageManager with sqlite3
- `scraper/orchestrator.py` — full file, ScraperOrchestrator with sequential site loop
- `main.py` — full file, CLI with sync command handlers
- `tests/` — all test files need async migration
- httpx async docs: https://www.python-httpx.org/async/
- aiosqlite docs: https://aiosqlite.omnilib.dev/en/stable/
- pytest-asyncio docs: https://pytest-asyncio.readthedocs.io/en/latest/

**Acceptance Criteria**:
- [x] `python -m pytest tests/ -v` → ALL 128 tests pass (no regressions)
- [x] `python main.py scrape --verbose` → fetches from all 3 existing sources (async)
- [x] `python main.py stats` → shows correct statistics
- [x] `python main.py export --format json` → creates valid JSON export
- [x] No sync httpx or sqlite3 imports remain in scraper/ (only aiosqlite, httpx.AsyncClient)
- [x] `grep -r "httpx.Client" scraper/` → 0 matches (only AsyncClient)
- [x] `grep -r "import sqlite3" scraper/` → 0 matches (only aiosqlite)

**Agent-Executed QA Scenarios**:
```
Scenario: All existing tests pass after async migration
  Tool: Bash
  Steps:
    1. python -m pytest tests/ -v
    2. Assert: 128 passed, 0 failed
  Expected Result: Zero regressions
  Evidence: Full pytest output captured

Scenario: Live scrape works with async
  Tool: Bash
  Steps:
    1. python main.py --verbose scrape
    2. Assert: output contains "Total fetched" with number > 0
    3. Assert: output contains "Matched" with number > 0
  Expected Result: Async pipeline fetches real data
  Evidence: Terminal output captured

Scenario: No sync code remains
  Tool: Bash (grep)
  Steps:
    1. grep -r "httpx.Client" scraper/ (should find 0 matches or only AsyncClient)
    2. grep -r "import sqlite3" scraper/ (should find 0 matches)
  Expected Result: All sync code migrated
  Evidence: grep output captured
```

**Commit**: YES
- Message: `refactor: migrate entire codebase from sync to async (httpx.AsyncClient + aiosqlite)`
- Files: all files in scraper/, main.py, all test files
- Pre-commit: `python -m pytest tests/ -v`

---

### Task 3: WorkGo Playwright Adapter (TDD)

**What to do**:
- Create `scraper/adapters/browser.py` with `WorkGoAdapter(BaseAdapter)`:
  - `name` → "WorkGo"
  - `source_id` → "workgo"
  - `async def fetch_jobs()`:
    1. Launch Playwright Chromium (headless)
    2. Navigate to workgo.ai login page
    3. Authenticate via Clerk using WORKGO_EMAIL / WORKGO_PASSWORD from env
    4. Navigate to /dashboard/job/job-search
    5. Intercept network request to `POST /auth/jobs/all` response
    6. Extract job data from intercepted JSON response
    7. Handle pagination: increment page param, re-request until no more pages
    8. Parse each job into JobPosting model
    9. Close browser
  - `_parse_entry(entry: dict) -> JobPosting | None` static method
  - Handle auth failures gracefully (log error, return empty list)
  - Handle session expiration (retry login once)
- Add `workgo` to `config/sites.yaml`:
  ```yaml
  workgo:
    enabled: true
    adapter: browser
    url: https://workgo.ai
    api_base: https://api.workgo.ai
    max_pages: 5
    rate_limit_seconds: 3
  ```
- Register in `scraper/orchestrator.py` `_ADAPTER_MAP`: `"workgo": WorkGoAdapter`
- Create fixture: `tests/fixtures/workgo_sample.json` — sample API response (captured manually or fabricated from known field structure)
- Write TDD tests: `tests/test_adapters/test_workgo.py`

**Must NOT do**:
- Do NOT store credentials in code or config files — .env only
- Do NOT keep browser open between scrape runs — launch and close per run
- Do NOT use visible browser mode in production — always headless
- Do NOT skip error handling for auth — Clerk login can fail

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
- **Skills**: [`playwright`]
  - `playwright`: Needed for Clerk auth flow and network interception patterns

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 4, 5, 6, 7, 8)
- **Blocks**: Task 9
- **Blocked By**: Task 2

**References**:
- `scraper/adapters/base.py` — BaseAdapter ABC to inherit from
- `scraper/adapters/api.py` — RemoteOKAdapter._parse_entry() pattern for field mapping
- `tests/test_adapters/test_remoteok.py` — Test fixture and mocking patterns
- workgo.ai API discovery: POST /auth/jobs/all with {"page": 1, "page_size": 20}, response has `data` array and `pagination` object
- Job fields: id, title, company, description, location, salary, job_type, tags, skills_required, experience_level, published_at
- Clerk auth: clerk.workgo.ai (email + password login flow)
- `.env.example` — WORKGO_EMAIL, WORKGO_PASSWORD variables

**Acceptance Criteria**:
- [x] `scraper/adapters/browser.py` exists with WorkGoAdapter class
- [x] `tests/test_adapters/test_workgo.py` exists with TDD tests
- [x] `tests/fixtures/workgo_sample.json` exists with sample data
- [x] `python -m pytest tests/test_adapters/test_workgo.py -v` → all tests pass
- [x] `python -m pytest tests/ -v` → all tests pass (no regressions)
- [x] WorkGoAdapter reads WORKGO_EMAIL and WORKGO_PASSWORD from environment
- [x] WorkGoAdapter handles missing credentials gracefully (logs error, returns [])

**Agent-Executed QA Scenarios**:
```
Scenario: WorkGo adapter tests pass
  Tool: Bash
  Steps:
    1. python -m pytest tests/test_adapters/test_workgo.py -v
    2. Assert: all tests pass
  Expected Result: TDD tests green
  Evidence: pytest output captured

Scenario: Missing credentials handled gracefully
  Tool: Bash
  Steps:
    1. unset WORKGO_EMAIL && unset WORKGO_PASSWORD
    2. python -c "import asyncio; from scraper.adapters.browser import WorkGoAdapter; a=WorkGoAdapter({'url':'https://workgo.ai','api_base':'https://api.workgo.ai'}); print(asyncio.run(a.fetch_jobs()))"
    3. Assert: returns empty list, no crash
  Expected Result: Graceful degradation
  Evidence: Terminal output captured

Scenario: Full test suite unbroken
  Tool: Bash
  Steps:
    1. python -m pytest tests/ -v
    2. Assert: 0 failures
  Expected Result: No regressions
  Evidence: pytest output captured
```

**Commit**: YES
- Message: `feat(adapters): add WorkGo Playwright adapter with Clerk auth`
- Files: `scraper/adapters/browser.py`, `tests/test_adapters/test_workgo.py`, `tests/fixtures/workgo_sample.json`, `config/sites.yaml`, `scraper/orchestrator.py`
- Pre-commit: `python -m pytest tests/ -v`

---

### Task 4: V2EX Hybrid Adapter (TDD)

**What to do**:
- Create `scraper/adapters/hybrid.py` with `V2EXAdapter(BaseAdapter)`:
  - `name` → "V2EX"
  - `source_id` → "v2ex"
  - `async def fetch_jobs()`:
    1. Fetch job listing page (HTML): `https://www.v2ex.com/go/remote` or similar job node
    2. Parse HTML with BeautifulSoup to extract topic IDs and titles
    3. For each topic, fetch detail via V2EX public API: `https://www.v2ex.com/api/v2/topics/{id}` (needs token) or `https://www.v2ex.com/api/topics/show.json?id={id}`
    4. Map API response to JobPosting
    5. Respect rate limit: 600 req/hour (~1 req/6s)
  - `_parse_listing_page(html: str) -> list[dict]` — extract topic IDs from HTML
  - `_parse_topic(data: dict) -> JobPosting | None` — map API response to model
- Add `v2ex` to `config/sites.yaml`
- Register in orchestrator `_ADAPTER_MAP`
- Create fixtures: `tests/fixtures/v2ex_listing.html`, `tests/fixtures/v2ex_topic.json`
- Write TDD tests

**Must NOT do**:
- Do NOT exceed V2EX rate limit (600 req/hour)
- Do NOT scrape user profiles or non-job content
- Do NOT use the V2EX API v2 if it requires auth — use v1 public API

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
- **Skills**: []
  - HTML parsing + API integration, no browser needed

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 3, 5, 6, 7, 8)
- **Blocks**: Task 9
- **Blocked By**: Task 2

**References**:
- `scraper/adapters/base.py` — BaseAdapter ABC
- `scraper/adapters/rss.py` — WeWorkRemotelyAdapter for HTML fetch + parse pattern
- V2EX API v1: `https://www.v2ex.com/api/topics/show.json?id={id}` — public, no auth
- V2EX job nodes: `/go/remote`, `/go/jobs` — HTML list pages
- V2EX rate limit: 600 req/hour (from `x-rate-limit-limit` header, Phase 1 research)
- `tests/test_adapters/test_wwr.py` — test pattern for adapters with fixture data

**Acceptance Criteria**:
- [x] `scraper/adapters/hybrid.py` exists with V2EXAdapter
- [x] `tests/test_adapters/test_v2ex.py` exists with TDD tests
- [x] `tests/fixtures/v2ex_listing.html` and `tests/fixtures/v2ex_topic.json` exist
- [x] `python -m pytest tests/test_adapters/test_v2ex.py -v` → all tests pass
- [x] `python -m pytest tests/ -v` → all tests pass (no regressions)
- [x] Rate limiting respected (delay between API calls)

**Agent-Executed QA Scenarios**:
```
Scenario: V2EX adapter tests pass
  Tool: Bash
  Steps:
    1. python -m pytest tests/test_adapters/test_v2ex.py -v
    2. Assert: all tests pass
  Expected Result: TDD tests green
  Evidence: pytest output captured

Scenario: HTML parsing extracts topic IDs
  Tool: Bash
  Steps:
    1. python -c "from scraper.adapters.hybrid import V2EXAdapter; ..." (test with fixture HTML)
    2. Assert: returns list of topic dicts with IDs
  Expected Result: HTML parsed correctly
  Evidence: Terminal output captured
```

**Commit**: YES
- Message: `feat(adapters): add V2EX hybrid adapter (HTML list + API detail)`
- Files: `scraper/adapters/hybrid.py`, `tests/test_adapters/test_v2ex.py`, `tests/fixtures/v2ex_*`, `config/sites.yaml`, `scraper/orchestrator.py`
- Pre-commit: `python -m pytest tests/ -v`

---

### Task 5: 远程.work HTML Adapter (TDD)

**What to do**:
- Create `scraper/adapters/html.py` with `YuanchengAdapter(BaseAdapter)`:
  - `name` → "远程.work"
  - `source_id` → "yuancheng"
  - `async def fetch_jobs()`:
    1. Fetch job listing page(s) from 远程.work
    2. Parse HTML with BeautifulSoup
    3. Extract job details from listing cards (title, company, location, tags, URL)
    4. Optionally fetch detail pages for full descriptions
    5. Map to JobPosting model
  - Handle empty/unreliable responses (site showed "0 positions" during research)
- Add `yuancheng` to `config/sites.yaml` (disabled by default due to reliability concerns)
- Register in orchestrator `_ADAPTER_MAP`
- Create fixture: `tests/fixtures/yuancheng_listing.html`
- Write TDD tests
- **IMPORTANT**: Live-probe the site first to verify it's still serving data before writing the adapter. If site is down/empty, implement adapter skeleton with tests but mark as `enabled: false` in config.

**Must NOT do**:
- Do NOT assume site structure — must probe live site first
- Do NOT crash if site returns empty/0 results — handle gracefully

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
- **Skills**: [`playwright`]
  - `playwright`: Needed to probe the live site and verify structure, take screenshots
  - HTML parsing with BS4 for the actual adapter

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 3, 4, 6, 7, 8)
- **Blocks**: Task 9
- **Blocked By**: Task 2

**References**:
- `scraper/adapters/base.py` — BaseAdapter ABC
- `scraper/adapters/rss.py` — WeWorkRemotelyAdapter for HTML fetch pattern
- 远程.work research: WordPress site, showed "0 positions, 0 users" during Phase 1 research but had listings
- `tests/test_adapters/test_wwr.py` — test patterns

**Acceptance Criteria**:
- [x] `scraper/adapters/html.py` exists with YuanchengAdapter
- [x] `tests/test_adapters/test_yuancheng.py` exists with TDD tests
- [x] `tests/fixtures/yuancheng_listing.html` exists
- [x] `python -m pytest tests/test_adapters/test_yuancheng.py -v` → all tests pass
- [x] `python -m pytest tests/ -v` → all tests pass (no regressions)
- [x] Adapter handles empty response gracefully (returns [])

**Agent-Executed QA Scenarios**:
```
Scenario: Yuancheng adapter tests pass
  Tool: Bash
  Steps:
    1. python -m pytest tests/test_adapters/test_yuancheng.py -v
    2. Assert: all tests pass
  Expected Result: TDD tests green
  Evidence: pytest output captured

Scenario: Empty response handled gracefully
  Tool: Bash
  Steps:
    1. Test with empty HTML fixture → returns []
    2. Assert: no exceptions
  Expected Result: Graceful degradation
  Evidence: Terminal output captured
```

**Commit**: YES
- Message: `feat(adapters): add 远程.work HTML adapter (WordPress scraping)`
- Files: `scraper/adapters/html.py`, `tests/test_adapters/test_yuancheng.py`, `tests/fixtures/yuancheng_*`, `config/sites.yaml`, `scraper/orchestrator.py`
- Pre-commit: `python -m pytest tests/ -v`

---

### Task 6: Arc.dev Playwright Adapter (TDD)

**What to do**:
- Add `ArcDevAdapter(BaseAdapter)` to `scraper/adapters/browser.py`:
  - `name` → "Arc.dev"
  - `source_id` → "arcdev"
  - `async def fetch_jobs()`:
    1. Launch Playwright Chromium (headless)
    2. Navigate to Arc.dev remote jobs page (https://arc.dev/remote-jobs or similar)
    3. Arc.dev is a Next.js SPA — intercept API/data responses OR extract from DOM
    4. Handle infinite scroll or pagination
    5. Parse job data into JobPosting model
    6. Close browser
  - **IMPORTANT**: Selectors are TBD — agent must live-probe the site first to determine:
    - Exact URL for remote job listings
    - Whether it uses API calls (intercept) or SSR (parse HTML)
    - DOM selectors for job cards, pagination
    - Available fields (title, company, salary, etc.)
- Add `arcdev` to `config/sites.yaml`
- Register in orchestrator `_ADAPTER_MAP`
- Create fixture: `tests/fixtures/arcdev_sample.json` or `.html`
- Write TDD tests

**Must NOT do**:
- Do NOT assume selectors — must discover by probing live site
- Do NOT use playwright-stealth (the pseudocode API is wrong) — basic Playwright is sufficient
- Do NOT keep browser open between runs

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
- **Skills**: [`playwright`]
  - `playwright`: Essential for probing Arc.dev SPA and writing browser adapter

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 3, 4, 5, 7, 8)
- **Blocks**: Task 9
- **Blocked By**: Task 2

**References**:
- `scraper/adapters/browser.py` — WorkGoAdapter pattern (from Task 3, same file)
- `scraper/adapters/base.py` — BaseAdapter ABC
- Arc.dev: Next.js SPA confirmed (Phase 1 research), selectors TBD
- `tests/test_adapters/test_workgo.py` — Playwright test mocking pattern (from Task 3)

**Acceptance Criteria**:
- [x] `ArcDevAdapter` class added to `scraper/adapters/browser.py`
- [x] `tests/test_adapters/test_arcdev.py` exists with TDD tests
- [x] `tests/fixtures/arcdev_sample.*` exists
- [x] `python -m pytest tests/test_adapters/test_arcdev.py -v` → all tests pass
- [x] `python -m pytest tests/ -v` → all tests pass (no regressions)

**Agent-Executed QA Scenarios**:
```
Scenario: Arc.dev adapter tests pass
  Tool: Bash
  Steps:
    1. python -m pytest tests/test_adapters/test_arcdev.py -v
    2. Assert: all tests pass
  Expected Result: TDD tests green
  Evidence: pytest output captured

Scenario: Full test suite unbroken
  Tool: Bash
  Steps:
    1. python -m pytest tests/ -v
    2. Assert: 0 failures
  Expected Result: No regressions
  Evidence: pytest output captured
```

**Commit**: YES
- Message: `feat(adapters): add Arc.dev Playwright adapter (Next.js SPA)`
- Files: `scraper/adapters/browser.py`, `tests/test_adapters/test_arcdev.py`, `tests/fixtures/arcdev_*`, `config/sites.yaml`, `scraper/orchestrator.py`
- Pre-commit: `python -m pytest tests/ -v`

---

### Task 7: Cross-Site Deduplication Utility (TDD)

**What to do**:
- Create `scraper/utils/dedup.py` with `DedupManager`:
  - `find_duplicates(jobs: list[JobPosting]) -> list[tuple[JobPosting, JobPosting]]` — find duplicate pairs
  - Dedup strategy: normalize company name + title, compute similarity
    - Company name normalization: lowercase, strip "Inc", "Ltd", "LLC", etc.
    - Title normalization: lowercase, strip common prefixes ("Senior", "Junior", "Lead")
    - Similarity: exact match after normalization, or fuzzy match (>0.85 ratio)
  - `merge_duplicates(original: JobPosting, duplicate: JobPosting) -> JobPosting` — merge fields, keep earliest first_seen, latest last_seen
  - Use `difflib.SequenceMatcher` for fuzzy string matching (stdlib, no new dependency)
- Integrate into `scraper/orchestrator.py`: run dedup after all adapters complete, before storage
- Write TDD tests: `tests/test_dedup.py`

**Must NOT do**:
- Do NOT add external fuzzy matching libraries (use stdlib difflib)
- Do NOT dedup within same source (only cross-source)
- Do NOT delete duplicates from DB — mark or skip, preserve data

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
- **Skills**: []
  - String comparison algorithms, no browser/UI needed

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 3, 4, 5, 6, 8)
- **Blocks**: Task 9
- **Blocked By**: Task 2

**References**:
- `scraper/models.py` — JobPosting model fields (title, company, url, source)
- `scraper/orchestrator.py` — integration point after `_scrape_site()` loop
- `scraper/utils/storage.py` — StorageManager.upsert_job() for how jobs are saved
- Python difflib docs: https://docs.python.org/3/library/difflib.html#difflib.SequenceMatcher

**Acceptance Criteria**:
- [x] `scraper/utils/dedup.py` exists with DedupManager class
- [x] `tests/test_dedup.py` exists with TDD tests
- [x] Dedup detects: same job posted on RemoteOK and WeWorkRemotely (different source, same company+title)
- [x] Dedup does NOT flag: different jobs at same company
- [x] `python -m pytest tests/test_dedup.py -v` → all tests pass
- [x] `python -m pytest tests/ -v` → all tests pass (no regressions)

**Agent-Executed QA Scenarios**:
```
Scenario: Dedup detects cross-source duplicates
  Tool: Bash
  Steps:
    1. python -m pytest tests/test_dedup.py -v -k "test_cross_source"
    2. Assert: test passes, duplicates detected
  Expected Result: Same job from different sources identified
  Evidence: pytest output captured

Scenario: Dedup ignores different jobs at same company
  Tool: Bash
  Steps:
    1. python -m pytest tests/test_dedup.py -v -k "test_different_jobs"
    2. Assert: test passes, no false positives
  Expected Result: No false dedup
  Evidence: pytest output captured
```

**Commit**: YES
- Message: `feat(utils): add cross-site job deduplication`
- Files: `scraper/utils/dedup.py`, `tests/test_dedup.py`, `scraper/orchestrator.py`
- Pre-commit: `python -m pytest tests/ -v`

---

### Task 8: Pagination Enhancement

**What to do**:
- Enhance pagination support for adapters that support it:
  - `EleduckAdapter`: already has pagination (max_pages config) — verify still works after async migration
  - `WorkGoAdapter`: paginated via page/page_size params (implemented in Task 3)
  - `V2EXAdapter`: paginate HTML listing pages if multi-page (implemented in Task 4)
  - `ArcDevAdapter`: handle infinite scroll or page-based (implemented in Task 6)
- Add `max_pages` config support to `config/sites.yaml` for all paginated adapters
- Add pagination logging: log current page, total pages, jobs per page
- Add configurable `page_size` where the API supports it (workgo: page_size param)
- **NOT paginated** (skip these): RemoteOK (single JSON array), WeWorkRemotely (single RSS feed)

**Must NOT do**:
- Do NOT add fake pagination to RemoteOK or WeWorkRemotely
- Do NOT fetch infinite pages — always respect max_pages config

**Recommended Agent Profile**:
- **Category**: `quick`
- **Skills**: []
  - Config updates and pagination verification, mostly already implemented in Tasks 3-6

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 3, 4, 5, 6, 7)
- **Blocks**: Task 9
- **Blocked By**: Task 2

**References**:
- `scraper/adapters/api.py` — EleduckAdapter pagination pattern (max_pages loop)
- `config/sites.yaml` — existing site configs with max_pages
- All new adapter implementations from Tasks 3-6

**Acceptance Criteria**:
- [x] `config/sites.yaml` has max_pages for all paginated adapters
- [x] Pagination logging shows page progress during scrape
- [x] `python -m pytest tests/ -v` → all tests pass

**Agent-Executed QA Scenarios**:
```
Scenario: Pagination config present
  Tool: Bash
  Steps:
    1. python -c "import yaml; c=yaml.safe_load(open('config/sites.yaml')); [print(f'{k}: max_pages={v.get(\"max_pages\",\"N/A\")}') for k,v in c.items()]"
    2. Assert: workgo, eleduck, v2ex show max_pages values
  Expected Result: Config complete
  Evidence: Terminal output captured
```

**Commit**: YES (groups with Task 9 if small)
- Message: `feat(config): standardize pagination config across all adapters`
- Files: `config/sites.yaml`
- Pre-commit: `python -m pytest tests/ -v`

---

### Task 9: Full Integration Test & Final Verification

**What to do**:
- Update `tests/test_integration.py`:
  - Add async integration tests for the full 7-source pipeline
  - Test: all adapters mocked → orchestrator runs → dedup applied → storage upserted
  - Test: single-site filter works for new sources
  - Test: error handling (one adapter fails, others continue)
  - Test: dry-run mode with new sources
  - Test: cross-site dedup removes duplicates in integration
- Run full test suite: `python -m pytest tests/ -v` — ALL tests pass
- Run live smoke test (for sources that don't require special auth):
  - `python main.py scrape --site remoteok --verbose` → async, returns jobs
  - `python main.py scrape --site eleduck --verbose` → async, returns jobs
  - `python main.py scrape --site weworkremotely --verbose` → async, returns jobs
- Verify stats and export still work:
  - `python main.py stats` → shows data
  - `python main.py export --format json` → creates valid JSON
- Final code quality check: all imports resolve, no sync code in async paths, no hardcoded secrets

**Must NOT do**:
- Do NOT test live against authenticated sources (workgo, arcdev) in CI — only mocked tests
- Do NOT skip the regression check on existing 128 tests

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
- **Skills**: []
  - Integration testing, full verification sweep

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 3 (final, after all Wave 2 tasks)
- **Blocks**: None (final task)
- **Blocked By**: Tasks 3, 4, 5, 6, 7, 8

**References**:
- `tests/test_integration.py` — existing integration tests (11 tests) to extend
- `scraper/orchestrator.py` — orchestrator with all 7 adapters registered
- All new adapter files and test files from Tasks 3-8

**Acceptance Criteria**:
- [x] `python -m pytest tests/ -v` → ALL tests pass (existing + new)
- [x] `python main.py scrape --site remoteok --verbose` → returns jobs (async)
- [x] `python main.py scrape --site eleduck --verbose` → returns jobs (async)
- [x] `python main.py scrape --site weworkremotely --verbose` → returns jobs (async)
- [x] `python main.py stats` → shows correct statistics
- [x] `python main.py export --format json` → creates valid JSON
- [x] No hardcoded secrets in any .py or .yaml files
- [x] All imports resolve cleanly

**Agent-Executed QA Scenarios**:
```
Scenario: Full test suite passes
  Tool: Bash
  Steps:
    1. python -m pytest tests/ -v --tb=short
    2. Assert: 0 failures, 0 errors
  Expected Result: All tests green
  Evidence: Full pytest output captured

Scenario: Live async scrape (safe sources only)
  Tool: Bash
  Steps:
    1. python main.py --verbose scrape --site remoteok
    2. Assert: output contains "Total fetched" with number > 0
    3. python main.py stats
    4. Assert: output shows remoteok count > 0
  Expected Result: Async pipeline works end-to-end
  Evidence: Terminal output captured

Scenario: Export still works
  Tool: Bash
  Steps:
    1. python main.py export --format json --output data/exports/phase2_test.json
    2. python -c "import json; d=json.load(open('data/exports/phase2_test.json')); print(f'{len(d)} jobs exported')"
    3. Assert: number > 0
  Expected Result: JSON export functional
  Evidence: Terminal output captured
```

**Commit**: YES
- Message: `test: add Phase 2 integration tests and verify full async pipeline`
- Files: `tests/test_integration.py`
- Pre-commit: `python -m pytest tests/ -v`

---

## Commit Strategy

| After Task | Message | Key Files | Verification |
|------------|---------|-----------|--------------|
| 1 | `feat(models): add Phase 2 source IDs and async dependencies` | models.py, pyproject.toml, .env.example, main.py | pytest (128 pass) |
| 2 | `refactor: migrate entire codebase from sync to async` | all scraper/*.py, all tests/ | pytest (128 pass) + live scrape |
| 3 | `feat(adapters): add WorkGo Playwright adapter` | browser.py, test_workgo.py, fixtures, sites.yaml | pytest (all pass) |
| 4 | `feat(adapters): add V2EX hybrid adapter` | hybrid.py, test_v2ex.py, fixtures, sites.yaml | pytest (all pass) |
| 5 | `feat(adapters): add 远程.work HTML adapter` | html.py, test_yuancheng.py, fixtures, sites.yaml | pytest (all pass) |
| 6 | `feat(adapters): add Arc.dev Playwright adapter` | browser.py, test_arcdev.py, fixtures, sites.yaml | pytest (all pass) |
| 7 | `feat(utils): add cross-site job deduplication` | dedup.py, test_dedup.py, orchestrator.py | pytest (all pass) |
| 8 | `feat(config): standardize pagination config` | sites.yaml | pytest (all pass) |
| 9 | `test: Phase 2 integration tests and verification` | test_integration.py | pytest (all pass) + live scrape |

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/ -v                              # ALL tests pass
python main.py --verbose scrape --site remoteok          # Async scrape works
python main.py --verbose scrape --site eleduck           # Async scrape works
python main.py --verbose scrape --site weworkremotely    # Async scrape works
python main.py stats                                     # Shows all sources
python main.py export --format json                      # JSON export works
grep -r "httpx.Client" scraper/                          # 0 matches (all async)
grep -r "import sqlite3" scraper/                        # 0 matches (all aiosqlite)
```

### Final Checklist
- [x] All Phase 1 tests still pass (no regressions)
- [x] All new adapter tests pass
- [x] Async migration complete (no sync httpx/sqlite3 in scraper/)
- [x] 4 new adapters registered and functional
- [x] Cross-site dedup working
- [x] CLI unchanged (scrape/stats/export)
- [x] Credentials in .env only (not in code)
- [x] Playwright browser binary installed
