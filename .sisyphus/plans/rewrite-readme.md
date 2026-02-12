# Rewrite README.md

## TL;DR

> **Quick Summary**: Rewrite README.md to reflect the current full-stack architecture (FastAPI + Next.js + Supabase), replacing the outdated CLI + SQLite description.
> 
> **Deliverables**: 
> - Updated `README.md` at project root
> 
> **Estimated Effort**: Quick
> **Parallel Execution**: NO - single task
> **Critical Path**: Task 1 only

---

## Context

### Original Request
User asked to rewrite README.md. The current README describes the old architecture (CLI tool, SQLite, YAML config, standalone scraper/) which no longer exists after the Phase 3 consolidation.

### What Changed
- CLI entry point (`main.py`) → FastAPI server (`app/main.py`)
- SQLite + aiosqlite → Supabase PostgreSQL + asyncpg
- YAML config files → Database-driven config via `config_service.py`
- Standalone `scraper/` directory → Consolidated into `app/scraper/`
- No tests directory (deleted during consolidation)
- Added: Next.js 16 frontend, Docker Compose, Supabase Auth, APScheduler
- Added: Favorites, subscriptions, notifications features
- 10 API routers: health, jobs, scraper, stats, auth, config, scheduler, favorites, notifications, subscriptions

---

## Work Objectives

### Core Objective
Replace the entire README.md with accurate content reflecting the current full-stack application.

### Must Have
- Accurate project description (full-stack, not CLI tool)
- Current tech stack (FastAPI, Next.js, Supabase, asyncpg, Docker)
- Current project structure (app/ with scraper/, services/, routers/, models/)
- Current architecture diagram (FastAPI → Orchestrator → Adapters → Matcher → Dedup → Supabase)
- Correct data sources table with adapter locations under `app/scraper/adapters/`
- Current setup instructions (backend + frontend + Docker)
- API endpoints overview (10 routers)
- Current environment variables (DATABASE_URL, SUPABASE_URL, SUPABASE_KEY)
- Accurate roadmap showing Phase 1-3 complete
- DB-driven config explanation (not YAML)

### Must NOT Have (Guardrails)
- ❌ NO references to `main.py` CLI, `python main.py scrape`, argparse
- ❌ NO references to SQLite, aiosqlite
- ❌ NO references to `config/sites.yaml` or `config/keywords.yaml`
- ❌ NO references to `scraper/` as a top-level directory
- ❌ NO references to `tests/` directory (deleted)
- ❌ NO references to `data/`, `scripts/`, `logs/` directories
- ❌ NO references to pyyaml
- ❌ NO test count claims (tests were deleted)
- ❌ NO fabricated features or endpoints not in the codebase

---

## Verification Strategy

### Test Decision
- **Automated tests**: None (documentation task)

### Agent-Executed QA Scenarios (MANDATORY)

```
Scenario: README contains no stale references
  Tool: Bash (grep)
  Steps:
    1. grep -i "sqlite\|aiosqlite\|main\.py scrape\|config/sites\.yaml\|config/keywords\.yaml\|pyyaml\|335 tests\|scraper/models" README.md
    2. Assert: zero matches (exit code 1 = no matches)
  Expected Result: No stale references found
  Evidence: grep output

Scenario: README contains all required sections
  Tool: Bash (grep)
  Steps:
    1. grep -c "FastAPI\|Supabase\|Next\.js\|Docker\|asyncpg" README.md
    2. Assert: count >= 5
  Expected Result: All key technologies mentioned
  Evidence: grep output

Scenario: Project structure in README matches actual filesystem
  Tool: Bash
  Steps:
    1. Verify README mentions app/scraper/, app/services/, app/routers/, frontend/
    2. Verify README does NOT mention scraper/ as top-level, tests/, config/, data/
  Expected Result: Structure matches reality
  Evidence: grep output
```

---

## Execution Strategy

Single task — no parallelization needed.

---

## TODOs

