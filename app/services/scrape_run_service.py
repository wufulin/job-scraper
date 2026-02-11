from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class RunStatus(str, Enum):
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScrapeRun(BaseModel):
    run_id: str
    status: RunStatus
    trigger: str = "manual"
    sites: Optional[list[str]] = None
    dry_run: bool = False
    started_at: datetime
    finished_at: Optional[datetime] = None
    matched: int = 0
    new: int = 0
    updated: int = 0
    errors: list[str] = []


class ScrapeRunService:
    """In-memory scrape run tracker (asyncio.Lock for concurrent access)."""

    def __init__(self, max_history: int = 50) -> None:
        self._runs: dict[str, ScrapeRun] = {}
        self._max_history = max_history
        self._lock = asyncio.Lock()

    async def start_run(
        self,
        run_id: str,
        *,
        trigger: str = "manual",
        sites: list[str] | None = None,
        dry_run: bool = False,
    ) -> ScrapeRun:
        run = ScrapeRun(
            run_id=run_id,
            status=RunStatus.STARTED,
            trigger=trigger,
            sites=sites,
            dry_run=dry_run,
            started_at=datetime.now(timezone.utc),
        )
        async with self._lock:
            self._runs[run_id] = run
            self._evict_old()
        return run

    async def complete_run(
        self,
        run_id: str,
        *,
        matched: int = 0,
        new: int = 0,
        updated: int = 0,
    ) -> ScrapeRun | None:
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            run.status = RunStatus.COMPLETED
            run.finished_at = datetime.now(timezone.utc)
            run.matched = matched
            run.new = new
            run.updated = updated
            return run

    async def fail_run(self, run_id: str, *, error: str) -> ScrapeRun | None:
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            run.status = RunStatus.FAILED
            run.finished_at = datetime.now(timezone.utc)
            run.errors.append(error)
            return run

    async def get_run(self, run_id: str) -> ScrapeRun | None:
        async with self._lock:
            return self._runs.get(run_id)

    async def list_runs(self, *, limit: int = 20) -> list[ScrapeRun]:
        async with self._lock:
            runs = sorted(
                self._runs.values(),
                key=lambda r: r.started_at,
                reverse=True,
            )
            return runs[:limit]

    def _evict_old(self) -> None:
        if len(self._runs) <= self._max_history:
            return
        sorted_ids = sorted(
            self._runs,
            key=lambda rid: self._runs[rid].started_at,
        )
        excess = len(self._runs) - self._max_history
        for rid in sorted_ids[:excess]:
            del self._runs[rid]


_scrape_run_service: ScrapeRunService | None = None


def get_scrape_run_service() -> ScrapeRunService:
    global _scrape_run_service  # noqa: PLW0603
    if _scrape_run_service is None:
        _scrape_run_service = ScrapeRunService()
    return _scrape_run_service
