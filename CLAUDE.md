# CLAUDE.md

## Commands

```bash
# Backend
pip install -e ".[dev]"           # Install with dev deps
python -m pytest tests/ -v        # Run tests (~20s, all mocked)
uvicorn app.main:app --reload     # Start FastAPI dev server

# Docker
docker-compose up -d              # Start all services
docker-compose logs -f backend    # View backend logs

# Frontend (in frontend/ directory)
cd frontend && pnpm install       # Install frontend deps
pnpm dev                          # Start Next.js dev server
```

## Architecture

Pipeline: `FastAPI (app/main.py) → Orchestrator (async) → Adapters (concurrent) → Matcher → Dedup → Storage (asyncpg/Supabase)`

- **API** (`app/`): FastAPI application with REST endpoints
  - `app/main.py`: FastAPI app with lifespan management
  - `app/routers/`: API endpoints (jobs, scraper, stats, auth, etc.)
  - `app/services/`: Business logic (SupabaseStorage, JobService, ScraperService, etc.)
  - `app/models/`: Pydantic request/response models
  
- **Adapters** (`scraper/adapters/`): BaseAdapter ABC with `async fetch_jobs() → list[JobPosting]`.
  Seven implementations across 5 modules:
  - `api.py`: RemoteOKAdapter (JSON API), EleduckAdapter (JSON API, paginated), WorkGoAdapter (JSON API, Clerk cookie auth)
  - `rss.py`: WeWorkRemotelyAdapter (RSS feed)
  - `browser.py`: ArcDevAdapter (Playwright + Next.js SSR)
  - `hybrid.py`: V2EXAdapter (HTML listing + JSON API detail)
  - `html.py`: YuanchengAdapter (BeautifulSoup, disabled — domain dead)
  Registry in `orchestrator.py::_ADAPTER_MAP` dict — add new adapters here.
  
- **Matcher** (`scraper/utils/matcher.py`): AND between keyword groups, OR within groups.
  Short English keywords (≤3 chars, alphanumeric) use `\b` word-boundary. CJK uses substring. Patterns precompiled at init.
  
- **Storage** (`app/services/storage.py`): SupabaseStorage using asyncpg. PostgreSQL with RLS policies.
  - `SupabaseStorage`: Async storage with connection pooling
  - `FakeStorage` (`tests/fakes/storage.py`): In-memory storage for tests
  
- **Dedup** (`scraper/utils/dedup.py`): Cross-site deduplication using `difflib.SequenceMatcher`. Compares company+title similarity. Runs after matching, before storage.

- **Models** (`scraper/models.py`): Single Pydantic v2 `JobPosting` model. ID = MD5 of `url|title`.
  - `to_pg_dict()`: Serialize for PostgreSQL
  - `from_pg_row()`: Deserialize from PostgreSQL row

- **Config**: Database-driven config via `app/services/config_service.py` — sites, keywords, match rules stored in Supabase and cached.

- **Frontend** (`frontend/`): Next.js 16 + TypeScript + Tailwind CSS + shadcn/ui
  - Server components for job listings
  - Client components for interactive features
  - Supabase Auth for authentication

## Key Conventions

- Python 3.11+, `from __future__ import annotations` in all modules
- Pydantic v2 for data validation (not dataclasses)
- `loguru` for logging (not stdlib `logging`) — import as `from loguru import logger`
- `httpx` async client (`httpx.AsyncClient`) — created per-request via `BaseAdapter._get_client()`; all adapters are `async def fetch_jobs()`
- `asyncpg` for async PostgreSQL (not aiosqlite/SQLite) — all storage methods are async
- `playwright` for browser-based adapters (ArcDevAdapter) — headless Chromium
- `fastapi` + `uvicorn` for API server
- `pytest` with `asyncio_mode = "auto"` — async tests need no decorator
- `fake-useragent` for rotating User-Agent headers
- Type hints everywhere, `Optional[X]` style (not `X | None` in annotations, though `X | None` used in some return types)
- Docstrings: Google-style with Args/Returns sections
- `__init__.py` files are empty (packages are implicit namespaces)

## Gotchas

- **RemoteOK API**: First element of JSON array is always a legal notice — must skip `data[1:]`
- **SupabaseStorage init**: Must call `await storage.init_pool()` before using, and `await storage.close_pool()` on shutdown
- **`JobPosting.url` is `str`**, not `HttpUrl` — intentional for database compatibility
- **Config paths**: `config/sites.yaml` and `config/keywords.yaml` still used by orchestrator for adapter configuration
- **Eleduck company**: Extracted from `user.nickname` field, not a top-level field
- **WWR title format**: RSS titles are "Company: Job Title" — split on first ": "
- **Env vars** in `.env`: DATABASE_URL, SUPABASE_* required for backend. NEXT_PUBLIC_* required for frontend.
- **`max_pages`** for Eleduck pagination defaults to 5 if not in config
- **Rate limiting**: `_delay()` sleeps random 50%-150% of `rate_limit_seconds` (default 2s)
- **V2EX rate limiting**: Uses 6s delay between requests; HTML listing page + individual JSON API calls per topic
- **V2EX topic detail**: Fetched via `v2ex.com/api/topics/show.json?id=N`, content is in `content_rendered` (HTML)
- **Arc.dev SSR data**: Job data embedded in `window.__NEXT_DATA__.props.pageProps.arcJobs` — extracted via Playwright `page.evaluate()`
- **WorkGo disabled**: `enabled: false` in sites.yaml — requires WORKGO_COOKIE env var (Clerk __client cookie from browser after Google OAuth login)
- **Yuancheng disabled**: `enabled: false` — domain `yuancheng.work` redirects to `arc.dev`, adapter returns [] on redirect
- **Async orchestrator**: Uses `asyncio.gather()` with `asyncio.Semaphore(3)` for concurrent adapter execution
- **Cross-site dedup**: `DedupManager.deduplicate()` runs after matching, before storage — removes fuzzy duplicates across sources
- **aiosqlite init**: `__init__` can't be async, so schema DDL uses `aiosqlite.core.sqlite3` (underlying sync module) for init

## Testing

- Framework: pytest (640+ tests)
- All HTTP mocked via `unittest.mock.patch` on `BaseAdapter._get_client`
- Fixtures: `tests/fixtures/` has sample JSON/XML/HTML responses for each adapter
- Integration tests: Full pipeline with mocked HTTP in `test_integration.py`
- API tests: FastAPI endpoint tests in `tests/test_api/`

## Project Status

**Phase 3 Complete**: Full-stack migration done
- ✅ FastAPI backend with Supabase PostgreSQL
- ✅ Next.js 16 frontend with shadcn/ui
- ✅ Docker Compose deployment
- ✅ Authentication with Supabase Auth
- ✅ Job favorites, subscriptions, notifications
- ✅ Admin dashboard for scraper management

Old CLI and SQLite storage removed. All data now in Supabase with RLS policies.
