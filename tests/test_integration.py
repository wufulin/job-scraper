"""Integration tests — full pipeline with mocked HTTP (no live APIs).

Covers all 7 adapters: RemoteOK, Eleduck, WeWorkRemotely, WorkGo, V2EX,
Arc.dev, and Yuancheng.  Tests use fixture files and mock HTTP/browser
interactions so they run offline and deterministically.
"""

from __future__ import annotations

import gc
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from scraper.adapters.api import EleduckAdapter, RemoteOKAdapter, WorkGoAdapter
from scraper.adapters.browser import ArcDevAdapter
from scraper.adapters.html import YuanchengAdapter
from scraper.adapters.hybrid import V2EXAdapter
from scraper.adapters.rss import WeWorkRemotelyAdapter
from scraper.models import JobPosting
from scraper.orchestrator import ScraperOrchestrator
from scraper.utils.dedup import DedupManager
from scraper.utils.matcher import KeywordMatcher
from tests.fakes.storage import FakeStorage

# ---------------------------------------------------------------------------
# Paths to fixture files
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).parent / "fixtures"
REMOTEOK_FIXTURE = FIXTURES_DIR / "remoteok_sample.json"
ELEDUCK_FIXTURE = FIXTURES_DIR / "eleduck_sample.json"
WWR_FIXTURE = FIXTURES_DIR / "wwr_sample.xml"
WORKGO_FIXTURE = FIXTURES_DIR / "workgo_sample.json"
V2EX_LISTING_FIXTURE = FIXTURES_DIR / "v2ex_listing.html"
V2EX_TOPIC_FIXTURE = FIXTURES_DIR / "v2ex_topic.json"
ARCDEV_FIXTURE = FIXTURES_DIR / "arcdev_sample.json"
YUANCHENG_FIXTURE = FIXTURES_DIR / "yuancheng_listing.html"


def _load_fixture(path: Path) -> str:
    """Return the raw text content of a fixture file."""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Keyword config that matches some of our fixture data
# ---------------------------------------------------------------------------
KEYWORDS_CONFIG = {
    "keyword_groups": {
        "location": ["remote", "远程", "anywhere"],
        "technology": [
            "AI",
            "LLM",
            "machine learning",
            "deep learning",
            "GPT",
            "DevOps",
            "data",
            "developer",
            "Artificial Intelligence",
        ],
    },
    "match_rules": {
        "default": "location AND technology",
        "skip_location_for": ["remoteok", "weworkremotely"],
    },
}

# Minimal sites config used to drive the orchestrator (original 3)
SITES_CONFIG_DICT = {
    "sites": {
        "remoteok": {
            "name": "RemoteOK",
            "url": "https://remoteok.com/api",
            "adapter": "api",
            "enabled": True,
            "skip_location_match": True,
            "rate_limit_seconds": 0,
            "headers": {"User-Agent": "test-agent"},
        },
        "eleduck": {
            "name": "电鸭",
            "url": "https://svc.eleduck.com/api/v1/posts",
            "adapter": "api",
            "enabled": True,
            "skip_location_match": False,
            "rate_limit_seconds": 0,
            "params": {"category": 5},
            "headers": {"User-Agent": "test-agent"},
        },
        "weworkremotely": {
            "name": "WeWorkRemotely",
            "url": "https://weworkremotely.com/remote-jobs.rss",
            "adapter": "rss",
            "enabled": True,
            "skip_location_match": True,
            "rate_limit_seconds": 0,
            "headers": {"User-Agent": "test-agent"},
        },
    }
}

