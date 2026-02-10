from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.responses import JobListResponse, JobResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/api", tags=["jobs"])


def get_job_service() -> JobService:
    return JobService()


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    source: Optional[str] = Query(default=None),
) -> JobListResponse:
    service = get_job_service()
    return await service.list_jobs(page=page, per_page=per_page, source=source)


@router.get("/jobs/search", response_model=JobListResponse)
async def search_jobs(
    q: str = Query(..., min_length=1),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    source: Optional[str] = Query(default=None),
) -> JobListResponse:
    service = get_job_service()
    return await service.search_jobs(query=q, page=page, per_page=per_page, source=source)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    service = get_job_service()
    job = await service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job
