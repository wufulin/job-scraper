from __future__ import annotations

import asyncio
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.services.scrape_run_service import get_scrape_run_service
from app.services.scraper_service import get_scraper_service

_scheduler: SchedulerService | None = None

DEFAULT_INTERVAL_HOURS = 2
JOB_ID = "periodic_scrape"


class SchedulerService:
    """Wraps APScheduler AsyncIOScheduler with mutex to prevent overlapping scrape runs."""

    def __init__(self, interval_hours: int = DEFAULT_INTERVAL_HOURS) -> None:
        self._scheduler = AsyncIOScheduler()
        self._interval_hours = interval_hours
        self._mutex = asyncio.Lock()
        self._paused = False
        self._started = False

    def start(self) -> None:
        self._scheduler.add_job(
            self._scheduled_scrape,
            "interval",
            hours=self._interval_hours,
            id=JOB_ID,
            replace_existing=True,
        )
        self._scheduler.start()
        self._started = True
        logger.info("Scheduler started — interval={}h", self._interval_hours)

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)
        self._started = False
        logger.info("Scheduler shut down")

    def pause(self) -> None:
        if not self._paused:
            self._scheduler.pause_job(JOB_ID)
            self._paused = True
            logger.info("Scheduler paused")

    def resume(self) -> None:
        if self._paused:
            self._scheduler.resume_job(JOB_ID)
            self._paused = False
            logger.info("Scheduler resumed")

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_running(self) -> bool:
        return self._started

    def get_next_run_time(self):
        job = self._scheduler.get_job(JOB_ID)
        if job is None:
            return None
        return job.next_run_time

    async def _scheduled_scrape(self) -> None:
        if self._mutex.locked():
            logger.warning("Skipping scheduled scrape — previous run still active")
            return

        async with self._mutex:
            run_id = uuid.uuid4().hex[:12]
            run_service = get_scrape_run_service()
            await run_service.start_run(run_id, trigger="scheduled")

            logger.info("Scheduled scrape started — run_id={}", run_id)
            try:
                scraper = get_scraper_service()
                summary = await scraper._run_scrape(
                    run_id=run_id, site=None, dry_run=False
                )
                await run_service.complete_run(
                    run_id,
                    matched=summary.get("matched", 0),
                    new=summary.get("new", 0),
                    updated=summary.get("updated", 0),
                )
                logger.info("Scheduled scrape completed — run_id={}, summary={}", run_id, summary)
            except Exception as exc:
                await run_service.fail_run(run_id, error=str(exc))
                logger.error("Scheduled scrape failed — run_id={}, error={}", run_id, exc)


def get_scheduler_service() -> SchedulerService:
    global _scheduler  # noqa: PLW0603
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


def init_scheduler() -> SchedulerService:
    svc = get_scheduler_service()
    svc.start()
    return svc


def shutdown_scheduler() -> None:
    global _scheduler  # noqa: PLW0603
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