# Full 7-source config for Phase 2 tests
SITES_CONFIG_7 = {
    "sites": {
        **SITES_CONFIG_DICT["sites"],
        "workgo": {
            "name": "WorkGo",
            "url": "https://workgo.ai",
            "api_url": "https://api.workgo.ai/auth/jobs/all",
            "clerk_base": "https://clerk.workgo.ai",
            "adapter": "api",
            "enabled": True,
            "skip_location_match": True,
            "rate_limit_seconds": 0,
            "page_size": 20,
            "max_pages": 5,
            "headers": {"User-Agent": "test-agent"},
        },
        "v2ex": {
            "name": "V2EX",
            "url": "https://www.v2ex.com/go/remote",
            "api_base": "https://www.v2ex.com/api/topics/show.json",
            "adapter": "hybrid",
            "enabled": True,
            "skip_location_match": False,
            "rate_limit_seconds": 0,
            "headers": {"User-Agent": "test-agent"},
        },
        "arcdev": {
            "name": "Arc.dev",
            "url": "https://arc.dev/remote-jobs",
            "adapter": "browser",
            "enabled": True,
            "skip_location_match": True,
            "rate_limit_seconds": 0,
            "headers": {"User-Agent": "test-agent"},
        },
        "yuancheng": {
            "name": "远程.work",
            "url": "https://yuancheng.work/jobs/",
            "adapter": "html",
            "enabled": True,
            "skip_location_match": False,
            "rate_limit_seconds": 0,
            "headers": {"User-Agent": "test-agent"},
        },
    }
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------





def _cleanup_file(path: str) -> None:
    """Remove a temp file, handling Windows file locking."""
    gc.collect()
    try:
        os.unlink(path)
    except OSError:
        pass


def _make_mock_client(responses):
    """Build a mock httpx.AsyncClient context-manager.

    *responses* is either a single MagicMock or a list of MagicMock responses.
    """
    client = AsyncMock()
    if isinstance(responses, list):
        client.get = AsyncMock(side_effect=responses)
    else:
        client.get = AsyncMock(return_value=responses)
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


def _build_mock_response(content: str, *, is_json: bool = False) -> MagicMock:
    """Create a mock httpx.Response with .text, .json(), .raise_for_status()."""
    resp = MagicMock()
    resp.text = content
    resp.raise_for_status = MagicMock()
    if is_json:
        resp.json = MagicMock(return_value=json.loads(content))
    else:
        resp.json = MagicMock(return_value=None)
    return resp


def _write_temp_yaml(data: dict) -> str:
    """Write dict to a temp yaml file and return the path."""
    import yaml

    fd, path = tempfile.mkstemp(suffix=".yaml")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)
    return path


# ---------------------------------------------------------------------------
# Fixtures (pytest)
# ---------------------------------------------------------------------------





@pytest.fixture()
def matcher():
    """Return a KeywordMatcher configured with our test keywords."""
    return KeywordMatcher(config=KEYWORDS_CONFIG)


@pytest.fixture()
def storage():
    """Return a FakeStorage instance for testing."""
    return FakeStorage()


@pytest.fixture()
def sites_yaml():
    """Write SITES_CONFIG_DICT to temp yaml; yield path; cleanup."""
    path = _write_temp_yaml(SITES_CONFIG_DICT)
    yield path
    _cleanup_file(path)


@pytest.fixture()
def sites_yaml_7():
    """Write full 7-source SITES_CONFIG_7 to temp yaml; yield path; cleanup."""
    path = _write_temp_yaml(SITES_CONFIG_7)
    yield path
    _cleanup_file(path)


@pytest.fixture()
def kw_yaml():
    """Write KEYWORDS_CONFIG to temp yaml; yield path; cleanup."""
    path = _write_temp_yaml(KEYWORDS_CONFIG)
    yield path
    _cleanup_file(path)


# ===========================================================================
# Scenario 1: Full pipeline — all 3 adapters → match → store → verify
# ===========================================================================


class TestFullPipeline:
    """Full pipeline: fetch (mocked) → match → store → verify DB has data."""

    async def test_full_pipeline_all_adapters(self, sites_yaml, kw_yaml):
        """Orchestrator processes all three sites, stores matched jobs."""
        remoteok_json = _load_fixture(REMOTEOK_FIXTURE)
        eleduck_json = _load_fixture(ELEDUCK_FIXTURE)
        wwr_xml = _load_fixture(WWR_FIXTURE)

        remoteok_resp = _build_mock_response(remoteok_json, is_json=True)
        eleduck_resp_p1 = _build_mock_response(eleduck_json, is_json=True)
        eleduck_resp_p2 = _build_mock_response(json.dumps({"posts": []}), is_json=True)
        wwr_resp = _build_mock_response(wwr_xml)

        def fake_get_client(self_adapter, timeout=30.0):
            """Return the right mock client based on adapter type."""
            if isinstance(self_adapter, EleduckAdapter):
                return _make_mock_client([eleduck_resp_p1, eleduck_resp_p2])
            elif isinstance(self_adapter, RemoteOKAdapter):
                return _make_mock_client(remoteok_resp)
            else:  # WeWorkRemotelyAdapter
                return _make_mock_client(wwr_resp)

        storage = FakeStorage()
        with patch("scraper.adapters.base.BaseAdapter._get_client", fake_get_client):
            orch = ScraperOrchestrator(
                sites_config_path=sites_yaml,
                keywords_config_path=kw_yaml,
                storage=storage,
            )
            summary = await orch.run()

        assert summary["total_scraped"] > 0, "Should have fetched jobs"
        assert summary["matched"] > 0, "Should have matched some jobs"
        assert summary["new"] > 0, "Should have stored new jobs"
        assert summary["new"] == summary["matched"], "First run: all matched = new"
        assert len(summary["errors"]) == 0, f"No errors expected, got: {summary['errors']}"

        # Verify DB has actual data
        stats = await storage.get_stats()
        assert stats["total"] > 0
        assert stats["total"] == summary["new"]
        assert stats["active"] == stats["total"]


