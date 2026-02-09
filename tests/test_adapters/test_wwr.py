"""Tests for WeWorkRemotely RSS adapter using saved fixture data."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import feedparser
import pytest

from scraper.adapters.rss import WeWorkRemotelyAdapter
from scraper.models import JobPosting

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "wwr_sample.xml"


@pytest.fixture
def fixture_xml() -> str:
    """Load the saved WWR RSS fixture as raw XML string."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def fixture_feed(fixture_xml: str) -> feedparser.FeedParserDict:
    """Parse the saved WWR RSS fixture with feedparser."""
    return feedparser.parse(fixture_xml)


@pytest.fixture
def adapter() -> WeWorkRemotelyAdapter:
    """Create a WeWorkRemotelyAdapter with default config."""
    config = {
        "name": "WeWorkRemotely",
        "url": "https://weworkremotely.com/remote-jobs.rss",
        "adapter": "rss",
        "enabled": True,
        "skip_location_match": True,
        "rate_limit_seconds": 2,
        "headers": {"User-Agent": "Mozilla/5.0"},
    }
    return WeWorkRemotelyAdapter(config)


class TestWeWorkRemotelyAdapter:
    """Tests for WeWorkRemotelyAdapter properties."""

    def test_name(self, adapter: WeWorkRemotelyAdapter) -> None:
        assert adapter.name == "We Work Remotely"

    def test_source_id(self, adapter: WeWorkRemotelyAdapter) -> None:
        assert adapter.source_id == "weworkremotely"


class TestTitleSplitting:
    """Tests for company extraction from title."""

    def test_company_colon_title(self) -> None:
        company, title = WeWorkRemotelyAdapter._split_title("Acme Corp: Senior Dev")
        assert company == "Acme Corp"
        assert title == "Senior Dev"

    def test_no_colon_returns_none_company(self) -> None:
        company, title = WeWorkRemotelyAdapter._split_title("Senior Developer")
        assert company is None
        assert title == "Senior Developer"

    def test_multiple_colons_splits_on_first(self) -> None:
        company, title = WeWorkRemotelyAdapter._split_title("Foo: Bar: Baz Role")
        assert company == "Foo"
        assert title == "Bar: Baz Role"

    def test_colon_at_end(self) -> None:
        company, title = WeWorkRemotelyAdapter._split_title("Company: ")
        # Falls back to full string since title would be empty
        assert company is None
        assert title == "Company: "

    def test_empty_company(self) -> None:
        company, title = WeWorkRemotelyAdapter._split_title(": Job Title")
        assert company is None
        assert title == "Job Title"

    def test_real_fixture_title(self) -> None:
        """Test with actual title format from fixture."""
        company, title = WeWorkRemotelyAdapter._split_title(
            "Remote Talent Cloud: Remote Customer Support - $20/hr - United States"
        )
        assert company == "Remote Talent Cloud"
        assert title == "Remote Customer Support - $20/hr - United States"


class TestParseEntry:
    """Tests for _parse_entry with feedparser entry dicts."""

    def test_parse_first_entry(self, fixture_feed: feedparser.FeedParserDict) -> None:
        """First fixture entry should parse into a valid JobPosting."""
        entry = fixture_feed.entries[0]
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert isinstance(job, JobPosting)
        assert job.source == "weworkremotely"
        assert len(job.id) == 32  # MD5 hex digest

    def test_title_extraction(self, fixture_feed: feedparser.FeedParserDict) -> None:
        """Company should be extracted from title before colon."""
        entry = fixture_feed.entries[0]
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert job.company == "Remote Talent Cloud"
        assert "Remote Customer Support" in job.title

    def test_url_mapping(self, fixture_feed: feedparser.FeedParserDict) -> None:
        entry = fixture_feed.entries[0]
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert "weworkremotely.com" in job.url

    def test_published_at_parsed(self, fixture_feed: feedparser.FeedParserDict) -> None:
        entry = fixture_feed.entries[0]
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert job.published_at is not None
        assert job.published_at.year == 2026

    def test_description_present(self, fixture_feed: feedparser.FeedParserDict) -> None:
        entry = fixture_feed.entries[0]
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert job.description is not None
        assert len(job.description) > 0

    def test_tags_from_category(self, fixture_feed: feedparser.FeedParserDict) -> None:
        """Tags should be extracted from RSS <category> element."""
        entry = fixture_feed.entries[0]
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert isinstance(job.tags, list)
        assert "Customer Support" in job.tags

    def test_location_from_region(self, fixture_feed: feedparser.FeedParserDict) -> None:
        """Location should come from the <region> field."""
        entry = fixture_feed.entries[0]
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert job.location == "Anywhere in the World"

    def test_source_always_weworkremotely(
        self, fixture_feed: feedparser.FeedParserDict
    ) -> None:
        """Every parsed entry must have source='weworkremotely'."""
        for entry in fixture_feed.entries:
            job = WeWorkRemotelyAdapter._parse_entry(entry)
            if job is not None:
                assert job.source == "weworkremotely"

    def test_all_entries_parse(self, fixture_feed: feedparser.FeedParserDict) -> None:
        """All fixture entries should parse without exceptions."""
        parsed = 0
        for entry in fixture_feed.entries:
            job = WeWorkRemotelyAdapter._parse_entry(entry)
            if job is not None:
                parsed += 1
        assert parsed == len(fixture_feed.entries)

    def test_salary_is_none(self, fixture_feed: feedparser.FeedParserDict) -> None:
        """WWR RSS doesn't provide structured salary data."""
        entry = fixture_feed.entries[0]
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert job.salary is None