- [ ] 1. Rewrite README.md

  **What to do**:
  - Read current README.md (already gathered)
  - Write complete replacement covering:
    - Project title + accurate 1-line description (full-stack app, not CLI tool)
    - Features list (updated: scheduled scraping, REST API, auth, favorites, notifications, Docker)
    - Data Sources table (same 7 sources, adapter paths now under `app/scraper/adapters/`)
    - Quick Start: Backend (`pip install -e ".[dev]"` + `uvicorn app.main:app --reload`), Frontend (`cd frontend && pnpm install && pnpm dev`), Docker (`docker-compose up -d`)
    - API Endpoints table (10 routers with paths)
    - Configuration: explain DB-driven config (site_configs, keyword_configs, match_rules tables)
    - Architecture diagram: `FastAPI → Orchestrator → Adapters → Matcher → Dedup → Supabase PostgreSQL`
    - Project structure tree (current: app/, frontend/, supabase/, docker files)
    - Tech stack (FastAPI, Next.js 16, Supabase, asyncpg, Playwright, APScheduler, Tailwind, shadcn/ui)
    - Environment variables (DATABASE_URL, SUPABASE_URL, SUPABASE_KEY, NEXT_PUBLIC_*)
    - Roadmap: Phase 1-3 complete, Phase 4 future
    - License
  - Run QA grep checks

  **Must NOT do**:
  - Reference any deleted directories or old CLI workflow
  - Fabricate features not in codebase
  - Include test instructions (no tests exist currently)

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation rewrite task — prose-heavy, no code changes
  - **Skills**: []
    - No special skills needed — pure file writing

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (single task)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `CLAUDE.md` — Contains the authoritative architecture description, commands, conventions, and gotchas. Use this as the primary source of truth.
  
  **Structure References**:
  - `app/routers/*.py` — 10 routers: health, jobs, scraper, stats, auth, config, scheduler, favorites, notifications, subscriptions
  - `app/services/*.py` — storage, config_service, scraper_service, job_service, scheduler, auth_service
  - `app/scraper/adapters/*.py` — 7 adapters: api (RemoteOK, Eleduck, WorkGo), rss (WWR), browser (Arc.dev), hybrid (V2EX), html (Yuancheng)
  - `app/scraper/orchestrator.py` — Pipeline coordination
  - `app/scraper/utils/matcher.py` — Keyword matching
  - `app/scraper/utils/dedup.py` — Cross-site dedup
  - `app/main.py` — FastAPI app with lifespan
  
  **Config References**:
  - `docker-compose.yml` — 3 services: backend, frontend, nginx
  - `Dockerfile.backend` — Playwright base image, uvicorn CMD
  - `pyproject.toml` — Dependencies list (no pyyaml, has asyncpg/supabase/apscheduler)
  - `.env` — DATABASE_URL, SUPABASE_URL, SUPABASE_KEY environment variables
  
  **DB Schema References**:
  - `supabase/migrations/` — 4 migration files defining schema
  - Tables: site_configs, keyword_configs, match_rules, jobs, favorites, subscriptions, notifications, scrape_runs, users

  **Acceptance Criteria**:
  - [ ] README.md rewritten with current architecture
  - [ ] Zero references to: sqlite, aiosqlite, main.py scrape, config/*.yaml, pyyaml, tests/
  - [ ] Mentions: FastAPI, Supabase, Next.js, Docker, asyncpg, APScheduler
  - [ ] Project structure tree matches actual filesystem
  - [ ] All 10 API routers documented
  - [ ] DB-driven config explained (not YAML)

  **Commit**: YES
  - Message: `docs: rewrite README to reflect full-stack architecture`
  - Files: `README.md`

---

## Success Criteria

### Verification Commands
```bash
grep -ci "sqlite\|aiosqlite\|main\.py scrape\|config/sites\.yaml\|pyyaml" README.md  # Expected: 0
grep -c "FastAPI" README.md  # Expected: >= 1
grep -c "Supabase" README.md  # Expected: >= 1
grep -c "Next.js" README.md  # Expected: >= 1
```

### Final Checklist
- [ ] README accurately describes current full-stack architecture
- [ ] No stale references to deleted components
- [ ] Setup instructions work for backend, frontend, and Docker
