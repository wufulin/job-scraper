from __future__ import annotations

from copy import deepcopy
from typing import Optional

from scraper.models import JobPosting


class FakeStorage:

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._healthy: bool = True

    async def init_pool(self) -> None:
        pass

    async def close_pool(self) -> None:
        pass

    async def upsert_job(self, job: JobPosting) -> tuple[int, int]:
        row = self._job_to_row(job)
        if job.id in self._jobs:
            existing = self._jobs[job.id]
            row["first_seen"] = existing["first_seen"]
            row["update_count"] = existing["update_count"] + 1
            self._jobs[job.id] = row
            return (0, 1)
        self._jobs[job.id] = row
        return (1, 0)

    async def upsert_jobs_batch(self, jobs: list[JobPosting]) -> tuple[int, int]:
        total_new = 0
        total_updated = 0
        for job in jobs:
            new, updated = await self.upsert_job(job)
            total_new += new
            total_updated += updated
        return (total_new, total_updated)

    async def get_all_jobs(self, source: Optional[str] = None) -> list[dict]:
        rows = list(self._jobs.values())
        if source:
            rows = [r for r in rows if r["source"] == source]
        rows.sort(key=lambda r: r["first_seen"], reverse=True)
        return [deepcopy(r) for r in rows]

    async def get_job_by_id(self, job_id: str) -> Optional[dict]:
        row = self._jobs.get(job_id)
        return deepcopy(row) if row else None

    async def get_stats(self) -> dict:
        by_source: dict[str, int] = {}
        for row in self._jobs.values():
            src = row["source"]
            by_source[src] = by_source.get(src, 0) + 1
        return {
            "total": len(self._jobs),
            "by_source": by_source,
        }

    async def export_jobs(self, source: Optional[str] = None) -> list[dict]:
        return await self.get_all_jobs(source=source)

    async def health_check(self) -> bool:
        return self._healthy

    @staticmethod
    def _job_to_row(job: JobPosting) -> dict:
        return {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "url": job.url,
            "source": job.source,
            "published_at": job.published_at,
            "salary": job.salary,
            "location": job.location,
            "description": job.description,
            "tags": job.tags,
            "first_seen": job.first_seen,
            "last_seen": job.last_seen,
            "last_updated": job.last_updated,
            "update_count": job.update_count,
            "is_active": True,
        }
