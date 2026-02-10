"""Tests for WorkGo cookie-based API adapter."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from scraper.adapters.api import WorkGoAdapter
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
        "adapter": "api",
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
        # 5 entries total, 1 has empty title -> 4 valid
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
    """Tests for fetch_jobs with mocked httpx client."""

    async def test_fetch_jobs_returns_list(
        self, adapter: WorkGoAdapter, fixture_data: dict
    ) -> None:
        """fetch_jobs should return a list of JobPostings from API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_ensure_jwt", new_callable=AsyncMock):
                with patch.object(adapter, "_delay", new_callable=AsyncMock):
                    jobs = await adapter.fetch_jobs()

        assert isinstance(jobs, list)
        assert len(jobs) == 4  # 5 entries minus 1 empty title
        for job in jobs:
            assert isinstance(job, JobPosting)
            assert job.source == "workgo"

    async def test_fetch_jobs_pagination(self, adapter: WorkGoAdapter) -> None:
        """fetch_jobs should handle multiple pages."""
        page1_data = {
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
        page2_data = {
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

        page1_response = MagicMock()
        page1_response.status_code = 200
        page1_response.json.return_value = page1_data
        page1_response.raise_for_status = MagicMock()

        page2_response = MagicMock()
        page2_response.status_code = 200
        page2_response.json.return_value = page2_data
        page2_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[page1_response, page2_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_ensure_jwt", new_callable=AsyncMock):
                with patch.object(adapter, "_delay", new_callable=AsyncMock):
                    jobs = await adapter.fetch_jobs()

        assert len(jobs) == 25
        assert mock_client.post.call_count == 2

    async def test_fetch_jobs_empty_response(self, adapter: WorkGoAdapter) -> None:
        """Empty API response should return empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobs": [], "has_more_pages": False}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_ensure_jwt", new_callable=AsyncMock):
                jobs = await adapter.fetch_jobs()

        assert jobs == []

    async def test_fetch_jobs_auth_failure(self, adapter: WorkGoAdapter) -> None:
        """Auth failure in _ensure_jwt should return empty list."""
        with patch.object(
            adapter, "_ensure_jwt", new_callable=AsyncMock,
            side_effect=ValueError("WORKGO_COOKIE environment variable is required"),
        ):
            jobs = await adapter.fetch_jobs()

        assert jobs == []

    async def test_fetch_jobs_missing_credentials(self) -> None:
        """Missing credentials should return empty list gracefully."""
        config = {
            "name": "WorkGo",
            "url": "https://workgo.ai",
            "api_url": "https://api.workgo.ai/auth/jobs/all",
            "adapter": "api",
            "enabled": True,
        }
        adapter = WorkGoAdapter(config)
        with patch.object(
            adapter, "_ensure_jwt", new_callable=AsyncMock,
            side_effect=ValueError("No credentials"),
        ):
            jobs = await adapter.fetch_jobs()
        assert jobs == []

    async def test_fetch_jobs_network_error(self, adapter: WorkGoAdapter) -> None:
        """Network errors during API call should be handled gracefully."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_ensure_jwt", new_callable=AsyncMock):
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


class TestWorkGoClerkAuth:
    """Tests for Clerk cookie-to-JWT authentication flow."""

    async def test_ensure_jwt_success(self, adapter: WorkGoAdapter) -> None:
        """Successful Clerk auth: GET /client -> session_id, POST /tokens -> jwt."""
        client_resp = MagicMock()
        client_resp.json.return_value = {
            "response": {"last_active_session_id": "sess_abc123"}
        }
        client_resp.raise_for_status = MagicMock()

        token_resp = MagicMock()
        token_resp.json.return_value = {"jwt": "test.jwt.token"}
        token_resp.raise_for_status = MagicMock()

        mock_clerk_client = AsyncMock()
        mock_clerk_client.get = AsyncMock(return_value=client_resp)
        mock_clerk_client.post = AsyncMock(return_value=token_resp)
        mock_clerk_client.__aenter__ = AsyncMock(return_value=mock_clerk_client)
        mock_clerk_client.__aexit__ = AsyncMock(return_value=None)

        with patch.dict(os.environ, {"WORKGO_COOKIE": "test_cookie_value"}):
            with patch("httpx.AsyncClient", return_value=mock_clerk_client):
                await adapter._ensure_jwt()

        assert adapter._jwt == "test.jwt.token"
        mock_clerk_client.get.assert_called_once()
        mock_clerk_client.post.assert_called_once()

    async def test_ensure_jwt_missing_cookie(self, adapter: WorkGoAdapter) -> None:
        """No WORKGO_COOKIE env var should raise ValueError with helpful message."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove WORKGO_COOKIE if present
            os.environ.pop("WORKGO_COOKIE", None)
            with pytest.raises(ValueError, match="WORKGO_COOKIE"):
                await adapter._ensure_jwt()

    async def test_ensure_jwt_expired_cookie(self, adapter: WorkGoAdapter) -> None:
        """Clerk returns session with last_active_session_id=null -> ValueError."""
        client_resp = MagicMock()
        client_resp.json.return_value = {
            "response": {"last_active_session_id": None}
        }
        client_resp.raise_for_status = MagicMock()

        mock_clerk_client = AsyncMock()
        mock_clerk_client.get = AsyncMock(return_value=client_resp)
        mock_clerk_client.__aenter__ = AsyncMock(return_value=mock_clerk_client)
        mock_clerk_client.__aexit__ = AsyncMock(return_value=None)

        with patch.dict(os.environ, {"WORKGO_COOKIE": "expired_cookie"}):
            with patch("httpx.AsyncClient", return_value=mock_clerk_client):
                with pytest.raises(ValueError, match="expired"):
                    await adapter._ensure_jwt()

    async def test_fetch_jobs_jwt_refresh_on_401(
        self, adapter: WorkGoAdapter
    ) -> None:
        """First API call returns 401, adapter refreshes JWT, retry succeeds."""
        fixture_path = FIXTURE_PATH
        with open(fixture_path, "r", encoding="utf-8") as f:
            fixture_data = json.load(f)

        # First call: 401
        resp_401 = MagicMock()
        resp_401.status_code = 401

        # Second call after JWT refresh: 200
        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = fixture_data
        resp_200.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[resp_401, resp_200])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_ensure_jwt", new_callable=AsyncMock):
                with patch.object(adapter, "_refresh_jwt", new_callable=AsyncMock):
                    jobs = await adapter.fetch_jobs()

        assert len(jobs) == 4
        # post called twice: first 401, then retry 200
        assert mock_client.post.call_count == 2

    async def test_fetch_jobs_double_401_gives_up(
        self, adapter: WorkGoAdapter
    ) -> None:
        """Both API calls return 401 -> log error, return []."""
        resp_401_first = MagicMock()
        resp_401_first.status_code = 401

        resp_401_second = MagicMock()
        resp_401_second.status_code = 401

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[resp_401_first, resp_401_second]
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_ensure_jwt", new_callable=AsyncMock):
                with patch.object(adapter, "_refresh_jwt", new_callable=AsyncMock):
                    jobs = await adapter.fetch_jobs()

        assert jobs == []

    async def test_ensure_jwt_clerk_network_error(
        self, adapter: WorkGoAdapter
    ) -> None:
        """Clerk API unreachable -> exception handled in fetch_jobs, return []."""
        mock_clerk_client = AsyncMock()
        mock_clerk_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Clerk unreachable")
        )
        mock_clerk_client.__aenter__ = AsyncMock(return_value=mock_clerk_client)
        mock_clerk_client.__aexit__ = AsyncMock(return_value=None)

        with patch.dict(os.environ, {"WORKGO_COOKIE": "test_cookie"}):
            with patch("httpx.AsyncClient", return_value=mock_clerk_client):
                # _ensure_jwt raises, fetch_jobs catches and returns []
                jobs = await adapter.fetch_jobs()

        assert jobs == []
