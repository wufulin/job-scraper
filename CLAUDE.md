# CLAUDE.md

## Commands

```bash
pip install -e ".[dev]"           # Install with dev deps
python -m pytest tests/ -v        # Run 314 tests (~9s, all mocked, no live HTTP)
python main.py scrape             # Scrape all enabled sites
python main.py scrape --site remoteok  # Single site
python main.py scrape --site v2ex      # Also: arcdev, workgo, yuancheng, eleduck, weworkremotely
python main.py scrape --dry-run   # Fetch + match without saving
python main.py stats              # Show DB statistics
python main.py export --format json    # Export to data/exports/jobs.json
python main.py --verbose scrape   # Debug logging (--verbose BEFORE subcommand)
```

## Architecture

Pipeline: `CLI (main.py) → asyncio.run → Orchestrator (async) → Adapters (concurrent) → Matcher → Dedup → Storage (aiosqlite)`

- **Adapters** (`scraper/adapters/`): BaseAdapter ABC with `async fetch_jobs() → list[JobPosting]`.
  Seven implementations across 5 modules:
  - `api.py`: RemoteOKAdapter (JSON API), EleduckAdapter (JSON API, paginated)
  - `rss.py`: WeWorkRemotelyAdapter (RSS feed)
  - `browser.py`: WorkGoAdapter (Playwright + Clerk auth), ArcDevAdapter (Playwright + Next.js SSR)
  - `hybrid.py`: V2EXAdapter (HTML listing + JSON API detail)
  - `html.py`: YuanchengAdapter (BeautifulSoup, disabled — domain dead)
  Registry in `orchestrator.py::_ADAPTER_MAP` dict — add new adapters here.
- **Matcher** (`scraper/utils/matcher.py`): AND between keyword groups, OR within groups.
  Short English keywords (≤3 chars, alphanumeric) use `\b` word-boundary. CJK uses substring. Patterns precompiled at init.
- **Storage** (`scraper/utils/storage.py`): aiosqlite with async check-then-insert/update upsert. DB at `data/jobs.db`.
- **Dedup** (`scraper/utils/dedup.py`): Cross-site deduplication using `difflib.SequenceMatcher`. Compares company+title similarity. Runs after matching, before storage.
- **Models** (`scraper/models.py`): Single Pydantic v2 `JobPosting` model. ID = MD5 of `url|title`.
- **Config**: YAML files in `config/` — `sites.yaml` (sources + adapter settings) and `keywords.yaml` (keyword groups + match rules).

## Key Conventions

- Python 3.11+, `from __future__ import annotations` in all modules
- Pydantic v2 for data validation (not dataclasses)
- `loguru` for logging (not stdlib `logging`) — import as `from loguru import logger`
- `httpx` async client (`httpx.AsyncClient`) — created per-request via `BaseAdapter._get_client()`; all adapters are `async def fetch_jobs()`
- `aiosqlite` for async SQLite (not sync `sqlite3`) — all storage methods are async
- `playwright` for browser-based adapters (ArcDevAdapter, WorkGoAdapter) — headless Chromium
- `asyncio_mode = "auto"` in pyproject.toml — async tests need no decorator
- `fake-useragent` for rotating User-Agent headers
- Type hints everywhere, `Optional[X]` style (not `X | None` in annotations, though `X | None` used in some return types)
- Docstrings: Google-style with Args/Returns sections
- `__init__.py` files are empty (packages are implicit namespaces)

## Gotchas

- **RemoteOK API**: First element of JSON array is always a legal notice — must skip `data[1:]`
- **`--verbose` flag**: Must come BEFORE the subcommand (`python main.py --verbose scrape`, not `python main.py scrape --verbose`)
- **`JobPosting.url` is `str`**, not `HttpUrl` — intentional for SQLite compatibility
- **Config paths are relative to CWD**: `config/sites.yaml`, `config/keywords.yaml`, `data/jobs.db` — must run from project root
- **Eleduck company**: Extracted from `user.nickname` field, not a top-level field
- **WWR title format**: RSS titles are "Company: Job Title" — split on first ": "
- **Graceful Ctrl+C**: Sets `orchestrator.interrupted = True`, finishes current job before exiting
- **Env vars** in `.env.example`: PROXY_URL, TELEGRAM_* are **not yet wired** (Phase 3+). WORKGO_EMAIL/WORKGO_PASSWORD are used by WorkGoAdapter for Clerk auth.
- **`max_pages`** for Eleduck pagination defaults to 5 if not in config
- **Rate limiting**: `_delay()` sleeps random 50%-150% of `rate_limit_seconds` (default 2s)
- **V2EX rate limiting**: Uses 6s delay between requests; HTML listing page + individual JSON API calls per topic
- **V2EX topic detail**: Fetched via `v2ex.com/api/topics/show.json?id=N`, content is in `content_rendered` (HTML)
- **Arc.dev SSR data**: Job data embedded in `window.__NEXT_DATA__.props.pageProps.arcJobs` — extracted via Playwright `page.evaluate()`
- **WorkGo disabled**: `enabled: false` in sites.yaml — requires Clerk JWT auth via WORKGO_EMAIL/WORKGO_PASSWORD env vars
- **Yuancheng disabled**: `enabled: false` — domain `yuancheng.work` redirects to `arc.dev`, adapter returns [] on redirect
- **Async orchestrator**: Uses `asyncio.gather()` with `asyncio.Semaphore(3)` for concurrent adapter execution
- **Cross-site dedup**: `DedupManager.deduplicate()` runs after matching, before storage — removes fuzzy duplicates across sources
- **aiosqlite init**: `__init__` can't be async, so schema DDL uses `aiosqlite.core.sqlite3` (underlying sync module) for init

## Testing

- Framework: pytest (314 tests, ~9s)
- All HTTP mocked via `unittest.mock.patch` on `BaseAdapter._get_client`
- Fixtures: `tests/fixtures/` has sample JSON/XML/HTML responses for each adapter
- Integration tests: Full pipeline with mocked HTTP in `test_integration.py`
- Pattern: Test classes grouped by component (`TestMatchGroup`, `TestMatchJob`, `TestEdgeCases`)
- Temp DBs use `tempfile.mkstemp` with cleanup handling for Windows file locking

## Project Status

Phase 1 MVP and Phase 2 complete. Phase 2 added: async migration (httpx.AsyncClient + aiosqlite), V2EX, Arc.dev, WorkGo, 远程.work adapters, cross-site dedup. Phase 3 planned: notifications, Docker.
Design docs in `docs/` (Chinese language).
