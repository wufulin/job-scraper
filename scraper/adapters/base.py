"""Base adapter abstract class for job scrapers."""

from __future__ import annotations

import abc
import asyncio
import random

import httpx
from fake_useragent import UserAgent
from loguru import logger

from scraper.models import JobPosting


class BaseAdapter(abc.ABC):
    """Abstract base class for all job site adapters.

    Each adapter must implement name, source_id, and fetch_jobs().
    Provides shared helpers for HTTP clients and rate limiting.
    """

    def __init__(self, config: dict) -> None:
        """Initialize adapter with site config from sites.yaml.

        Args:
            config: Site configuration dict (url, headers, rate_limit_seconds, etc.)
        """
        self.config = config

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable name for this adapter (e.g., 'RemoteOK')."""
        ...

    @property
    @abc.abstractmethod
    def source_id(self) -> str:
        """Machine ID for this adapter (e.g., 'remoteok')."""
        ...

    @abc.abstractmethod
    async def fetch_jobs(self) -> list[JobPosting]:
        """Fetch and return job postings from the source.

        Returns:
            List of parsed JobPosting objects.
        """
        ...

    def _get_client(self, timeout: float = 30.0) -> httpx.AsyncClient:
        """Create an httpx async client with randomized User-Agent.

        Args:
            timeout: Request timeout in seconds (default 30).

        Returns:
            Configured httpx.AsyncClient instance.
        """
        ua = UserAgent()
        headers = dict(self.config.get("headers", {}))
        headers["User-Agent"] = ua.random
        logger.debug("Using User-Agent: {}", headers["User-Agent"])
        return httpx.AsyncClient(headers=headers, timeout=timeout)

    async def _delay(self) -> None:
        """Sleep for a random duration within the configured rate limit range.

        Uses rate_limit_seconds from config (default 2s).
        Actual sleep is between 50%-150% of the configured value.
        """
        base = self.config.get("rate_limit_seconds", 2)
        sleep_time = random.uniform(base * 0.5, base * 1.5)
        logger.debug("Rate-limiting: sleeping {:.2f}s", sleep_time)
        await asyncio.sleep(sleep_time)
