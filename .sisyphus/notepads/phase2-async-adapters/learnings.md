# Phase 2 - Async Migration Learnings

## Task 2: Sync → Async Migration

### Key Patterns
- `httpx.Client` → `httpx.AsyncClient`: `_get_client()` returns `AsyncClient`, callers use `async with`
- `time.sleep()` → `asyncio.sleep()`: `_delay()` becomes `async def _delay()`
- `sqlite3.connect()` → `aiosqlite.connect()`: all DB methods become async
- `with ... as client:` → `async with ... as client:` for httpx and aiosqlite
- `cursor.execute()` → `await cursor.execute()`, same for `fetchone/fetchall/commit`
- Orchestrator uses `asyncio.gather()` with `asyncio.Semaphore(3)` for parallel adapter execution
- CLI wraps async calls with `asyncio.run()`

### Storage Init Pattern
- `__init__` can't be async, so schema initialization uses `aiosqlite.core.sqlite3` (the underlying sqlite3 module re-exported by aiosqlite) for synchronous-only schema DDL
- This avoids a top-level `import sqlite3` in the scraper/ package while keeping sync init

### Test Migration Patterns
- `asyncio_mode = "auto"` in pyproject.toml → no need for `@pytest.mark.asyncio` decorators
- Tests calling async methods just use `async def test_*` and `await`
- Mock httpx clients: `AsyncMock()` with `__aenter__`/`__aexit__` instead of `__enter__`/`__exit__`
- Mock `_delay`: `patch.object(adapter, "_delay", new_callable=AsyncMock)`
- Pure sync tests (static methods, parsing) don't need any changes
- Test verification code that uses sync sqlite3 directly (e.g., checking schema) stays sync — it's test-only

### Environment Notes
- Conda env: `job-scraper` at `/c/Users/wu_fu/miniconda3/envs/job-scraper/python.exe`
- Windows Store python stub at default PATH doesn't work — must use conda python
- pytest-asyncio 1.3.0 installed, aiosqlite 0.22.1

### Results
- All 128 tests pass (4.10s)
- Zero `httpx.Client` matches in scraper/
- Zero `import sqlite3` matches in scraper/
- No business logic changes — pure async refactor

## Task: YuanchengAdapter (远程.work HTML scraping)

### Site Probe Results
- `yuancheng.work` redirects to `arc.dev/remote-jobs` (domain no longer independent)
- The punycode domain `xn--wtqx46b.work` (远程.work) gives `ERR_CONNECTION_CLOSED`
- `eleduck.com` (电鸭) is the actual Chinese remote work community, already has its own adapter
- Site was a WordPress-based job board using WP Job Manager plugin

### Design Decisions
- Created `scraper/adapters/html.py` as a new adapter module for HTML/BeautifulSoup scraping
- Adapter detects redirect away from yuancheng.work domain and returns [] gracefully
- Uses WP Job Manager markup (`<article class="job_listing">`) for parsing
- Disabled by default (`enabled: false`) since domain is dead
- Handles all error cases (HTTP errors, connection errors, redirects, empty pages) → returns []

### Test Coverage
- 32 tests covering: properties, HTML parsing, article parsing, missing fields, ID generation, fetch_jobs with mocked HTTP, fixture integrity
- Fixture has 5 articles: 4 valid + 1 with empty title (edge case)

### Environment
- Use `"C:\Users\wu_fu\miniconda3\python.exe"` to run tests (not bare `python`)
- All 301 tests pass (9.71s)

## Task: ArcDevAdapter (Arc.dev Playwright scraping)

### Site Probe Results
- Arc.dev is a Next.js SPA with SSR — job data embedded in `window.__NEXT_DATA__.props.pageProps.arcJobs`
- 30 featured "Arc Exclusive" jobs loaded at once, no pagination needed
- No API calls made client-side for job data — everything is SSR
- Page also has `externalJobs` array (empty at time of probing) and `totalExternalJobCount`
- Job URL pattern: `https://arc.dev/remote-jobs/details/{urlString}-{randomKey}`

### Data Schema
- `randomKey`: unique job ID (alphanumeric)
- `title`, `jobType` (contract/permanent), `jobRole` (engineering/marketing/etc.)
- `experienceLevel` (junior/mid/senior), `urlString` (slug)
- `postedAt`: Unix epoch timestamp
- `minHourlyRate`/`maxHourlyRate` and `minAnnualSalary`/`maxAnnualSalary`: salary data
- `company.randomKey`: null for Arc Exclusive, set for company jobs
- `categories[]`: array of `{name, urlString}` tech skill tags
- `requiredCountries[]`: ISO country codes
- `timeZone`: string or "no-preference" or null

### Design Decisions
- Uses Playwright to navigate and extract `__NEXT_DATA__` via `page.evaluate()`
- Added to existing `scraper/adapters/browser.py` alongside WorkGoAdapter
- SSR extraction approach: more reliable than DOM scraping, gets structured JSON directly
- Salary formatter handles both annual and hourly rates, annual takes precedence
- Location formatter summarizes countries (list ≤3 or "N countries") + timezone

### Test Coverage
- 33 tests: properties, parse_entry, salary formatting, location formatting, fetch_jobs
- Fixture: 5 representative jobs covering contract/permanent, hourly/annual, various countries
- All tests mock `_extract_next_data` — no real browser needed

### Results
- All 301 tests pass (11.52s) including 33 new arcdev tests
