"""Browser-based adapters using Playwright for JS-rendered sites."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

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


class WorkGoAdapter(BaseAdapter):
    """Adapter for WorkGo.ai using Playwright browser automation.

    WorkGo requires Clerk JWT authentication. This adapter:
    1. Launches a headless Chromium browser
    2. Navigates to workgo.ai and authenticates via Clerk
    3. Intercepts POST /auth/jobs/all API responses
    4. Extracts and parses job data with pagination support
    """

    @property
    def name(self) -> str:
        return "WorkGo"

    @property
    def source_id(self) -> str:
        return "workgo"

    async def fetch_jobs(self) -> list[JobPosting]:
        """Fetch jobs from WorkGo via browser automation.

        Launches Playwright, authenticates, and intercepts API responses.
        Handles pagination automatically.

        Returns:
            List of parsed JobPosting objects. Empty list on auth failure.
        """
        all_jobs: list[JobPosting] = []
        page_num = 1
        page_size = self.config.get("page_size", 20)

        try:
            while True:
                logger.info(
                    "Fetching WorkGo jobs page {} (page_size={})", page_num, page_size
                )
                data = await self._fetch_via_browser(page_num, page_size)

                page_jobs = self._parse_api_response(data)
                all_jobs.extend(page_jobs)

                logger.info(
                    "Parsed {} jobs from WorkGo page {}", len(page_jobs), page_num
                )

                has_more = data.get("has_more_pages", False) if isinstance(data, dict) else False
                if not has_more or not page_jobs:
                    break

                page_num += 1
                await self._delay()

        except Exception as exc:
            logger.error("WorkGo fetch failed: {}", exc)

        logger.info("Total {} jobs fetched from WorkGo", len(all_jobs))
        return all_jobs

    async def _fetch_via_browser(
        self, page_num: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """Launch browser, authenticate, and intercept API response.

        Args:
            page_num: Page number to request.
            page_size: Number of results per page.

        Returns:
            Parsed JSON dict from the intercepted API response.

        Raises:
            Exception: On authentication failure or network errors.
        """
        email = os.environ.get("WORKGO_EMAIL")
        password = os.environ.get("WORKGO_PASSWORD")

        if not email or not password:
            raise ValueError(
                "WORKGO_EMAIL and WORKGO_PASSWORD environment variables are required"
            )

        api_url = self.config.get("api_url", "https://api.workgo.ai/auth/jobs/all")
        base_url = self.config.get("url", "https://workgo.ai")
        captured_response: dict[str, Any] = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Set up response interception for the jobs API
            async def _handle_response(response):
                if api_url in response.url and response.request.method == "POST":
                    try:
                        body = await response.json()
                        captured_response.update(body)
                        logger.debug(
                            "Intercepted WorkGo API response from {}", response.url
                        )
                    except Exception as exc:
                        logger.warning(
                            "Failed to parse intercepted response: {}", exc
                        )

            page.on("response", _handle_response)

            try:
                # Step 1: Navigate to login page
                logger.debug("Navigating to WorkGo login...")
                await page.goto(f"{base_url}/sign-in", wait_until="networkidle")

                # Step 2: Clerk authentication — fill email
                logger.debug("Filling Clerk email...")
                await page.fill(
                    'input[name="identifier"], input[type="email"]', email
                )
                await page.click(
                    'button[type="submit"], button:has-text("Continue")'
                )
                await page.wait_for_timeout(2000)

                # Step 3: Fill password
                logger.debug("Filling Clerk password...")
                await page.fill('input[type="password"]', password)
                await page.click(
                    'button[type="submit"], button:has-text("Continue")'
                )

                # Step 4: Wait for auth to complete
                await page.wait_for_url(
                    f"{base_url}/dashboard/**", timeout=15000
                )
                logger.info("WorkGo authentication successful")

                # Step 5: Navigate to job search and trigger API call
                logger.debug("Navigating to job search page...")
                await page.goto(
                    f"{base_url}/dashboard/job/job-search",
                    wait_until="networkidle",
                )

                # Step 6: If specific page requested, trigger via API directly
                if page_num > 1:
                    # Use page.evaluate to make a fetch call with the auth cookies
                    js_code = f"""
                    async () => {{
                        const response = await fetch('{api_url}', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{page: {page_num}, page_size: {page_size}}}),
                            credentials: 'include'
                        }});
                        return await response.json();
                    }}
                    """
                    result = await page.evaluate(js_code)
                    if isinstance(result, dict):
                        captured_response.update(result)

                # Wait briefly for any pending response interceptions
                await page.wait_for_timeout(3000)

            finally:
                await browser.close()

        if not captured_response:
            logger.warning("No API response captured from WorkGo")
            return {"jobs": [], "has_more_pages": False}

        return captured_response

    @staticmethod
    def _parse_api_response(data: Any) -> list[JobPosting]:
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
