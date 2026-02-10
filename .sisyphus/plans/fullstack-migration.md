# Full-Stack Migration: CLI → FastAPI + Supabase + Next.js 16

## TL;DR

> **Quick Summary**: 将现有 Python CLI 爬虫工具迁移为全栈 SaaS 平台。后端改用 FastAPI 纯 API 服务，数据库从 SQLite 迁移到 Supabase (PostgreSQL via asyncpg)，新建 Next.js 16 前端（独立仓库）包含职位浏览、用户认证、收藏订阅、管理控制台等功能。
>
> **Deliverables**:
> - FastAPI 后端 API（替代 CLI，含定时调度）
> - Supabase PostgreSQL 数据库（多表 schema + RLS）
> - Next.js 16 前端（6 大功能模块）
> - Docker Compose 部署配置
>
> **Estimated Effort**: XL (40+ tasks across 5 phases)
> **Parallel Execution**: YES - 5 waves (phases are sequential, tasks within phases can parallelize)
> **Critical Path**: Phase 1 (FastAPI shell) → Phase 2 (Supabase storage) → Phase 3 (Auth+Scheduler) → Phase 4 (Frontend core) → Phase 5 (Frontend features)

---

## Context

### Original Request
用户要求三项重大变更：
1. 将 CLI (argparse) 改为 FastAPI 纯 API 服务
2. 数据库从 SQLite/aiosqlite 迁移到 Supabase
3. 新增 Next.js 16 + Tailwind CSS + TypeScript + shadcn/ui 前端（独立仓库）

### Interview Summary
**Key Discussions**:
- **后端职责**: 纯 API 服务，不保留 CLI
- **前端功能**: 全部 6 个模块（职位列表+搜索、详情页、统计仪表盘、爬虫管理、用户认证、收藏/订阅通知）
- **仓库结构**: 前后端分开两个仓库
- **部署**: Docker Compose
- **定时调度**: APScheduler (AsyncIOScheduler) 内置 FastAPI
- **认证**: Supabase Auth 邮箱+密码 + OAuth (Google/GitHub)
- **配置管理**: 关键词和站点配置迁移到数据库
- **通知**: 站内通知 + 邮件通知
- **用户体系**: 多用户平台
- **测试**: TDD for new code，保留现有 320 个测试
- **主题**: 深色/浅色切换
- **API 文档**: FastAPI 自动生成即可

**Research Findings**:
- 核心爬虫逻辑（7 个 adapter、matcher、dedup）完全解耦于存储层，可直接复用
- 仅需重写：StorageManager、main.py CLI、Orchestrator 初始化部分
- ~292 个 adapter/matcher/dedup 测试无需修改，~28 个 storage/integration 测试需重写
- supabase-py REST 不适合批量 upsert（每 job 一次 HTTP），推荐 asyncpg 做数据操作
- FastAPI lifespan events 管理 APScheduler 生命周期
- Next.js 16 默认 Server Components + Turbopack

### Metis Review
**Identified Gaps** (addressed):
- **asyncpg vs supabase-py**: 用 asyncpg 做数据操作（批量 upsert、查询），supabase-py 仅做 Auth JWT 验证
- **VALID_SOURCES 硬编码**: 改为从数据库动态加载
- **并发爬取冲突**: 实现 "skip if busy" 互斥锁
- **时区处理**: 使用 UTC timezone-aware datetime
- **Tags 类型**: PostgreSQL 使用 `TEXT[]` 原生数组
- **Playwright in Docker**: 使用 `mcr.microsoft.com/playwright/python` 基础镜像
- **DB 初始化数据**: 创建 seed 脚本从 YAML 导入初始配置
- **Config 缓存**: 内存缓存 + TTL，不每次请求都查 DB
- **爬取历史**: 新增 `scrape_runs` 表记录每次爬取状态

---

## Work Objectives

### Core Objective
将单用户 CLI 爬虫工具升级为多用户全栈 SaaS 平台，保持核心爬虫逻辑不变，替换入口层和存储层，新建前端。

### Concrete Deliverables
- `app/` — FastAPI 后端应用（routers, services, models, config）
- Supabase PostgreSQL schema（8+ 表，含 RLS 策略）
- `frontend/` — Next.js 16 前端应用（独立仓库）
- `docker-compose.yml` — 编排 FastAPI + Next.js + nginx
- `Dockerfile.backend` + `Dockerfile.frontend` — 容器化配置
- 数据迁移脚本（SQLite → Supabase）
- DB seed 脚本（初始站点和关键词配置）

### Definition of Done
- [ ] FastAPI 启动并提供 /docs OpenAPI 文档
- [ ] 所有 292+ adapter/matcher/dedup 测试通过（不修改）
- [ ] 爬虫通过 API 端点触发并存储结果到 Supabase
- [ ] 用户可注册/登录，收藏职位，设置订阅
- [ ] 前端展示职位列表、详情、统计仪表盘
- [ ] Docker Compose 一键启动所有服务
- [ ] 深色/浅色主题切换正常

### Must Have
- FastAPI REST API 替代所有 CLI 功能
- asyncpg 直连 Supabase PostgreSQL（非 REST）
- Supabase Auth 认证（邮箱 + OAuth）
- APScheduler 定时爬取 + 互斥锁
- 多表 schema + RLS 数据隔离
- 前端 6 大模块全部实现
- 站内通知 + 邮件通知
- TDD（新代码先写测试）
- Docker Compose 部署

### Must NOT Have (Guardrails)
- ❌ 不修改任何 adapter 文件（`scraper/adapters/*.py` 零改动）
- ❌ 不修改 `DedupManager`（`scraper/utils/dedup.py` 零改动）
- ❌ 不修改 adapter/matcher/dedup 测试文件
- ❌ 不创建 StorageInterface ABC 抽象层（用 Protocol + 单实现 + 测试 Fake）
- ❌ 不实现实时功能（Supabase Realtime 留待 v2）
- ❌ 不加 Elasticsearch（用 PostgreSQL 全文搜索）
- ❌ 不做国际化（i18n）
- ❌ 不做移动端适配
- ❌ 不做多租户/团队功能
- ❌ 不做 Kubernetes 部署
- ❌ 不做 Slack/SMS/Push 通知渠道
- ❌ 不修改 `JobPosting` 构造函数签名（7 个 adapter 依赖它）
- ❌ 不做 API 版本管理（v1/v2 前缀）
- ❌ 不做应用追踪（application tracking）
- ❌ 不做复杂用户 profile（仅 name + email）

---

## Verification Strategy

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-asyncio)
- **Automated tests**: TDD (RED-GREEN-REFACTOR)
- **Framework**: pytest (backend), vitest (frontend)

### Agent-Executed QA Tools

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| **Backend API** | Bash (curl) | Send requests, parse JSON, assert fields/status |
| **Frontend UI** | Playwright (playwright skill) | Navigate, interact, assert DOM, screenshot |
| **Database** | Bash (python script) | Connect via asyncpg, query, assert results |
| **Docker** | Bash (docker compose) | Build, start, health check |
| **Tests** | Bash (pytest/vitest) | Run suite, assert 0 failures |

---

## Database Schema Design

### Tables

```sql
-- 1. jobs: Core job postings (migrated from SQLite)
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,                    -- MD5(url|title), keep existing format
    title TEXT NOT NULL,
    company TEXT,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    salary TEXT,
    location TEXT,
    description TEXT,
    tags TEXT[] DEFAULT '{}',               -- Native PostgreSQL array
    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL,
    update_count INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_is_active ON jobs(is_active);
CREATE INDEX idx_jobs_first_seen ON jobs(first_seen DESC);
CREATE INDEX idx_jobs_company ON jobs(company);
CREATE INDEX idx_jobs_fulltext ON jobs USING GIN(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,'')));

-- 2. site_configs: Dynamic site configuration (replaces sites.yaml)
CREATE TABLE site_configs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    site_id TEXT UNIQUE NOT NULL,           -- e.g. "remoteok"
    name TEXT NOT NULL,                     -- e.g. "RemoteOK"
    adapter_type TEXT NOT NULL,             -- e.g. "api", "rss", "browser"
    url TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    skip_location_match BOOLEAN DEFAULT FALSE,
    rate_limit_seconds REAL DEFAULT 2.0,
    extra_config JSONB DEFAULT '{}',        -- headers, pagination, auth etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. keyword_configs: Dynamic keyword configuration (replaces keywords.yaml)
CREATE TABLE keyword_configs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    group_name TEXT NOT NULL,               -- "location" or "technology"
    keyword TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_name, keyword)
);

-- 4. match_rules: Keyword matching rules
CREATE TABLE match_rules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    rule_expression TEXT NOT NULL DEFAULT 'location AND technology',
    skip_location_for TEXT[] DEFAULT '{}',  -- site_ids that skip location matching
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. profiles: User profiles (extends Supabase auth.users)
CREATE TABLE profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT NOT NULL,
    display_name TEXT,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    notification_preferences JSONB DEFAULT '{"in_app": true, "email": false}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. favorites: User job bookmarks
CREATE TABLE favorites (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    job_id TEXT REFERENCES jobs(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, job_id)
);
CREATE INDEX idx_favorites_user ON favorites(user_id);

-- 7. subscriptions: User keyword subscriptions for notifications
CREATE TABLE subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,                      -- User-facing name
    keywords TEXT[] NOT NULL,                -- Keywords to match
    match_mode TEXT DEFAULT 'any' CHECK (match_mode IN ('any', 'all')),
    sources TEXT[] DEFAULT '{}',             -- Empty = all sources
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);

-- 8. notifications: In-app + email notifications
CREATE TABLE notifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('new_match', 'scrape_complete', 'system')),
    title TEXT NOT NULL,
    body TEXT,
    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    is_read BOOLEAN DEFAULT FALSE,
    email_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read) WHERE NOT is_read;

-- 9. scrape_runs: Scraping history and status tracking
CREATE TABLE scrape_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    triggered_by UUID REFERENCES profiles(id) ON DELETE SET NULL, -- NULL = scheduler
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('manual', 'scheduled')),
    sites TEXT[] NOT NULL,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    dry_run BOOLEAN DEFAULT FALSE,
    summary JSONB,                          -- {total_scraped, matched, dedup_removed, new, updated}
    errors JSONB DEFAULT '[]',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX idx_scrape_runs_status ON scrape_runs(status);

-- RLS Policies
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Jobs readable by all authenticated" ON jobs FOR SELECT TO authenticated USING (true);
CREATE POLICY "Jobs writable by service role" ON jobs FOR ALL TO service_role USING (true);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own profile" ON profiles FOR SELECT TO authenticated USING (auth.uid() = id);
CREATE POLICY "Users update own profile" ON profiles FOR UPDATE TO authenticated USING (auth.uid() = id);

ALTER TABLE favorites ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own favorites" ON favorites FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own subscriptions" ON subscriptions FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own notifications" ON notifications FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE site_configs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Site configs readable by all authenticated" ON site_configs FOR SELECT TO authenticated USING (true);
CREATE POLICY "Site configs writable by admin" ON site_configs FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
);

ALTER TABLE keyword_configs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Keywords readable by all authenticated" ON keyword_configs FOR SELECT TO authenticated USING (true);
CREATE POLICY "Keywords writable by admin" ON keyword_configs FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
);

ALTER TABLE scrape_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Scrape runs readable by all authenticated" ON scrape_runs FOR SELECT TO authenticated USING (true);
CREATE POLICY "Scrape runs writable by service role" ON scrape_runs FOR ALL TO service_role USING (true);
```

---

## Execution Strategy

### Parallel Execution Waves

