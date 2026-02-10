-- 002_rls_policies.sql
-- Row Level Security policies for all tables.
--
-- Policy design:
--   Backend tables (jobs, site_configs, keyword_configs, match_rules, scrape_runs):
--     Read-only for authenticated users. Writes via service_role only.
--   User tables (profiles, favorites, subscriptions, notifications):
--     Users can CRUD their own data only.

-- =============================================================================
-- Enable RLS on all tables
-- =============================================================================
ALTER TABLE jobs             ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_configs     ENABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_configs  ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_rules      ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles         ENABLE ROW LEVEL SECURITY;
ALTER TABLE favorites        ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications    ENABLE ROW LEVEL SECURITY;
ALTER TABLE scrape_runs      ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- Backend tables: read-only for authenticated users
-- =============================================================================

-- jobs
CREATE POLICY "jobs_select_authenticated"
    ON jobs FOR SELECT
    TO authenticated
    USING (true);

-- site_configs
CREATE POLICY "site_configs_select_authenticated"
    ON site_configs FOR SELECT
    TO authenticated
    USING (true);

-- keyword_configs
CREATE POLICY "keyword_configs_select_authenticated"
    ON keyword_configs FOR SELECT
    TO authenticated
    USING (true);

-- match_rules
CREATE POLICY "match_rules_select_authenticated"
    ON match_rules FOR SELECT
    TO authenticated
    USING (true);

-- scrape_runs
CREATE POLICY "scrape_runs_select_authenticated"
    ON scrape_runs FOR SELECT
    TO authenticated
    USING (true);

-- =============================================================================
-- User tables: own-data CRUD
-- =============================================================================

-- profiles
CREATE POLICY "profiles_select_own"
    ON profiles FOR SELECT
    TO authenticated
    USING (id = auth.uid());

CREATE POLICY "profiles_insert_own"
    ON profiles FOR INSERT
    TO authenticated
    WITH CHECK (id = auth.uid());

CREATE POLICY "profiles_update_own"
    ON profiles FOR UPDATE
    TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

CREATE POLICY "profiles_delete_own"
    ON profiles FOR DELETE
    TO authenticated
    USING (id = auth.uid());

-- favorites
CREATE POLICY "favorites_select_own"
    ON favorites FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "favorites_insert_own"
    ON favorites FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "favorites_delete_own"
    ON favorites FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

-- subscriptions
CREATE POLICY "subscriptions_select_own"
    ON subscriptions FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "subscriptions_insert_own"
    ON subscriptions FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "subscriptions_update_own"
    ON subscriptions FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "subscriptions_delete_own"
    ON subscriptions FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

-- notifications
CREATE POLICY "notifications_select_own"
    ON notifications FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- =============================================================================
-- Anonymous read access for public job listings
-- =============================================================================
CREATE POLICY "jobs_select_anon"
    ON jobs FOR SELECT
    TO anon
    USING (is_active = true);
