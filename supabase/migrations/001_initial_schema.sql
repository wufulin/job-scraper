-- 001_initial_schema.sql
-- Initial Supabase schema for job-scraper
-- Creates all 9 tables with proper types, indexes, and constraints.
--
-- Key design decisions:
--   - jobs.id is TEXT (MD5 hex), not UUID — matches existing Python model
--   - All datetime columns use timestamptz
--   - jsonb for structured data (tags, extra_config)
--   - text[] arrays for multi-value fields (skip_location_for, sites, keywords, sources)
--   - Supabase auth.uid() used for user-scoped tables

-- =============================================================================
-- 1. jobs — scraped job postings (mirrors existing SQLite schema, upgraded types)
-- =============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    id              text        PRIMARY KEY,            -- MD5 hex of url|title
    title           text        NOT NULL,
    company         text,
    url             text,
    source          text        NOT NULL,
    published_at    timestamptz,
    salary          text,
    location        text,
    description     text,
    tags            jsonb       NOT NULL DEFAULT '[]'::jsonb,
    first_seen      timestamptz NOT NULL DEFAULT now(),
    last_seen       timestamptz NOT NULL DEFAULT now(),
    last_updated    timestamptz NOT NULL DEFAULT now(),
    update_count    integer     NOT NULL DEFAULT 1,
    is_active       boolean     NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_jobs_source       ON jobs (source);
CREATE INDEX IF NOT EXISTS idx_jobs_company      ON jobs (company);
CREATE INDEX IF NOT EXISTS idx_jobs_is_active    ON jobs (is_active);
CREATE INDEX IF NOT EXISTS idx_jobs_first_seen   ON jobs (first_seen DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_published_at ON jobs (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_last_seen    ON jobs (last_seen DESC);

-- =============================================================================
-- 2. site_configs — mirrors config/sites.yaml rows
-- =============================================================================
CREATE TABLE IF NOT EXISTS site_configs (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    site_key            text        NOT NULL UNIQUE,    -- e.g. "remoteok"
    name                text        NOT NULL,           -- display name
    url                 text        NOT NULL,
    adapter             text        NOT NULL,           -- api | rss | browser | hybrid | html
    enabled             boolean     NOT NULL DEFAULT true,
    skip_location_match boolean     NOT NULL DEFAULT false,
    rate_limit_seconds  integer     NOT NULL DEFAULT 2,
    max_pages           integer,
    extra_config        jsonb       NOT NULL DEFAULT '{}'::jsonb,  -- headers, params, api_url, etc.
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_site_configs_enabled ON site_configs (enabled);

-- =============================================================================
-- 3. keyword_configs — individual keywords belonging to a group
-- =============================================================================
CREATE TABLE IF NOT EXISTS keyword_configs (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    group_name  text    NOT NULL,           -- "location" | "technology"
    keyword     text    NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),

    UNIQUE (group_name, keyword)
);

CREATE INDEX IF NOT EXISTS idx_keyword_configs_group ON keyword_configs (group_name);

-- =============================================================================
-- 4. match_rules — keyword matching rules
-- =============================================================================
CREATE TABLE IF NOT EXISTS match_rules (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_name           text        NOT NULL UNIQUE DEFAULT 'default',
    expression          text        NOT NULL,           -- e.g. "location AND technology"
    skip_location_for   text[]      NOT NULL DEFAULT '{}',  -- site_keys that skip location group
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 5. profiles — user profiles linked to Supabase Auth
-- =============================================================================
CREATE TABLE IF NOT EXISTS profiles (
    id          uuid        PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    email       text        UNIQUE,
    display_name text,
    avatar_url  text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 6. favorites — user-bookmarked jobs
-- =============================================================================
CREATE TABLE IF NOT EXISTS favorites (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     uuid    NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    job_id      text    NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    created_at  timestamptz NOT NULL DEFAULT now(),

    UNIQUE (user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites (user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_job_id  ON favorites (job_id);

-- =============================================================================
-- 7. subscriptions — user notification subscriptions
-- =============================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     uuid        NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    name        text        NOT NULL DEFAULT 'default',
    sites       text[]      NOT NULL DEFAULT '{}',      -- filter by source site_keys
    keywords    text[]      NOT NULL DEFAULT '{}',      -- additional keyword filters
    sources     text[]      NOT NULL DEFAULT '{}',      -- notification channels
    is_active   boolean     NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),

    UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id   ON subscriptions (user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_is_active ON subscriptions (is_active);

-- =============================================================================
-- 8. notifications — sent notification log
-- =============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     uuid        NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    job_id      text        NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    channel     text        NOT NULL,       -- "email" | "telegram" | "webhook"
    sent_at     timestamptz NOT NULL DEFAULT now(),
    status      text        NOT NULL DEFAULT 'sent',    -- sent | failed | pending
    error       text,

    UNIQUE (user_id, job_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_job_id  ON notifications (job_id);
CREATE INDEX IF NOT EXISTS idx_notifications_sent_at ON notifications (sent_at DESC);

-- =============================================================================
-- 9. scrape_runs — audit log for each scrape execution
-- =============================================================================
CREATE TABLE IF NOT EXISTS scrape_runs (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    status          text        NOT NULL DEFAULT 'running',  -- running | completed | failed | interrupted
    sites_scraped   text[]      NOT NULL DEFAULT '{}',
    total_fetched   integer     NOT NULL DEFAULT 0,
    total_matched   integer     NOT NULL DEFAULT 0,
    total_new       integer     NOT NULL DEFAULT 0,
    total_updated   integer     NOT NULL DEFAULT 0,
    total_deduped   integer     NOT NULL DEFAULT 0,
    error           text,
    metadata        jsonb       NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_scrape_runs_started_at ON scrape_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_status     ON scrape_runs (status);

-- =============================================================================
-- Trigger: auto-update updated_at columns
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_site_configs_updated_at
    BEFORE UPDATE ON site_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_match_rules_updated_at
    BEFORE UPDATE ON match_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
