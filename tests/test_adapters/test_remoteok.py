"""Tests for RemoteOK adapter using saved fixture data."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scraper.adapters.api import RemoteOKAdapter
from scraper.models import JobPosting

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "remoteok_sample.json"


@pytest.fixture
def fixture_data() -> list[dict]:
    """Load the saved RemoteOK API fixture."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def adapter() -> RemoteOKAdapter:
    """Create a RemoteOKAdapter with default config."""
    config = {
        "name": "RemoteOK",
        "url": "https://remoteok.com/api",
        "adapter": "api",
        "enabled": True,
        "skip_location_match": True,
        "rate_limit_seconds": 2,
        "headers": {"User-Agent": "Mozilla/5.0"},
    }
    return RemoteOKAdapter(config)


class TestRemoteOKAdapter:
    """Tests for RemoteOKAdapter."""

    def test_name(self, adapter: RemoteOKAdapter) -> None:
        assert adapter.name == "RemoteOK"

    def test_source_id(self, adapter: RemoteOKAdapter) -> None:
        assert adapter.source_id == "remoteok"

    def test_legal_notice_skipped(
        self, adapter: RemoteOKAdapter, fixture_data: list[dict]
    ) -> None:
        """The first element (legal notice) must never produce a JobPosting."""
        legal = fixture_data[0]
        # Legal notice has 'legal' key and no 'position'
        assert "legal" in legal
        result = RemoteOKAdapter._parse_entry(legal)
        assert result is None

    def test_parse_valid_job(self, fixture_data: list[dict]) -> None:
        """Second element should parse into a valid JobPosting."""
        entry = fixture_data[1]
        job = RemoteOKAdapter._parse_entry(entry)
        assert job is not None
        assert isinstance(job, JobPosting)
        assert job.title == entry["position"]
        assert job.company == entry["company"]
        assert job.source == "remoteok"
        assert len(job.id) == 32  # MD5 hex digest

    def test_field_mapping_title(self, fixture_data: list[dict]) -> None:
        entry = fixture_data[1]
        job = RemoteOKAdapter._parse_entry(entry)
        assert job is not None
        assert job.title == entry["position"]

    def test_field_mapping_company(self, fixture_data: list[dict]) -> None:
        entry = fixture_data[1]
        job = RemoteOKAdapter._parse_entry(entry)
        assert job is not None
        assert job.company == entry["company"]

    def test_field_mapping_url(self, fixture_data: list[dict]) -> None:
        entry = fixture_data[1]
        job = RemoteOKAdapter._parse_entry(entry)
        assert job is not None
        assert "remoteok" in job.url.lower() or "remoteOK" in job.url

    def test_field_mapping_tags(self, fixture_data: list[dict]) -> None:
        entry = fixture_data[1]
        job = RemoteOKAdapter._parse_entry(entry)
        assert job is not None
        assert isinstance(job.tags, list)
        assert job.tags == entry["tags"]

    def test_field_mapping_location(self, fixture_data: list[dict]) -> None:
        entry = fixture_data[1]
        job = RemoteOKAdapter._parse_entry(entry)
        assert job is not None
        if entry.get("location"):
            assert job.location == entry["location"]

    def test_field_mapping_published_at(self, fixture_data: list[dict]) -> None:
        entry = fixture_data[1]
        job = RemoteOKAdapter._parse_entry(entry)
        assert job is not None
        assert job.published_at is not None

    def test_source_always_remoteok(self, fixture_data: list[dict]) -> None:
        """Every parsed entry must have source='remoteok'."""
        for entry in fixture_data[1:]:
            job = RemoteOKAdapter._parse_entry(entry)
            if job is not None:
                assert job.source == "remoteok"

    def test_missing_position_returns_none(self) -> None:
        """Entry with no position/title should be skipped."""
        entry = {"id": "999", "company": "Test", "url": "https://example.com"}
        result = RemoteOKAdapter._parse_entry(entry)
        assert result is None

    def test_missing_url_and_slug_returns_none(self) -> None:
        """Entry with neither url nor slug should be skipped."""
        entry = {"id": "999", "position": "Test Job"}
        result = RemoteOKAdapter._parse_entry(entry)
        assert result is None

    def test_empty_position_returns_none(self) -> None:
        entry = {"id": "999", "position": "  ", "url": "https://example.com"}
        result = RemoteOKAdapter._parse_entry(entry)
        assert result is None

    def test_missing_optional_fields(self) -> None:
        """Entry with only required fields should still parse."""
        entry = {
            "position": "Minimal Job",
            "url": "https://remoteok.com/remote-jobs/test",
        }
        job = RemoteOKAdapter._parse_entry(entry)
        assert job is not None
        assert job.title == "Minimal Job"
        assert job.company is None
        assert job.salary is None
        assert job.location is None
        assert job.description is None
        assert job.tags == []

    def test_salary_formatting_range(self) -> None:
        assert RemoteOKAdapter._format_salary(60000, 85000) == "$60,000 - $85,000"

    def test_salary_formatting_min_only(self) -> None:
        assert RemoteOKAdapter._format_salary(60000, 0) == "$60,000+"

    def test_salary_formatting_max_only(self) -> None:
        assert RemoteOKAdapter._format_salary(0, 85000) == "Up to $85,000"

    def test_salary_formatting_zero_both(self) -> None:
        assert RemoteOKAdapter._format_salary(0, 0) is None

    def test_salary_formatting_none(self) -> None:
        assert RemoteOKAdapter._format_salary(None, None) is None

    def test_fetch_jobs_with_fixture(
        self, adapter: RemoteOKAdapter, fixture_data: list[dict]
    ) -> None:
        """fetch_jobs() should skip legal notice and parse remaining entries."""
        mock_response = MagicMock()
        mock_response.json.return_value = fixture_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            jobs = adapter.fetch_jobs()

        assert len(jobs) > 0
        # Should be at most len(fixture_data) - 1 (minus the legal notice)
        assert len(jobs) <= len(fixture_data) - 1
        for job in jobs:
            assert isinstance(job, JobPosting)
            assert job.source == "remoteok"

    def test_fixture_has_entries(self, fixture_data: list[dict]) -> None:
        """Fixture should contain the legal notice + at least some jobs."""
        assert len(fixture_data) > 2
        # First element is legal notice
        assert "legal" in fixture_data[0]
        # Second element should be a job with position
        assert "position" in fixture_data[1]