```
Phase 1 — FastAPI Shell (Backend Repo):
├── Task 1: Project restructure + FastAPI app skeleton
├── Task 2: Jobs API endpoints (list, detail, search)
├── Task 3: Scrape trigger + stats + export endpoints
└── Task 4: Integration wiring (orchestrator → API)
    [Gate: AC-1 through AC-8 pass]

Phase 2 — Supabase Storage (Backend Repo):
├── Task 5: Supabase project setup + schema migration
├── Task 6: SupabaseStorage service (asyncpg)
├── Task 7: JobPosting model evolution + data migration script
├── Task 8: Orchestrator integration with new storage
└── Task 9: Rewrite storage/integration tests
    [Gate: AC-15, AC-16 + new tests pass]

Phase 3 — Auth + Scheduler (Backend Repo):
├── Task 10: Supabase Auth integration (register, login, JWT middleware)
├── Task 11: Config-from-DB (site_configs + keyword_configs + seed script)
├── Task 12: APScheduler + scrape_runs tracking
├── Task 13: Favorites + subscriptions API
└── Task 14: Notifications service (in-app + email)
    [Gate: AC-9 through AC-14 pass]

Phase 4 — Frontend Core (Frontend Repo):
├── Task 15: Next.js 16 project init + shadcn + Tailwind
├── Task 16: Auth pages (login, register, OAuth)
├── Task 17: Job listing page (Server Component + search/filter)
├── Task 18: Job detail page
└── Task 19: Stats dashboard
    [Gate: AC-17 through AC-20 pass]

Phase 5 — Frontend Features + Deployment:
├── Task 20: Favorites + subscriptions UI
├── Task 21: Notification center
├── Task 22: Scraper admin console
├── Task 23: Dark/light theme toggle
├── Task 24: Docker Compose deployment
└── Task 25: Data migration (SQLite → Supabase)
    [Gate: AC-21 through AC-23 pass]
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3, 4 | None |
| 2 | 1 | 4 | 3 |
| 3 | 1 | 4 | 2 |
| 4 | 2, 3 | Phase 2 | None |
| 5 | None | 6, 7 | None |
| 6 | 5 | 8 | 7 |
| 7 | 5 | 8 | 6 |
| 8 | 6, 7 | 9 | None |
| 9 | 8 | Phase 3 | None |
| 10 | Phase 2 | 13, 14 | 11, 12 |
| 11 | Phase 2 | 12 | 10 |
| 12 | 11 | 14 | 10 |
| 13 | 10 | Phase 5 (Task 20) | 14 |
| 14 | 10, 12 | Phase 5 (Task 21) | 13 |
| 15 | None | 16, 17, 18, 19 | None |
| 16 | 15, Phase 3 (Task 10) | 20 | 17, 18, 19 |
| 17 | 15, Phase 2 | 20 | 16, 18, 19 |
| 18 | 17 | None | 16, 19 |
| 19 | 15, Phase 2 | None | 16, 17, 18 |
| 20 | 16, 17, Phase 3 (Task 13) | None | 21, 22, 23 |
| 21 | 16, Phase 3 (Task 14) | None | 20, 22, 23 |
| 22 | 16, Phase 3 (Task 12) | None | 20, 21, 23 |
| 23 | 15 | None | 20, 21, 22 |
| 24 | Phase 3, Phase 4 | 25 | None |
| 25 | 24 | None | None |

---

## TODOs

### Phase 1: FastAPI Shell (Keep SQLite Temporarily)

- [x] 1. Project Restructure + FastAPI App Skeleton

  **What to do**:
  - Create `app/` directory structure: `app/__init__.py`, `app/main.py`, `app/config/settings.py`, `app/routers/__init__.py`, `app/services/__init__.py`, `app/dependencies.py`
  - Install FastAPI + uvicorn: `pip install fastapi uvicorn[standard]`
  - Update `pyproject.toml` with new dependencies
  - Create `app/main.py` with FastAPI app instance, CORS middleware, lifespan placeholder
  - Create `app/config/settings.py` using Pydantic `BaseSettings` for env-based config (SUPABASE_URL, SUPABASE_KEY, etc.)
  - Create health check router: `app/routers/health.py` with `GET /api/health`
  - Verify existing 292+ adapter/matcher/dedup tests still pass (zero changes to `scraper/` directory)
  - **TDD**: Write test `tests/test_api/test_health.py` first → then implement

  **Must NOT do**:
  - Do NOT modify anything in `scraper/adapters/`, `scraper/utils/matcher.py`, `scraper/utils/dedup.py`
  - Do NOT modify any test files in `tests/test_adapters/`, `tests/test_matcher.py`, `tests/test_dedup.py`
  - Do NOT touch `scraper/utils/storage.py` yet (SQLite still in use)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Backend scaffolding with FastAPI, project restructuring requires understanding existing architecture
  - **Skills**: []
    - No specialized skills needed — standard Python/FastAPI setup

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential — Phase 1 foundation
  - **Blocks**: Tasks 2, 3, 4
  - **Blocked By**: None (start immediately)

  **References**:
  - `main.py:119-167` — Current CLI structure (build_parser) — understand what commands exist to map to API routes
  - `scraper/orchestrator.py:22-30` — `_ADAPTER_MAP` dict — will need to be accessible from API layer
  - `scraper/orchestrator.py:42-58` — `__init__` method — understand constructor params for service wiring
  - `pyproject.toml` — Current dependencies list — add FastAPI/uvicorn alongside existing deps
  - FastAPI official: https://fastapi.tiangolo.com/tutorial/bigger-applications/ — APIRouter pattern
  - FastAPI official: https://fastapi.tiangolo.com/advanced/events/ — Lifespan events pattern

  **Acceptance Criteria**:
  - [ ] `app/main.py` exists with FastAPI app instance
  - [ ] `python -m pytest tests/test_adapters/ tests/test_matcher.py tests/test_dedup.py -v` → 292+ tests pass, 0 failures
  - [ ] Test file `tests/test_api/test_health.py` exists and passes

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: FastAPI starts and serves docs
    Tool: Bash (curl)
    Preconditions: uvicorn running on localhost:8000
    Steps:
      1. Start server: uvicorn app.main:app --host 0.0.0.0 --port 8000 &
      2. Wait 3 seconds
      3. curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
      4. Assert: HTTP status is 200
      5. curl -s http://localhost:8000/api/health | python -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok'"
      6. Assert: Exit code 0
    Expected Result: FastAPI serves OpenAPI docs and health endpoint
    Evidence: Response captured

  Scenario: Existing tests unaffected
    Tool: Bash (pytest)
    Preconditions: None
    Steps:
      1. python -m pytest tests/test_adapters/ tests/test_matcher.py tests/test_dedup.py -v --tb=short
      2. Assert: Exit code 0
      3. Assert: stdout contains "passed" and "0 failed" or no "FAILED"
    Expected Result: All 292+ tests pass unchanged
    Evidence: pytest output captured
  ```

  **Commit**: YES
  - Message: `feat(api): add FastAPI app skeleton with health endpoint`
  - Files: `app/`, `pyproject.toml`, `tests/test_api/`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 2. Jobs API Endpoints

  **What to do**:
  - Create `app/routers/jobs.py` with:
    - `GET /api/jobs` — List jobs with pagination (page, per_page), search (q), source filter
    - `GET /api/jobs/{job_id}` — Single job detail
    - `GET /api/jobs/search` — Full-text search endpoint
  - Create `app/services/job_service.py` that wraps `StorageManager` (temporary, will be replaced by Supabase in Phase 2)
  - Add Pydantic response models in `app/models/responses.py`:
    - `JobResponse`, `JobListResponse` (with pagination metadata), `PaginationMeta`
  - **TDD**: Write `tests/test_api/test_jobs.py` first with mocked storage → then implement

  **Must NOT do**:
  - Do NOT add auth middleware yet (Phase 3)
  - Do NOT implement write operations yet
  - Do NOT modify `scraper/models.py` JobPosting class

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: API endpoint design with proper REST conventions, response models, pagination
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1.2 (with Task 3)
  - **Blocks**: Task 4
  - **Blocked By**: Task 1

  **References**:
  - `scraper/utils/storage.py:137-175` — `get_all_jobs()` method — understand current query and return type
  - `scraper/utils/storage.py:178-220` — `get_stats()` method — stats query structure
  - `scraper/models.py:16-73` — `JobPosting` model — all fields for API response schema
  - `scraper/models.py:74-97` — `to_db_dict()`, `from_db_row()` — serialization patterns
  - FastAPI: https://fastapi.tiangolo.com/tutorial/response-model/ — Response model pattern

  **Acceptance Criteria**:
  - [ ] Test `tests/test_api/test_jobs.py` created and passes
  - [ ] `GET /api/jobs` returns paginated job list with correct schema
  - [ ] `GET /api/jobs/{id}` returns single job or 404

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Jobs list endpoint with pagination
    Tool: Bash (curl)
    Preconditions: Server running, some jobs in SQLite DB
    Steps:
      1. curl -s "http://localhost:8000/api/jobs?page=1&per_page=5" > /tmp/jobs_response.json
      2. python -c "import json; d=json.load(open('/tmp/jobs_response.json')); assert 'data' in d; assert 'pagination' in d; assert len(d['data']) <= 5"
      3. Assert: Exit code 0
      4. python -c "import json; d=json.load(open('/tmp/jobs_response.json')); j=d['data'][0]; assert all(k in j for k in ['id','title','url','source'])"
      5. Assert: Exit code 0
    Expected Result: Paginated list with proper schema
    Evidence: /tmp/jobs_response.json

  Scenario: Job detail returns 404 for missing ID
    Tool: Bash (curl)
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/jobs/nonexistent-id
      2. Assert: Output is "404"
    Expected Result: 404 for non-existent job
    Evidence: HTTP status code
  ```

  **Commit**: YES
  - Message: `feat(api): add jobs list, detail, and search endpoints`
  - Files: `app/routers/jobs.py`, `app/services/job_service.py`, `app/models/responses.py`, `tests/test_api/test_jobs.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 3. Scrape Trigger + Stats + Export Endpoints

  **What to do**:
  - Create `app/routers/scraper.py` with:
    - `POST /api/scrape` — Trigger scrape (body: `{sites?: string[], dry_run?: bool}`)
    - `GET /api/scrape/status/{run_id}` — Check scrape status (placeholder, full impl in Phase 3)
  - Create `app/routers/stats.py` with:
    - `GET /api/stats` — Database statistics
    - `GET /api/export` — Export jobs as JSON (returns file download)
  - Wire `ScraperOrchestrator` as a FastAPI dependency in `app/services/scraper_service.py`
  - Use `BackgroundTasks` for non-blocking scrape execution
  - **TDD**: Write `tests/test_api/test_scraper.py` and `tests/test_api/test_stats.py` first

  **Must NOT do**:
  - Do NOT implement APScheduler yet (Phase 3)
  - Do NOT require authentication yet (Phase 3)
  - Do NOT add scrape_runs table yet (Phase 3)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: API design + async background task orchestration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1.2 (with Task 2)
  - **Blocks**: Task 4
  - **Blocked By**: Task 1

  **References**:
  - `scraper/orchestrator.py:61-157` — `run()` method — complete pipeline logic
  - `scraper/orchestrator.py:75-82` — Return summary dict structure
  - `scraper/utils/storage.py:178-220` — `get_stats()` — stats structure
  - `scraper/utils/storage.py:222-259` — `export_json()` — export logic
  - `main.py:36-68` — `cmd_scrape()` — current scrape flow with signal handling
  - FastAPI: https://fastapi.tiangolo.com/tutorial/background-tasks/ — BackgroundTasks pattern

  **Acceptance Criteria**:
  - [ ] Tests `tests/test_api/test_scraper.py` and `tests/test_api/test_stats.py` pass
  - [ ] `POST /api/scrape` accepts JSON body and returns status
  - [ ] `GET /api/stats` returns `{total, active, inactive, by_source}`
  - [ ] `GET /api/export` returns JSON file download

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Scrape trigger with dry_run
    Tool: Bash (curl)
    Preconditions: Server running
    Steps:
      1. curl -s -X POST http://localhost:8000/api/scrape \
           -H "Content-Type: application/json" \
           -d '{"sites": ["remoteok"], "dry_run": true}'
      2. Assert: HTTP status is 200 or 202
      3. Assert: response contains "status" field
    Expected Result: Scrape triggered successfully
    Evidence: Response body captured

  Scenario: Stats endpoint returns valid structure
    Tool: Bash (curl)
    Steps:
      1. curl -s http://localhost:8000/api/stats | python -c "import sys,json; d=json.load(sys.stdin); assert all(k in d for k in ['total','active','by_source'])"
      2. Assert: Exit code 0
    Expected Result: Stats with correct keys
    Evidence: Response body
  ```

  **Commit**: YES
  - Message: `feat(api): add scrape trigger, stats, and export endpoints`
  - Files: `app/routers/scraper.py`, `app/routers/stats.py`, `app/services/scraper_service.py`, `tests/test_api/`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 4. Integration Wiring + Phase 1 Verification

  **What to do**:
  - Wire all routers into `app/main.py` with proper prefixes
  - Add request/response logging middleware using loguru
  - Add global exception handler
  - Ensure `scraper/` package is importable from `app/` (adjust sys.path or make proper package)
  - Create comprehensive integration test: `tests/test_api/test_integration.py`
  - Run full test suite to verify zero regression
  - **TDD**: Integration tests first

  **Must NOT do**:
  - Do NOT add auth middleware
  - Do NOT modify scraper/ internal logic

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration work requires understanding all components together
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential — Phase 1 final task
  - **Blocks**: Phase 2
  - **Blocked By**: Tasks 2, 3

  **References**:
  - `app/main.py` — FastAPI app (created in Task 1)
  - `app/routers/` — All routers (created in Tasks 2, 3)
  - `scraper/logger.py` — Existing loguru setup — extend for API request logging
  - `scraper/orchestrator.py:42-58` — Orchestrator init — understand dependency chain

  **Acceptance Criteria**:
  - [ ] All routers mounted at `/api/*` prefix
  - [ ] `python -m pytest tests/ -v` → ALL tests pass (292+ old + new API tests)
  - [ ] Exception handler returns proper JSON errors
  - [ ] Request logging shows in loguru

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Full API integration smoke test
    Tool: Bash (curl)
    Preconditions: Server running with uvicorn
    Steps:
      1. curl -s http://localhost:8000/api/health → assert status 200
      2. curl -s http://localhost:8000/api/jobs → assert status 200, has "data" key
      3. curl -s http://localhost:8000/api/stats → assert status 200, has "total" key
      4. curl -s http://localhost:8000/api/export → assert status 200, Content-Type is application/json
      5. curl -s http://localhost:8000/nonexistent → assert status 404, body is JSON with "detail"
    Expected Result: All endpoints respond correctly
    Evidence: All responses captured

  Scenario: Complete test suite passes
    Tool: Bash (pytest)
    Steps:
      1. python -m pytest tests/ -v --tb=short
      2. Assert: Exit code 0
      3. Assert: No "FAILED" in output
    Expected Result: 0 failures across all tests
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `feat(api): complete Phase 1 - FastAPI shell with all endpoints wired`
  - Files: `app/main.py`, `tests/test_api/test_integration.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

### Phase 2: Supabase Storage Migration

- [ ] 5. Supabase Project Setup + Schema Migration

  **What to do**:
  - Document Supabase project setup steps (manual: create project, get URL + keys)
  - Create `supabase/` directory with migration SQL files
  - Create `supabase/migrations/001_initial_schema.sql` with ALL tables from schema design above
  - Create `supabase/migrations/002_rls_policies.sql` with ALL RLS policies
  - Create `supabase/seed.sql` — Import initial data from current `config/sites.yaml` and `config/keywords.yaml` into `site_configs` and `keyword_configs` tables
  - Add `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `DATABASE_URL` to `app/config/settings.py`
  - Update `.env.example` with all Supabase env vars
  - **TDD**: Write test that verifies schema can be applied to a test database

  **Must NOT do**:
  - Do NOT migrate actual data yet (Task 25)
  - Do NOT set up Supabase Auth yet (Phase 3)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Database schema design, PostgreSQL migrations, SQL expertise needed
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential — Phase 2 foundation
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: Phase 1 (Task 4)

  **References**:
  - `scraper/utils/storage.py:15-40` — Current SQLite schema — source for migration mapping
  - `config/sites.yaml` — Site configurations — must be converted to seed data INSERT statements
  - `config/keywords.yaml` — Keyword configurations — must be converted to seed data INSERT statements
  - Database Schema Design section in this plan — complete SQL definitions
  - Supabase docs: https://supabase.com/docs/guides/database/postgres/row-level-security — RLS setup

  **Acceptance Criteria**:
  - [ ] `supabase/migrations/001_initial_schema.sql` creates all 9 tables
  - [ ] `supabase/migrations/002_rls_policies.sql` creates all RLS policies
  - [ ] `supabase/seed.sql` inserts all 7 site configs and all keywords from YAML
  - [ ] `.env.example` contains SUPABASE_URL, SUPABASE_SERVICE_KEY, DATABASE_URL

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Schema SQL is valid
    Tool: Bash (python + psycopg2 or asyncpg)
    Preconditions: Supabase project created, DATABASE_URL available
    Steps:
      1. Read supabase/migrations/001_initial_schema.sql
      2. Execute against Supabase database
      3. Assert: No SQL errors
      4. Query: SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'
      5. Assert: Contains jobs, site_configs, keyword_configs, match_rules, profiles, favorites, subscriptions, notifications, scrape_runs
    Expected Result: All 9 tables created successfully
    Evidence: Table list query output

  Scenario: Seed data applied
    Tool: Bash
    Steps:
      1. Execute supabase/seed.sql
      2. Query: SELECT count(*) FROM site_configs
      3. Assert: count = 7
      4. Query: SELECT count(*) FROM keyword_configs
      5. Assert: count matches total keywords in keywords.yaml
    Expected Result: All seed data present
    Evidence: Count query outputs
  ```

  **Commit**: YES
  - Message: `feat(db): add Supabase schema migrations, RLS policies, and seed data`
  - Files: `supabase/`, `.env.example`, `app/config/settings.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 6. SupabaseStorage Service (asyncpg)

  **What to do**:
  - Install `asyncpg`: `pip install asyncpg`
  - Create `app/services/storage.py` with `SupabaseStorage` class:
    - `async def init_pool()` — Create `asyncpg.Pool` from `DATABASE_URL`
    - `async def close_pool()` — Graceful shutdown
    - `async def upsert_job(job: JobPosting) → tuple[int, int]` — Bulk-ready upsert using `ON CONFLICT (id) DO UPDATE`
    - `async def upsert_jobs_batch(jobs: list[JobPosting]) → tuple[int, int]` — Batch upsert using `executemany`
    - `async def get_all_jobs(active_only, page, per_page, source, search_query) → tuple[list[JobPosting], int]` — Paginated with filters + total count
    - `async def get_job_by_id(job_id: str) → Optional[JobPosting]`
    - `async def get_stats() → dict`
    - `async def export_jobs() → list[dict]`
    - `async def health_check() → bool`
  - Define `StorageProtocol` (Python `typing.Protocol`) for type safety
  - Create `FakeStorage` in `tests/fakes/storage.py` (in-memory dict implementation for tests)
  - Integrate pool lifecycle into FastAPI lifespan
  - **TDD**: Write `tests/test_storage_supabase.py` using FakeStorage first, then integration tests with real DB

  **Must NOT do**:
  - Do NOT use supabase-py for data operations (use asyncpg)
  - Do NOT create `StorageInterface` ABC (use Protocol)
  - Do NOT modify original `scraper/utils/storage.py` (keep for reference/fallback)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Complex async database layer with connection pooling, batch operations, Protocol pattern
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2.1 (with Task 7)
  - **Blocks**: Task 8
  - **Blocked By**: Task 5

  **References**:
  - `scraper/utils/storage.py:42-175` — Current StorageManager — all methods to re-implement
  - `scraper/utils/storage.py:72-135` — `upsert_job()` — check-then-insert pattern (replace with ON CONFLICT)
  - `scraper/models.py:74-97` — `to_db_dict()` — current serialization (replace with asyncpg-native)
  - asyncpg docs: https://magicstack.github.io/asyncpg/current/api/index.html — Pool, Connection, executemany

  **Acceptance Criteria**:
  - [ ] `app/services/storage.py` implements all methods from `StorageProtocol`
  - [ ] `tests/fakes/storage.py` provides `FakeStorage` for tests
  - [ ] `tests/test_storage_supabase.py` tests pass with FakeStorage
  - [ ] Batch upsert handles 200+ jobs in one call
  - [ ] Connection pool properly initialized and closed via lifespan

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Storage health check connects to Supabase
    Tool: Bash (python script)
    Preconditions: Supabase project running, DATABASE_URL set
    Steps:
      1. python -c "
         import asyncio
         from app.services.storage import SupabaseStorage
         async def check():
             s = SupabaseStorage()
             await s.init_pool()
             assert await s.health_check() == True
             await s.close_pool()
             print('OK')
         asyncio.run(check())"
      2. Assert: Exit code 0, output "OK"
    Expected Result: Successfully connects to Supabase PostgreSQL
    Evidence: Script output

  Scenario: Batch upsert works with 100+ jobs
    Tool: Bash (python script)
    Preconditions: DB schema applied, pool initialized
    Steps:
      1. Create 100 test JobPosting objects
      2. Call upsert_jobs_batch(jobs)
      3. Query: SELECT count(*) FROM jobs WHERE source = 'test'
      4. Assert: count = 100
      5. Call upsert_jobs_batch(jobs) again (same data)
      6. Query: SELECT count(*) FROM jobs WHERE source = 'test'
      7. Assert: count still 100 (upsert, not duplicate insert)
    Expected Result: Batch upsert is idempotent
    Evidence: Count query outputs
  ```

  **Commit**: YES
  - Message: `feat(db): implement SupabaseStorage with asyncpg connection pooling and batch upsert`
  - Files: `app/services/storage.py`, `tests/fakes/storage.py`, `tests/test_storage_supabase.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 7. JobPosting Model Evolution

  **What to do**:
  - Add `to_pg_dict()` method to `JobPosting` — returns dict with timezone-aware datetimes and native list for tags (no JSON string)
  - Add `from_pg_row(row: asyncpg.Record) → JobPosting` class method
  - Ensure all datetime fields use `datetime.now(timezone.utc)` — update defaults
  - Make `VALID_SOURCES` dynamic: load from `site_configs` table at startup, cache in module-level variable
  - Update `source` field validator to use dynamic set
  - Keep `to_db_dict()` and `from_db_row()` for backward compatibility (old tests use them)
  - **TDD**: Write tests for new methods first

  **Must NOT do**:
  - Do NOT change `JobPosting.__init__` signature
  - Do NOT remove `to_db_dict()` or `from_db_row()` (adapter tests may depend on them)
  - Do NOT change field names or types

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Focused model changes, well-scoped, low risk
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2.1 (with Task 6)
  - **Blocks**: Task 8
  - **Blocked By**: Task 5

  **References**:
  - `scraper/models.py:16-132` — Complete JobPosting model — understand all fields, validators, methods
  - `scraper/models.py:14` — `VALID_SOURCES` set — must become dynamic
  - `scraper/models.py:74-97` — `to_db_dict()` — understand current serialization for comparison
  - `scraper/models.py:99-130` — `from_db_row()` — understand current deserialization
  - `tests/test_adapters/test_remoteok.py` — Example adapter test creating JobPosting — verify constructor compatibility

  **Acceptance Criteria**:
  - [ ] `to_pg_dict()` returns timezone-aware datetimes and `list[str]` tags (not JSON string)
  - [ ] `from_pg_row()` correctly deserializes asyncpg Record
  - [ ] `VALID_SOURCES` loads dynamically from a configurable source
  - [ ] All 292+ existing adapter/matcher/dedup tests still pass
  - [ ] New tests for `to_pg_dict()` and `from_pg_row()` pass

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Existing tests unaffected by model changes
    Tool: Bash (pytest)
    Steps:
      1. python -m pytest tests/test_adapters/ tests/test_matcher.py tests/test_dedup.py -v --tb=short
      2. Assert: Exit code 0, all pass
    Expected Result: Zero regression from model changes
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `feat(models): add PostgreSQL serialization methods and dynamic source validation`
  - Files: `scraper/models.py`, `tests/test_models.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 8. Orchestrator Integration with Supabase Storage

  **What to do**:
  - Modify `ScraperOrchestrator.__init__()` to accept `StorageProtocol` instance (dependency injection) instead of creating `StorageManager` internally
  - Change `_scrape_site()` to use `upsert_jobs_batch()` instead of per-job `upsert_job()` loop
  - Update `run()` to use the injected storage instance
  - Update `app/services/scraper_service.py` to inject `SupabaseStorage` into orchestrator
  - Keep config loading from YAML for now (DB config comes in Phase 3, Task 11)
  - **TDD**: Write integration test with FakeStorage first

  **Must NOT do**:
  - Do NOT modify adapter fetch logic
  - Do NOT modify matcher or dedup logic
  - Do NOT remove YAML config loading yet

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Refactoring core pipeline to use dependency injection — requires careful understanding of data flow
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential — requires Tasks 6 + 7
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 6, 7

  **References**:
  - `scraper/orchestrator.py:42-58` — `__init__` method — modify to accept storage parameter
  - `scraper/orchestrator.py:137-143` — Job upsert loop — replace with batch operation
  - `scraper/orchestrator.py:61-157` — Full `run()` method — understand complete flow for integration
  - `app/services/storage.py` — SupabaseStorage (created in Task 6) — inject into orchestrator
  - `tests/fakes/storage.py` — FakeStorage — use in integration tests

  **Acceptance Criteria**:
  - [ ] `ScraperOrchestrator.__init__` accepts optional `storage` parameter
  - [ ] If no storage passed, defaults to SupabaseStorage (backward compat)
  - [ ] Batch upsert used instead of per-job loop
  - [ ] Integration test with FakeStorage passes
  - [ ] Full API scrape endpoint works with Supabase backend

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Scrape endpoint stores to Supabase
    Tool: Bash (curl + python)
    Preconditions: Server running with Supabase storage, remoteok accessible
    Steps:
      1. curl -s -X POST http://localhost:8000/api/scrape -H "Content-Type: application/json" -d '{"sites":["remoteok"],"dry_run":false}'
      2. Wait 30 seconds for background task
      3. curl -s http://localhost:8000/api/stats | python -c "import sys,json; d=json.load(sys.stdin); assert d['total'] > 0; print(f'Total: {d[\"total\"]}')"
      4. Assert: Exit code 0, total > 0
    Expected Result: Jobs scraped and stored in Supabase
    Evidence: Stats response
  ```

  **Commit**: YES
  - Message: `refactor(orchestrator): inject storage dependency, use batch upsert for Supabase`
  - Files: `scraper/orchestrator.py`, `app/services/scraper_service.py`, `tests/test_api/test_scrape_integration.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 9. Rewrite Storage + Integration Tests

  **What to do**:
  - Rewrite `tests/test_storage.py` to test `SupabaseStorage` using `FakeStorage`
  - Rewrite `tests/test_integration.py` to use `FakeStorage` instead of `StorageManager`
  - Add new integration tests for batch upsert, pagination, search, filtering
  - Verify ALL tests (old adapter + new storage + new integration) pass together
  - **TDD**: N/A (this IS the test rewrite task)

  **Must NOT do**:
  - Do NOT modify adapter tests
  - Do NOT modify matcher or dedup tests
  - Do NOT delete old test files (rename to `test_storage_sqlite.py.bak` for reference)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Comprehensive test rewrite requiring understanding of both old and new storage
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential — Phase 2 final task
  - **Blocks**: Phase 3
  - **Blocked By**: Task 8

  **References**:
  - `tests/test_storage.py` — Current 16 storage tests — rewrite for new SupabaseStorage
  - `tests/test_integration.py` — Current 12 integration tests — rewrite with FakeStorage
  - `tests/fakes/storage.py` — FakeStorage — use as test double
  - `app/services/storage.py` — SupabaseStorage API — match test expectations

  **Acceptance Criteria**:
  - [ ] `tests/test_storage.py` rewritten with ≥16 tests for SupabaseStorage
  - [ ] `tests/test_integration.py` rewritten with ≥12 tests using FakeStorage
  - [ ] `python -m pytest tests/ -v` → ALL tests pass (old adapter + new storage + new integration)
  - [ ] Zero test imports from `scraper.utils.storage.StorageManager`

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Full test suite green
    Tool: Bash (pytest)
    Steps:
      1. python -m pytest tests/ -v --tb=short 2>&1 | tail -5
      2. Assert: Exit code 0
      3. Assert: "passed" count ≥ 320
      4. Assert: no "FAILED"
    Expected Result: All tests pass
    Evidence: pytest summary output
  ```

  **Commit**: YES
  - Message: `test: rewrite storage and integration tests for Supabase backend`
  - Files: `tests/test_storage.py`, `tests/test_integration.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

### Phase 3: Auth + Scheduler + Config

- [ ] 10. Supabase Auth Integration

  **What to do**:
  - Install `supabase`: `pip install supabase` (for Auth client only)
  - Create `app/services/auth.py`:
    - `register(email, password) → UserResponse` — via Supabase Auth API
    - `login(email, password) → TokenResponse` — returns access_token + refresh_token
    - `login_oauth(provider) → OAuthRedirectURL` — Google/GitHub OAuth
    - `verify_jwt(token) → UserPayload` — Validate JWT, extract user_id
    - `get_current_user(token) → UserPayload` — FastAPI dependency
  - Create `app/routers/auth.py`:
    - `POST /api/auth/register`
    - `POST /api/auth/login`
    - `GET /api/auth/oauth/{provider}` — OAuth redirect
    - `GET /api/auth/callback` — OAuth callback
    - `POST /api/auth/refresh` — Refresh token
    - `GET /api/auth/me` — Current user profile
  - Create `app/dependencies.py`:
    - `get_current_user` — JWT extraction dependency
    - `require_admin` — Admin role check dependency
  - Create `profiles` trigger: auto-create profile row on `auth.users` insert
  - Apply auth middleware to protected endpoints (favorites, subscriptions, scraper admin)
  - **TDD**: Write auth tests with mocked Supabase client

  **Must NOT do**:
  - Do NOT implement full user profile management (just name + email)
  - Do NOT add OAuth providers beyond Google and GitHub

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Auth system with JWT, OAuth, RLS — security-critical, needs careful implementation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3.1 (with Task 11)
  - **Blocks**: Tasks 13, 14
  - **Blocked By**: Phase 2 (Task 9)

  **References**:
  - Database Schema section — `profiles` table definition + RLS policies
  - Supabase Auth docs: https://supabase.com/docs/reference/python/auth-signup — Python client auth
  - Supabase Auth docs: https://supabase.com/docs/guides/auth/social-login — OAuth setup
  - FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/ — OAuth2 with JWT pattern

  **Acceptance Criteria**:
  - [ ] `POST /api/auth/register` creates user and returns user data
  - [ ] `POST /api/auth/login` returns valid JWT
  - [ ] `GET /api/auth/me` returns user profile with valid JWT
  - [ ] Protected endpoints return 401 without token
  - [ ] Admin endpoints return 403 for non-admin users

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Registration and login flow
    Tool: Bash (curl)
    Steps:
      1. curl -s -X POST http://localhost:8000/api/auth/register \
           -H "Content-Type: application/json" \
           -d '{"email":"test@example.com","password":"TestPass123!"}' > /tmp/register.json
      2. Assert: HTTP 201, response has "user.email" = "test@example.com"
      3. curl -s -X POST http://localhost:8000/api/auth/login \
           -H "Content-Type: application/json" \
           -d '{"email":"test@example.com","password":"TestPass123!"}' > /tmp/login.json
      4. Assert: response has "access_token" (non-empty string)
      5. TOKEN=$(python -c "import json; print(json.load(open('/tmp/login.json'))['access_token'])")
      6. curl -s http://localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN" > /tmp/me.json
      7. Assert: response has "email" = "test@example.com"
    Expected Result: Full auth flow works
    Evidence: /tmp/register.json, /tmp/login.json, /tmp/me.json

  Scenario: Unauthenticated access blocked
    Tool: Bash (curl)
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/favorites
      2. Assert: Output is "401"
    Expected Result: 401 Unauthorized
    Evidence: HTTP status
  ```

  **Commit**: YES
  - Message: `feat(auth): add Supabase Auth with email/password, OAuth, JWT middleware`
  - Files: `app/services/auth.py`, `app/routers/auth.py`, `app/dependencies.py`, `tests/test_api/test_auth.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 11. Config-from-DB (Sites + Keywords + Seed)

  **What to do**:
  - Create `app/services/config_service.py`:
    - `get_site_configs() → list[SiteConfig]` — Query `site_configs` table, cache in memory (TTL 5 min)
    - `get_keyword_configs() → dict` — Query `keyword_configs` + `match_rules`, cache (TTL 5 min)
    - `update_site_config(site_id, data) → SiteConfig` — Admin update
    - `update_keyword(group, keyword, is_active) → KeywordConfig` — Admin toggle
    - `invalidate_cache()` — Force refresh after admin changes
  - Create Pydantic models: `SiteConfigModel`, `KeywordConfigModel`, `MatchRuleModel`
  - Create `app/routers/config.py`:
    - `GET /api/config/sites` — List all site configs
    - `PUT /api/config/sites/{site_id}` — Update site (admin only)
    - `GET /api/config/keywords` — List all keywords
    - `POST /api/config/keywords` — Add keyword (admin only)
    - `DELETE /api/config/keywords/{id}` — Remove keyword (admin only)
  - Modify `ScraperOrchestrator` to accept config dict from `ConfigService` instead of YAML file
  - Modify `KeywordMatcher.__init__` to accept `config: dict` parameter (already does! just need to pass DB-sourced dict)
  - Create `scripts/seed_db.py` — Read YAML files, insert into Supabase tables
  - **TDD**: Tests for config service with FakeStorage

  **Must NOT do**:
  - Do NOT allow non-admin users to modify configs
  - Do NOT auto-create adapter classes from UI (keep `_ADAPTER_MAP` hardcoded)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Config caching, admin CRUD, integration with orchestrator — multi-component work
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3.1 (with Task 10)
  - **Blocks**: Task 12
  - **Blocked By**: Phase 2 (Task 9)

  **References**:
  - `config/sites.yaml` — Current site config structure — map to `site_configs` table
  - `config/keywords.yaml` — Current keyword config structure — map to `keyword_configs` + `match_rules`
  - `scraper/orchestrator.py:49-56` — Current YAML loading — replace with DB query
  - `scraper/utils/matcher.py:22-40` — Matcher init from config dict — reuse this interface
  - `scraper/utils/matcher.py:42-67` — Pattern compilation — understand caching needs

  **Acceptance Criteria**:
  - [ ] `GET /api/config/sites` returns all 7 site configs
  - [ ] `PUT /api/config/sites/remoteok` updates config (admin only)
  - [ ] Config cache refreshes after 5 min or manual invalidation
  - [ ] `scripts/seed_db.py` successfully imports YAML to DB
  - [ ] Orchestrator uses DB-backed config for scraping

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Config endpoints work
    Tool: Bash (curl)
    Preconditions: DB seeded, admin JWT available
    Steps:
      1. curl -s http://localhost:8000/api/config/sites -H "Authorization: Bearer $ADMIN_TOKEN" > /tmp/sites.json
      2. Assert: array length = 7
      3. Assert: first item has "site_id", "name", "enabled" keys
    Expected Result: All site configs returned
    Evidence: /tmp/sites.json
  ```

  **Commit**: YES
  - Message: `feat(config): add DB-backed site and keyword configuration with admin CRUD`
  - Files: `app/services/config_service.py`, `app/routers/config.py`, `scripts/seed_db.py`, `tests/test_api/test_config.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 12. APScheduler + Scrape Runs Tracking

  **What to do**:
  - Install `apscheduler`: `pip install apscheduler`
  - Create `app/services/scheduler.py`:
    - Initialize `AsyncIOScheduler` in FastAPI lifespan
    - `schedule_scraping(interval_minutes, sites)` — Add periodic job
    - `pause_scheduler()` / `resume_scheduler()`
    - `get_scheduler_status() → dict` — Jobs, next run times
    - **Mutex**: `asyncio.Lock` to prevent overlapping scrape runs
  - Create `app/services/scrape_run_service.py`:
    - `create_run(triggered_by, trigger_type, sites, dry_run) → ScrapeRun`
    - `update_run(run_id, status, summary, errors)`
    - `get_run(run_id) → ScrapeRun`
    - `list_runs(page, per_page) → list[ScrapeRun]`
  - Create `app/routers/scheduler.py`:
    - `GET /api/scheduler/status` — Scheduler info
    - `POST /api/scheduler/pause` — Pause (admin)
    - `POST /api/scheduler/resume` — Resume (admin)
    - `GET /api/scrape/runs` — List scrape history
    - `GET /api/scrape/runs/{run_id}` — Single run detail
  - Update `POST /api/scrape` to create scrape_run record and track status
  - **TDD**: Write scheduler tests with mocked scraper

  **Must NOT do**:
  - Do NOT use Celery (keep it simple with APScheduler)
  - Do NOT implement Supabase Realtime for status updates

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Scheduler lifecycle management, concurrency control with mutex, background task tracking
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential — depends on config service (Task 11)
  - **Blocks**: Task 14
  - **Blocked By**: Task 11

  **References**:
  - `scraper/orchestrator.py:61-82` — `run()` return summary — record in scrape_runs
  - `main.py:19-28` — Current signal handling / interruption — adapt for scheduler graceful stop
  - Database Schema — `scrape_runs` table definition
  - APScheduler docs: https://apscheduler.readthedocs.io/en/stable/modules/schedulers/asyncio.html

  **Acceptance Criteria**:
  - [ ] Scheduler starts automatically with configurable interval
  - [ ] `GET /api/scheduler/status` shows scheduler state and next run times
  - [ ] Overlapping scrapes prevented (skip if busy)
  - [ ] `GET /api/scrape/runs` shows scrape history with status
  - [ ] Manual scrape trigger creates scrape_run record

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Scheduler status endpoint
    Tool: Bash (curl)
    Steps:
      1. curl -s http://localhost:8000/api/scheduler/status | python -c "import sys,json; d=json.load(sys.stdin); assert 'running' in d; print(d)"
      2. Assert: Exit code 0
    Expected Result: Scheduler status returned
    Evidence: Response body

  Scenario: Scrape run tracking
    Tool: Bash (curl)
    Steps:
      1. curl -s -X POST http://localhost:8000/api/scrape -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"sites":["remoteok"],"dry_run":true}'
      2. Extract run_id from response
      3. Wait 30s
      4. curl -s http://localhost:8000/api/scrape/runs/{run_id} -H "Authorization: Bearer $TOKEN"
      5. Assert: status is "completed" or "failed"
      6. Assert: summary is not null
    Expected Result: Run tracked from start to completion
    Evidence: Run detail response
  ```

  **Commit**: YES
  - Message: `feat(scheduler): add APScheduler with scrape run tracking and mutex protection`
  - Files: `app/services/scheduler.py`, `app/services/scrape_run_service.py`, `app/routers/scheduler.py`, `tests/test_api/test_scheduler.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 13. Favorites + Subscriptions API

  **What to do**:
  - Create `app/routers/favorites.py`:
    - `GET /api/favorites` — List user's favorite jobs
    - `POST /api/favorites` — Add job to favorites (`{job_id}`)
    - `DELETE /api/favorites/{job_id}` — Remove from favorites
  - Create `app/routers/subscriptions.py`:
    - `GET /api/subscriptions` — List user's subscriptions
    - `POST /api/subscriptions` — Create subscription (`{name, keywords[], match_mode, sources[]}`)
    - `PUT /api/subscriptions/{id}` — Update subscription
    - `DELETE /api/subscriptions/{id}` — Delete subscription
    - `POST /api/subscriptions/{id}/toggle` — Activate/deactivate
  - Create `app/services/favorite_service.py` and `app/services/subscription_service.py`
  - All endpoints require authentication (`Depends(get_current_user)`)
  - RLS ensures users only see/modify their own data
  - **TDD**: Write tests with mocked auth and FakeStorage

  **Must NOT do**:
  - Do NOT implement notification matching logic here (Task 14)
  - Do NOT build subscription sharing features

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Standard CRUD endpoints, straightforward implementation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3.2 (with Task 14)
  - **Blocks**: Task 20 (Frontend)
  - **Blocked By**: Task 10

  **References**:
  - Database Schema — `favorites` and `subscriptions` tables + RLS
  - `app/dependencies.py` — `get_current_user` dependency (created in Task 10)

  **Acceptance Criteria**:
  - [ ] Authenticated user can add/remove favorites
  - [ ] Authenticated user can CRUD subscriptions
  - [ ] Unauthenticated requests return 401
  - [ ] Users cannot see other users' favorites/subscriptions (RLS)

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Favorite a job
    Tool: Bash (curl)
    Preconditions: User logged in, jobs exist in DB
    Steps:
      1. Get first job ID: JOB_ID=$(curl -s http://localhost:8000/api/jobs?per_page=1 | python -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
      2. curl -s -X POST http://localhost:8000/api/favorites -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"job_id\":\"$JOB_ID\"}"
      3. Assert: HTTP 201
      4. curl -s http://localhost:8000/api/favorites -H "Authorization: Bearer $TOKEN"
      5. Assert: response array length ≥ 1
      6. curl -s -X DELETE http://localhost:8000/api/favorites/$JOB_ID -H "Authorization: Bearer $TOKEN"
      7. Assert: HTTP 204
    Expected Result: Full favorite lifecycle works
    Evidence: Responses captured
  ```

  **Commit**: YES
  - Message: `feat(api): add favorites and subscriptions CRUD endpoints`
  - Files: `app/routers/favorites.py`, `app/routers/subscriptions.py`, `app/services/`, `tests/test_api/`
  - Pre-commit: `python -m pytest tests/ -v`

---

- [ ] 14. Notifications Service (In-App + Email)

  **What to do**:
  - Create `app/services/notification_service.py`:
    - `check_subscriptions_after_scrape(new_jobs: list[JobPosting])` — Match new jobs against all active subscriptions
    - `create_notification(user_id, type, title, body, job_id)` — Insert to notifications table
    - `send_email_notification(user_id, notification)` — Send via Supabase Edge Function or SMTP
    - `get_notifications(user_id, page, per_page, unread_only)` — List user notifications
    - `mark_read(notification_id, user_id)` — Mark as read
    - `mark_all_read(user_id)` — Mark all as read
  - Create `app/routers/notifications.py`:
    - `GET /api/notifications` — List notifications (auth required)
    - `GET /api/notifications/unread-count` — Count unread
    - `POST /api/notifications/{id}/read` — Mark read
    - `POST /api/notifications/read-all` — Mark all read
  - Integrate with scheduler: after each scrape run, check subscriptions and create notifications
  - Email sending: use `smtplib` or Supabase Edge Functions (configurable via env var)
  - **TDD**: Write notification matching logic tests first

  **Must NOT do**:
  - Do NOT implement push notifications or WebSocket
  - Do NOT implement Slack/SMS channels
  - Do NOT implement digest emails (send immediately or not at all)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Subscription matching logic + email delivery + integration with scheduler pipeline
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3.2 (with Task 13)
  - **Blocks**: Task 21 (Frontend)
  - **Blocked By**: Tasks 10, 12

  **References**:
  - Database Schema — `notifications` and `subscriptions` tables
  - `scraper/utils/matcher.py:89-126` — Matching logic pattern — reuse for subscription matching
  - `app/services/scheduler.py` (Task 12) — Integration point after scrape completion

  **Acceptance Criteria**:
  - [ ] New matching jobs trigger notifications for subscribers
  - [ ] Notification list endpoint returns user's notifications
  - [ ] Unread count endpoint returns correct number
  - [ ] Mark read/all-read works
  - [ ] Email sent when user has email notifications enabled

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Notification created on subscription match
    Tool: Bash (curl + python)
    Steps:
      1. Create subscription with keywords ["remote", "AI"]
      2. Trigger scrape that produces matching jobs
      3. Wait 30s
      4. GET /api/notifications → Assert: at least 1 notification with type "new_match"
      5. GET /api/notifications/unread-count → Assert: count ≥ 1
      6. POST /api/notifications/{id}/read → Assert: 200
      7. GET /api/notifications/unread-count → Assert: count decreased by 1
    Expected Result: Subscription → scrape → notification flow works
    Evidence: Notification list response
  ```

  **Commit**: YES
  - Message: `feat(notifications): add in-app + email notification service with subscription matching`
  - Files: `app/services/notification_service.py`, `app/routers/notifications.py`, `tests/test_api/test_notifications.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

### Phase 4: Frontend Core (New Repository)

- [ ] 15. Next.js 16 Project Initialization

  **What to do**:
  - Initialize new Next.js 16 project: `npx create-next-app@latest job-scraper-web --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"`
  - Initialize shadcn/ui: `pnpm dlx shadcn@latest init` (style: new-york, base color: zinc)
  - Install core shadcn components: `pnpm dlx shadcn@latest add button card input dialog table badge select dropdown-menu sheet separator tabs avatar`
  - Set up project structure:
    ```
    src/
    ├── app/
    │   ├── layout.tsx        # Root layout with providers
    │   ├── page.tsx          # Landing/home
    │   ├── (auth)/           # Auth group
    │   │   ├── login/page.tsx
    │   │   └── register/page.tsx
    │   ├── jobs/
    │   │   ├── page.tsx      # Job listing
    │   │   └── [id]/page.tsx # Job detail
    │   ├── dashboard/page.tsx
    │   └── admin/            # Admin pages
    ├── components/
    │   ├── ui/               # shadcn components
    │   ├── layout/           # Header, sidebar, footer
    │   └── jobs/             # Job-specific components
    ├── lib/
    │   ├── api.ts            # FastAPI client
    │   ├── supabase.ts       # Supabase client (auth only)
    │   ├── utils.ts          # Utility functions
    │   └── types.ts          # TypeScript types
    └── hooks/                # Custom React hooks
    ```
  - Create API client (`lib/api.ts`) with base URL from env var `NEXT_PUBLIC_API_URL`
  - Create Supabase client (`lib/supabase.ts`) for auth
  - Set up dark/light theme provider using `next-themes`
  - Create basic layout with header (logo, nav, theme toggle, auth button)
  - Add `data-testid` attributes to all interactive elements
  - **Environment**: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

  **Must NOT do**:
  - Do NOT implement any feature pages yet (just skeleton routes)
  - Do NOT add i18n or complex routing

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Frontend scaffolding with shadcn/ui, theme setup, visual layout design
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: UI component setup, theme design, responsive layout

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential — Phase 4 foundation
  - **Blocks**: Tasks 16, 17, 18, 19
  - **Blocked By**: None (can start before Phase 3 if Phase 2 backend API is available)

  **References**:
  - Next.js docs: https://nextjs.org/docs/getting-started/installation — Project init
  - shadcn/ui docs: https://ui.shadcn.com/docs/installation/next — Next.js setup
  - next-themes: https://github.com/pacocoursey/next-themes — Dark mode
  - `app/main.py` — FastAPI CORS origins — ensure frontend URL is whitelisted

  **Acceptance Criteria**:
  - [ ] `pnpm dev` starts on localhost:3000
  - [ ] shadcn/ui components installed and usable
  - [ ] Theme toggle switches dark/light mode
  - [ ] API client configured with env var
  - [ ] All route stubs exist

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Next.js app starts and renders
    Tool: Playwright (playwright skill)
    Preconditions: pnpm dev running on localhost:3000
    Steps:
      1. Navigate to: http://localhost:3000
      2. Wait for: body visible (timeout: 10s)
      3. Assert: Page title contains "Job"
      4. Assert: [data-testid="header"] exists
      5. Assert: [data-testid="theme-toggle"] exists
      6. Screenshot: .sisyphus/evidence/task-15-homepage.png
    Expected Result: App renders with header and theme toggle
    Evidence: .sisyphus/evidence/task-15-homepage.png

  Scenario: Dark mode toggle works
    Tool: Playwright (playwright skill)
    Steps:
      1. Navigate to: http://localhost:3000
      2. Click: [data-testid="theme-toggle"]
      3. Wait 500ms
      4. Assert: html element has class "dark"
      5. Screenshot: .sisyphus/evidence/task-15-dark-mode.png
      6. Click: [data-testid="theme-toggle"]
      7. Assert: html element does NOT have class "dark"
    Expected Result: Theme toggles correctly
    Evidence: .sisyphus/evidence/task-15-dark-mode.png
  ```

  **Commit**: YES
  - Message: `feat: initialize Next.js 16 project with shadcn/ui, Tailwind, and dark mode`
  - Files: entire project
  - Pre-commit: `pnpm build`

---

- [ ] 16. Auth Pages (Login, Register, OAuth)

  **What to do**:
  - Create login page: `src/app/(auth)/login/page.tsx`
    - Email + password form with validation (zod + react-hook-form)
    - OAuth buttons (Google, GitHub)
    - Link to register page
  - Create register page: `src/app/(auth)/register/page.tsx`
    - Email + password + confirm password form
    - Link to login page
  - Create auth context/provider: `src/lib/auth-context.tsx`
    - `useAuth()` hook — user, loading, login, logout, register
    - Persist session via Supabase client
  - Create protected route middleware: `src/middleware.ts`
    - Redirect unauthenticated users from protected routes to /login
  - Add auth state to header (show user avatar/name when logged in, login button when not)
  - **Use shadcn components**: Card, Input, Button, Label, Form

  **Must NOT do**:
  - Do NOT implement profile page
  - Do NOT implement password reset (v2 feature)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Auth UI with form validation, OAuth flow, responsive design
  - **Skills**: [`frontend-ui-ux`, `playwright`]
    - `frontend-ui-ux`: Form design, auth UX patterns
    - `playwright`: Browser-based QA verification

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4.1 (with Tasks 17, 18, 19)
  - **Blocks**: Tasks 20, 21, 22
  - **Blocked By**: Task 15, Phase 3 Task 10 (auth API)

  **References**:
  - `app/routers/auth.py` (Task 10) — Auth API endpoints — match request/response schemas
  - Supabase JS docs: https://supabase.com/docs/reference/javascript/auth-signinwithpassword
  - shadcn Form: https://ui.shadcn.com/docs/components/form

  **Acceptance Criteria**:
  - [ ] Login page renders with email/password fields and OAuth buttons
  - [ ] Register page renders with form validation
  - [ ] Successful login redirects to /jobs
  - [ ] Protected routes redirect to /login when unauthenticated
  - [ ] Header shows user state

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Login form validation
    Tool: Playwright (playwright skill)
    Steps:
      1. Navigate to: http://localhost:3000/login
      2. Click: button[type="submit"] (without filling form)
      3. Assert: Error messages visible for email and password fields
      4. Fill: input[name="email"] → "invalid-email"
      5. Assert: Email validation error shown
      6. Fill: input[name="email"] → "test@example.com"
      7. Fill: input[name="password"] → "TestPass123!"
      8. Click: button[type="submit"]
      9. Wait for: navigation to /jobs (timeout: 10s)
      10. Assert: URL is /jobs
      11. Screenshot: .sisyphus/evidence/task-16-login-success.png
    Expected Result: Form validates and login redirects
    Evidence: .sisyphus/evidence/task-16-login-success.png

  Scenario: Unauthenticated redirect
    Tool: Playwright (playwright skill)
    Steps:
      1. Clear cookies/storage
      2. Navigate to: http://localhost:3000/dashboard
      3. Wait for: URL contains "/login" (timeout: 5s)
      4. Assert: URL contains "/login"
    Expected Result: Protected route redirects to login
    Evidence: URL assertion
  ```

  **Commit**: YES
  - Message: `feat(auth): add login, register pages with Supabase Auth integration`
  - Files: `src/app/(auth)/`, `src/lib/auth-context.tsx`, `src/middleware.ts`
  - Pre-commit: `pnpm build`

---

- [ ] 17. Job Listing Page (Server Component + Search/Filter)

  **What to do**:
  - Create job listing page: `src/app/jobs/page.tsx` (Server Component)
    - Fetch jobs from FastAPI via `lib/api.ts`
    - Pagination with URL search params (?page=1&per_page=20)
    - Source filter (dropdown with all sources)
    - Text search input (debounced, updates URL params)
  - Create job card component: `src/components/jobs/JobCard.tsx` (Client Component)
    - Title, company, source badge, salary, location, tags, published date
    - Link to detail page
    - Favorite button (if authenticated)
  - Create filter bar component: `src/components/jobs/FilterBar.tsx` (Client Component)
    - Search input, source select, date range filter
  - Create pagination component: `src/components/jobs/Pagination.tsx`
  - Loading skeleton: `src/app/jobs/loading.tsx`
  - **Use shadcn**: Card, Badge, Input, Select, Button, Skeleton

  **Must NOT do**:
  - Do NOT implement Elasticsearch or advanced search
  - Do NOT implement infinite scroll (use pagination)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex UI with Server/Client Component split, search UX, responsive card grid
  - **Skills**: [`frontend-ui-ux`, `playwright`]
    - `frontend-ui-ux`: Job card design, filter UX, responsive grid
    - `playwright`: Visual verification

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4.1 (with Tasks 16, 18, 19)
  - **Blocks**: Task 18, Task 20
  - **Blocked By**: Task 15, Phase 2 (API endpoints needed)

  **References**:
  - `app/routers/jobs.py` (Task 2) — Jobs API endpoints — match query params and response schema
  - `app/models/responses.py` (Task 2) — Response models — generate TypeScript types
  - `scraper/models.py:16-73` — JobPosting fields — determine what to display on cards
  - Next.js: https://nextjs.org/docs/app/getting-started/server-and-client-components — RSC pattern

  **Acceptance Criteria**:
  - [ ] Job listing page renders with job cards
  - [ ] Pagination works (URL updates, page changes)
  - [ ] Source filter filters jobs by source
  - [ ] Search filters jobs by text
  - [ ] Loading skeleton shows while fetching
  - [ ] All interactive elements have `data-testid`

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Job listing renders with data
    Tool: Playwright (playwright skill)
    Preconditions: Backend running with jobs in DB
    Steps:
      1. Navigate to: http://localhost:3000/jobs
      2. Wait for: [data-testid="job-card"] visible (timeout: 10s)
      3. Assert: At least 1 [data-testid="job-card"] visible
      4. Assert: [data-testid="pagination"] exists
      5. Assert: [data-testid="search-input"] exists
      6. Assert: [data-testid="source-filter"] exists
      7. Screenshot: .sisyphus/evidence/task-17-job-listing.png
    Expected Result: Jobs displayed with filters and pagination
    Evidence: .sisyphus/evidence/task-17-job-listing.png

  Scenario: Search filters jobs
    Tool: Playwright (playwright skill)
    Steps:
      1. Navigate to: http://localhost:3000/jobs
      2. Fill: [data-testid="search-input"] → "remote AI"
      3. Wait 1s (debounce)
      4. Wait for: [data-testid="job-card"] (timeout: 5s)
      5. Assert: URL contains "q=remote+AI" or "q=remote%20AI"
      6. Screenshot: .sisyphus/evidence/task-17-search.png
    Expected Result: Search updates URL and filters results
    Evidence: .sisyphus/evidence/task-17-search.png
  ```

  **Commit**: YES
  - Message: `feat(jobs): add job listing page with search, filter, and pagination`
  - Files: `src/app/jobs/`, `src/components/jobs/`
  - Pre-commit: `pnpm build`

---

- [ ] 18. Job Detail Page

  **What to do**:
  - Create detail page: `src/app/jobs/[id]/page.tsx` (Server Component)
    - Fetch single job from `GET /api/jobs/{id}`
    - Display: title, company, salary, location, source, published date, tags, full description (render HTML safely)
    - Favorite toggle button (authenticated only)
    - "Back to list" navigation
    - External link to original job posting
  - Error page: `src/app/jobs/[id]/error.tsx`
  - Not found: `src/app/jobs/[id]/not-found.tsx`
  - **Use shadcn**: Card, Badge, Button, Separator

  **Must NOT do**:
  - Do NOT add application tracking
  - Do NOT add sharing or PDF export

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Detail page layout, HTML content rendering, responsive design
  - **Skills**: [`frontend-ui-ux`, `playwright`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4.1 (with Tasks 16, 17, 19)
  - **Blocks**: None
  - **Blocked By**: Task 17 (shares job components)

  **References**:
  - `app/routers/jobs.py` — `GET /api/jobs/{id}` endpoint
  - `scraper/models.py:16-73` — All JobPosting fields to display
  - `src/components/jobs/JobCard.tsx` (Task 17) — Reuse badge/tag components

  **Acceptance Criteria**:
  - [ ] Detail page renders all job fields
  - [ ] HTML description rendered safely
  - [ ] 404 page for non-existent job
  - [ ] External link opens in new tab
  - [ ] Favorite button visible for authenticated users

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Job detail page renders
    Tool: Playwright (playwright skill)
    Steps:
      1. Navigate to: http://localhost:3000/jobs
      2. Click first [data-testid="job-card"] link
      3. Wait for: [data-testid="job-title"] visible (timeout: 5s)
      4. Assert: [data-testid="job-description"] exists
      5. Assert: [data-testid="external-link"] has href attribute
      6. Screenshot: .sisyphus/evidence/task-18-detail.png
    Expected Result: Detail page shows full job info
    Evidence: .sisyphus/evidence/task-18-detail.png
  ```

  **Commit**: YES
  - Message: `feat(jobs): add job detail page with description rendering`
  - Files: `src/app/jobs/[id]/`
  - Pre-commit: `pnpm build`

---

- [ ] 19. Stats Dashboard

  **What to do**:
  - Create dashboard page: `src/app/dashboard/page.tsx`
    - Fetch stats from `GET /api/stats`
    - Cards: Total jobs, Active jobs, Sources count, Last scrape time
    - Chart: Jobs by source (bar chart using recharts or similar)
    - Chart: Jobs over time (line chart, last 30 days)
    - Recent scrape runs table (from `GET /api/scrape/runs`)
  - Install charting lib: `pnpm add recharts`
  - Create dashboard components: `src/components/dashboard/StatsCard.tsx`, `SourceChart.tsx`, `TimelineChart.tsx`
  - **Use shadcn**: Card, Table, Badge

  **Must NOT do**:
  - Do NOT implement real-time updating
  - Do NOT add complex analytics

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Data visualization with charts, dashboard layout design
  - **Skills**: [`frontend-ui-ux`, `playwright`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4.1 (with Tasks 16, 17, 18)
  - **Blocks**: None
  - **Blocked By**: Task 15, Phase 2 (stats API)

  **References**:
  - `app/routers/stats.py` (Task 3) — Stats API response structure
  - `app/routers/scheduler.py` (Task 12) — Scrape runs API
  - Recharts: https://recharts.org/en-US/examples — Chart examples

  **Acceptance Criteria**:
  - [ ] Dashboard shows stats cards with real data
  - [ ] Source distribution chart renders
  - [ ] Scrape runs table shows history
  - [ ] Page responsive on mobile

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Dashboard renders with charts
    Tool: Playwright (playwright skill)
    Steps:
      1. Login first
      2. Navigate to: http://localhost:3000/dashboard
      3. Wait for: [data-testid="stats-card"] visible (timeout: 10s)
      4. Assert: At least 3 [data-testid="stats-card"] elements
      5. Assert: [data-testid="source-chart"] exists
      6. Screenshot: .sisyphus/evidence/task-19-dashboard.png
    Expected Result: Dashboard with stats and charts
    Evidence: .sisyphus/evidence/task-19-dashboard.png
  ```

  **Commit**: YES
  - Message: `feat(dashboard): add statistics dashboard with charts and scrape history`
  - Files: `src/app/dashboard/`, `src/components/dashboard/`
  - Pre-commit: `pnpm build`

---

### Phase 5: Frontend Features + Deployment

- [ ] 20. Favorites + Subscriptions UI

  **What to do**:
  - Create favorites page: `src/app/favorites/page.tsx`
    - List favorited jobs (reuse JobCard component)
    - Remove from favorites action
  - Create subscriptions page: `src/app/subscriptions/page.tsx`
    - List active subscriptions
    - Create new subscription dialog (keywords input, source multi-select, match mode)
    - Edit/delete subscription
    - Toggle active/inactive
  - Integrate favorite button into JobCard and job detail page
  - **Use shadcn**: Dialog, MultiSelect, Switch, Card

  **Must NOT do**:
  - Do NOT implement subscription sharing
  - Do NOT implement import/export of subscriptions

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Interactive UI with dialogs, multi-select, state management
  - **Skills**: [`frontend-ui-ux`, `playwright`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5.1 (with Tasks 21, 22, 23)
  - **Blocks**: None
  - **Blocked By**: Tasks 16, 17, Phase 3 Task 13

  **References**:
  - `app/routers/favorites.py` (Task 13) — Favorites API
  - `app/routers/subscriptions.py` (Task 13) — Subscriptions API
  - `src/components/jobs/JobCard.tsx` (Task 17) — Add favorite button

  **Acceptance Criteria**:
  - [ ] Favorites page shows bookmarked jobs
  - [ ] Favorite toggle works on job cards and detail page
  - [ ] Subscription creation dialog with keyword input
  - [ ] Subscription toggle active/inactive works

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Favorite and unfavorite a job
    Tool: Playwright (playwright skill)
    Steps:
      1. Login
      2. Navigate to /jobs
      3. Click [data-testid="favorite-btn"] on first job card
      4. Assert: Button shows "favorited" state
      5. Navigate to /favorites
      6. Assert: At least 1 [data-testid="job-card"]
      7. Click [data-testid="unfavorite-btn"] on the card
      8. Assert: Card removed from list
      9. Screenshot: .sisyphus/evidence/task-20-favorites.png
    Expected Result: Favorite lifecycle works
    Evidence: .sisyphus/evidence/task-20-favorites.png
  ```

  **Commit**: YES
  - Message: `feat(favorites): add favorites and subscriptions UI`
  - Files: `src/app/favorites/`, `src/app/subscriptions/`
  - Pre-commit: `pnpm build`

---

- [ ] 21. Notification Center

  **What to do**:
  - Create notification bell in header: `src/components/layout/NotificationBell.tsx`
    - Unread count badge
    - Click opens dropdown/sheet with notification list
  - Create notifications page: `src/app/notifications/page.tsx`
    - Full notification list with pagination
    - Mark read/unread
    - Mark all read
    - Click notification → navigate to related job
  - Create notification preferences in settings: email on/off toggle
  - Poll for new notifications every 30 seconds (or on page focus)
  - **Use shadcn**: Sheet, Badge, Button, Switch

  **Must NOT do**:
  - Do NOT implement WebSocket/real-time push
  - Do NOT implement notification sound or browser push

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Notification UX with bell, dropdown, polling, state management
  - **Skills**: [`frontend-ui-ux`, `playwright`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5.1 (with Tasks 20, 22, 23)
  - **Blocks**: None
  - **Blocked By**: Task 16, Phase 3 Task 14

  **References**:
  - `app/routers/notifications.py` (Task 14) — Notifications API
  - shadcn Sheet: https://ui.shadcn.com/docs/components/sheet — Slide-over panel

  **Acceptance Criteria**:
  - [ ] Notification bell shows unread count
  - [ ] Clicking bell opens notification list
  - [ ] Mark read works
  - [ ] Clicking notification navigates to job

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Notification bell and list
    Tool: Playwright (playwright skill)
    Preconditions: User has notifications (from subscription match)
    Steps:
      1. Login
      2. Assert: [data-testid="notification-bell"] visible
      3. Assert: [data-testid="unread-count"] shows number > 0
      4. Click: [data-testid="notification-bell"]
      5. Wait for: [data-testid="notification-list"] visible
      6. Assert: At least 1 [data-testid="notification-item"]
      7. Click first [data-testid="notification-item"]
      8. Assert: URL contains "/jobs/"
      9. Screenshot: .sisyphus/evidence/task-21-notifications.png
    Expected Result: Notification flow works end-to-end
    Evidence: .sisyphus/evidence/task-21-notifications.png
  ```

  **Commit**: YES
  - Message: `feat(notifications): add notification center with bell, list, and read management`
  - Files: `src/components/layout/NotificationBell.tsx`, `src/app/notifications/`
  - Pre-commit: `pnpm build`

---

- [ ] 22. Scraper Admin Console

  **What to do**:
  - Create admin page: `src/app/admin/page.tsx` (admin only, redirect non-admins)
  - Site management tab:
    - Table of all sites with enable/disable toggle
    - Edit site config (rate limit, URL, extra config)
  - Keyword management tab:
    - List keywords by group
    - Add/remove keywords
    - Toggle keyword active/inactive
  - Scraper control tab:
    - Manual scrape trigger (select sites, dry run option)
    - Scrape history table (from scrape_runs)
    - Scheduler status (running/paused) with pause/resume buttons
  - **Use shadcn**: Tabs, Table, Switch, Dialog, Badge

  **Must NOT do**:
  - Do NOT allow creating new adapter types via UI
  - Do NOT implement real-time log streaming

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Admin panel with multiple tabs, tables, forms, data management UI
  - **Skills**: [`frontend-ui-ux`, `playwright`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5.1 (with Tasks 20, 21, 23)
  - **Blocks**: None
  - **Blocked By**: Task 16, Phase 3 Tasks 11, 12

  **References**:
  - `app/routers/config.py` (Task 11) — Config CRUD API
  - `app/routers/scheduler.py` (Task 12) — Scheduler control API
  - `app/routers/scraper.py` (Task 3) — Scrape trigger API

  **Acceptance Criteria**:
  - [ ] Admin page accessible only to admin users
  - [ ] Site enable/disable toggle works
  - [ ] Keyword add/remove works
  - [ ] Manual scrape trigger works
  - [ ] Scrape history table shows past runs

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Admin console functionality
    Tool: Playwright (playwright skill)
    Preconditions: Admin user logged in
    Steps:
      1. Navigate to: http://localhost:3000/admin
      2. Assert: [data-testid="admin-tabs"] visible
      3. Click: Sites tab
      4. Assert: Table with 7 site rows
      5. Click: toggle switch on first site
      6. Assert: Site status changed
      7. Click: Keywords tab
      8. Assert: Keywords listed by group
      9. Click: Scraper tab
      10. Assert: [data-testid="trigger-scrape-btn"] visible
      11. Screenshot: .sisyphus/evidence/task-22-admin.png
    Expected Result: Admin console fully functional
    Evidence: .sisyphus/evidence/task-22-admin.png
  ```

  **Commit**: YES
  - Message: `feat(admin): add scraper admin console with site, keyword, and scheduler management`
  - Files: `src/app/admin/`
  - Pre-commit: `pnpm build`

---

- [ ] 23. Dark/Light Theme Polish

  **What to do**:
  - Ensure `next-themes` provider set up correctly (Task 15 started this)
  - Create theme toggle component: `src/components/layout/ThemeToggle.tsx`
    - Sun/moon icon toggle
    - System preference detection
    - Persist choice in localStorage
  - Audit ALL pages for dark mode compatibility:
    - Verify shadcn components render correctly in both themes
    - Check custom components for hardcoded colors
    - Ensure charts (recharts) respect theme
    - Test all form inputs, modals, dropdowns
  - Add `data-testid="theme-toggle"` to toggle button
  - Update Tailwind config for custom dark mode colors if needed

  **Must NOT do**:
  - Do NOT add more themes beyond dark/light
  - Do NOT add per-user theme preferences in DB (localStorage is enough)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: CSS theming, visual audit across all pages
  - **Skills**: [`frontend-ui-ux`, `playwright`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5.1 (with Tasks 20, 21, 22)
  - **Blocks**: None
  - **Blocked By**: Task 15

  **References**:
  - next-themes: https://github.com/pacocoursey/next-themes — Theme provider docs
  - shadcn theming: https://ui.shadcn.com/docs/dark-mode/next — Dark mode with Next.js

  **Acceptance Criteria**:
  - [ ] Theme toggle switches between dark and light
  - [ ] Theme persists across page refresh
  - [ ] All pages render correctly in both themes
  - [ ] Charts update colors for dark mode

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Theme toggle and persistence
    Tool: Playwright (playwright skill)
    Steps:
      1. Navigate to: http://localhost:3000
      2. Click: [data-testid="theme-toggle"]
      3. Assert: html has class "dark"
      4. Screenshot: .sisyphus/evidence/task-23-dark.png
      5. Reload page
      6. Assert: html still has class "dark" (persisted)
      7. Navigate to /jobs
      8. Assert: html has class "dark" (persisted across routes)
      9. Click: [data-testid="theme-toggle"]
      10. Assert: html does NOT have class "dark"
      11. Screenshot: .sisyphus/evidence/task-23-light.png
    Expected Result: Theme toggles and persists
    Evidence: .sisyphus/evidence/task-23-dark.png, .sisyphus/evidence/task-23-light.png
  ```

  **Commit**: YES
  - Message: `feat(theme): polish dark/light theme toggle with persistence and full audit`
  - Files: `src/components/layout/ThemeToggle.tsx`, various component fixes
  - Pre-commit: `pnpm build`

---

- [ ] 24. Docker Compose Deployment

  **What to do**:
  - Create `Dockerfile.backend` in backend repo:
    - Base: `mcr.microsoft.com/playwright/python:v1.40.0-jammy` (for Playwright adapter)
    - Install Python deps, copy app
    - CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
  - Create `Dockerfile.frontend` in frontend repo:
    - Base: `node:20-alpine`
    - Multi-stage: install deps → build → serve with standalone output
    - CMD: `node server.js`
  - Create `docker-compose.yml`:
    - Service `backend`: FastAPI (port 8000)
    - Service `frontend`: Next.js (port 3000)
    - Service `nginx`: Reverse proxy (port 80)
      - `/api/*` → backend:8000
      - `/*` → frontend:3000
  - Create `nginx.conf` for reverse proxy rules
  - Create `.env.docker` template with all env vars
  - Create `docker-compose.override.yml` for local dev (volume mounts, hot reload)
  - Test full stack startup with `docker compose up --build`

  **Must NOT do**:
  - Do NOT add Kubernetes configs
  - Do NOT add CI/CD pipeline (v2 feature)
  - Do NOT include secrets in Dockerfile or docker-compose.yml

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Docker multi-stage builds, nginx config, compose orchestration — infra expertise needed
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential — requires both backend and frontend complete
  - **Blocks**: Task 25
  - **Blocked By**: Phase 3, Phase 4

  **References**:
  - `scraper/adapters/browser.py` — ArcDevAdapter uses Playwright — needs system deps in Docker
  - Playwright Docker: https://playwright.dev/python/docs/docker — Official Docker images
  - Next.js Docker: https://nextjs.org/docs/pages/building-your-application/deploying#docker-image — Standalone output

  **Acceptance Criteria**:
  - [ ] `docker compose build` succeeds with no errors
  - [ ] `docker compose up -d` starts all 3 services
  - [ ] `curl http://localhost/api/health` returns 200 (via nginx → backend)
  - [ ] `curl http://localhost` returns 200 (via nginx → frontend)
  - [ ] Playwright-based scraping works inside Docker container

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Full stack Docker deployment
    Tool: Bash (docker)
    Steps:
      1. docker compose build --no-cache 2>&1 | tail -3
      2. Assert: exit code 0
      3. docker compose up -d
      4. sleep 15
      5. docker compose ps --format "table {{.Name}}\t{{.Status}}"
      6. Assert: All 3 services show "Up" or "running"
      7. curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health
      8. Assert: 200
      9. curl -s -o /dev/null -w "%{http_code}" http://localhost
      10. Assert: 200
      11. docker compose down
    Expected Result: Full stack runs in Docker
    Evidence: docker compose ps output, curl responses

  Scenario: Playwright works in Docker
    Tool: Bash (docker)
    Steps:
      1. docker compose up -d
      2. docker compose exec backend python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(); b.close(); p.stop(); print('OK')"
      3. Assert: Output contains "OK"
      4. docker compose down
    Expected Result: Playwright Chromium runs inside container
    Evidence: Script output
  ```

  **Commit**: YES (in backend repo)
  - Message: `feat(deploy): add Docker Compose with nginx, backend, and frontend services`
  - Files: `Dockerfile.backend`, `docker-compose.yml`, `nginx.conf`, `.env.docker`
  - Pre-commit: `docker compose build`

---

- [ ] 25. Data Migration (SQLite → Supabase)

  **What to do**:
  - Create `scripts/migrate_sqlite_to_supabase.py`:
    - Read all jobs from `data/jobs.db` via aiosqlite
    - Convert to PostgreSQL-compatible format (datetimes → UTC aware, tags → list)
    - Batch insert to Supabase via asyncpg (100 per batch)
    - Handle duplicates (ON CONFLICT DO UPDATE)
    - Progress bar and logging
  - Verify migration:
    - Compare counts (SQLite vs Supabase)
    - Spot-check 10 random jobs for data integrity
  - Ensure `scripts/seed_db.py` (Task 11) runs before migration
  - **This is the final task — only run when everything else is working**

  **Must NOT do**:
  - Do NOT delete SQLite DB (keep as backup)
  - Do NOT run migration automatically on startup

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: One-off migration script, well-scoped, uses existing patterns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential — final task
  - **Blocks**: None
  - **Blocked By**: Task 24

  **References**:
  - `scraper/utils/storage.py:137-175` — `get_all_jobs()` — read all from SQLite
  - `scraper/models.py:99-130` — `from_db_row()` — deserialize SQLite rows
  - `scraper/models.py` — `to_pg_dict()` (Task 7) — serialize for PostgreSQL
  - `app/services/storage.py` — `upsert_jobs_batch()` (Task 6) — batch insert

  **Acceptance Criteria**:
  - [ ] Migration script completes without errors
  - [ ] Job count in Supabase matches SQLite (within dedup tolerance)
  - [ ] Spot-check: 10 random jobs match between sources
  - [ ] `data/jobs.db` preserved as backup

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Data migration integrity
    Tool: Bash (python script)
    Steps:
      1. python scripts/migrate_sqlite_to_supabase.py
      2. Assert: Exit code 0
      3. python -c "
         import aiosqlite, asyncio, asyncpg, os
         async def check():
             db = await aiosqlite.connect('data/jobs.db')
             cursor = await db.execute('SELECT count(*) FROM jobs')
             sqlite_count = (await cursor.fetchone())[0]
             pool = await asyncpg.create_pool(os.environ['DATABASE_URL'])
             pg_count = await pool.fetchval('SELECT count(*) FROM jobs')
             assert abs(sqlite_count - pg_count) < 5, f'Count mismatch: SQLite={sqlite_count}, PG={pg_count}'
             print(f'OK: SQLite={sqlite_count}, PG={pg_count}')
             await pool.close()
             await db.close()
         asyncio.run(check())"
      4. Assert: Exit code 0
    Expected Result: Counts match between databases
    Evidence: Count comparison output
  ```

  **Commit**: YES
  - Message: `feat(migration): add SQLite to Supabase data migration script`
  - Files: `scripts/migrate_sqlite_to_supabase.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(api): add FastAPI app skeleton with health endpoint` | `app/`, `pyproject.toml` | `pytest tests/ -v` |
| 2 | `feat(api): add jobs list, detail, and search endpoints` | `app/routers/jobs.py`, `app/services/`, `app/models/` | `pytest tests/ -v` |
| 3 | `feat(api): add scrape trigger, stats, and export endpoints` | `app/routers/scraper.py`, `app/routers/stats.py` | `pytest tests/ -v` |
| 4 | `feat(api): complete Phase 1 - FastAPI shell wired` | `app/main.py`, integration tests | `pytest tests/ -v` |
| 5 | `feat(db): add Supabase schema migrations and seed data` | `supabase/` | SQL validation |
| 6 | `feat(db): implement SupabaseStorage with asyncpg` | `app/services/storage.py`, `tests/fakes/` | `pytest tests/ -v` |
| 7 | `feat(models): add PostgreSQL serialization and dynamic sources` | `scraper/models.py` | `pytest tests/ -v` |
| 8 | `refactor(orchestrator): inject storage, use batch upsert` | `scraper/orchestrator.py` | `pytest tests/ -v` |
| 9 | `test: rewrite storage and integration tests for Supabase` | `tests/test_storage.py`, `tests/test_integration.py` | `pytest tests/ -v` |
| 10 | `feat(auth): add Supabase Auth with JWT middleware` | `app/services/auth.py`, `app/routers/auth.py` | `pytest tests/ -v` |
| 11 | `feat(config): add DB-backed config with admin CRUD` | `app/services/config_service.py`, `scripts/seed_db.py` | `pytest tests/ -v` |
| 12 | `feat(scheduler): add APScheduler with scrape run tracking` | `app/services/scheduler.py` | `pytest tests/ -v` |
| 13 | `feat(api): add favorites and subscriptions CRUD` | `app/routers/favorites.py`, `app/routers/subscriptions.py` | `pytest tests/ -v` |
| 14 | `feat(notifications): add in-app + email notifications` | `app/services/notification_service.py` | `pytest tests/ -v` |
| 15 | `feat: initialize Next.js 16 with shadcn/ui` | entire frontend project | `pnpm build` |
| 16 | `feat(auth): add login, register pages` | `src/app/(auth)/` | `pnpm build` |
| 17 | `feat(jobs): add job listing with search and pagination` | `src/app/jobs/`, `src/components/jobs/` | `pnpm build` |
| 18 | `feat(jobs): add job detail page` | `src/app/jobs/[id]/` | `pnpm build` |
| 19 | `feat(dashboard): add stats dashboard with charts` | `src/app/dashboard/` | `pnpm build` |
| 20 | `feat(favorites): add favorites and subscriptions UI` | `src/app/favorites/`, `src/app/subscriptions/` | `pnpm build` |
| 21 | `feat(notifications): add notification center` | `src/components/layout/NotificationBell.tsx` | `pnpm build` |
| 22 | `feat(admin): add scraper admin console` | `src/app/admin/` | `pnpm build` |
| 23 | `feat(theme): polish dark/light theme` | theme components | `pnpm build` |
| 24 | `feat(deploy): add Docker Compose deployment` | `Dockerfile.*`, `docker-compose.yml`, `nginx.conf` | `docker compose build` |
| 25 | `feat(migration): add SQLite to Supabase migration script` | `scripts/migrate_sqlite_to_supabase.py` | script + verification |

---

## Success Criteria

### Verification Commands
```bash
# Backend tests (all 320+ pass)
python -m pytest tests/ -v                    # Expected: 0 failures

# FastAPI serves docs
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs  # Expected: 200

# API health
curl -s http://localhost:8000/api/health       # Expected: {"status":"ok"}

# Jobs API
curl -s http://localhost:8000/api/jobs         # Expected: JSON with "data" array

# Auth flow
curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@test.com","password":"Test123!"}' # Expected: {"access_token":"..."}

# Frontend builds
pnpm build                                     # Expected: exit code 0

# Docker full stack
docker compose up -d && sleep 15 && curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health  # Expected: 200
docker compose down
```

### Final Checklist
- [ ] All "Must Have" items present
- [ ] All "Must NOT Have" items absent
- [ ] 292+ adapter/matcher/dedup tests pass unchanged
- [ ] All new TDD tests pass
- [ ] Supabase schema created with RLS policies
- [ ] Auth flow works (register, login, protected routes)
- [ ] Frontend 6 modules functional
- [ ] Dark/light theme works
- [ ] Docker Compose deploys successfully
- [ ] Data migration script works
