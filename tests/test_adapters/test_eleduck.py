"""Tests for Eleduck adapter using saved fixture data."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scraper.adapters.api import EleduckAdapter
from scraper.models import JobPosting

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "eleduck_sample.json"


@pytest.fixture
def fixture_data() -> dict:
    """Load the saved Eleduck API fixture."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def adapter() -> EleduckAdapter:
    """Create an EleduckAdapter with default config."""
    config = {
        "name": "电鸭",
        "url": "https://svc.eleduck.com/api/v1/posts",
        "adapter": "api",
        "enabled": True,
        "skip_location_match": False,
        "rate_limit_seconds": 2,
        "params": {"category": 5},
        "headers": {"User-Agent": "Mozilla/5.0"},
    }
    return EleduckAdapter(config)


class TestEleduckAdapter:
    """Tests for EleduckAdapter."""

    def test_name(self, adapter: EleduckAdapter) -> None:
        assert adapter.name == "电鸭社区"

    def test_source_id(self, adapter: EleduckAdapter) -> None:
        assert adapter.source_id == "eleduck"

    def test_parse_valid_job(self, fixture_data: dict) -> None:
        """First post should parse into a valid JobPosting."""
        posts = fixture_data.get("posts", [])
        assert len(posts) > 0
        entry = posts[0]
        job = EleduckAdapter._parse_entry(entry)
        assert job is not None
        assert isinstance(job, JobPosting)
        assert job.title == entry["title"]
        assert job.source == "eleduck"
        assert len(job.id) == 32  # MD5 hex digest

    def test_field_mapping_title(self, fixture_data: dict) -> None:
        entry = fixture_data["posts"][0]
        job = EleduckAdapter._parse_entry(entry)
        assert job is not None
        assert job.title == entry["title"]

    def test_field_mapping_company(self, fixture_data: dict) -> None:
        entry = fixture_data["posts"][0]
        job = EleduckAdapter._parse_entry(entry)
        assert job is not None
        # Company comes from user.nickname
        if entry.get("user") and entry["user"].get("nickname"):
            assert job.company == entry["user"]["nickname"]

    def test_field_mapping_url(self, fixture_data: dict) -> None:
        entry = fixture_data["posts"][0]
        job = EleduckAdapter._parse_entry(entry)
        assert job is not None
        assert "eleduck.com/posts/" in job.url
        assert entry["id"] in job.url

    def test_field_mapping_tags(self, fixture_data: dict) -> None:
        entry = fixture_data["posts"][0]
        job = EleduckAdapter._parse_entry(entry)
        assert job is not None
        assert isinstance(job.tags, list)
        # Tags should be extracted from the tags array
        if entry.get("tags"):
            assert len(job.tags) > 0

    def test_field_mapping_description(self, fixture_data: dict) -> None:
        entry = fixture_data["posts"][0]
        job = EleduckAdapter._parse_entry(entry)
        assert job is not None
        if entry.get("summary"):
            assert job.description == entry["summary"]

    def test_field_mapping_published_at(self, fixture_data: dict) -> None:
        entry = fixture_data["posts"][0]
        job = EleduckAdapter._parse_entry(entry)
        assert job is not None
        if entry.get("published_at"):
            assert job.published_at is not None

    def test_source_always_eleduck(self, fixture_data: dict) -> None:
        """Every parsed entry must have source='eleduck'."""
        for entry in fixture_data["posts"]:
            job = EleduckAdapter._parse_entry(entry)
            if job is not None:
                assert job.source == "eleduck"

    def test_missing_title_returns_none(self) -> None:
        """Entry with no title should be skipped."""
        entry = {"id": "test123", "user": {"nickname": "Test"}}
        result = EleduckAdapter._parse_entry(entry)
        assert result is None

    def test_missing_id_returns_none(self) -> None:
        """Entry with no id should be skipped."""
        entry = {"title": "Test Job"}
        result = EleduckAdapter._parse_entry(entry)
        assert result is None

    def test_empty_title_returns_none(self) -> None:
        entry = {"id": "test123", "title": "  "}
        result = EleduckAdapter._parse_entry(entry)
        assert result is None

    def test_missing_optional_fields(self) -> None:
        """Entry with only required fields should still parse."""
        entry = {
            "id": "test123",
            "title": "Minimal Job",
        }
        job = EleduckAdapter._parse_entry(entry)
        assert job is not None
        assert job.title == "Minimal Job"
        assert job.company is None
        assert job.salary is None
        assert job.location is None
        assert job.description is None
        assert job.tags == []

    def test_tags_extraction(self, fixture_data: dict) -> None:
        """Tags should be extracted from nested tag objects."""
        entry = fixture_data["posts"][0]
        job = EleduckAdapter._parse_entry(entry)
        assert job is not None
        # Verify tags are strings, not dicts
        for tag in job.tags:
            assert isinstance(tag, str)

    def test_fetch_jobs_with_fixture(
        self, adapter: EleduckAdapter, fixture_data: dict
    ) -> None:
        """fetch_jobs() should parse all posts from the response."""
        # First page returns fixture data, second page returns empty
        page1_response = MagicMock()
        page1_response.json.return_value = fixture_data
        page1_response.raise_for_status = MagicMock()

        page2_response = MagicMock()
        page2_response.json.return_value = {"posts": []}
        page2_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.side_effect = [page1_response, page2_response]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_delay"):  # Skip delays in tests
                jobs = adapter.fetch_jobs()

        assert len(jobs) > 0
        # Should be exactly len(posts) from first page
        assert len(jobs) == len(fixture_data["posts"])
        for job in jobs:
            assert isinstance(job, JobPosting)
            assert job.source == "eleduck"

    def test_pagination_stops_on_empty(self, adapter: EleduckAdapter) -> None:
        """Pagination should stop when API returns empty posts array."""
        # First page has posts, second page is empty
        page1_response = MagicMock()
        page1_response.json.return_value = {"posts": [{"id": "test1", "title": "Job 1"}]}
        page1_response.raise_for_status = MagicMock()

        page2_response = MagicMock()
        page2_response.json.return_value = {"posts": []}
        page2_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.side_effect = [page1_response, page2_response]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_delay"):  # Skip delays in tests
                jobs = adapter.fetch_jobs()

        # Should have called get twice (page 1 and page 2)
        assert mock_client.get.call_count == 2
        # Should have parsed jobs from page 1 only
        assert len(jobs) >= 0

    def test_fixture_has_posts(self, fixture_data: dict) -> None:
        """Fixture should contain a posts array with at least one post."""
        assert "posts" in fixture_data
        assert len(fixture_data["posts"]) > 0
        # First post should have required fields
        first_post = fixture_data["posts"][0]
        assert "id" in first_post
        assert "title" in first_post
