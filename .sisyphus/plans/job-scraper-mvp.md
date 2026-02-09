# Plan: Job Scraper MVP (Phase 1)

> Remote AI Job Scraper — Phase 1 MVP
> Based on: docs/2026-02-10-design-brainstorm.md (authoritative), docs/2026-02-07-job-scraper-design.md (superseded)
> Created: 2026-02-10

## Overview

Build a working Python job scraper that fetches remote AI job postings from 3 data sources (RemoteOK API, 电鸭 API, WeWorkRemotely RSS), matches them against configurable keyword groups, stores results in SQLite, and provides a CLI interface. Phase 1 is **synchronous** — async orchestration deferred to Phase 2.

## Design References

- Directory structure: `docs/2026-02-10-design-brainstorm.md` lines 964-1011
- Adapter hierarchy: `docs/2026-02-10-design-brainstorm.md` lines 102-108
- Keyword matching: `docs/2026-02-10-design-brainstorm.md` lines 123-224
- Data model: `docs/2026-02-10-design-brainstorm.md` lines 288-310
- SQLite storage: `docs/2026-02-10-design-brainstorm.md` lines 676-763
- CLI design: `docs/2026-02-10-design-brainstorm.md` lines 1017-1075
- Sites config: `docs/2026-02-10-design-brainstorm.md` lines 833-910

## Critical Constraints

- **Python 3.11+** target
- **Synchronous** httpx (no async in Phase 1)
- **NO**: circuit breaker, notifications, cross-site dedup, structure monitoring, Docker
- **NO**: OfferShow (unreachable), Arc.dev (needs Playwright, Phase 2), 远程.work (Phase 2)
- **DO NOT** copy brainstorm pseudocode verbatim — it has incorrect APIs
- **WeWorkRemotely RSS URL**: Use `/remote-jobs.rss`, NOT `/categories/remote-programming-jobs.rss` (old URL returns 301)
- **RemoteOK API**: First array element is a legal notice, NOT a job — must skip

---

## Tasks

### Task 1: Project Skeleton & Configuration
<!-- parallelizable: false | depends_on: none | modifies: pyproject.toml, .gitignore, .env.example, config/, scraper/__init__.py, scraper/adapters/__init__.py, scraper/utils/__init__.py, tests/ -->

- [x] 1.1 Create `pyproject.toml` with project metadata, dependencies (httpx, beautifulsoup4, feedparser, fake-useragent, pyyaml, loguru, pydantic>=2.0, chardet), and dev dependencies (pytest). Use setuptools backend.
- [x] 1.2 Create directory structure following brainstorm (lines 964-1011): `scraper/`, `scraper/adapters/`, `scraper/utils/`, `config/`, `data/`, `logs/`, `tests/`, `tests/test_adapters/`. All with `__init__.py` where needed.
- [x] 1.3 Create `.gitignore` (data/, logs/, cookies/, .env, __pycache__, *.pyc, .venv/, *.db)
- [x] 1.4 Create `.env.example` with placeholder config (PROXY_URL, TELEGRAM_BOT_TOKEN, etc.)
- [x] 1.5 Create `config/sites.yaml` with site configurations for RemoteOK, 电鸭, WeWorkRemotely only (Phase 1 scope). Use VERIFIED endpoints.
- [x] 1.6 Create `config/keywords.yaml` with keyword groups (location OR, technology OR) per brainstorm lines 139-183.
- [x] 1.7 Set up loguru logging in `scraper/logger.py` — file rotation, console output, UTF-8 encoding per brainstorm lines 436-448.

**Acceptance**: `pip install -e ".[dev]"` succeeds. All directories exist. YAML configs parse without error.

---

### Task 2: Pydantic Data Models
<!-- parallelizable: false | depends_on: 1 | modifies: scraper/models.py -->

- [x] 2.1 Create `scraper/models.py` with `JobPosting` Pydantic model. Phase 1 fields ONLY: id, title, company (optional), url (str, not HttpUrl), source, published_at (optional datetime), salary (optional), location (optional), description (optional), tags (list[str]), first_seen (datetime), last_seen (datetime), last_updated (datetime), update_count (int=1). NO source_urls, NO match_score, NO matched_keywords yet.
- [x] 2.2 Add `@field_validator` for title (not empty), source (must be in valid set: remoteok, eleduck, weworkremotely).
- [x] 2.3 Add `generate_id(url: str, title: str) -> str` static method using MD5 hash.
- [x] 2.4 Add `to_db_dict() -> dict` method that serializes all fields to SQLite-compatible types (datetime→ISO string, list→JSON string).
- [x] 2.5 Add `from_db_row(row: dict) -> JobPosting` classmethod that deserializes from SQLite row.

