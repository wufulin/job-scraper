from __future__ import annotations

import json
import math
from typing import Optional

from app.models.responses import JobListResponse, JobResponse, PaginationMeta
from app.services.storage import SupabaseStorage, get_storage


class JobService:

    def __init__(self, storage: Optional[SupabaseStorage] = None) -> None:
        self._storage = storage or get_storage()

    async def list_jobs(
        self,
        page: int = 1,
        per_page: int = 20,
        source: Optional[str] = None,
    ) -> JobListResponse:
        all_jobs = await self._storage.get_all_jobs(source=source)

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
        job = await self._storage.get_job_by_id(job_id)
        if job:
            return self._to_response(job)
        return None

    async def search_jobs(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        source: Optional[str] = None,
    ) -> JobListResponse:
        all_jobs = await self._storage.get_all_jobs(source=source)

        q_lower = query.lower()
        matched = []
        for j in all_jobs:
            if hasattr(j, "title"):
                # JobPosting object
                title = j.title or ""
                description = j.description or ""
            else:
                # dict
                title = j.get("title") or ""
                description = j.get("description") or ""
            if q_lower in title.lower() or q_lower in description.lower():
                matched.append(j)

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
    def _to_response(job):
        # Handle both dict (from SupabaseStorage) and JobPosting (from tests/mocks)
        if hasattr(job, "model_dump"):
            # It's a JobPosting or similar Pydantic model
            return JobResponse(**job.model_dump())
        else:
            # It's a dict from SupabaseStorage
            # Handle tags which may be JSON string from Supabase
            tags = job.get("tags", [])
            if isinstance(tags, str):
                tags = json.loads(tags)
            data = dict(job)
            data["tags"] = tags
            return JobResponse(**data)