# ===========================================================================
# Scenario 2: Dry-run — fetch → match → verify nothing stored
# ===========================================================================


class TestDryRun:
    """Dry-run mode: match but don't persist."""

    async def test_dry_run_stores_nothing(self, kw_yaml):
        """In dry-run mode, matched jobs are NOT written to the database."""
        remoteok_json = _load_fixture(REMOTEOK_FIXTURE)
        remoteok_resp = _build_mock_response(remoteok_json, is_json=True)

        single_site = {"sites": {"remoteok": SITES_CONFIG_DICT["sites"]["remoteok"]}}
        sites_path = _write_temp_yaml(single_site)

        try:
            def fake_get_client(self_adapter, timeout=30.0):
                return _make_mock_client(remoteok_resp)

            storage = FakeStorage()
            with patch("scraper.adapters.base.BaseAdapter._get_client", fake_get_client):
                orch = ScraperOrchestrator(
                    sites_config_path=sites_path,
                    keywords_config_path=kw_yaml,
                    storage=storage,
                )
                summary = await orch.run(dry_run=True)

            assert summary["matched"] > 0, "Should match jobs even in dry-run"
            assert summary["new"] == 0, "Dry-run should not store any jobs"
            assert summary["updated"] == 0, "Dry-run should not update any jobs"

            # Verify DB is empty
            stats = await storage.get_stats()
            assert stats["total"] == 0, "Database should be empty after dry-run"
        finally:
            _cleanup_file(sites_path)


# ===========================================================================
# Scenario 3: Single-site filter — only scrape one site
# ===========================================================================


class TestSingleSiteFilter:
    """Filter to a single site."""

    async def test_single_site_only_scrapes_that_site(self, storage, sites_yaml, kw_yaml):
        """When site='remoteok', only RemoteOK adapter is invoked."""
        remoteok_json = _load_fixture(REMOTEOK_FIXTURE)
        remoteok_resp = _build_mock_response(remoteok_json, is_json=True)

        adapter_types_called = []

        def fake_get_client(self_adapter, timeout=30.0):
            adapter_types_called.append(type(self_adapter).__name__)
            return _make_mock_client(remoteok_resp)

        with patch("scraper.adapters.base.BaseAdapter._get_client", fake_get_client):
            orch = ScraperOrchestrator(
                sites_config_path=sites_yaml,
                keywords_config_path=kw_yaml,
                storage=storage,
            )
            summary = await orch.run(site="remoteok")

        # Only RemoteOKAdapter should have been called
        assert adapter_types_called == ["RemoteOKAdapter"]
        assert summary["total_scraped"] > 0

        # All stored jobs should be from remoteok
        sm = FakeStorage()
        stats = await sm.get_stats()
        if stats["total"] > 0:
            assert list(stats["by_source"].keys()) == ["remoteok"]


# ===========================================================================
# Scenario 4: Error handling — one adapter fails, others continue
# ===========================================================================


