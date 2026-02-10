"""Tests for WorkGo browser-based adapter."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scraper.adapters.browser import WorkGoAdapter
from scraper.models import JobPosting

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "workgo_sample.json"


@pytest.fixture
def fixture_data() -> dict:
    """Load the saved WorkGo API fixture."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def adapter() -> WorkGoAdapter:
    """Create a WorkGoAdapter with default config."""
    config = {
        "name": "WorkGo",
        "url": "https://workgo.ai",
        "api_url": "https://api.workgo.ai/auth/jobs/all",
        "adapter": "browser",
        "enabled": True,
        "skip_location_match": False,
        "rate_limit_seconds": 2,
        "page_size": 20,
        "headers": {"User-Agent": "Mozilla/5.0"},
    }
    return WorkGoAdapter(config)


class TestWorkGoAdapterProperties:
    """Tests for WorkGoAdapter basic properties."""

    def test_name(self, adapter: WorkGoAdapter) -> None:
        assert adapter.name == "WorkGo"

    def test_source_id(self, adapter: WorkGoAdapter) -> None:
        assert adapter.source_id == "workgo"

    def test_is_base_adapter(self, adapter: WorkGoAdapter) -> None:
        from scraper.adapters.base import BaseAdapter
        assert isinstance(adapter, BaseAdapter)


class TestWorkGoParseEntry:
    """Tests for _parse_entry static method."""

    def test_parse_valid_entry(self, fixture_data: dict) -> None:
        """First valid entry should parse into a JobPosting."""
        entry = fixture_data["jobs"][0]
        job = WorkGoAdapter._parse_entry(entry)
        assert job is not None
        assert isinstance(job, JobPosting)
        assert job.title == "Senior AI/ML Engineer"
        assert job.company == "TechCorp AI"
        assert job.source == "workgo"
        assert len(job.id) == 32  # MD5 hex digest

    def test_parse_entry_url(self, fixture_data: dict) -> None:
        """URL should use workgo.ai domain with job id."""
        entry = fixture_data["jobs"][0]
        job = WorkGoAdapter._parse_entry(entry)
        assert job is not None
        assert "workgo.ai" in job.url
        assert "job_abc123" in job.url

    def test_parse_entry_description(self, fixture_data: dict) -> None:
        entry = fixture_data["jobs"][0]
        job = WorkGoAdapter._parse_entry(entry)
        assert job is not None
        assert "LLM" in job.description

    def test_parse_entry_location(self, fixture_data: dict) -> None:
        entry = fixture_data["jobs"][0]
        job = WorkGoAdapter._parse_entry(entry)
        assert job is not None
        assert job.location == "Remote"

    def test_parse_entry_salary(self, fixture_data: dict) -> None:
        entry = fixture_data["jobs"][0]
        job = WorkGoAdapter._parse_entry(entry)
        assert job is not None
        assert job.salary == "$150,000 - $200,000"

    def test_parse_entry_tags_combined(self, fixture_data: dict) -> None:
        """Tags should combine tags + skills_required without duplicates."""
        entry = fixture_data["jobs"][0]
        job = WorkGoAdapter._parse_entry(entry)
        assert job is not None
        assert isinstance(job.tags, list)
        assert "AI" in job.tags
        assert "Python" in job.tags
        # Tags from skills_required should also be included
        assert "TensorFlow" in job.tags

    def test_parse_entry_published_at(self, fixture_data: dict) -> None:
        entry = fixture_data["jobs"][0]
        job = WorkGoAdapter._parse_entry(entry)
        assert job is not None
        assert job.published_at is not None
        assert isinstance(job.published_at, datetime)

    def test_parse_all_valid_entries(self, fixture_data: dict) -> None:
        """All entries with non-empty titles should parse."""
        parsed = []
        for entry in fixture_data["jobs"]:
            job = WorkGoAdapter._parse_entry(entry)
            if job is not None:
                parsed.append(job)
                assert job.source == "workgo"
        # 5 entries total, 1 has empty title → 4 valid
        assert len(parsed) == 4

    def test_empty_title_returns_none(self) -> None:
        """Entry with empty title should return None."""
        entry = {
            "id": "job_empty",
            "title": "",
            "company": "Test",
            "description": "test",
        }
        result = WorkGoAdapter._parse_entry(entry)
        assert result is None

    def test_whitespace_title_returns_none(self) -> None:
        """Entry with whitespace-only title should return None."""
        entry = {
            "id": "job_ws",
            "title": "   ",
            "company": "Test",
            "description": "test",
        }
        result = WorkGoAdapter._parse_entry(entry)
        assert result is None

    def test_missing_title_returns_none(self) -> None:
        """Entry with no title key should return None."""
        entry = {"id": "job_no_title", "company": "Test"}
        result = WorkGoAdapter._parse_entry(entry)
        assert result is None

    def test_missing_id_returns_none(self) -> None:
        """Entry with no id should return None."""
        entry = {"title": "Test Job", "company": "Test"}
        result = WorkGoAdapter._parse_entry(entry)
        assert result is None

    def test_missing_optional_fields(self) -> None:
        """Entry with only id and title should still parse."""
        entry = {"id": "job_min", "title": "Minimal Job"}
        job = WorkGoAdapter._parse_entry(entry)
        assert job is not None
        assert job.title == "Minimal Job"
        assert job.company is None
        assert job.salary is None
        assert job.location is None
        assert job.tags == []

    def test_invalid_date_still_parses(self) -> None:
        """Entry with bad date should parse with published_at=None."""
        entry = {
            "id": "job_baddate",
            "title": "Bad Date Job",
            "published_at": "not-a-date",
        }
        job = WorkGoAdapter._parse_entry(entry)
        assert job is not None
        assert job.published_at is None

    def test_null_salary(self) -> None:
        """Null salary should be None, not 'None' string."""
        entry = {
            "id": "job_nullsal",
            "title": "Null Salary Job",
            "salary": None,
        }
        job = WorkGoAdapter._parse_entry(entry)
        assert job is not None
        assert job.salary is None


