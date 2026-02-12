# Remote AI Job Aggregator

Full-stack web application that aggregates remote AI/ML job postings from multiple sources with intelligent filtering, cross-site deduplication, and automated scheduling.

## Features

- **REST API**: FastAPI backend with 10 endpoint groups (jobs, scraper, stats, auth, config, scheduler, favorites, notifications, subscriptions, health)
- **Scheduled Scraping**: APScheduler runs automated scraping every 2 hours
- **Authentication**: Supabase Auth with JWT verification and row-level security (RLS)
- **7 Data Sources**: RemoteOK, Eleduck, WeWorkRemotely, V2EX, Arc.dev, WorkGo, 远程.work
- **Cross-site Deduplication**: Fuzzy matching removes duplicate postings across sources
- **Smart Keyword Matching**: CJK (Chinese, Japanese, Korean) support with configurable rules
- **User Features**: Job favorites, email subscriptions, notifications
- **Admin Dashboard**: Manage scraper configuration, view statistics, trigger manual scrapes
- **Docker Deployment**: Production-ready Docker Compose setup with nginx reverse proxy
- **Modern Frontend**: Next.js 16 with TypeScript, Tailwind CSS, and shadcn/ui components

## Data Sources

| Source | Type | Adapter | Status |
|--------|------|---------|--------|
| RemoteOK | JSON API | `app/scraper/adapters/api.py` | Enabled |
| Eleduck (电鸭) | JSON API (paginated) | `app/scraper/adapters/api.py` | Enabled |
| WeWorkRemotely | RSS Feed | `app/scraper/adapters/rss.py` | Enabled |
| V2EX | Hybrid HTML+API | `app/scraper/adapters/hybrid.py` | Enabled |
| Arc.dev | Browser (Playwright) | `app/scraper/adapters/browser.py` | Enabled |
| WorkGo | JSON API (Clerk auth) | `app/scraper/adapters/api.py` | Disabled* |
| 远程.work | HTML Scraping | `app/scraper/adapters/html.py` | Disabled** |

\* Requires `WORKGO_COOKIE` environment variable (Clerk `__client` cookie after Google OAuth)
\*\* Domain redirects to arc.dev — adapter returns empty list

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ and pnpm
- PostgreSQL (or Supabase account)
- (Optional) Docker and Docker Compose

### Backend Setup

```bash
git clone https://github.com/wufulin/job-scraper.git
cd job-scraper

# Install Python dependencies
pip install -e ".[dev]"

# Install Playwright browsers (for Arc.dev scraping)
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, SUPABASE_URL, SUPABASE_KEY

# Start FastAPI development server
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd frontend
pnpm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY

# Start Next.js development server
pnpm dev
```

Frontend runs at `http://localhost:3000`.

### Docker Deployment

```bash
# Configure environment
cp .env.example .env.docker
# Edit .env.docker with production values

# Start all services (backend + frontend + nginx)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

Application serves at `http://localhost` via nginx reverse proxy.

## API Endpoints

| Router | Prefix | Description |
|--------|--------|-------------|
| health | `/api/health` | Health check |
| jobs | `/api/jobs` | List, search, and retrieve job postings |
| scraper | `/api/scrape` | Trigger manual scrapes, check scrape status |
| stats | `/api/stats` | Database statistics (total jobs, by source, etc.) |
| auth | `/api/auth` | User authentication (login, register, JWT verification) |
| config | `/api/config` | Manage site configs, keywords, match rules |
| scheduler | `/api/scheduler` | View and manage scheduled scraping jobs |
| favorites | `/api/favorites` | User job favorites (add, remove, list) |
| notifications | `/api/notifications` | User notifications for new job matches |
| subscriptions | `/api/subscriptions` | Email subscription management |

Interactive API docs available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

## Configuration

All configuration is **database-driven** — managed via the Config API or admin dashboard.

### Database Tables

| Table | Purpose |
|-------|---------|
| `site_configs` | Data source settings (URL, adapter type, rate limits, enabled/disabled) |
| `keyword_configs` | Keyword groups for matching (location, technology) |
| `match_rules` | Matching logic and site-specific overrides |
| `jobs` | Stored job postings |
| `scrape_runs` | Scrape execution history |
| `users` | User accounts (Supabase Auth) |
| `favorites` | User job bookmarks |
| `subscriptions` | Email subscription preferences |
| `notifications` | User notification queue |

### Keyword Matching

- **AND** between keyword groups (e.g., must match both `location` AND `technology`)
- **OR** within each group (e.g., "remote" OR "远程" OR "work from home")
- Short English keywords (≤3 chars) use `\b` word-boundary matching to prevent false positives
- CJK keywords use substring matching
- Site-specific overrides: RemoteOK and WeWorkRemotely skip location matching (all jobs are remote by default)

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│                        Frontend                           │
│       Next.js 16 + TypeScript + Tailwind + shadcn/ui      │
└─────────────────────────┬─────────────────────────────────┘
                          │ HTTP/REST
┌─────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend                         │
│                    (app/main.py)                           │
│                                                           │
│  Routers → Services → Orchestrator                        │
│                          │                                │
│            ┌─────────────┼─────────────┐                  │
│            ▼             ▼             ▼                   │
│        Adapter 1    Adapter 2    Adapter N                 │
│       (RemoteOK)   (Eleduck)     (...)                    │
│            │             │             │                   │
│            └─────────────┼─────────────┘                  │
│                          ▼                                │
│                   Keyword Matcher                         │
│                          ▼                                │
│                Cross-site Deduplicator                    │
│                          ▼                                │
│                  SupabaseStorage (asyncpg)                │
└───────────────────────────────────────────────────────────┘
                          │
               ┌──────────▼──────────┐
               │  Supabase PostgreSQL │
               │  (with RLS policies) │
               └─────────────────────┘
