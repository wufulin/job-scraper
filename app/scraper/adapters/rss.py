"""WeWorkRemotely RSS adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
from loguru import logger

from app.scraper.adapters.base import BaseAdapter
from app.scraper.models import JobPosting


class WeWorkRemotelyAdapter(BaseAdapter):
    """Adapter for the WeWorkRemotely RSS feed.

    RSS endpoint: https://weworkremotely.com/remote-jobs.rss
    Returns an RSS 2.0 feed with <item> elements.
    """

    @property
    def name(self) -> str:
        return "We Work Remotely"

    @property
    def source_id(self) -> str:
        return "weworkremotely"

    async def fetch_jobs(self) -> list[JobPosting]:
        """Fetch jobs from the WeWorkRemotely RSS feed.

        Returns:
            List of parsed JobPosting objects.
        """
        url = self.config.get("url", "https://weworkremotely.com/remote-jobs.rss")
        logger.info("Fetching jobs from {} ({})", self.name, url)

        async with self._get_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            xml_text = response.text

        feed = feedparser.parse(xml_text)

        if feed.bozo:
            logger.warning(
                "Feed parse warning for {}: {}",
                self.name,
                feed.get("bozo_exception", "unknown"),
            )

        entries = feed.entries
        logger.info("Received {} RSS entries from {}", len(entries), self.name)

        jobs: list[JobPosting] = []
        for entry in entries:
            try:
                job = self._parse_entry(entry)
                if job is not None:
                    jobs.append(job)
            except Exception:
                logger.exception(
                    "Failed to parse WWR entry title={}",
                    entry.get("title", "unknown"),
                )

        logger.info("Parsed {} valid jobs from {}", len(jobs), self.name)
        return jobs

    @staticmethod
    def _parse_entry(entry: dict) -> JobPosting | None:
        """Parse a single RSS entry into a JobPosting.

        Args:
            entry: feedparser entry dict.

        Returns:
            JobPosting or None if the entry lacks required fields.
        """
        raw_title = (entry.get("title") or "").strip()
        if not raw_title:
            logger.debug("Skipping entry with no title")
            return None

        # Extract company and job title from "Company: Job Title" format
        company, title = WeWorkRemotelyAdapter._split_title(raw_title)

        # Get URL from link field
        job_url = entry.get("link") or ""
        if not job_url:
            logger.debug("Skipping entry with no link: {}", raw_title)
            return None

        # Parse publication date from RFC 2822 format
        published_at = None
        published_str = entry.get("published")
        if published_str:
            try:
                published_at = parsedate_to_datetime(published_str)
            except (ValueError, TypeError):
                logger.debug("Could not parse date '{}' for entry '{}'", published_str, raw_title)

        # Get description/summary
        description = entry.get("summary") or None

        # Extract tags from feedparser's tag structure (from <category>)
        tags: list[str] = []
        raw_tags = entry.get("tags", [])
        if isinstance(raw_tags, list):
            for tag in raw_tags:
                if isinstance(tag, dict):
                    term = tag.get("term")
                    if term:
                        tags.append(term)

        # Extract location from region field
        location = entry.get("region") or None

        now = datetime.now()

        return JobPosting(
            id=JobPosting.generate_id(job_url, title),
            title=title,
            company=company,
            url=job_url,
            source="weworkremotely",
            published_at=published_at,
            salary=None,  # WWR RSS doesn't provide structured salary data
            location=location,
            description=description,
            tags=tags,
            first_seen=now,
            last_seen=now,
            last_updated=now,
        )

    @staticmethod
    def _split_title(raw_title: str) -> tuple[str | None, str]:
        """Split "Company: Job Title" into (company, title).

        If no colon is found, returns (None, raw_title).

        Args:
            raw_title: The raw RSS title string.

        Returns:
            Tuple of (company, title).
        """
        if ": " in raw_title:
            company, title = raw_title.split(": ", 1)
            company = company.strip() or None
            title = title.strip()
            if not title:
                # Colon at end — use full string as title
                return None, raw_title
            return company, title
        return None, raw_title