class TestWorkGoFetchJobs:
    """Tests for fetch_jobs with mocked browser."""

    async def test_fetch_jobs_returns_list(
        self, adapter: WorkGoAdapter, fixture_data: dict
    ) -> None:
        """fetch_jobs should return a list of JobPostings from intercepted API data."""
        with patch.object(
            adapter, "_fetch_via_browser", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = fixture_data
            jobs = await adapter.fetch_jobs()

        assert isinstance(jobs, list)
        assert len(jobs) == 4  # 5 entries minus 1 empty title
        for job in jobs:
            assert isinstance(job, JobPosting)
            assert job.source == "workgo"

    async def test_fetch_jobs_pagination(self, adapter: WorkGoAdapter) -> None:
        """fetch_jobs should handle multiple pages."""
        page1 = {
            "jobs": [
                {
                    "id": f"job_p1_{i}",
                    "title": f"Job Page1 {i}",
                    "company": "TestCo",
                    "description": "desc",
                }
                for i in range(20)
            ],
            "total": 25,
            "page": 1,
            "page_size": 20,
            "has_more_pages": True,
        }
        page2 = {
            "jobs": [
                {
                    "id": f"job_p2_{i}",
                    "title": f"Job Page2 {i}",
                    "company": "TestCo",
                    "description": "desc",
                }
                for i in range(5)
            ],
            "total": 25,
            "page": 2,
            "page_size": 20,
            "has_more_pages": False,
        }

        with patch.object(
            adapter, "_fetch_via_browser", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = [page1, page2]
            jobs = await adapter.fetch_jobs()

        assert len(jobs) == 25
        assert mock_fetch.call_count == 2

    async def test_fetch_jobs_empty_response(self, adapter: WorkGoAdapter) -> None:
        """Empty API response should return empty list."""
        with patch.object(
            adapter, "_fetch_via_browser", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = {"jobs": [], "has_more_pages": False}
            jobs = await adapter.fetch_jobs()

        assert jobs == []

    async def test_fetch_jobs_auth_failure(self, adapter: WorkGoAdapter) -> None:
        """Auth failure should log error and return empty list."""
        with patch.object(
            adapter, "_fetch_via_browser", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Authentication failed")
            jobs = await adapter.fetch_jobs()

        assert jobs == []

    async def test_fetch_jobs_missing_credentials(self) -> None:
        """Missing credentials should return empty list gracefully."""
        config = {
            "name": "WorkGo",
            "url": "https://workgo.ai",
            "api_url": "https://api.workgo.ai/auth/jobs/all",
            "adapter": "browser",
            "enabled": True,
        }
        adapter = WorkGoAdapter(config)
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(
                adapter, "_fetch_via_browser", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.side_effect = Exception("No credentials")
                jobs = await adapter.fetch_jobs()
        assert jobs == []

    async def test_fetch_jobs_network_error(self, adapter: WorkGoAdapter) -> None:
        """Network errors should be handled gracefully."""
        with patch.object(
            adapter, "_fetch_via_browser", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = TimeoutError("Browser timeout")
            jobs = await adapter.fetch_jobs()

        assert jobs == []


class TestWorkGoResponseParsing:
    """Tests for _parse_api_response method."""

    def test_parse_full_response(self, fixture_data: dict) -> None:
        """Parse a full API response into job list."""
        jobs = WorkGoAdapter._parse_api_response(fixture_data)
        assert len(jobs) == 4

    def test_parse_empty_jobs_list(self) -> None:
        data = {"jobs": [], "has_more_pages": False}
        jobs = WorkGoAdapter._parse_api_response(data)
        assert jobs == []

    def test_parse_missing_jobs_key(self) -> None:
        """Response without 'jobs' key should return empty list."""
        data = {"total": 0}
        jobs = WorkGoAdapter._parse_api_response(data)
        assert jobs == []

    def test_parse_invalid_data(self) -> None:
        """Non-dict response should return empty list."""
        jobs = WorkGoAdapter._parse_api_response(None)
        assert jobs == []

    def test_parse_skips_invalid_entries(self) -> None:
        """Invalid entries should be skipped, not crash."""
        data = {
            "jobs": [
                {"id": "valid1", "title": "Valid Job"},
                {"id": "invalid", "title": ""},  # empty title
                {"id": "valid2", "title": "Another Valid Job"},
            ]
        }
        jobs = WorkGoAdapter._parse_api_response(data)
        assert len(jobs) == 2
