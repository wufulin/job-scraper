from __future__ import annotations

import uuid

from fastapi import BackgroundTasks
from loguru import logger

from scraper.orchestrator import ScraperOrchestrator


class ScraperService:

    def __init__(self) -> None:
        self._orchestrator = ScraperOrchestrator()

    def trigger_scrape(
        self,
        background_tasks: BackgroundTasks,
        *,
        sites: list[str] | None = None,
        dry_run: bool = False,
    ) -> str:
        run_id = uuid.uuid4().hex[:12]

        if sites:
            for site in sites:
                background_tasks.add_task(
                    self._run_scrape, run_id=run_id, site=site, dry_run=dry_run
                )
        else:
            background_tasks.add_task(
                self._run_scrape, run_id=run_id, site=None, dry_run=dry_run
            )

        logger.info("Scrape triggered — run_id={}, sites={}, dry_run={}", run_id, sites, dry_run)
        return run_id

    async def _run_scrape(
        self, *, run_id: str, site: str | None, dry_run: bool
    ) -> dict:
        logger.info("Background scrape started — run_id={}, site={}", run_id, site)
        try:
            summary = await self._orchestrator.run(site=site, dry_run=dry_run)
            logger.info("Background scrape finished — run_id={}, summary={}", run_id, summary)
            return summary
        except Exception as exc:
            logger.error("Background scrape failed — run_id={}, error={}", run_id, exc)
            raise


_scraper_service: ScraperService | None = None


def get_scraper_service() -> ScraperService:
    global _scraper_service  # noqa: PLW0603
    if _scraper_service is None:
        _scraper_service = ScraperService()
    return _scraper_service
