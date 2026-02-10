"""HTML scraping adapters using BeautifulSoup.

远程.work (yuancheng.work) is a WordPress-based Chinese remote job board.
The domain currently redirects to arc.dev, so this adapter is disabled by default.
When the site is available, it scrapes job listings from the HTML listing page.
"""

from __future__ import annotations

from datetime import datetime

from bs4 import BeautifulSoup
from loguru import logger

from scraper.adapters.base import BaseAdapter
from scraper.models import JobPosting


class YuanchengAdapter(BaseAdapter):
    """Adapter for 远程.work (yuancheng.work) WordPress job board.

    Scrapes job listings from HTML using BeautifulSoup.
    The site uses WP Job Manager plugin with <article class="job_listing"> elements.

    NOTE: yuancheng.work currently redirects to arc.dev/remote-jobs.
    This adapter is disabled by default until the site becomes available again.

    Config keys:
        url:  Listing page URL (default: https://yuancheng.work/jobs/)
        rate_limit_seconds: Delay between requests (default: 2)
    """

    @property
    def name(self) -> str:
        return "远程.work"

    @property
    def source_id(self) -> str:
        return "yuancheng"

    async def fetch_jobs(self) -> list[JobPosting]:
        """Fetch jobs by scraping the HTML listing page.

        Returns:
            List of parsed JobPosting objects. Returns [] on errors or empty pages.
        """
        url = self.config.get("url", "https://yuancheng.work/jobs/")
        logger.info("Fetching jobs from {} ({})", self.name, url)

        try:
            async with self._get_client() as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                html = response.text
        except Exception:
            logger.exception("Failed to fetch HTML from {}", url)
            return []

        # Detect if we were redirected away from the expected domain
        final_url = str(response.url) if hasattr(response, "url") else url
        if "yuancheng.work" not in final_url and "xn--wtqx46b.work" not in final_url:
            logger.warning(
                "Redirected away from yuancheng.work to {} — site may be unavailable",
                final_url,
            )
            return []

        jobs = self._parse_listings(html)
        logger.info("Parsed {} valid jobs from {}", len(jobs), self.name)
        return jobs

    def _parse_listings(self, html: str) -> list[JobPosting]:
        """Parse job listings from WordPress HTML.

        Extracts job data from <article class="job_listing"> elements,
        which is the standard WP Job Manager markup.

        Args:
            html: Raw HTML string from the listing page.

        Returns:
            List of parsed JobPosting objects.
        """
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.find_all("article", class_="job_listing")

        if not articles:
            logger.info("No job_listing articles found in HTML")
            return []

        logger.debug("Found {} job_listing articles", len(articles))

        jobs: list[JobPosting] = []
        for article in articles:
            try:
                job = self._parse_article(article)
                if job is not None:
                    jobs.append(job)
            except Exception:
                post_id = article.get("data-post-id", "unknown")
                logger.exception(
                    "Failed to parse yuancheng article post_id={}", post_id
                )

        return jobs

    @staticmethod
    def _parse_article(article) -> JobPosting | None:
        """Parse a single <article class="job_listing"> into a JobPosting.

        Args:
            article: BeautifulSoup Tag for the article element.

        Returns:
            JobPosting or None if the article lacks required fields.
        """
        # Extract title from <h3> inside .position
        title_tag = article.find("h3")
        title = (title_tag.get_text(strip=True) if title_tag else "").strip()
        if not title:
            post_id = article.get("data-post-id", "unknown")
            logger.debug("Skipping article with no title: post_id={}", post_id)
            return None

        # Extract URL from the permalink <a>
        link_tag = article.find("a", class_="job-permalink")
        if not link_tag or not link_tag.get("href"):
            logger.debug("Skipping article with no permalink: title={}", title)
            return None
        job_url = link_tag["href"]

        # Extract company from .company > strong
        company = None
        company_tag = article.find("div", class_="company")
        if company_tag:
            strong = company_tag.find("strong")
            if strong:
                company = strong.get_text(strip=True) or None

        # Extract location from .location
        location = None
        location_tag = article.find("div", class_="location")
        if location_tag:
            location = location_tag.get_text(strip=True) or None

        # Extract job type from .job-type
        tags: list[str] = []
        job_type_tag = article.find("li", class_="job-type")
        if job_type_tag:
            job_type = job_type_tag.get_text(strip=True)
            if job_type:
                tags.append(job_type)

        # Extract publication date from <time datetime="...">
        published_at = None
        time_tag = article.find("time")
        if time_tag and time_tag.get("datetime"):
            try:
                published_at = datetime.fromisoformat(time_tag["datetime"])
            except (ValueError, TypeError):
                logger.debug(
                    "Could not parse datetime '{}' for article",
                    time_tag.get("datetime"),
                )

        now = datetime.now()

        return JobPosting(
            id=JobPosting.generate_id(job_url, title),
            title=title,
            company=company,
            url=job_url,
            source="yuancheng",
            published_at=published_at,
            salary=None,  # Not available in listing page HTML
            location=location,
            description=None,  # Would need detail page fetch
            tags=tags,
            first_seen=now,
            last_seen=now,
            last_updated=now,
        )