```

### Pipeline Flow

1. **Request** — API endpoint or scheduler triggers a scrape
2. **Orchestrator** — Initializes enabled adapters, runs concurrent fetch via `asyncio.gather()` (semaphore=3)
3. **Adapters** — Each adapter fetches jobs from its source (API, RSS, browser, or hybrid)
4. **Matcher** — Filters jobs by keyword rules (AND between groups, OR within groups)
5. **Deduplicator** — Removes cross-site duplicates using fuzzy company+title matching
6. **Storage** — Upserts deduplicated jobs to PostgreSQL via asyncpg connection pool
7. **Response** — Returns summary (total fetched, matched, deduplicated, stored)

## Project Structure

```
job-scraper/
├── app/                          # FastAPI backend
│   ├── main.py                   # App entry point with lifespan management
│   ├── config/
│   │   └── settings.py           # Pydantic settings (env vars)
│   ├── routers/                  # API endpoint handlers
│   │   ├── health.py
│   │   ├── jobs.py
│   │   ├── scraper.py
│   │   ├── stats.py
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── scheduler.py
│   │   ├── favorites.py
│   │   ├── notifications.py
│   │   └── subscriptions.py
│   ├── services/                 # Business logic
│   │   ├── storage.py            # SupabaseStorage (asyncpg pool)
│   │   ├── job_service.py        # Job CRUD operations
│   │   ├── scraper_service.py    # Scrape orchestration
│   │   ├── config_service.py     # DB-driven configuration
│   │   ├── scheduler.py          # APScheduler setup
│   │   └── auth_service.py       # JWT verification
│   ├── models/                   # Pydantic request/response schemas
│   └── scraper/                  # Scraper module
│       ├── models.py             # JobPosting model
│       ├── orchestrator.py       # Async pipeline coordinator
│       ├── adapters/             # Data source adapters
│       │   ├── base.py           # BaseAdapter ABC
│       │   ├── api.py            # RemoteOK, Eleduck, WorkGo
│       │   ├── rss.py            # WeWorkRemotely
│       │   ├── browser.py        # Arc.dev (Playwright)
│       │   ├── hybrid.py         # V2EX (HTML listing + JSON API)
│       │   └── html.py           # Yuancheng (disabled)
│       └── utils/
│           ├── matcher.py        # Keyword matching (CJK support)
│           └── dedup.py          # Cross-site deduplication
├── frontend/                     # Next.js 16 frontend
│   ├── src/
│   │   ├── app/                  # App Router pages
│   │   ├── components/           # React components (shadcn/ui)
│   │   └── lib/                  # Supabase client, utilities
│   ├── package.json
│   └── Dockerfile
├── supabase/
│   └── migrations/               # SQL migration files (001-004)
├── docker-compose.yml            # Backend + Frontend + nginx
├── Dockerfile.backend            # Playwright base image
├── nginx.conf                    # Reverse proxy configuration
├── pyproject.toml                # Python project metadata
└── CLAUDE.md                     # Project context for Claude Code
```

## Tech Stack

### Backend

| Library | Purpose |
|---------|---------|
| FastAPI | Async web framework |
| asyncpg | PostgreSQL driver |
| Supabase | Database + Auth + RLS |
| APScheduler | Scheduled scraping |
| httpx | Async HTTP client |
| Playwright | Browser automation (Arc.dev) |
| feedparser | RSS parsing (WeWorkRemotely) |
| beautifulsoup4 | HTML parsing (V2EX, Yuancheng) |
| Pydantic v2 | Data validation |
| loguru | Structured logging |
| python-jose | JWT handling |
| fake-useragent | User-Agent rotation |

### Frontend

| Library | Purpose |
|---------|---------|
| Next.js 16 | React framework (App Router) |
| TypeScript | Type safety |
| Tailwind CSS | Utility-first styling |
| shadcn/ui | UI component library |
| Supabase JS | Auth + database client |

### Infrastructure

| Tool | Purpose |
|------|---------|
| Docker Compose | Multi-container orchestration |
| nginx | Reverse proxy |
| uvicorn | ASGI server |

## Environment Variables

### Backend (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase service role key |
| `SUPABASE_JWT_SECRET` | Yes | JWT verification secret |
| `WORKGO_COOKIE` | No | Clerk `__client` cookie for WorkGo |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

### Frontend (`.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |
| `NEXT_PUBLIC_API_URL` | No | Backend API URL (default: `/api`) |

## Roadmap

### Phase 1 ✅
- RemoteOK, Eleduck, WeWorkRemotely adapters
- Keyword matching with CJK support
- Cross-site deduplication
- Async architecture (httpx, asyncpg)

### Phase 2 ✅
- V2EX, Arc.dev, WorkGo, 远程.work adapters
- Concurrent scraping with asyncio.gather
- Browser automation with Playwright

### Phase 3 ✅
- FastAPI backend with Supabase PostgreSQL
- Next.js 16 frontend with shadcn/ui
- Docker Compose deployment (backend + frontend + nginx)
- Supabase Auth with JWT and RLS
- Job favorites, subscriptions, notifications
- Admin dashboard for scraper management
- APScheduler for automated 2-hour scraping

### Future
- Job scoring and ranking algorithms
- Advanced search filters (salary, experience, location)
- Telegram/Slack notifications
- Email digest subscriptions
- Analytics dashboard

## License

MIT License