**Acceptance**: `python -c "from scraper.models import JobPosting; print('OK')"` works. Round-trip test: create model → to_db_dict → from_db_row → compare.

---

### Task 3: Keyword Matcher with Tests
<!-- parallelizable: true (with Task 4) | depends_on: 1 | modifies: scraper/utils/matcher.py, config/keywords.yaml, tests/test_matcher.py -->

- [x] 3.1 Create `scraper/utils/matcher.py` with `KeywordMatcher` class. Load keyword groups from `config/keywords.yaml`.
- [x] 3.2 Implement `match_group(text: str, group_name: str) -> bool` — OR logic within group (any keyword hit = True).
- [x] 3.3 Implement `match_job(job: dict, source: str) -> bool` — AND logic between groups. Skip location group for sources in `skip_location_for` list.
- [x] 3.4 Handle Chinese text: for CJK keywords use substring match; for short English keywords like "AI" use word-boundary regex `\bAI\b` to avoid false positives on "email", "wait", etc.
- [x] 3.5 Write `tests/test_matcher.py` with test cases:
  - "Senior AI Engineer - Remote" → technology=True, location=True
  - "email marketing specialist" → technology=False
  - "waiting room attendant" → technology=False (no false positive on "AI" in "waiting")
  - "AI应用开发工程师" → technology=True (Chinese substring match)
  - "远程 LLM 应用开发" → technology=True, location=True
  - Source "remoteok" skips location matching
  - Empty text → False

**Acceptance**: `python -m pytest tests/test_matcher.py -v` — all tests pass.

---

### Task 4: SQLite Storage with Tests
<!-- parallelizable: true (with Task 3) | depends_on: 1, 2 | modifies: scraper/utils/storage.py, tests/test_storage.py -->

- [x] 4.1 Create `scraper/utils/storage.py` with `StorageManager` class. Sync `sqlite3` (Phase 1 is synchronous).
- [x] 4.2 Implement `_init_db()` — CREATE TABLE with all Phase 1 JobPosting fields. Add indexes on source, company, is_active, first_seen.
- [x] 4.3 Implement `upsert_job(job: JobPosting)` — INSERT OR UPDATE using job.id as primary key. On conflict: update last_seen, last_updated, increment update_count, preserve first_seen.
- [x] 4.4 Implement `get_all_jobs(active_only: bool = True) -> list[JobPosting]` — query and deserialize.
- [x] 4.5 Implement `get_stats() -> dict` — return counts by source, total active, total inactive.
- [x] 4.6 Implement `export_json(filepath: str)` — export active jobs to JSON file.
- [x] 4.7 Write `tests/test_storage.py` with test cases:
  - Insert new job → verify stored correctly
  - Upsert same job → update_count increments, first_seen preserved
  - Get stats returns correct counts
  - Export JSON produces valid file

**Acceptance**: `python -m pytest tests/test_storage.py -v` — all tests pass.

---

### Task 5: Base Adapter + RemoteOK ApiAdapter with Tests
<!-- parallelizable: false | depends_on: 2, 3, 4 | modifies: scraper/adapters/base.py, scraper/adapters/api.py, tests/test_adapters/test_api_adapter.py, tests/fixtures/ -->

- [x] 5.1 Create `scraper/adapters/base.py` with `BaseAdapter` ABC. Methods: `fetch_jobs() -> list[JobPosting]`, `name` property, `source_id` property. Include basic httpx client setup with fake-useragent UA rotation and configurable delay.
- [x] 5.2 Probe RemoteOK API: fetch `https://remoteok.com/api`, save response to `tests/fixtures/remoteok_sample.json`. Document response structure.
- [x] 5.3 Create `scraper/adapters/api.py` with `RemoteOKAdapter(BaseAdapter)`. Parse JSON response, skip first element (legal notice), map fields to JobPosting model. Handle missing fields gracefully.
- [x] 5.4 Write `tests/test_adapters/test_remoteok.py` — test parsing against saved fixture (not live API). Test: legal notice skipped, valid jobs parsed, missing fields handled.
- [x] 5.5 Manual smoke test: run adapter against live API, verify it returns >0 jobs.

**Acceptance**: `python -m pytest tests/test_adapters/test_remoteok.py -v` passes. Live smoke test returns jobs.

---

### Task 6: 电鸭 (Eleduck) ApiAdapter with Tests
<!-- parallelizable: false | depends_on: 5 | modifies: scraper/adapters/api.py, tests/test_adapters/test_eleduck.py, tests/fixtures/ -->