class TestErrorHandling:
    """One adapter failure doesn't kill the whole pipeline."""

    async def test_one_adapter_fails_others_continue(self, storage, sites_yaml, kw_yaml):
        """If one adapter raises, the others still get processed."""
        eleduck_json = _load_fixture(ELEDUCK_FIXTURE)
        wwr_xml = _load_fixture(WWR_FIXTURE)

        eleduck_resp_p1 = _build_mock_response(eleduck_json, is_json=True)
        eleduck_resp_p2 = _build_mock_response(json.dumps({"posts": []}), is_json=True)
        wwr_resp = _build_mock_response(wwr_xml)

        def fake_get_client(self_adapter, timeout=30.0):
            if isinstance(self_adapter, RemoteOKAdapter):
                raise httpx.ConnectError("Connection refused")
            elif isinstance(self_adapter, EleduckAdapter):
                return _make_mock_client([eleduck_resp_p1, eleduck_resp_p2])
            else:
                return _make_mock_client(wwr_resp)

        with patch("scraper.adapters.base.BaseAdapter._get_client", fake_get_client):
            orch = ScraperOrchestrator(
                sites_config_path=sites_yaml,
                keywords_config_path=kw_yaml,
                storage=storage,
            )
            summary = await orch.run()

        # Should have exactly one error (for remoteok)
        assert len(summary["errors"]) == 1
        assert "remoteok" in summary["errors"][0]

        # Other sites should still have produced data
        assert summary["total_scraped"] > 0, "Other adapters should have fetched jobs"


# ===========================================================================
# Scenario 5: Stats after scrape — counts match
# ===========================================================================


class TestStatsAfterScrape:
    """Verify stats match what was stored."""

    async def test_stats_match_stored_count(self, storage, matcher):
        """Stats total should equal number of upserted jobs."""
        from datetime import datetime

        now = datetime.now()

        # Create and store some jobs that would match
        jobs = [
            JobPosting(
                id=JobPosting.generate_id("https://example.com/1", "AI Engineer"),
                title="AI Engineer",
                company="TestCo",
                url="https://example.com/1",
                source="remoteok",
                description="Looking for an AI engineer with LLM experience",
                tags=["AI", "machine learning"],
                first_seen=now,
                last_seen=now,
                last_updated=now,
            ),
            JobPosting(
                id=JobPosting.generate_id("https://example.com/2", "ML Engineer"),
                title="ML Engineer",
                company="AnotherCo",
                url="https://example.com/2",
                source="eleduck",
                description="Remote machine learning position",
                tags=["ML", "remote"],
                first_seen=now,
                last_seen=now,
                last_updated=now,
            ),
            JobPosting(
                id=JobPosting.generate_id("https://example.com/3", "GPT Developer"),
                title="GPT Developer",
                company="ThirdCo",
                url="https://example.com/3",
                source="weworkremotely",
                description="Build GPT-powered applications",
                tags=["GPT", "LLM"],
                first_seen=now,
                last_seen=now,
                last_updated=now,
            ),
        ]

        total_new = 0
        for job in jobs:
            new, _ = await storage.upsert_job(job)
            total_new += new

        assert total_new == 3

        stats = await storage.get_stats()
        assert stats["total"] == 3
        assert stats["active"] == 3
        assert stats["inactive"] == 0
        assert stats["by_source"]["remoteok"] == 1
        assert stats["by_source"]["eleduck"] == 1
        assert stats["by_source"]["weworkremotely"] == 1

    async def test_stats_after_update(self, storage):
        """After upserting same job twice, count stays 1 but update_count increments."""
        from datetime import datetime

        now = datetime.now()

        job = JobPosting(
            id=JobPosting.generate_id("https://example.com/dup", "Duplicate Job"),
            title="Duplicate Job",
            company="DupCo",
            url="https://example.com/dup",
            source="remoteok",
            description="Test duplicate",
            tags=[],
            first_seen=now,
            last_seen=now,
            last_updated=now,
        )

        new1, upd1 = await storage.upsert_job(job)
        assert (new1, upd1) == (1, 0)

        new2, upd2 = await storage.upsert_job(job)
        assert (new2, upd2) == (0, 1)

        stats = await storage.get_stats()
        assert stats["total"] == 1, "Still only one unique job"


# ===========================================================================
# Scenario 6: Export after scrape — verify JSON file is valid
# ===========================================================================


