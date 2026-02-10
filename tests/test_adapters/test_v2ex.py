"""Tests for V2EX hybrid adapter using saved fixture data."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scraper.adapters.hybrid import V2EXAdapter
from scraper.models import JobPosting

LISTING_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "v2ex_listing.html"
TOPIC_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "v2ex_topic.json"


@pytest.fixture
def listing_html() -> str:
    """Load the saved V2EX listing HTML fixture."""
    with open(LISTING_FIXTURE_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def topic_data() -> list[dict]:
    """Load the saved V2EX topic API fixture."""
    with open(TOPIC_FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def adapter() -> V2EXAdapter:
    """Create a V2EXAdapter with default config."""
    config = {
        "name": "V2EX",
        "url": "https://www.v2ex.com/go/remote",
        "api_base": "https://www.v2ex.com/api/topics/show.json",
        "adapter": "hybrid",
        "enabled": True,
        "skip_location_match": False,
        "rate_limit_seconds": 6,
        "headers": {"User-Agent": "Mozilla/5.0"},
    }
    return V2EXAdapter(config)


class TestV2EXAdapter:
    """Tests for V2EXAdapter."""

    def test_name(self, adapter: V2EXAdapter) -> None:
        assert adapter.name == "V2EX"

    def test_source_id(self, adapter: V2EXAdapter) -> None:
        assert adapter.source_id == "v2ex"

    # ------------------------------------------------------------------
    # HTML parsing tests
    # ------------------------------------------------------------------

    def test_parse_topic_ids_from_html(
        self, adapter: V2EXAdapter, listing_html: str
    ) -> None:
        """Should extract topic IDs from listing HTML."""
        topic_ids = adapter._parse_topic_ids(listing_html)
        assert isinstance(topic_ids, list)
        assert len(topic_ids) == 3
        assert 1001001 in topic_ids
        assert 1001002 in topic_ids
        assert 1001003 in topic_ids

    def test_parse_topic_ids_empty_html(self, adapter: V2EXAdapter) -> None:
        """Empty HTML should return empty list."""
        topic_ids = adapter._parse_topic_ids("<html><body></body></html>")
        assert topic_ids == []

    def test_parse_topic_ids_no_links(self, adapter: V2EXAdapter) -> None:
        """HTML without topic links should return empty list."""
        html = '<html><body><a href="/go/remote">remote</a></body></html>'
        topic_ids = adapter._parse_topic_ids(html)
        assert topic_ids == []

    def test_parse_topic_ids_deduplicates(self, adapter: V2EXAdapter) -> None:
        """Duplicate topic IDs should be deduplicated."""
        html = """
        <html><body>
        <span class="item_title"><a href="/t/1001001#reply0">Job 1</a></span>
        <span class="item_title"><a href="/t/1001001#reply0">Job 1 again</a></span>
        </body></html>
        """
        topic_ids = adapter._parse_topic_ids(html)
        assert len(topic_ids) == 1
        assert topic_ids[0] == 1001001

    # ------------------------------------------------------------------
    # API response parsing tests
    # ------------------------------------------------------------------

    def test_parse_topic_valid(self, topic_data: list[dict]) -> None:
        """Valid topic API response should parse into a JobPosting."""
        topic = topic_data[0]
        job = V2EXAdapter._parse_topic(topic)
        assert job is not None
        assert isinstance(job, JobPosting)
        assert job.title == "远程招聘：高级 AI 工程师，全球远程"
        assert job.source == "v2ex"
        assert job.company == "testuser1"
        assert "v2ex.com/t/1001001" in job.url
        assert job.description is not None
        assert len(job.id) == 32  # MD5 hex digest

    def test_parse_topic_url(self, topic_data: list[dict]) -> None:
        topic = topic_data[0]
        job = V2EXAdapter._parse_topic(topic)
        assert job is not None
        assert job.url == "https://www.v2ex.com/t/1001001"

    def test_parse_topic_member_as_company(self, topic_data: list[dict]) -> None:
        topic = topic_data[0]
        job = V2EXAdapter._parse_topic(topic)
        assert job is not None
        assert job.company == topic["member"]["username"]

    def test_parse_topic_tags_from_node(self, topic_data: list[dict]) -> None:
        topic = topic_data[0]
        job = V2EXAdapter._parse_topic(topic)
        assert job is not None
        assert isinstance(job.tags, list)
        assert "远程工作" in job.tags

    def test_parse_topic_created_timestamp(self, topic_data: list[dict]) -> None:
        topic = topic_data[0]
        job = V2EXAdapter._parse_topic(topic)
        assert job is not None
        assert job.published_at is not None

    def test_parse_topic_missing_title(self) -> None:
        """Topic with no title should return None."""
        topic = {"id": 999, "content": "test", "url": "https://v2ex.com/t/999"}
        result = V2EXAdapter._parse_topic(topic)
        assert result is None

    def test_parse_topic_empty_title(self) -> None:
        """Topic with empty title should return None."""
        topic = {
            "id": 999,
            "title": "  ",
            "content": "test",
            "url": "https://v2ex.com/t/999",
        }
        result = V2EXAdapter._parse_topic(topic)
        assert result is None

    def test_parse_topic_missing_id(self) -> None:
        """Topic with no id should return None."""
        topic = {"title": "Test Job", "content": "test"}
        result = V2EXAdapter._parse_topic(topic)
        assert result is None

    def test_parse_topic_minimal_fields(self) -> None:
        """Topic with only required fields should still parse."""
        topic = {
            "id": 999,
            "title": "Minimal Job Post",
            "url": "https://www.v2ex.com/t/999",
            "created": 1736912400,
        }
        job = V2EXAdapter._parse_topic(topic)
        assert job is not None
        assert job.title == "Minimal Job Post"
        assert job.company is None
        assert job.description is None
        assert job.tags == []

    def test_parse_topic_no_member(self) -> None:
        """Topic without member field should have company=None."""
        topic = {
            "id": 999,
            "title": "Job Post",
            "url": "https://www.v2ex.com/t/999",
            "created": 1736912400,
        }
        job = V2EXAdapter._parse_topic(topic)
        assert job is not None
        assert job.company is None

    def test_parse_topic_no_node(self) -> None:
        """Topic without node field should have empty tags."""
        topic = {
            "id": 999,
            "title": "Job Post",
            "url": "https://www.v2ex.com/t/999",
            "created": 1736912400,
        }
        job = V2EXAdapter._parse_topic(topic)
        assert job is not None
        assert job.tags == []

    def test_source_always_v2ex(self, topic_data: list[dict]) -> None:
        """Every parsed topic must have source='v2ex'."""
        for topic in topic_data:
            job = V2EXAdapter._parse_topic(topic)
            if job is not None:
                assert job.source == "v2ex"

    # ------------------------------------------------------------------
    # Integration / fetch_jobs tests
    # ------------------------------------------------------------------

    async def test_fetch_jobs_full_pipeline(
        self,
        adapter: V2EXAdapter,
        listing_html: str,
        topic_data: list[dict],
    ) -> None:
        """fetch_jobs() should fetch listing HTML, extract IDs, then call API for each."""
        # Mock the listing HTML response
        listing_response = MagicMock()
        listing_response.text = listing_html
        listing_response.raise_for_status = MagicMock()

        # Mock the topic API response (returns for any topic ID)
        topic_response = MagicMock()
        topic_response.json.return_value = topic_data
        topic_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        # First call is listing HTML, subsequent calls are API topic fetches
        mock_client.get.side_effect = [
            listing_response,
            topic_response,
            topic_response,
            topic_response,
        ]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_delay", new_callable=AsyncMock):
                jobs = await adapter.fetch_jobs()

        assert len(jobs) > 0
        # 3 topic IDs from listing, each returns 1 topic from API
        assert len(jobs) == 3
        for job in jobs:
            assert isinstance(job, JobPosting)
            assert job.source == "v2ex"

        # Verify listing URL was called first
        first_call = mock_client.get.call_args_list[0]
        assert "v2ex.com/go/remote" in str(first_call)

    async def test_fetch_jobs_api_error_skips_topic(
        self, adapter: V2EXAdapter, listing_html: str, topic_data: list[dict]
    ) -> None:
        """If API call for a single topic fails, other topics should still be processed."""
        import httpx

        listing_response = MagicMock()
        listing_response.text = listing_html
        listing_response.raise_for_status = MagicMock()

        topic_response = MagicMock()
        topic_response.json.return_value = topic_data
        topic_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        # Listing OK, first topic fails, second/third topics OK
        mock_client.get.side_effect = [
            listing_response,
            httpx.HTTPStatusError("429 Too Many Requests", request=MagicMock(), response=MagicMock()),
            topic_response,
            topic_response,
        ]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_delay", new_callable=AsyncMock):
                jobs = await adapter.fetch_jobs()

        # Should have 2 jobs (one topic errored out)
        assert len(jobs) == 2

    async def test_fetch_jobs_empty_listing(self, adapter: V2EXAdapter) -> None:
        """Empty listing should return empty list without making API calls."""
        listing_response = MagicMock()
        listing_response.text = "<html><body></body></html>"
        listing_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = listing_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch.object(adapter, "_get_client", return_value=mock_client):
            jobs = await adapter.fetch_jobs()

        assert jobs == []
        # Only the listing call, no API calls
        assert mock_client.get.call_count == 1

    async def test_rate_limiting_between_api_calls(
        self,
        adapter: V2EXAdapter,
        listing_html: str,
        topic_data: list[dict],
    ) -> None:
        """_delay() should be called between each API call."""
        listing_response = MagicMock()
        listing_response.text = listing_html
        listing_response.raise_for_status = MagicMock()

        topic_response = MagicMock()
        topic_response.json.return_value = topic_data
        topic_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            listing_response,
            topic_response,
            topic_response,
            topic_response,
        ]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        mock_delay = AsyncMock()

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with patch.object(adapter, "_delay", mock_delay):
                await adapter.fetch_jobs()

        # _delay should be called before each API topic fetch (3 times)
        assert mock_delay.call_count == 3

    # ------------------------------------------------------------------
    # Fixture integrity tests
    # ------------------------------------------------------------------

    def test_listing_fixture_has_topics(self, listing_html: str) -> None:
        """Listing fixture should contain topic links."""
        assert "/t/1001001" in listing_html
        assert "/t/1001002" in listing_html
        assert "/t/1001003" in listing_html

    def test_topic_fixture_has_required_fields(self, topic_data: list[dict]) -> None:
        """Topic fixture should contain required API fields."""
        assert len(topic_data) > 0
        topic = topic_data[0]
        assert "id" in topic
        assert "title" in topic
        assert "content" in topic
        assert "url" in topic
        assert "member" in topic
        assert "node" in topic
        assert "created" in topic
        assert "username" in topic["member"]
        assert "name" in topic["node"]
        assert "title" in topic["node"]