- [x] 6.1 Probe 电鸭 API: fetch `https://svc.eleduck.com/api/v1/posts?category=5&page=1`, save response to `tests/fixtures/eleduck_sample.json`. Document response structure.
- [x] 6.2 Implement `EleduckAdapter(BaseAdapter)` in `scraper/adapters/api.py`. Parse API response, map fields to JobPosting. Support pagination (up to 5 pages per config).
- [x] 6.3 Write `tests/test_adapters/test_eleduck.py` — test parsing against saved fixture. Test: valid jobs parsed, pagination logic, missing fields handled.
- [x] 6.4 Manual smoke test: run adapter against live API, verify it returns >0 jobs.

**Acceptance**: `python -m pytest tests/test_adapters/test_eleduck.py -v` passes. Live smoke test returns jobs.

---

### Task 7: WeWorkRemotely RssAdapter with Tests
<!-- parallelizable: false | depends_on: 5 | modifies: scraper/adapters/rss.py, tests/test_adapters/test_wwr.py, tests/fixtures/ -->

- [x] 7.1 Probe WeWorkRemotely RSS: fetch `https://weworkremotely.com/remote-jobs.rss`, save response to `tests/fixtures/wwr_sample.xml`. Document feed structure.
- [x] 7.2 Create `scraper/adapters/rss.py` with `WeWorkRemotelyAdapter(BaseAdapter)`. Use `feedparser` to parse RSS. Map feed entries to JobPosting model. Handle encoding issues (install chardet).
- [x] 7.3 Write `tests/test_adapters/test_wwr.py` — test parsing against saved fixture. Test: valid jobs parsed, feed entries mapped correctly, encoding handled.
- [x] 7.4 Manual smoke test: run adapter against live RSS feed, verify it returns >0 jobs.

**Acceptance**: `python -m pytest tests/test_adapters/test_wwr.py -v` passes. Live smoke test returns jobs.

---

### Task 8: CLI Entry Point + Logging Integration
<!-- parallelizable: false | depends_on: 3, 4, 5, 6, 7 | modifies: main.py, scraper/orchestrator.py -->

- [x] 8.1 Create `scraper/orchestrator.py` with `ScraperOrchestrator` class. Synchronous. Instantiates all 3 adapters, runs them sequentially, applies keyword matching, stores results via StorageManager. Returns summary dict (total_scraped, matched, new, updated).
- [x] 8.2 Create `main.py` with argparse CLI. Subcommands: `scrape` (--site, --dry-run, --verbose), `export` (--format json, --output), `stats`. Per brainstorm lines 1017-1075.
- [x] 8.3 Integrate loguru logging: verbose mode shows DEBUG, normal shows INFO. Log to `logs/scraper_YYYY-MM-DD.log` with rotation.
- [x] 8.4 Implement graceful Ctrl+C handling: register signal handler, save already-scraped data before exit.

**Acceptance**: `python main.py scrape --verbose` runs successfully, fetches from all 3 sites, prints summary. `python main.py stats` shows database statistics. `python main.py export --format json` creates export file.

---

### Task 9: Integration Test & Final Verification
<!-- parallelizable: false | depends_on: 8 | modifies: tests/test_integration.py -->

- [x] 9.1 Write `tests/test_integration.py` — end-to-end test that runs the full pipeline (scrape → match → store) against fixtures (not live APIs).
- [x] 9.2 Run full test suite: `python -m pytest tests/ -v` — ALL tests pass.
- [x] 9.3 Run live smoke test: `python main.py scrape --verbose` — fetches real data from all 3 sites, stores in SQLite.
- [x] 9.4 Verify SQLite has data: `python main.py stats` shows >0 jobs.
- [x] 9.5 Verify JSON export: `python main.py export --format json --output data/exports/jobs.json` creates valid JSON.
- [x] 9.6 Final code quality check: no linting errors, all imports resolve, no hardcoded secrets.

**Acceptance**: All tests pass. Live scrape succeeds. Database has real job data. Export works.

---

## Future Phases (Milestones Only)

### Phase 2: Complete Data Sources + Async
- HybridAdapter for V2EX (HTML list + API detail)
- HtmlAdapter for 远程.work (WordPress scraping)
- BrowserAdapter + playwright-stealth for Arc.dev
- Migrate to asyncio + httpx async + aiosqlite
- Cross-site dedup (company + title similarity)
- Pagination support for all adapters

### Phase 3: Production Hardening
- Circuit breaker per site
- Notification system (Telegram/Discord/Server酱)
- Site structure change detection
- APScheduler for cron-based scheduling
- Docker + docker-compose deployment
- CSV export support
- Health check endpoint

### Phase 4: Enhancement
- Match scoring and ranking
- Job lifecycle management (stale detection)
- Notion / Google Sheets integration
- Statistics dashboard (stats command)
- Full test coverage
- Documentation (README, contributing guide)
