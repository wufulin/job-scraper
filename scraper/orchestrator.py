"""Scraper orchestrator — ties all components together."""

from __future__ import annotations

import asyncio

import yaml
from loguru import logger

from scraper.adapters.api import EleduckAdapter, RemoteOKAdapter
from scraper.adapters.base import BaseAdapter
from scraper.adapters.browser import ArcDevAdapter, WorkGoAdapter
from scraper.adapters.html import YuanchengAdapter
from scraper.adapters.hybrid import V2EXAdapter
from scraper.adapters.rss import WeWorkRemotelyAdapter
from scraper.models import JobPosting
from scraper.utils.dedup import DedupManager
from scraper.utils.matcher import KeywordMatcher
from scraper.utils.storage import StorageManager

# Mapping of site_id → adapter class
_ADAPTER_MAP: dict[str, type[BaseAdapter]] = {
    "remoteok": RemoteOKAdapter,
    "eleduck": EleduckAdapter,
    "weworkremotely": WeWorkRemotelyAdapter,
    "workgo": WorkGoAdapter,
    "v2ex": V2EXAdapter,
    "yuancheng": YuanchengAdapter,
    "arcdev": ArcDevAdapter,
}


class ScraperOrchestrator:
    """Orchestrates fetching, matching, and storing jobs from all configured sites."""

    def __init__(
        self,
        sites_config_path: str = "config/sites.yaml",
        keywords_config_path: str = "config/keywords.yaml",
        db_path: str = "data/jobs.db",
    ) -> None:
        """Initialize orchestrator with config paths.

        Args:
            sites_config_path: Path to sites.yaml
            keywords_config_path: Path to keywords.yaml
            db_path: Path to SQLite database
        """
        # Load sites config
        with open(sites_config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.sites_config: dict = data.get("sites", {})

        # Create matcher and storage
        self.matcher = KeywordMatcher(config_path=keywords_config_path)
        self.storage = StorageManager(db_path=db_path)

        # Interrupt flag for graceful Ctrl+C
        self.interrupted = False

    async def run(
        self,
        site: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Run the scraping pipeline.

        Args:
            site: If given, only scrape this site (e.g. 'remoteok').
            dry_run: If True, fetch and match but don't persist.

        Returns:
            Summary dict with total_scraped, matched, new, updated, errors.
        """
        summary: dict = {
            "total_scraped": 0,
            "matched": 0,
            "dedup_removed": 0,
            "new": 0,
            "updated": 0,
            "errors": [],
        }

        # Determine which sites to process
        sites_to_run = self._resolve_sites(site)
        if not sites_to_run:
            logger.warning("No sites to scrape")
            return summary

        logger.info(
            "Starting scrape run — sites: {}, dry_run: {}",
            list(sites_to_run.keys()),
            dry_run,
        )

        # Phase 1: Fetch & match from all adapters concurrently
        semaphore = asyncio.Semaphore(3)
        all_matched: list[JobPosting] = []
        lock = asyncio.Lock()

        async def _guarded_scrape(site_id: str, site_cfg: dict) -> None:
            async with semaphore:
                if self.interrupted:
                    logger.warning("Interrupted — skipping {}", site_id)
                    return
                try:
                    matched = await self._scrape_site(site_id, site_cfg, summary)
                    async with lock:
                        all_matched.extend(matched)
                except Exception as exc:
                    error_msg = f"{site_id}: {exc}"
                    logger.error("Error scraping {}: {}", site_id, exc)
                    summary["errors"].append(error_msg)

        tasks = [
            _guarded_scrape(site_id, site_cfg)
            for site_id, site_cfg in sites_to_run.items()
        ]
        await asyncio.gather(*tasks)

        summary["matched"] = len(all_matched)

        # Phase 2: Cross-site deduplication
        deduped = DedupManager.deduplicate(all_matched)
        dedup_removed = len(all_matched) - len(deduped)
        if dedup_removed:
            logger.info(
                "Cross-site dedup removed {} duplicate(s) ({} → {})",
                dedup_removed,
                len(all_matched),
                len(deduped),
            )
        summary["dedup_removed"] = dedup_removed

        # Phase 3: Store deduplicated jobs
        if not dry_run:
            for job in deduped:
                if self.interrupted:
                    logger.warning("Interrupted during storage")
                    break
                new_count, updated_count = await self.storage.upsert_job(job)
                summary["new"] += new_count
                summary["updated"] += updated_count
        else:
            for job in deduped:
                logger.debug("[dry-run] Matched: {}", job.title)

        logger.info(
            "Scrape complete — scraped: {}, matched: {}, dedup_removed: {}, new: {}, updated: {}, errors: {}",
            summary["total_scraped"],
            summary["matched"],
            summary["dedup_removed"],
            summary["new"],
            summary["updated"],
            len(summary["errors"]),
        )
        return summary

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_sites(self, site: str | None) -> dict:
        """Return the subset of sites config to process.

        Args:
            site: Optional single site id filter.

        Returns:
            Dict of site_id → config for enabled sites.
        """
        if site:
            if site not in self.sites_config:
                logger.error("Unknown site '{}'. Available: {}", site, list(self.sites_config.keys()))
                return {}
            cfg = self.sites_config[site]
            if not cfg.get("enabled", True):
                logger.warning("Site '{}' is disabled in config", site)
                return {}
            return {site: cfg}

        # All enabled sites
        return {
            sid: cfg
            for sid, cfg in self.sites_config.items()
            if cfg.get("enabled", True)
        }

    def _create_adapter(self, site_id: str, site_config: dict) -> BaseAdapter:
        """Instantiate the correct adapter for a site.

        Args:
            site_id: Site identifier (e.g. 'remoteok').
            site_config: Site configuration dict from sites.yaml.

        Returns:
            Instantiated BaseAdapter subclass.

        Raises:
            ValueError: If no adapter class is known for the site_id.
        """
        adapter_cls = _ADAPTER_MAP.get(site_id)
        if adapter_cls is None:
            raise ValueError(f"No adapter registered for site '{site_id}'")
        return adapter_cls(config=site_config)

    async def _scrape_site(
        self,
        site_id: str,
        site_cfg: dict,
        summary: dict,
    ) -> list[JobPosting]:
        """Fetch and match jobs for a single site.

        Returns matched jobs for cross-site dedup.  Mutates *summary*
        total_scraped counter in place.
        """
        logger.info("--- Scraping {} ---", site_id)
        adapter = self._create_adapter(site_id, site_cfg)

        # Fetch
        jobs = await adapter.fetch_jobs()
        summary["total_scraped"] += len(jobs)
        logger.info("Fetched {} jobs from {}", len(jobs), site_id)

        # Match (collect, don't store yet — dedup happens later)
        matched: list[JobPosting] = []
        for job in jobs:
            if self.interrupted:
                logger.warning("Interrupted during {} matching", site_id)
                break

            job_dict = {
                "title": job.title,
                "description": job.description or "",
                "tags": job.tags,
            }

            if self.matcher.match_job(job_dict, adapter.source_id):
                matched.append(job)

        logger.info("Matched {} jobs from {}", len(matched), site_id)
        return matched
