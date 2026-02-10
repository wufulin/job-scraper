"""API-based adapters for job scrapers."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx
from loguru import logger

from scraper.adapters.base import BaseAdapter
from scraper.models import JobPosting


class RemoteOKAdapter(BaseAdapter):
    """Adapter for the RemoteOK public JSON API.

    API endpoint: https://remoteok.com/api
    Returns a JSON array where the first element is a legal notice (must skip).
    """

    @property
    def name(self) -> str:
        return "RemoteOK"

    @property
    def source_id(self) -> str:
        return "remoteok"

    async def fetch_jobs(self) -> list[JobPosting]:
        """Fetch jobs from the RemoteOK API.

        Returns:
            List of parsed JobPosting objects.
        """
        url = self.config.get("url", "https://remoteok.com/api")
        logger.info("Fetching jobs from {} ({})", self.name, url)

        async with self._get_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        # First element is always a legal notice — skip it
        raw_jobs = data[1:] if len(data) > 1 else []
        logger.info("Received {} raw job entries from {}", len(raw_jobs), self.name)

        jobs: list[JobPosting] = []
        for entry in raw_jobs:
            try:
                job = self._parse_entry(entry)
                if job is not None:
                    jobs.append(job)
            except Exception:
                logger.exception(
                    "Failed to parse RemoteOK entry id={}",
                    entry.get("id", "unknown"),
                )

        logger.info("Parsed {} valid jobs from {}", len(jobs), self.name)
        return jobs

    @staticmethod
    def _parse_entry(entry: dict) -> JobPosting | None:
        """Parse a single RemoteOK API entry into a JobPosting.

        Args:
            entry: Raw dict from the API response.

        Returns:
            JobPosting or None if the entry lacks required fields.
        """
        title = (entry.get("position") or "").strip()
        if not title:
            logger.debug("Skipping entry with no title: {}", entry.get("id"))
            return None

        # Build URL — prefer the url field, fall back to slug-based construction
        job_url = entry.get("url") or ""
        if not job_url:
            slug = entry.get("slug", "")
            if slug:
                job_url = f"https://remoteok.com/remote-jobs/{slug}"
            else:
                logger.debug("Skipping entry with no url/slug: {}", entry.get("id"))
                return None

        # Parse publication date
        published_at = None
        date_str = entry.get("date")
        if date_str:
            try:
                published_at = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                logger.debug("Could not parse date '{}' for entry {}", date_str, entry.get("id"))

        # Format salary range
        salary = RemoteOKAdapter._format_salary(
            entry.get("salary_min"),
            entry.get("salary_max"),
        )

        now = datetime.now()

        return JobPosting(
            id=JobPosting.generate_id(job_url, title),
            title=title,
            company=entry.get("company") or None,
            url=job_url,
            source="remoteok",
            published_at=published_at,
            salary=salary,
            location=entry.get("location") or None,
            description=entry.get("description") or None,
            tags=entry.get("tags") or [],
            first_seen=now,
            last_seen=now,
            last_updated=now,
        )

    @staticmethod
    def _format_salary(salary_min: int | None, salary_max: int | None) -> str | None:
        """Format salary_min/salary_max into a human-readable range string.

        Args:
            salary_min: Minimum salary (0 or None means not provided).
            salary_max: Maximum salary (0 or None means not provided).

        Returns:
            Formatted string like "$60,000 - $85,000" or None.
        """
        lo = salary_min or 0
        hi = salary_max or 0
        if lo > 0 and hi > 0:
            return f"${lo:,} - ${hi:,}"
        if lo > 0:
            return f"${lo:,}+"
        if hi > 0:
            return f"Up to ${hi:,}"
        return None


class EleduckAdapter(BaseAdapter):
    """Adapter for the 电鸭 (Eleduck) public API.

    API endpoint: https://svc.eleduck.com/api/v1/posts?category=5
    Category 5 = 招聘 (recruitment)
    Returns a JSON object with a 'posts' array.
    """

    @property
    def name(self) -> str:
        return "电鸭社区"

    @property
    def source_id(self) -> str:
        return "eleduck"

    async def fetch_jobs(self) -> list[JobPosting]:
        """Fetch jobs from the Eleduck API.

        Supports pagination up to 5 pages (configurable via max_pages in config).

        Returns:
            List of parsed JobPosting objects.
        """
        base_url = self.config.get("url", "https://svc.eleduck.com/api/v1/posts")
        params = dict(self.config.get("params", {}))
        max_pages = self.config.get("max_pages", 5)
        
        logger.info("Fetching jobs from {} ({})", self.name, base_url)

        jobs: list[JobPosting] = []
        
        async with self._get_client() as client:
            for page in range(1, max_pages + 1):
                params["page"] = page
                logger.debug("Fetching page {} from {}", page, self.name)
                
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                raw_posts = data.get("posts", [])
                if not raw_posts:
                    logger.info("No more posts on page {}, stopping pagination", page)
                    break
                
                logger.info("Received {} posts from {} page {}", len(raw_posts), self.name, page)
                
                for entry in raw_posts:
                    try:
                        job = self._parse_entry(entry)
                        if job is not None:
                            jobs.append(job)
                    except Exception:
                        logger.exception(
                            "Failed to parse Eleduck entry id={}",
                            entry.get("id", "unknown"),
                        )
                
                # Rate limit between pages
                if page < max_pages and raw_posts:
                    await self._delay()

        logger.info("Parsed {} valid jobs from {}", len(jobs), self.name)
        return jobs

    @staticmethod
    def _parse_entry(entry: dict) -> JobPosting | None:
        """Parse a single Eleduck API entry into a JobPosting.

        Args:
            entry: Raw dict from the API response.

        Returns:
            JobPosting or None if the entry lacks required fields.
        """
        title = (entry.get("title") or "").strip()
        if not title:
            logger.debug("Skipping entry with no title: {}", entry.get("id"))
            return None

        # Build URL from post ID
        post_id = entry.get("id")
        if not post_id:
            logger.debug("Skipping entry with no id")
            return None
        
        job_url = f"https://eleduck.com/posts/{post_id}"

        # Parse publication date
        published_at = None
        date_str = entry.get("published_at")
        if date_str:
            try:
                published_at = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                logger.debug("Could not parse date '{}' for entry {}", date_str, post_id)

        # Extract company from user.nickname
        company = None
        user = entry.get("user")
        if user and isinstance(user, dict):
            company = user.get("nickname")

        # Extract description from summary
        description = entry.get("summary") or None

        # Extract tag names from tags array
        tags = []
        raw_tags = entry.get("tags", [])
        if isinstance(raw_tags, list):
            for tag in raw_tags:
                if isinstance(tag, dict):
                    tag_name = tag.get("name")
                    if tag_name:
                        tags.append(tag_name)

        now = datetime.now()

        return JobPosting(
            id=JobPosting.generate_id(job_url, title),
            title=title,
            company=company,
            url=job_url,
            source="eleduck",
            published_at=published_at,
            salary=None,  # Eleduck API doesn't provide structured salary data
            location=None,  # Location is in tags, not as a separate field
            description=description,
            tags=tags,
            first_seen=now,
            last_seen=now,
            last_updated=now,
        )


class WorkGoAdapter(BaseAdapter):
    """WorkGo adapter using Clerk cookie→JWT authentication.

    Authenticates via Clerk __client cookie to obtain a session JWT,
    then uses Bearer token auth to fetch jobs from the WorkGo API.
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._jwt: str | None = None

    @property
    def name(self) -> str:
        return "WorkGo"

    @property
    def source_id(self) -> str:
        return "workgo"

    async def fetch_jobs(self) -> list[JobPosting]:
        """Fetch jobs from the WorkGo API with Clerk JWT auth.

        Returns:
            List of parsed JobPosting objects.
        """
        api_url = self.config.get("api_url", "https://workgo.ai/api/jobs")
        max_pages = self.config.get("max_pages", 5)
        page_size = self.config.get("page_size", 20)

        logger.info("Fetching jobs from {} ({})", self.name, api_url)

        try:
            await self._ensure_jwt()
        except Exception:
            logger.exception("Failed to obtain JWT for {}", self.name)
            return []

        jobs: list[JobPosting] = []

        async with self._get_client() as client:
            for page in range(1, max_pages + 1):
                logger.debug("Fetching page {} from {}", page, self.name)

                headers = {"Authorization": f"Bearer {self._jwt}"}
                payload = {"page": page, "page_size": page_size}

                try:
                    response = await client.post(
                        api_url, json=payload, headers=headers
                    )
                except Exception:
                    logger.exception(
                        "Request failed for {} page {}", self.name, page
                    )
                    break

                # Handle 401 — refresh JWT once and retry
                if response.status_code == 401:
                    logger.warning(
                        "Got 401 from {} on page {}, refreshing JWT", self.name, page
                    )
                    try:
                        await self._refresh_jwt()
                        headers = {"Authorization": f"Bearer {self._jwt}"}
                        response = await client.post(
                            api_url, json=payload, headers=headers
                        )
                    except Exception:
                        logger.exception(
                            "JWT refresh failed for {}", self.name
                        )
                        break

                    if response.status_code == 401:
                        logger.error(
                            "Still 401 after JWT refresh for {}, aborting",
                            self.name,
                        )
                        break

                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError:
                    logger.exception(
                        "HTTP error from {} page {}: {}",
                        self.name,
                        page,
                        response.status_code,
                    )
                    break

                data = response.json()
                page_jobs = self._parse_api_response(data)

                if not page_jobs:
                    logger.info(
                        "No more jobs on page {}, stopping pagination", page
                    )
                    break

                jobs.extend(page_jobs)
                logger.info(
                    "Received {} jobs from {} page {}",
                    len(page_jobs),
                    self.name,
                    page,
                )

                # Check has_more_pages flag
                has_more = data.get("has_more_pages", True)
                if not has_more:
                    logger.info("No more pages flagged by {}", self.name)
                    break

                # Rate limit between pages
                if page < max_pages:
                    await self._delay()

        logger.info("Parsed {} valid jobs from {}", len(jobs), self.name)
        return jobs

    async def _ensure_jwt(self) -> None:
        """Obtain a Clerk JWT from the __client cookie if not already cached.

        Raises:
            ValueError: If WORKGO_COOKIE env var is missing or session is invalid.
        """
        if self._jwt is not None:
            return

        cookie = os.environ.get("WORKGO_COOKIE")
        if not cookie:
            logger.warning(
                "WORKGO_COOKIE env var not set. "
                "Set it to your Clerk __client cookie value to use WorkGo."
            )
            raise ValueError("WORKGO_COOKIE environment variable is required")

        clerk_base = self.config.get("clerk_base", "https://clerk.workgo.ai")
        clerk_js_version = self.config.get("clerk_js_version", "5.43.6")

        async with httpx.AsyncClient() as client:
            # Step 1: Get client info and active session ID
            client_url = (
                f"{clerk_base}/v1/client"
                f"?_clerk_js_version={clerk_js_version}"
            )
            client_resp = await client.get(
                client_url,
                headers={"Cookie": f"__client={cookie}"},
            )
            client_resp.raise_for_status()
            client_data = client_resp.json()

            session_id = (
                client_data.get("response", {}).get("last_active_session_id")
            )
            if session_id is None:
                logger.error(
                    "No active session found in Clerk client response"
                )
                raise ValueError("No active Clerk session — cookie may be expired")

            # Step 2: Exchange session for JWT
            token_url = (
                f"{clerk_base}/v1/client/sessions/{session_id}/tokens"
            )
            token_resp = await client.post(
                token_url,
                headers={"Cookie": f"__client={cookie}"},
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            self._jwt = token_data.get("jwt")
            if not self._jwt:
                logger.error("No JWT in Clerk token response")
                raise ValueError("Failed to obtain JWT from Clerk")

            logger.info("Successfully obtained Clerk JWT for {}", self.name)

    async def _refresh_jwt(self) -> None:
        """Clear cached JWT and re-fetch from Clerk."""
        self._jwt = None
        await self._ensure_jwt()

    @staticmethod
    def _parse_api_response(data: dict[str, Any]) -> list[JobPosting]:
        """Parse an API response dict into a list of JobPostings.

        Args:
            data: Parsed JSON response from the WorkGo API.

        Returns:
            List of successfully parsed JobPosting objects.
        """
        if not isinstance(data, dict):
            logger.warning("Invalid WorkGo API response type: {}", type(data))
            return []

        raw_jobs = data.get("jobs", [])
        if not isinstance(raw_jobs, list):
            logger.warning("'jobs' key is not a list in WorkGo response")
            return []

        jobs: list[JobPosting] = []
        for entry in raw_jobs:
            try:
                job = WorkGoAdapter._parse_entry(entry)
                if job is not None:
                    jobs.append(job)
            except Exception:
                logger.exception(
                    "Failed to parse WorkGo entry id={}",
                    entry.get("id", "unknown"),
                )

        return jobs

    @staticmethod
    def _parse_entry(entry: dict) -> JobPosting | None:
        """Parse a single WorkGo API entry into a JobPosting.

        Args:
            entry: Raw dict from the API response 'jobs' array.

        Returns:
            JobPosting or None if the entry lacks required fields.
        """
        title = (entry.get("title") or "").strip()
        if not title:
            logger.debug("Skipping WorkGo entry with no title: {}", entry.get("id"))
            return None

        job_id = entry.get("id")
        if not job_id:
            logger.debug("Skipping WorkGo entry with no id")
            return None

        job_url = f"https://workgo.ai/dashboard/job/{job_id}"

        # Parse publication date
        published_at = None
        date_str = entry.get("published_at")
        if date_str:
            try:
                published_at = datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                logger.debug(
                    "Could not parse date '{}' for WorkGo entry {}", date_str, job_id
                )

        # Combine tags + skills_required, deduplicate preserving order
        tags: list[str] = []
        seen: set[str] = set()
        for tag in entry.get("tags", []) or []:
            if isinstance(tag, str) and tag not in seen:
                tags.append(tag)
                seen.add(tag)
        for skill in entry.get("skills_required", []) or []:
            if isinstance(skill, str) and skill not in seen:
                tags.append(skill)
                seen.add(skill)

        now = datetime.now()

        return JobPosting(
            id=JobPosting.generate_id(job_url, title),
            title=title,
            company=entry.get("company") or None,
            url=job_url,
            source="workgo",
            published_at=published_at,
            salary=entry.get("salary") or None,
            location=entry.get("location") or None,
            description=entry.get("description") or None,
            tags=tags,
            first_seen=now,
            last_seen=now,
            last_updated=now,
        )
