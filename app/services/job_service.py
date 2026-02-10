# Temporary: wraps StorageManager until Supabase migration (Phase 2)
from __future__ import annotations

import math
from typing import Optional

from scraper.models import JobPosting
from scraper.utils.storage import StorageManager

from app.models.responses import JobListResponse, JobResponse, PaginationMeta


class JobService:

    def __init__(self, storage: Optional[StorageManager] = None) -> None:
        self._storage = storage or StorageManager()

    async def list_jobs(
        self,
        page: int = 1,
        per_page: int = 20,
        source: Optional[str] = None,
    ) -> JobListResponse:
        all_jobs = await self._storage.get_all_jobs(active_only=True)

        if source:
            all_jobs = [j for j in all_jobs if j.source == source]

        total = len(all_jobs)
        total_pages = max(1, math.ceil(total / per_page))

        start = (page - 1) * per_page
        end = start + per_page
        page_jobs = all_jobs[start:end]

        return JobListResponse(
            data=[self._to_response(j) for j in page_jobs],
            pagination=PaginationMeta(
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def get_job(self, job_id: str) -> Optional[JobResponse]:
        all_jobs = await self._storage.get_all_jobs(active_only=True)
        for job in all_jobs:
            if job.id == job_id:
                return self._to_response(job)
        return None

    async def search_jobs(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        source: Optional[str] = None,
    ) -> JobListResponse:
        all_jobs = await self._storage.get_all_jobs(active_only=True)

        if source:
            all_jobs = [j for j in all_jobs if j.source == source]

        q_lower = query.lower()
        matched = [
            j
            for j in all_jobs
            if q_lower in (j.title or "").lower()
            or q_lower in (j.description or "").lower()
        ]

        total = len(matched)
        total_pages = max(1, math.ceil(total / per_page))

        start = (page - 1) * per_page
        end = start + per_page
        page_jobs = matched[start:end]

        return JobListResponse(
            data=[self._to_response(j) for j in page_jobs],
            pagination=PaginationMeta(
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
            ),
        )

    @staticmethod
    def _to_response(job: JobPosting) -> JobResponse:
        return JobResponse(
            id=job.id,
            title=job.title,
            company=job.company,
            url=job.url,
            source=job.source,
            published_at=job.published_at,
            salary=job.salary,
            location=job.location,
            description=job.description,
            tags=job.tags,
            first_seen=job.first_seen,
            last_seen=job.last_seen,
            last_updated=job.last_updated,
            update_count=job.update_count,
        )
