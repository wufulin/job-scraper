from __future__ import annotations

import uuid

from fastapi import BackgroundTasks
from loguru import logger

from app.config.settings import settings
from app.services.scrape_run_service import get_scrape_run_service
from app.services.storage import SupabaseStorage
from app.scraper.orchestrator import ScraperOrchestrator

_storage: SupabaseStorage | None = None


async def init_scraper_storage() -> None:
    global _storage  # noqa: PLW0603
    if settings.DATABASE_URL:
        _storage = SupabaseStorage()
        await _storage.init_pool()


async def close_scraper_storage() -> None:
    global _storage  # noqa: PLW0603
    if _storage:
        await _storage.close_pool()
        _storage = None


class ScraperService:

    def __init__(self, storage: object | None = None) -> None:
        self._orchestrator = ScraperOrchestrator(storage=storage)

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
                    self._tracked_scrape, run_id=run_id, site=site, dry_run=dry_run,
                    sites_list=sites,
                )
        else:
            background_tasks.add_task(
                self._tracked_scrape, run_id=run_id, site=None, dry_run=dry_run,
                sites_list=None,
            )

        logger.info("Scrape triggered — run_id={}, sites={}, dry_run={}", run_id, sites, dry_run)
        return run_id

    async def _tracked_scrape(
        self,
        *,
        run_id: str,
        site: str | None,
        dry_run: bool,
        sites_list: list[str] | None,
    ) -> dict:
        run_service = get_scrape_run_service()
        await run_service.start_run(
            run_id, trigger="manual", sites=sites_list, dry_run=dry_run
        )
        try:
            summary = await self._run_scrape(run_id=run_id, site=site, dry_run=dry_run)
            await run_service.complete_run(
                run_id,
                matched=summary.get("matched", 0),
                new=summary.get("new", 0),
                updated=summary.get("updated", 0),
            )
            return summary
        except Exception as exc:
            await run_service.fail_run(run_id, error=str(exc))
            raise

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
        _scraper_service = ScraperService(storage=_storage)
    return _scraper_service
