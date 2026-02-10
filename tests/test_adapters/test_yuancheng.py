"""Tests for YuanchengAdapter (远程.work) HTML scraping adapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from scraper.adapters.html import YuanchengAdapter
from scraper.models import JobPosting

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "yuancheng_listing.html"


@pytest.fixture
def fixture_html() -> str:
    """Load the saved yuancheng listing HTML fixture."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def adapter() -> YuanchengAdapter:
    """Create a YuanchengAdapter with default config."""
    config = {
        "name": "远程.work",
        "url": "https://yuancheng.work/jobs/",
        "adapter": "html",
        "enabled": False,
        "skip_location_match": False,
        "rate_limit_seconds": 2,
        "headers": {"User-Agent": "Mozilla/5.0"},
    }
    return YuanchengAdapter(config)


class TestYuanchengAdapterProperties:
    """Tests for YuanchengAdapter properties."""

    def test_name(self, adapter: YuanchengAdapter) -> None:
        assert adapter.name == "远程.work"

    def test_source_id(self, adapter: YuanchengAdapter) -> None:
        assert adapter.source_id == "yuancheng"


class TestParseListings:
    """Tests for _parse_listings HTML parsing."""

    def test_parse_fixture_returns_jobs(
        self, adapter: YuanchengAdapter, fixture_html: str
    ) -> None:
        """Fixture should produce valid job listings."""
        jobs = adapter._parse_listings(fixture_html)
        # Fixture has 5 articles, but #5 has empty title → 4 valid jobs
        assert len(jobs) == 4

    def test_all_jobs_are_jobposting(
        self, adapter: YuanchengAdapter, fixture_html: str
    ) -> None:
        jobs = adapter._parse_listings(fixture_html)
        for job in jobs:
            assert isinstance(job, JobPosting)

    def test_all_jobs_have_source_yuancheng(
        self, adapter: YuanchengAdapter, fixture_html: str
    ) -> None:
        jobs = adapter._parse_listings(fixture_html)
        for job in jobs:
            assert job.source == "yuancheng"

    def test_empty_html_returns_empty(self, adapter: YuanchengAdapter) -> None:
        jobs = adapter._parse_listings("<html><body></body></html>")
        assert jobs == []

    def test_no_articles_returns_empty(self, adapter: YuanchengAdapter) -> None:
        html = '<html><body><div class="job-listings"></div></body></html>'
        jobs = adapter._parse_listings(html)
        assert jobs == []


class TestParseArticle:
    """Tests for _parse_article with individual article elements."""

    def test_first_article_title(self, fixture_html: str) -> None:
        """First article should parse title correctly."""
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[0]
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.title == "高级 AI 算法工程师 - 全球远程"

    def test_first_article_company(self, fixture_html: str) -> None:
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[0]
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.company == "DeepTech AI"

    def test_first_article_url(self, fixture_html: str) -> None:
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[0]
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.url == "https://yuancheng.work/jobs/10001/"

    def test_first_article_location(self, fixture_html: str) -> None:
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[0]
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.location == "远程"

    def test_first_article_published_at(self, fixture_html: str) -> None:
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[0]
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.published_at is not None
        assert job.published_at.year == 2026
        assert job.published_at.month == 2
        assert job.published_at.day == 1

    def test_first_article_tags_include_job_type(self, fixture_html: str) -> None:
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[0]
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert "全职" in job.tags

    def test_third_article_english_title(self, fixture_html: str) -> None:
        """Third article has English title."""
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[2]
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.title == "Machine Learning Engineer - LLM Fine-tuning"
        assert job.company == "NovaTech Solutions"
        assert job.location == "Remote"

    def test_fourth_article_empty_company(self, fixture_html: str) -> None:
        """Fourth article has empty <strong> for company → should be None."""
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[3]
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.company is None

    def test_fifth_article_empty_title_returns_none(self, fixture_html: str) -> None:
        """Fifth article has empty <h3> → should return None."""
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[4]
        job = YuanchengAdapter._parse_article(article)
        assert job is None

    def test_salary_is_none(self, fixture_html: str) -> None:
        """Listing page doesn't provide salary data."""
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[0]
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.salary is None

    def test_description_is_none(self, fixture_html: str) -> None:
        """Listing page doesn't provide description."""
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[0]
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.description is None


