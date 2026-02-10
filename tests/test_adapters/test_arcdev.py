"""Tests for Arc.dev adapter using saved fixture data."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from scraper.adapters.browser import ArcDevAdapter
from scraper.models import JobPosting

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "arcdev_sample.json"


@pytest.fixture
def fixture_data() -> list[dict]:
    """Load the saved Arc.dev fixture."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def adapter() -> ArcDevAdapter:
    """Create an ArcDevAdapter with default config."""
    config = {
        "name": "Arc.dev",
        "url": "https://arc.dev/remote-jobs",
        "adapter": "browser",
        "enabled": True,
        "skip_location_match": True,
        "rate_limit_seconds": 2,
        "headers": {"User-Agent": "Mozilla/5.0"},
    }
    return ArcDevAdapter(config)


class TestArcDevAdapterProperties:
    """Tests for adapter properties."""

    def test_name(self, adapter: ArcDevAdapter) -> None:
        assert adapter.name == "Arc.dev"

    def test_source_id(self, adapter: ArcDevAdapter) -> None:
        assert adapter.source_id == "arcdev"


class TestArcDevParseEntry:
    """Tests for _parse_entry static method."""

    def test_parse_valid_contract_job(self, fixture_data: list[dict]) -> None:
        """First fixture entry (contract with hourly rate) should parse."""
        entry = fixture_data[0]
        job = ArcDevAdapter._parse_entry(entry)
        assert job is not None
        assert isinstance(job, JobPosting)
        assert job.title == "React + Node Developer for Prototype"
        assert job.source == "arcdev"
        assert len(job.id) == 32  # MD5 hex digest

    def test_parse_valid_permanent_job(self, fixture_data: list[dict]) -> None:
        """Second fixture entry (permanent with annual salary) should parse."""
        entry = fixture_data[1]
        job = ArcDevAdapter._parse_entry(entry)
        assert job is not None
        assert job.title == "PPC and data entry"
        assert job.source == "arcdev"

    def test_field_mapping_url(self, fixture_data: list[dict]) -> None:
        """URL should be constructed from urlString and randomKey."""
        entry = fixture_data[0]
        job = ArcDevAdapter._parse_entry(entry)
        assert job is not None
        assert "arc.dev/remote-jobs/details/" in job.url
        assert "o1ati8xjlv" in job.url
        assert "react-node-developer-for-prototype" in job.url

    def test_field_mapping_tags_from_categories(self, fixture_data: list[dict]) -> None:
        """Tags should include category names + jobType + experienceLevel."""
        entry = fixture_data[0]
        job = ArcDevAdapter._parse_entry(entry)
        assert job is not None
        assert "Node.js" in job.tags
        assert "React" in job.tags
        assert "contract" in job.tags
        assert "mid" in job.tags

    def test_field_mapping_published_at(self, fixture_data: list[dict]) -> None:
        """postedAt epoch should be parsed into published_at datetime."""
        entry = fixture_data[0]
        job = ArcDevAdapter._parse_entry(entry)
        assert job is not None
        assert job.published_at is not None

    def test_source_always_arcdev(self, fixture_data: list[dict]) -> None:
        """Every parsed entry must have source='arcdev'."""
        for entry in fixture_data:
            job = ArcDevAdapter._parse_entry(entry)
            if job is not None:
                assert job.source == "arcdev"

    def test_missing_title_returns_none(self) -> None:
        """Entry with no title should be skipped."""
        entry = {
            "randomKey": "abc123",
            "urlString": "test-job",
            "postedAt": 1770000000,
        }
        result = ArcDevAdapter._parse_entry(entry)
        assert result is None

    def test_empty_title_returns_none(self) -> None:
        entry = {
            "title": "  ",
            "randomKey": "abc123",
            "urlString": "test-job",
        }
        result = ArcDevAdapter._parse_entry(entry)
        assert result is None

    def test_missing_random_key_returns_none(self) -> None:
        """Entry with no randomKey should be skipped."""
        entry = {
            "title": "Test Job",
            "urlString": "test-job",
        }
        result = ArcDevAdapter._parse_entry(entry)
        assert result is None

    def test_missing_url_string_returns_none(self) -> None:
        """Entry with no urlString should be skipped."""
        entry = {
            "title": "Test Job",
            "randomKey": "abc123",
        }
        result = ArcDevAdapter._parse_entry(entry)
        assert result is None

    def test_minimal_entry_parses(self) -> None:
        """Entry with only required fields should still parse."""
        entry = {
            "title": "Minimal Job",
            "randomKey": "min123",
            "urlString": "minimal-job",
        }
        job = ArcDevAdapter._parse_entry(entry)
        assert job is not None
        assert job.title == "Minimal Job"
        assert job.company is None
        assert job.salary is None
        assert job.description is None

    def test_location_few_countries(self, fixture_data: list[dict]) -> None:
        """Entry with <= 3 required countries should list them."""
        entry = fixture_data[3]  # Has ["TT", "PE", "BR"]
        job = ArcDevAdapter._parse_entry(entry)
        assert job is not None
        assert job.location is not None
        assert "TT" in job.location
        assert "PE" in job.location
        assert "BR" in job.location

    def test_location_remote_anywhere(self, fixture_data: list[dict]) -> None:
        """Entry with no required countries should show 'Remote anywhere'."""
        entry = fixture_data[2]  # Foundational AI Engineer, no countries
        job = ArcDevAdapter._parse_entry(entry)
        assert job is not None
        assert "Remote anywhere" in job.location

    def test_location_with_timezone(self, fixture_data: list[dict]) -> None:
        """Entry with a timezone preference should include it."""
        entry = fixture_data[0]  # Perth timezone
        job = ArcDevAdapter._parse_entry(entry)
        assert job is not None
        assert "TZ: Perth" in job.location

    def test_fixture_has_entries(self, fixture_data: list[dict]) -> None:
        """Fixture should contain multiple jobs."""
        assert len(fixture_data) >= 3