class TestMissingFields:
    """Tests for handling missing or null fields."""

    def test_missing_title_returns_none(self) -> None:
        entry = {"link": "https://example.com/job"}
        result = WeWorkRemotelyAdapter._parse_entry(entry)
        assert result is None

    def test_empty_title_returns_none(self) -> None:
        entry = {"title": "  ", "link": "https://example.com/job"}
        result = WeWorkRemotelyAdapter._parse_entry(entry)
        assert result is None

    def test_missing_link_returns_none(self) -> None:
        entry = {"title": "Acme: Good Job"}
        result = WeWorkRemotelyAdapter._parse_entry(entry)
        assert result is None

    def test_minimal_entry_parses(self) -> None:
        """Entry with only title and link should still parse."""
        entry = {
            "title": "TestCo: Minimal Job",
            "link": "https://weworkremotely.com/remote-jobs/test",
        }
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert job.title == "Minimal Job"
        assert job.company == "TestCo"
        assert job.description is None
        assert job.tags == []
        assert job.location is None
        assert job.published_at is None

    def test_entry_without_colon_in_title(self) -> None:
        """Title without colon — no company extracted."""
        entry = {
            "title": "Senior Developer Position",
            "link": "https://weworkremotely.com/remote-jobs/test-2",
        }
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert job.title == "Senior Developer Position"
        assert job.company is None

    def test_invalid_date_handled(self) -> None:
        """Invalid date string should not crash, published_at should be None."""
        entry = {
            "title": "Corp: Some Role",
            "link": "https://weworkremotely.com/remote-jobs/test-3",
            "published": "not-a-date",
        }
        job = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job is not None
        assert job.published_at is None


class TestFetchJobs:
    """Tests for the full fetch_jobs() method with mocked HTTP."""

    def test_fetch_jobs_returns_postings(
        self, adapter: WeWorkRemotelyAdapter, fixture_xml: str
    ) -> None:
        """fetch_jobs() should return JobPosting objects from RSS."""
        mock_response = MagicMock()
        mock_response.text = fixture_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            jobs = adapter.fetch_jobs()

        assert len(jobs) > 0
        assert len(jobs) <= 10  # Fixture has 10 entries
        for job in jobs:
            assert isinstance(job, JobPosting)
            assert job.source == "weworkremotely"

    def test_fetch_jobs_handles_bozo_feed(
        self, adapter: WeWorkRemotelyAdapter
    ) -> None:
        """fetch_jobs() should handle malformed XML gracefully."""
        broken_xml = "<?xml version='1.0'?><rss><channel><item><title>Test: Job</title><link>https://example.com</link></item></channel></rss>"

        mock_response = MagicMock()
        mock_response.text = broken_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            jobs = adapter.fetch_jobs()

        # Should still parse what it can
        assert isinstance(jobs, list)

    def test_fixture_has_entries(self, fixture_xml: str) -> None:
        """Fixture should contain entries."""
        feed = feedparser.parse(fixture_xml)
        assert len(feed.entries) == 10


class TestIDGeneration:
    """Tests for consistent ID generation."""

    def test_same_input_same_id(self) -> None:
        """Same URL and title should produce same ID."""
        entry = {
            "title": "Corp: Developer",
            "link": "https://weworkremotely.com/remote-jobs/corp-developer",
        }
        job1 = WeWorkRemotelyAdapter._parse_entry(entry)
        job2 = WeWorkRemotelyAdapter._parse_entry(entry)
        assert job1 is not None and job2 is not None
        assert job1.id == job2.id

    def test_different_url_different_id(self) -> None:
        """Different URLs should produce different IDs."""
        entry1 = {
            "title": "Corp: Developer",
            "link": "https://weworkremotely.com/remote-jobs/corp-developer-1",
        }
        entry2 = {
            "title": "Corp: Developer",
            "link": "https://weworkremotely.com/remote-jobs/corp-developer-2",
        }
        job1 = WeWorkRemotelyAdapter._parse_entry(entry1)
        job2 = WeWorkRemotelyAdapter._parse_entry(entry2)
        assert job1 is not None and job2 is not None
        assert job1.id != job2.id
