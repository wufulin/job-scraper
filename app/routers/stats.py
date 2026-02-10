from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import Response

from scraper.utils.storage import StorageManager

router = APIRouter(prefix="/api", tags=["stats"])


async def get_storage() -> StorageManager:
    return StorageManager()


@router.get("/stats")
async def get_stats() -> dict:
    storage = await get_storage()
    return await storage.get_stats()


@router.get("/export")
async def export_jobs() -> Response:
    storage = await get_storage()
    jobs = await storage.get_all_jobs(active_only=True)

    jobs_data = []
    for job in jobs:
        if hasattr(job, "model_dump"):
            jobs_data.append(job.model_dump(mode="json"))
        else:
            jobs_data.append(job)

    content = json.dumps(jobs_data, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="jobs.json"'},
    )
