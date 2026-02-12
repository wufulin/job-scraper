"""Hybrid adapters: HTML listing + API detail fetching."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from loguru import logger

from app.scraper.adapters.base import BaseAdapter
from app.scraper.models import JobPosting


class V2EXAdapter(BaseAdapter):
    """Adapter for V2EX job boards using a hybrid approach.

    Step 1: Fetch the HTML listing page (e.g. /go/remote or /go/jobs)
            and parse topic IDs from the links using BeautifulSoup.
    Step 2: For each topic ID, call the public JSON API to get full details:
            GET /api/topics/show.json?id={topic_id}
    Rate limit: 600 req/hour (~1 req/6s). We respect this via _delay().

    Config keys:
        url:             HTML listing URL (e.g. https://www.v2ex.com/go/remote)
        api_base:        API endpoint base (default: https://www.v2ex.com/api/topics/show.json)
        rate_limit_seconds: Delay between API calls (default: 6)
    """

    @property
    def name(self) -> str:
        return "V2EX"

    @property
    def source_id(self) -> str:
        return "v2ex"

    async def fetch_jobs(self) -> list[JobPosting]:
        """Fetch jobs using the hybrid HTML-list + API-detail approach.

        Returns:
            List of parsed JobPosting objects.
        """
        listing_url = self.config.get("url", "https://www.v2ex.com/go/remote")
        api_base = self.config.get(
            "api_base", "https://www.v2ex.com/api/topics/show.json"
        )

        logger.info("Fetching V2EX listing from {}", listing_url)

        async with self._get_client() as client:
            # Step 1: Fetch HTML listing page
            response = await client.get(listing_url)
            response.raise_for_status()
            html = response.text

            # Step 2: Extract topic IDs
            topic_ids = self._parse_topic_ids(html)
            logger.info("Found {} topic IDs from listing", len(topic_ids))

            if not topic_ids:
                return []

            # Step 3: Fetch each topic via API
            jobs: list[JobPosting] = []
            for topic_id in topic_ids:
                await self._delay()
                try:
                    api_url = f"{api_base}?id={topic_id}"
                    logger.debug("Fetching topic {} from API", topic_id)
                    resp = await client.get(api_url)
                    resp.raise_for_status()
                    topic_list = resp.json()

                    # API returns a list of topics (usually length 1)
                    for topic in topic_list:
                        try:
                            job = self._parse_topic(topic)
                            if job is not None:
                                jobs.append(job)
                        except Exception:
                            logger.exception(
                                "Failed to parse V2EX topic id={}",
                                topic.get("id", "unknown"),
                            )
                except Exception:
                    logger.exception(
                        "Failed to fetch V2EX topic id={}", topic_id
                    )

        logger.info("Parsed {} valid jobs from V2EX", len(jobs))
        return jobs

    def _parse_topic_ids(self, html: str) -> list[int]:
        """Extract unique topic IDs from V2EX listing HTML.

        Looks for links matching /t/{id} inside <span class="item_title"> elements.

        Args:
            html: Raw HTML string from the listing page.

        Returns:
            List of unique topic IDs (ints).
        """
        soup = BeautifulSoup(html, "html.parser")
        topic_id_pattern = re.compile(r"/t/(\d+)")

        seen: set[int] = set()
        result: list[int] = []

        # V2EX listing pages have topic links in <span class="item_title"> > <a>
        for span in soup.find_all("span", class_="item_title"):
            link = span.find("a", href=topic_id_pattern)
            if link:
                match = topic_id_pattern.search(link["href"])
                if match:
                    tid = int(match.group(1))
                    if tid not in seen:
                        seen.add(tid)
                        result.append(tid)

        return result

    @staticmethod
    def _parse_topic(topic: dict) -> JobPosting | None:
        """Parse a single V2EX topic API response into a JobPosting.

        Args:
            topic: Dict from /api/topics/show.json response.

        Returns:
            JobPosting or None if the topic lacks required fields.
        """
        topic_id = topic.get("id")
        if not topic_id:
            logger.debug("Skipping topic with no id")
            return None

        title = (topic.get("title") or "").strip()
        if not title:
            logger.debug("Skipping topic {} with no title", topic_id)
            return None

        # Build URL
        job_url = topic.get("url") or f"https://www.v2ex.com/t/{topic_id}"

        # Parse created timestamp (Unix epoch)
        published_at = None
        created = topic.get("created")
        if created:
            try:
                published_at = datetime.fromtimestamp(created, tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                logger.debug(
                    "Could not parse timestamp '{}' for topic {}", created, topic_id
                )

        # Extract member.username as company (poster)
        company = None
        member = topic.get("member")
        if member and isinstance(member, dict):
            company = member.get("username")

        # Extract description from content field
        description = topic.get("content") or None

        # Extract tags from node.title
        tags: list[str] = []
        node = topic.get("node")
        if node and isinstance(node, dict):
            node_title = node.get("title")
            if node_title:
                tags.append(node_title)

        now = datetime.now()

        return JobPosting(
            id=JobPosting.generate_id(job_url, title),
            title=title,
            company=company,
            url=job_url,
            source="v2ex",
            published_at=published_at,
            salary=None,  # V2EX doesn't provide structured salary data
            location=None,  # Location is in content text, not structured
            description=description,
            tags=tags,
            first_seen=now,
            last_seen=now,
            last_updated=now,
        )