class TestMissingFields:
    """Tests for handling missing or malformed fields."""

    def test_article_without_h3_returns_none(self) -> None:
        html = '<article class="job_listing"><a href="/jobs/1/" class="job-permalink"></a></article>'
        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article")
        result = YuanchengAdapter._parse_article(article)
        assert result is None

    def test_article_without_permalink_returns_none(self) -> None:
        html = '<article class="job_listing"><div class="position"><h3>Test Job</h3></div></article>'
        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article")
        result = YuanchengAdapter._parse_article(article)
        assert result is None

    def test_article_minimal_fields_parses(self) -> None:
        """Article with only title and permalink should parse."""
        html = """
        <article class="job_listing">
          <a href="https://yuancheng.work/jobs/999/" class="job-permalink">
            <div class="position"><h3>Minimal Job</h3></div>
          </a>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article")
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.title == "Minimal Job"
        assert job.company is None
        assert job.location is None
        assert job.published_at is None
        assert job.tags == []

    def test_article_invalid_datetime(self) -> None:
        """Invalid datetime should not crash."""
        html = """
        <article class="job_listing">
          <a href="https://yuancheng.work/jobs/999/" class="job-permalink">
            <div class="position"><h3>Bad Date Job</h3></div>
          </a>
          <ul class="meta">
            <li class="date"><time datetime="not-a-date">not-a-date</time></li>
          </ul>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article")
        job = YuanchengAdapter._parse_article(article)
        assert job is not None
        assert job.published_at is None


class TestIDGeneration:
    """Tests for consistent ID generation."""

    def test_same_input_same_id(self, fixture_html: str) -> None:
        """Same article should produce same ID."""
        soup = BeautifulSoup(fixture_html, "html.parser")
        article = soup.find_all("article", class_="job_listing")[0]
        job1 = YuanchengAdapter._parse_article(article)
        job2 = YuanchengAdapter._parse_article(article)
        assert job1 is not None and job2 is not None
        assert job1.id == job2.id
        assert len(job1.id) == 32  # MD5 hex digest

    def test_different_articles_different_ids(self, fixture_html: str) -> None:
        soup = BeautifulSoup(fixture_html, "html.parser")
        articles = soup.find_all("article", class_="job_listing")
        job1 = YuanchengAdapter._parse_article(articles[0])
        job2 = YuanchengAdapter._parse_article(articles[1])
        assert job1 is not None and job2 is not None
        assert job1.id != job2.id


class TestFetchJobs:
    """Tests for the full fetch_jobs() method with mocked HTTP."""

    async def test_fetch_jobs_returns_postings(
        self, adapter: YuanchengAdapter, fixture_html: str
    ) -> None:
        """fetch_jobs() should return JobPosting objects from HTML."""
        mock_response = MagicMock()
        mock_response.text = fixture_html
        mock_response.raise_for_status = MagicMock()
        mock_response.url = "https://yuancheng.work/jobs/"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch.object(adapter, "_get_client", return_value=mock_client):
            jobs = await adapter.fetch_jobs()

        assert len(jobs) == 4
        for job in jobs:
            assert isinstance(job, JobPosting)
            assert job.source == "yuancheng"

    async def test_fetch_jobs_redirect_returns_empty(
        self, adapter: YuanchengAdapter
    ) -> None:
        """If site redirects to arc.dev, should return empty list."""
        mock_response = MagicMock()
        mock_response.text = "<html><body>Arc.dev</body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_response.url = "https://arc.dev/remote-jobs"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch.object(adapter, "_get_client", return_value=mock_client):
            jobs = await adapter.fetch_jobs()

        assert jobs == []

    async def test_fetch_jobs_http_error_returns_empty(
        self, adapter: YuanchengAdapter
    ) -> None:
        """HTTP errors should return empty list, not crash."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error", request=MagicMock(), response=MagicMock()
        )
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch.object(adapter, "_get_client", return_value=mock_client):
            jobs = await adapter.fetch_jobs()

        assert jobs == []

    async def test_fetch_jobs_connection_error_returns_empty(
        self, adapter: YuanchengAdapter
    ) -> None:
        """Connection errors should return empty list, not crash."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch.object(adapter, "_get_client", return_value=mock_client):
            jobs = await adapter.fetch_jobs()

        assert jobs == []

    async def test_fetch_jobs_empty_page_returns_empty(
        self, adapter: YuanchengAdapter
    ) -> None:
        """Empty HTML page should return empty list."""
        mock_response = MagicMock()
        mock_response.text = "<html><body><div class='job-listings'></div></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_response.url = "https://yuancheng.work/jobs/"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch.object(adapter, "_get_client", return_value=mock_client):
            jobs = await adapter.fetch_jobs()

        assert jobs == []


class TestFixtureIntegrity:
    """Tests for fixture file integrity."""

    def test_fixture_file_exists(self) -> None:
        assert FIXTURE_PATH.exists()

    def test_fixture_has_articles(self, fixture_html: str) -> None:
        soup = BeautifulSoup(fixture_html, "html.parser")
        articles = soup.find_all("article", class_="job_listing")
        assert len(articles) == 5

    def test_fixture_has_valid_and_invalid_articles(self, fixture_html: str) -> None:
        """Fixture should contain both valid and invalid (empty title) articles."""
        soup = BeautifulSoup(fixture_html, "html.parser")
        articles = soup.find_all("article", class_="job_listing")
        valid = 0
        invalid = 0
        for article in articles:
            job = YuanchengAdapter._parse_article(article)
            if job is not None:
                valid += 1
            else:
                invalid += 1
        assert valid == 4
        assert invalid == 1