class TestExportAfterScrape:
    """Export produces a valid JSON file with correct data."""

    async def test_export_json_valid(self, storage):
        """Export creates a JSON file with all stored jobs."""
        from datetime import datetime

        now = datetime.now()

        jobs = [
            JobPosting(
                id=JobPosting.generate_id("https://example.com/e1", "AI Researcher"),
                title="AI Researcher",
                company="LabCo",
                url="https://example.com/e1",
                source="remoteok",
                description="AI research position",
                tags=["AI", "research"],
                first_seen=now,
                last_seen=now,
                last_updated=now,
            ),
            JobPosting(
                id=JobPosting.generate_id("https://example.com/e2", "LLM Engineer"),
                title="LLM Engineer",
                company="ModelCo",
                url="https://example.com/e2",
                source="eleduck",
                description="Work on large language models",
                tags=["LLM", "远程"],
                first_seen=now,
                last_seen=now,
                last_updated=now,
            ),
        ]

        for job in jobs:
            await storage.upsert_job(job)

        # Export to a temp file
        fd, export_path = tempfile.mkstemp(suffix=".json", prefix="test_export_")
        os.close(fd)

        try:
            await storage.export_json(export_path)

            # Verify file exists and is valid JSON
            assert os.path.exists(export_path)

            with open(export_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert isinstance(data, list)
            assert len(data) == 2

            # Verify fields are present
            titles = {item["title"] for item in data}
            assert "AI Researcher" in titles
            assert "LLM Engineer" in titles

            # Verify Chinese characters survived serialization
            for item in data:
                if item["title"] == "LLM Engineer":
                    assert "远程" in json.dumps(item["tags"], ensure_ascii=False)
        finally:
            gc.collect()
            try:
                os.unlink(export_path)
            except OSError:
                pass

    async def test_export_empty_db(self, storage):
        """Export on empty DB creates a valid empty JSON array."""
        fd, export_path = tempfile.mkstemp(suffix=".json", prefix="test_export_empty_")
        os.close(fd)

        try:
            await storage.export_json(export_path)

            with open(export_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data == []
        finally:
            gc.collect()
            try:
                os.unlink(export_path)
            except OSError:
                pass


# ===========================================================================
# Bonus: Component-level integration tests
# ===========================================================================


class TestComponentIntegration:
    """Verify key components work together correctly."""

    def test_matcher_with_real_fixture_data(self, matcher):
        """KeywordMatcher correctly filters fixture jobs."""
        # Job that SHOULD match (has "AI" in description, remoteok skips location)
        matching_job = {
            "title": "Senior DevOps Engineer",
            "description": "Anduril is committed to bringing cutting-edge autonomy, AI, computer vision",
            "tags": ["devops", "engineer"],
        }
        assert matcher.match_job(matching_job, "remoteok") is True

        # Job that should NOT match (no tech keywords)
        non_matching = {
            "title": "Customer Support Specialist",
            "description": "Responding to customer inquiries via phone, email, and chat",
            "tags": ["support"],
        }
        assert matcher.match_job(non_matching, "remoteok") is False

    async def test_model_round_trip_through_storage(self, storage):
        """JobPosting → DB → JobPosting preserves all fields."""
        from datetime import datetime

        now = datetime.now()

        original = JobPosting(
            id=JobPosting.generate_id("https://example.com/rt", "Round Trip Test"),
            title="Round Trip Test",
            company="TestCo",
            url="https://example.com/rt",
            source="remoteok",
            published_at=now,
            salary="$100,000 - $150,000",
            location="Remote",
            description="Testing round trip serialization",
            tags=["python", "AI", "远程"],
            first_seen=now,
            last_seen=now,
            last_updated=now,
        )

        await storage.upsert_job(original)
        retrieved = await storage.get_all_jobs()

        assert len(retrieved) == 1
        r = retrieved[0]
        assert r["id"] == original.id
        assert r["title"] == original.title
        assert r["company"] == original.company
        assert r["url"] == original.url
        assert r["source"] == original.source
        assert r["salary"] == original.salary
        assert r["location"] == original.location
        assert r["description"] == original.description
        assert r["tags"] == original.tags

    def test_all_modules_importable(self):
        """All project modules import without error — including Phase 2 modules."""
        import scraper
        import scraper.adapters
        import scraper.adapters.api
        import scraper.adapters.base
        import scraper.adapters.browser
        import scraper.adapters.html
        import scraper.adapters.hybrid
        import scraper.adapters.rss
        import scraper.models
        import scraper.orchestrator
        import scraper.utils
        import scraper.utils.dedup
        import scraper.utils.matcher
        import config

        # If we reach here, all imports succeeded
        assert True


# ===========================================================================
# Scenario 7: Full 7-source pipeline — mocked fetch for all adapters
# ===========================================================================


def _mock_adapter_fetch(adapter, jobs: list[JobPosting]):
    """Monkey-patch an adapter's fetch_jobs to return pre-built jobs."""
    adapter.fetch_jobs = AsyncMock(return_value=jobs)
    return adapter


class TestSevenSourcePipeline:
    """Full pipeline with all 7 adapters mocked at the fetch_jobs level."""

    async def test_seven_source_pipeline_fetches_all(self, storage, sites_yaml_7, kw_yaml):
        """Orchestrator with 7 sources fetches, matches, deduplicates, and stores."""
        from datetime import datetime

        now = datetime.now()

        # Build fake jobs per adapter — each has a tech keyword so matcher passes
        fake_jobs = {
            "remoteok": [
                JobPosting(
                    id=JobPosting.generate_id("https://remoteok.com/j/1", "AI Eng"),
                    title="AI Engineer",
                    company="AlphaAI",
                    url="https://remoteok.com/j/1",
                    source="remoteok",
                    description="Work on AI systems",
                    tags=["AI"],
                    first_seen=now, last_seen=now, last_updated=now,
                ),
            ],
            "eleduck": [
                JobPosting(
                    id=JobPosting.generate_id("https://eleduck.com/p/1", "LLM Dev"),
                    title="LLM Developer",
                    company="DuckCo",
                    url="https://eleduck.com/p/1",
                    source="eleduck",
                    description="远程 LLM 开发",
                    tags=["LLM", "远程"],
                    first_seen=now, last_seen=now, last_updated=now,
                ),
            ],
            "weworkremotely": [
                JobPosting(
                    id=JobPosting.generate_id("https://wwr.com/j/1", "ML Eng"),
                    title="Machine Learning Engineer",
                    company="WWRCo",
                    url="https://wwr.com/j/1",
                    source="weworkremotely",
                    description="ML pipeline development",
                    tags=["machine learning"],
                    first_seen=now, last_seen=now, last_updated=now,
                ),
            ],
            "workgo": [
                JobPosting(
                    id=JobPosting.generate_id("https://workgo.ai/j/1", "GPT Dev"),
                    title="GPT Developer",
                    company="WorkGoCo",
                    url="https://workgo.ai/j/1",
                    source="workgo",
                    description="Build GPT tools",
                    tags=["GPT"],
                    first_seen=now, last_seen=now, last_updated=now,
                ),
            ],
            "v2ex": [
                JobPosting(
                    id=JobPosting.generate_id("https://v2ex.com/t/1", "DevOps Eng"),
                    title="DevOps Engineer",
                    company="V2Co",
                    url="https://v2ex.com/t/1",
                    source="v2ex",
                    description="远程 DevOps position",
                    tags=["DevOps", "远程"],
                    first_seen=now, last_seen=now, last_updated=now,
                ),
            ],
            "arcdev": [
                JobPosting(
                    id=JobPosting.generate_id("https://arc.dev/j/1", "Data Eng"),
                    title="Data Engineer",
                    company="ArcCo",
                    url="https://arc.dev/j/1",
                    source="arcdev",
                    description="Data pipeline engineering",
                    tags=["data"],
                    first_seen=now, last_seen=now, last_updated=now,
                ),
            ],
            "yuancheng": [
                JobPosting(
                    id=JobPosting.generate_id("https://yuancheng.work/j/1", "AI 研究员"),
                    title="AI 研究员",
                    company="远程Co",
                    url="https://yuancheng.work/j/1",
                    source="yuancheng",
                    description="远程 AI research position 远程",
                    tags=["AI", "远程"],
                    first_seen=now, last_seen=now, last_updated=now,
                ),
            ],
        }

        original_create = ScraperOrchestrator._create_adapter

        def mock_create_adapter(self_orch, site_id, site_config):
            adapter = original_create(self_orch, site_id, site_config)
            if site_id in fake_jobs:
                adapter.fetch_jobs = AsyncMock(return_value=fake_jobs[site_id])
            return adapter

        with patch.object(ScraperOrchestrator, "_create_adapter", mock_create_adapter):
            orch = ScraperOrchestrator(
                sites_config_path=sites_yaml_7,
                keywords_config_path=kw_yaml,
                storage=storage,
            )
            summary = await orch.run()

        assert summary["total_scraped"] == 7, f"Should fetch 7 jobs total, got {summary['total_scraped']}"
        assert summary["matched"] > 0, "Should have matched some jobs"
        assert len(summary["errors"]) == 0, f"No errors expected: {summary['errors']}"

        stats = await storage.get_stats()
        assert stats["total"] > 0
        # Verify we have jobs from multiple sources
        assert len(stats["by_source"]) >= 3, f"Expected jobs from >=3 sources, got: {stats['by_source']}"

    async def test_seven_source_one_failure_continues(self, storage, sites_yaml_7, kw_yaml):
        """If one of 7 adapters fails, the other 6 still process."""
        from datetime import datetime

        now = datetime.now()

        def make_job(source, title, url):
            return JobPosting(
                id=JobPosting.generate_id(url, title),
                title=title, company="TestCo", url=url,
                source=source, description=f"AI {title}",
                tags=["AI"],
                first_seen=now, last_seen=now, last_updated=now,
            )

        original_create = ScraperOrchestrator._create_adapter

        def mock_create_adapter(self_orch, site_id, site_config):
            adapter = original_create(self_orch, site_id, site_config)
            if site_id == "v2ex":
                adapter.fetch_jobs = AsyncMock(side_effect=httpx.ConnectError("V2EX down"))
            else:
                adapter.fetch_jobs = AsyncMock(return_value=[
                    make_job(site_id, f"AI Eng at {site_id}", f"https://{site_id}.test/j/1"),
                ])
            return adapter

        with patch.object(ScraperOrchestrator, "_create_adapter", mock_create_adapter):
            orch = ScraperOrchestrator(
                sites_config_path=sites_yaml_7,
                keywords_config_path=kw_yaml,
                storage=storage,
            )
            summary = await orch.run()

        assert len(summary["errors"]) == 1, f"Expected 1 error, got: {summary['errors']}"
        assert "v2ex" in summary["errors"][0]
        assert summary["total_scraped"] == 6, "Other 6 adapters should still fetch"


# ===========================================================================
# Scenario 8: Single-site filter for all 7 sources
# ===========================================================================


class TestSingleSiteFilterAll7:
    """Verify single-site filter works for each of the 7 adapters."""

    @pytest.mark.parametrize("site_id", [
        "remoteok", "eleduck", "weworkremotely",
        "workgo", "v2ex", "arcdev", "yuancheng",
    ])
    async def test_single_site_filter(self, storage, site_id, sites_yaml_7, kw_yaml):
        """When site=<id>, only that adapter is invoked."""
        from datetime import datetime

        now = datetime.now()
        adapters_called = []

        original_create = ScraperOrchestrator._create_adapter

        def mock_create_adapter(self_orch, sid, site_config):
            adapter = original_create(self_orch, sid, site_config)
            adapters_called.append(sid)
            adapter.fetch_jobs = AsyncMock(return_value=[
                JobPosting(
                    id=JobPosting.generate_id(f"https://{sid}.test/1", "AI Eng"),
                    title="AI Engineer", company="Co", url=f"https://{sid}.test/1",
                    source=sid, description="远程 AI developer role",
                    tags=["AI", "远程"],
                    first_seen=now, last_seen=now, last_updated=now,
                ),
            ])
            return adapter

        with patch.object(ScraperOrchestrator, "_create_adapter", mock_create_adapter):
            orch = ScraperOrchestrator(
                sites_config_path=sites_yaml_7,
                keywords_config_path=kw_yaml,
                storage=storage,
            )
            summary = await orch.run(site=site_id)

        assert adapters_called == [site_id], (
            f"Only {site_id} adapter should be called, got: {adapters_called}"
        )
        assert summary["total_scraped"] == 1


# ===========================================================================
# Scenario 9: Cross-site dedup integration
# ===========================================================================


class TestCrossSiteDedup:
    """Cross-site dedup removes duplicates posted on multiple boards."""

    async def test_cross_site_dedup_removes_duplicate(self, storage, sites_yaml_7, kw_yaml):
        """Same job posted on remoteok and arcdev gets deduplicated."""
        from datetime import datetime

        now = datetime.now()
        earlier = datetime(2025, 1, 10, 12, 0, 0)

        original_create = ScraperOrchestrator._create_adapter

        def mock_create_adapter(self_orch, sid, site_config):
            adapter = original_create(self_orch, sid, site_config)
            if sid == "remoteok":
                adapter.fetch_jobs = AsyncMock(return_value=[
                    JobPosting(
                        id=JobPosting.generate_id("https://remoteok.com/j/dup", "AI Engineer"),
                        title="AI Engineer", company="Acme Inc",
                        url="https://remoteok.com/j/dup", source="remoteok",
                        description="AI engineer role", tags=["AI"],
                        first_seen=earlier, last_seen=now, last_updated=now,
                    ),
                ])
            elif sid == "arcdev":
                adapter.fetch_jobs = AsyncMock(return_value=[
                    JobPosting(
                        id=JobPosting.generate_id("https://arc.dev/j/dup", "AI Engineer"),
                        title="AI Engineer", company="Acme",
                        url="https://arc.dev/j/dup", source="arcdev",
                        description="Remote AI engineer role anywhere",
                        tags=["AI", "remote"],
                        first_seen=now, last_seen=now, last_updated=now,
                    ),
                ])
            else:
                adapter.fetch_jobs = AsyncMock(return_value=[])
            return adapter

        with patch.object(ScraperOrchestrator, "_create_adapter", mock_create_adapter):
            orch = ScraperOrchestrator(
                sites_config_path=sites_yaml_7,
                keywords_config_path=kw_yaml,
                storage=storage,
            )
            summary = await orch.run()

        # 2 scraped, both matched, but dedup removes 1
        assert summary["total_scraped"] == 2
        assert summary["matched"] == 2
        assert summary["dedup_removed"] == 1
        assert summary["new"] == 1, "Only one unique job should be stored"

    async def test_no_dedup_for_different_jobs(self, storage, sites_yaml_7, kw_yaml):
        """Different jobs from different sources are all kept."""
        from datetime import datetime

        now = datetime.now()

        original_create = ScraperOrchestrator._create_adapter

        def mock_create_adapter(self_orch, sid, site_config):
            adapter = original_create(self_orch, sid, site_config)
            if sid == "remoteok":
                adapter.fetch_jobs = AsyncMock(return_value=[
                    JobPosting(
                        id=JobPosting.generate_id("https://remoteok.com/j/a", "AI Engineer"),
                        title="AI Engineer", company="AlphaCo",
                        url="https://remoteok.com/j/a", source="remoteok",
                        description="AI engineer", tags=["AI"],
                        first_seen=now, last_seen=now, last_updated=now,
                    ),
                ])
            elif sid == "eleduck":
                adapter.fetch_jobs = AsyncMock(return_value=[
                    JobPosting(
                        id=JobPosting.generate_id("https://eleduck.com/j/b", "LLM Dev"),
                        title="LLM Developer", company="BetaCo",
                        url="https://eleduck.com/j/b", source="eleduck",
                        description="远程 LLM", tags=["LLM", "远程"],
                        first_seen=now, last_seen=now, last_updated=now,
                    ),
                ])
            else:
                adapter.fetch_jobs = AsyncMock(return_value=[])
            return adapter

        with patch.object(ScraperOrchestrator, "_create_adapter", mock_create_adapter):
            orch = ScraperOrchestrator(
                sites_config_path=sites_yaml_7,
                keywords_config_path=kw_yaml,
                storage=storage,
            )
            summary = await orch.run()

        assert summary["dedup_removed"] == 0, "Different jobs should not be deduped"
        assert summary["new"] == summary["matched"]


# ===========================================================================
# Scenario 10: Adapter registration completeness
# ===========================================================================


class TestAdapterRegistration:
    """Verify the orchestrator's _ADAPTER_MAP has all 7 adapters."""

    def test_all_seven_adapters_registered(self):
        """_ADAPTER_MAP contains entries for all 7 source IDs."""
        from scraper.orchestrator import _ADAPTER_MAP

        expected = {"remoteok", "eleduck", "weworkremotely", "workgo", "v2ex", "arcdev", "yuancheng"}
        assert set(_ADAPTER_MAP.keys()) == expected

    def test_adapter_map_values_are_base_adapter_subclasses(self):
        """All adapter classes in the map inherit from BaseAdapter."""
        from scraper.adapters.base import BaseAdapter
        from scraper.orchestrator import _ADAPTER_MAP

        for site_id, cls in _ADAPTER_MAP.items():
            assert issubclass(cls, BaseAdapter), f"{site_id} adapter is not a BaseAdapter subclass"
