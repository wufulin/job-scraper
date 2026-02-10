"""Browser-based adapters using Playwright for JS-rendered sites."""

from __future__ import annotations

import json
from datetime import datetime

from loguru import logger
from playwright.async_api import async_playwright

from scraper.adapters.base import BaseAdapter
from scraper.models import JobPosting


class ArcDevAdapter(BaseAdapter):
    """Adapter for Arc.dev remote jobs.

    Arc.dev is a Next.js SPA that embeds job data via SSR in
    ``window.__NEXT_DATA__.props.pageProps.arcJobs``.

    We launch a headless browser, navigate to the remote-jobs page,
    extract the embedded JSON, and parse it — no API calls required.
    """

    @property
    def name(self) -> str:
        return "Arc.dev"

    @property
    def source_id(self) -> str:
        return "arcdev"

    async def fetch_jobs(self) -> list[JobPosting]:
        """Fetch jobs from Arc.dev using Playwright.

        Returns:
            List of parsed JobPosting objects.
        """
        url = self.config.get("url", "https://arc.dev/remote-jobs")
        logger.info("Fetching jobs from {} ({})", self.name, url)

        raw_jobs = await self._extract_next_data(url)
        logger.info("Extracted {} raw jobs from __NEXT_DATA__", len(raw_jobs))

        jobs: list[JobPosting] = []
        for entry in raw_jobs:
            try:
                job = self._parse_entry(entry)
                if job is not None:
                    jobs.append(job)
            except Exception:
                logger.exception(
                    "Failed to parse Arc.dev entry key={}",
                    entry.get("randomKey", "unknown"),
                )

        logger.info("Parsed {} valid jobs from {}", len(jobs), self.name)
        return jobs

    async def _extract_next_data(self, url: str) -> list[dict]:
        """Navigate to Arc.dev and extract arcJobs from __NEXT_DATA__.

        Args:
            url: The Arc.dev remote jobs page URL.

        Returns:
            List of raw job dicts from the embedded JSON.
        """
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Extract the __NEXT_DATA__ JSON from the page
                raw = await page.evaluate(
                    """() => {
                        const data = window.__NEXT_DATA__;
                        if (!data) return null;
                        return JSON.stringify(
                            data.props.pageProps.arcJobs || []
                        );
                    }"""
                )

                if raw is None:
                    logger.warning("No __NEXT_DATA__ found on {}", url)
                    return []

                return json.loads(raw)
            finally:
                await browser.close()

    @staticmethod
    def _parse_entry(entry: dict) -> JobPosting | None:
        """Parse a single Arc.dev job entry into a JobPosting.

        Args:
            entry: Raw dict from __NEXT_DATA__.props.pageProps.arcJobs.

        Returns:
            JobPosting or None if the entry lacks required fields.
        """
        title = (entry.get("title") or "").strip()
        if not title:
            logger.debug("Skipping entry with no title: {}", entry.get("randomKey"))
            return None

        # Build URL from randomKey and urlString
        random_key = entry.get("randomKey", "")
        url_string = entry.get("urlString", "")
        if not random_key or not url_string:
            logger.debug("Skipping entry with no randomKey/urlString: {}", title)
            return None

        job_url = f"https://arc.dev/remote-jobs/details/{url_string}-{random_key}"

        # Parse publication date from epoch
        published_at = None
        posted_at = entry.get("postedAt")
        if posted_at:
            try:
                published_at = datetime.fromtimestamp(posted_at)
            except (ValueError, TypeError, OSError):
                logger.debug(
                    "Could not parse postedAt {} for {}", posted_at, random_key
                )

        # Format salary
        salary = ArcDevAdapter._format_salary(entry)

        # Build location from requiredCountries + timeZone
        location = ArcDevAdapter._format_location(entry)

        # Extract tags from categories
        tags = [
            cat["name"]
            for cat in entry.get("categories", [])
            if isinstance(cat, dict) and cat.get("name")
        ]

        # Add jobType and experienceLevel as tags
        job_type = entry.get("jobType")
        if job_type:
            tags.append(job_type)
        exp_level = entry.get("experienceLevel")
        if exp_level:
            tags.append(exp_level)

        now = datetime.now()

        return JobPosting(
            id=JobPosting.generate_id(job_url, title),
            title=title,
            company=None,  # Arc Exclusive jobs don't expose company name
            url=job_url,
            source="arcdev",
            published_at=published_at,
            salary=salary,
            location=location,
            description=None,  # Description not available in listing
            tags=tags,
            first_seen=now,
            last_seen=now,
            last_updated=now,
        )

    @staticmethod
    def _format_salary(entry: dict) -> str | None:
        """Format salary information from Arc.dev entry.

        Handles both annual salary and hourly rate formats.

        Args:
            entry: Raw job entry dict.

        Returns:
            Human-readable salary string or None.
        """
        min_annual = entry.get("minAnnualSalary") or 0
        max_annual = entry.get("maxAnnualSalary") or 0
        min_hourly = entry.get("minHourlyRate") or 0
        max_hourly = entry.get("maxHourlyRate") or 0

        if min_annual > 0 and max_annual > 0:
            return f"US${min_annual:,} - ${max_annual:,}/yr"
        if min_annual > 0:
            return f"US${min_annual:,}+/yr"
        if max_annual > 0:
            return f"Up to US${max_annual:,}/yr"
        if min_hourly > 0 and max_hourly > 0:
            return f"US${min_hourly} - ${max_hourly}/hr"
        if min_hourly > 0:
            return f"US${min_hourly}+/hr"
        if max_hourly > 0:
            return f"Up to US${max_hourly}/hr"
        return None

    @staticmethod
    def _format_location(entry: dict) -> str | None:
        """Build location string from requiredCountries and timeZone.

        Args:
            entry: Raw job entry dict.

        Returns:
            Location string or None.
        """
        countries = entry.get("requiredCountries", [])
        time_zone = entry.get("timeZone")

        parts: list[str] = []
        if countries:
            if len(countries) <= 3:
                parts.append(", ".join(countries))
            else:
                parts.append(f"{len(countries)} countries")
        else:
            parts.append("Remote anywhere")

        if time_zone and time_zone != "no-preference":
            parts.append(f"TZ: {time_zone}")

        return " | ".join(parts) if parts else None