class TestArcDevSalaryFormatting:
    """Tests for _format_salary static method."""

    def test_annual_range(self) -> None:
        entry = {"minAnnualSalary": 40000, "maxAnnualSalary": 80000}
        assert ArcDevAdapter._format_salary(entry) == "US$40,000 - $80,000/yr"

    def test_annual_min_only(self) -> None:
        entry = {"minAnnualSalary": 50000, "maxAnnualSalary": None}
        assert ArcDevAdapter._format_salary(entry) == "US$50,000+/yr"

    def test_annual_max_only(self) -> None:
        entry = {"minAnnualSalary": None, "maxAnnualSalary": 100000}
        assert ArcDevAdapter._format_salary(entry) == "Up to US$100,000/yr"

    def test_hourly_range(self) -> None:
        entry = {"minHourlyRate": 30, "maxHourlyRate": 45}
        assert ArcDevAdapter._format_salary(entry) == "US$30 - $45/hr"

    def test_hourly_min_only(self) -> None:
        entry = {"minHourlyRate": 25, "maxHourlyRate": None}
        assert ArcDevAdapter._format_salary(entry) == "US$25+/hr"

    def test_hourly_max_only(self) -> None:
        entry = {"minHourlyRate": None, "maxHourlyRate": 55}
        assert ArcDevAdapter._format_salary(entry) == "Up to US$55/hr"

    def test_no_salary(self) -> None:
        entry = {}
        assert ArcDevAdapter._format_salary(entry) is None

    def test_annual_takes_precedence_over_hourly(self) -> None:
        """When both annual and hourly exist, annual should be used."""
        entry = {
            "minAnnualSalary": 60000,
            "maxAnnualSalary": 90000,
            "minHourlyRate": 30,
            "maxHourlyRate": 45,
        }
        result = ArcDevAdapter._format_salary(entry)
        assert "/yr" in result


class TestArcDevLocationFormatting:
    """Tests for _format_location static method."""

    def test_no_countries_no_tz(self) -> None:
        entry = {"requiredCountries": [], "timeZone": None}
        assert ArcDevAdapter._format_location(entry) == "Remote anywhere"

    def test_no_countries_with_tz(self) -> None:
        entry = {"requiredCountries": [], "timeZone": "Perth"}
        result = ArcDevAdapter._format_location(entry)
        assert "Remote anywhere" in result
        assert "TZ: Perth" in result

    def test_few_countries(self) -> None:
        entry = {"requiredCountries": ["US", "CA"]}
        assert ArcDevAdapter._format_location(entry) == "US, CA"

    def test_many_countries(self) -> None:
        entry = {"requiredCountries": ["US", "CA", "BR", "MX", "AR"]}
        assert "5 countries" in ArcDevAdapter._format_location(entry)

    def test_no_preference_tz_ignored(self) -> None:
        entry = {"requiredCountries": [], "timeZone": "no-preference"}
        assert ArcDevAdapter._format_location(entry) == "Remote anywhere"


class TestArcDevFetchJobs:
    """Tests for fetch_jobs using mocked Playwright."""

    async def test_fetch_jobs_with_fixture(
        self, adapter: ArcDevAdapter, fixture_data: list[dict]
    ) -> None:
        """fetch_jobs() should use _extract_next_data and parse all entries."""
        with patch.object(
            adapter, "_extract_next_data", new_callable=AsyncMock, return_value=fixture_data
        ):
            jobs = await adapter.fetch_jobs()

        assert len(jobs) > 0
        assert len(jobs) <= len(fixture_data)
        for job in jobs:
            assert isinstance(job, JobPosting)
            assert job.source == "arcdev"

    async def test_fetch_jobs_empty(self, adapter: ArcDevAdapter) -> None:
        """fetch_jobs() should handle empty response."""
        with patch.object(
            adapter, "_extract_next_data", new_callable=AsyncMock, return_value=[]
        ):
            jobs = await adapter.fetch_jobs()

        assert jobs == []

    async def test_fetch_jobs_skips_invalid(self, adapter: ArcDevAdapter) -> None:
        """fetch_jobs() should skip entries that fail validation."""
        bad_data = [
            {"title": "", "randomKey": "x", "urlString": "x"},  # empty title
            {"title": "Valid Job", "randomKey": "abc", "urlString": "valid-job"},
        ]
        with patch.object(
            adapter, "_extract_next_data", new_callable=AsyncMock, return_value=bad_data
        ):
            jobs = await adapter.fetch_jobs()

        assert len(jobs) == 1
        assert jobs[0].title == "Valid Job"
