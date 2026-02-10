"""Validation tests for Supabase SQL migration and seed files."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


SUPABASE_DIR = Path(__file__).parent.parent / "supabase"
MIGRATIONS_DIR = SUPABASE_DIR / "migrations"


def _read_sql(filename: str) -> str:
    filepath = SUPABASE_DIR / filename
    if not filepath.exists():
        filepath = MIGRATIONS_DIR / filename
    return filepath.read_text(encoding="utf-8")


class TestMigrationFilesExist:

    def test_001_initial_schema_exists(self):
        assert (MIGRATIONS_DIR / "001_initial_schema.sql").exists()

    def test_002_rls_policies_exists(self):
        assert (MIGRATIONS_DIR / "002_rls_policies.sql").exists()

    def test_seed_sql_exists(self):
        assert (SUPABASE_DIR / "seed.sql").exists()


class TestInitialSchema:

    @pytest.fixture(autouse=True)
    def _load_sql(self):
        self.sql = _read_sql("001_initial_schema.sql")

    EXPECTED_TABLES = [
        "jobs",
        "site_configs",
        "keyword_configs",
        "match_rules",
        "profiles",
        "favorites",
        "subscriptions",
        "notifications",
        "scrape_runs",
    ]

    @pytest.mark.parametrize("table", EXPECTED_TABLES)
    def test_table_created(self, table: str):
        pattern = rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{table}\s*\("
        assert re.search(pattern, self.sql, re.IGNORECASE), f"Table '{table}' not found"

    def test_jobs_id_is_text(self):
        match = re.search(r"CREATE\s+TABLE.*?jobs\s*\((.*?)\);", self.sql, re.DOTALL | re.IGNORECASE)
        assert match, "jobs table definition not found"
        body = match.group(1)
        assert re.search(r"id\s+text\s+PRIMARY\s+KEY", body, re.IGNORECASE), "jobs.id must be TEXT PRIMARY KEY"

    def test_jobs_id_not_uuid(self):
        match = re.search(r"CREATE\s+TABLE.*?jobs\s*\((.*?)\);", self.sql, re.DOTALL | re.IGNORECASE)
        assert match
        body = match.group(1)
        assert not re.search(r"id\s+uuid", body, re.IGNORECASE), "jobs.id must NOT be UUID"

    def test_timestamptz_used(self):
        assert "timestamptz" in self.sql.lower()
        assert "timestamp " not in self.sql.lower().replace("timestamptz", ""), \
            "Use timestamptz, not bare timestamp"

    def test_jsonb_for_tags(self):
        match = re.search(r"CREATE\s+TABLE.*?jobs\s*\((.*?)\);", self.sql, re.DOTALL | re.IGNORECASE)
        assert match
        body = match.group(1)
        assert re.search(r"tags\s+jsonb", body, re.IGNORECASE), "jobs.tags must be jsonb"

    def test_jsonb_for_extra_config(self):
        assert re.search(r"extra_config\s+jsonb", self.sql, re.IGNORECASE), \
            "site_configs.extra_config must be jsonb"

    def test_text_array_for_skip_location_for(self):
        assert re.search(r"skip_location_for\s+text\[\]", self.sql, re.IGNORECASE)

    def test_text_array_for_sites(self):
        assert re.search(r"sites\s+text\[\]", self.sql, re.IGNORECASE)

    def test_text_array_for_keywords(self):
        assert re.search(r"keywords\s+text\[\]", self.sql, re.IGNORECASE)

    def test_text_array_for_sources(self):
        assert re.search(r"sources\s+text\[\]", self.sql, re.IGNORECASE)

    EXPECTED_INDEXES = [
        "idx_jobs_source",
        "idx_jobs_company",
        "idx_jobs_is_active",
        "idx_jobs_first_seen",
        "idx_jobs_published_at",
        "idx_jobs_last_seen",
        "idx_site_configs_enabled",
        "idx_keyword_configs_group",
        "idx_favorites_user_id",
        "idx_favorites_job_id",
        "idx_subscriptions_user_id",
        "idx_subscriptions_is_active",
        "idx_notifications_user_id",
        "idx_notifications_job_id",
        "idx_notifications_sent_at",
        "idx_scrape_runs_started_at",
        "idx_scrape_runs_status",
    ]

    @pytest.mark.parametrize("index_name", EXPECTED_INDEXES)
    def test_index_exists(self, index_name: str):
        assert index_name in self.sql, f"Index '{index_name}' not found"

    def test_profiles_references_auth_users(self):
        assert re.search(r"REFERENCES\s+auth\.users", self.sql, re.IGNORECASE)

    def test_favorites_references_jobs(self):
        assert re.search(r"favorites.*?REFERENCES\s+jobs", self.sql, re.DOTALL | re.IGNORECASE)

    def test_updated_at_trigger_function(self):
        assert "update_updated_at_column" in self.sql

    def test_nine_tables_total(self):
        tables = re.findall(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", self.sql, re.IGNORECASE)
        assert len(tables) == 9, f"Expected 9 tables, found {len(tables)}: {tables}"


class TestRLSPolicies:

    @pytest.fixture(autouse=True)
    def _load_sql(self):
        self.sql = _read_sql("002_rls_policies.sql")

    EXPECTED_RLS_TABLES = [
        "jobs",
        "site_configs",
        "keyword_configs",
        "match_rules",
        "profiles",
        "favorites",
        "subscriptions",
        "notifications",
        "scrape_runs",
    ]

    @pytest.mark.parametrize("table", EXPECTED_RLS_TABLES)
    def test_rls_enabled(self, table: str):
        pattern = rf"ALTER\s+TABLE\s+{table}\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY"
        assert re.search(pattern, self.sql, re.IGNORECASE), f"RLS not enabled for '{table}'"

    BACKEND_TABLES = ["jobs", "site_configs", "keyword_configs", "match_rules", "scrape_runs"]

    @pytest.mark.parametrize("table", BACKEND_TABLES)
    def test_backend_table_has_select_policy(self, table: str):
        pattern = rf'CREATE\s+POLICY\s+"[^"]*"\s+ON\s+{table}\s+FOR\s+SELECT'
        assert re.search(pattern, self.sql, re.IGNORECASE), \
            f"No SELECT policy for backend table '{table}'"

    @pytest.mark.parametrize("table", BACKEND_TABLES)
    def test_backend_table_no_insert_policy(self, table: str):
        pattern = rf'CREATE\s+POLICY\s+"[^"]*"\s+ON\s+{table}\s+FOR\s+INSERT'
        assert not re.search(pattern, self.sql, re.IGNORECASE), \
            f"Backend table '{table}' should NOT have INSERT policy (service_role only)"

    USER_TABLES = ["profiles", "favorites", "subscriptions"]

    @pytest.mark.parametrize("table", USER_TABLES)
    def test_user_table_has_select_policy(self, table: str):
        pattern = rf'CREATE\s+POLICY\s+"[^"]*"\s+ON\s+{table}\s+FOR\s+SELECT'
        assert re.search(pattern, self.sql, re.IGNORECASE)

    @pytest.mark.parametrize("table", USER_TABLES)
    def test_user_table_has_insert_policy(self, table: str):
        pattern = rf'CREATE\s+POLICY\s+"[^"]*"\s+ON\s+{table}\s+FOR\s+INSERT'
        assert re.search(pattern, self.sql, re.IGNORECASE)

    @pytest.mark.parametrize("table", USER_TABLES)
    def test_user_table_has_delete_policy(self, table: str):
        pattern = rf'CREATE\s+POLICY\s+"[^"]*"\s+ON\s+{table}\s+FOR\s+DELETE'
        assert re.search(pattern, self.sql, re.IGNORECASE)

    def test_user_policies_use_auth_uid(self):
        assert "auth.uid()" in self.sql

    def test_anon_can_read_active_jobs(self):
        assert re.search(r'ON\s+jobs\s+FOR\s+SELECT\s+TO\s+anon', self.sql, re.IGNORECASE)


class TestSeedSQL:

    @pytest.fixture(autouse=True)
    def _load_sql(self):
        self.sql = _read_sql("seed.sql")

    def test_on_conflict_do_nothing(self):
        sql_no_comments = re.sub(r"--.*$", "", self.sql, flags=re.MULTILINE)
        insert_count = len(re.findall(r"INSERT\s+INTO", sql_no_comments, re.IGNORECASE))
        conflict_count = len(re.findall(r"ON\s+CONFLICT.*?DO\s+NOTHING", sql_no_comments, re.IGNORECASE))
        assert insert_count > 0
        assert conflict_count == insert_count, \
            f"All {insert_count} INSERTs must use ON CONFLICT DO NOTHING (found {conflict_count})"

    EXPECTED_SITES = ["remoteok", "eleduck", "weworkremotely", "workgo", "v2ex", "arcdev", "yuancheng"]

    @pytest.mark.parametrize("site_key", EXPECTED_SITES)
    def test_site_config_seeded(self, site_key: str):
        assert f"'{site_key}'" in self.sql, f"Site '{site_key}' not found in seed"

    EXPECTED_LOCATION_KEYWORDS = ["remote", "远程", "远程工作", "远程办公", "在家办公", "work from home", "wfh"]

    @pytest.mark.parametrize("keyword", EXPECTED_LOCATION_KEYWORDS)
    def test_location_keyword_seeded(self, keyword: str):
        assert keyword in self.sql, f"Location keyword '{keyword}' not found in seed"

    EXPECTED_TECH_KEYWORDS = ["AI", "LLM", "GPT", "Claude", "RAG", "NLP", "langchain", "machine learning"]

    @pytest.mark.parametrize("keyword", EXPECTED_TECH_KEYWORDS)
    def test_technology_keyword_seeded(self, keyword: str):
        assert keyword in self.sql, f"Technology keyword '{keyword}' not found in seed"

    def test_match_rule_seeded(self):
        assert "location AND technology" in self.sql

    def test_skip_location_for_seeded(self):
        assert "remoteok" in self.sql
        assert "weworkremotely" in self.sql

    def test_no_service_key_exposed(self):
        assert "service_key" not in self.sql.lower()
        assert "service_role" not in self.sql.lower()


class TestSQLSyntaxBasic:

    @pytest.fixture(params=["001_initial_schema.sql", "002_rls_policies.sql"])
    def migration_sql(self, request) -> str:
        return _read_sql(request.param)

    def test_no_trailing_semicolon_missing(self, migration_sql: str):
        lines = migration_sql.strip().split("\n")
        non_comment_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("--")]
        statements = migration_sql.split(";")
        assert len(statements) > 1, "SQL file has no semicolons"

    def test_balanced_parentheses(self, migration_sql: str):
        sql_no_comments = re.sub(r"--.*$", "", migration_sql, flags=re.MULTILINE)
        sql_no_strings = re.sub(r"'[^']*'", "", sql_no_comments)
        open_count = sql_no_strings.count("(")
        close_count = sql_no_strings.count(")")
        assert open_count == close_count, \
            f"Unbalanced parentheses: {open_count} open, {close_count} close"

    def test_no_syntax_red_flags(self, migration_sql: str):
        assert "CREAT TABLE" not in migration_sql
        assert "CRAETE" not in migration_sql
        assert "INSER INTO" not in migration_sql


class TestEnvExample:

    def test_supabase_vars_present(self):
        env_path = Path(__file__).parent.parent / ".env.example"
        content = env_path.read_text(encoding="utf-8")
        assert "SUPABASE_URL=" in content
        assert "SUPABASE_ANON_KEY=" in content
        assert "SUPABASE_SERVICE_KEY=" in content
        assert "SUPABASE_DB_URL=" in content
