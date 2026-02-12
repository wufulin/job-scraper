from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import Response

from app.services.storage import SupabaseStorage

router = APIRouter(prefix="/api", tags=["stats"])


async def get_storage() -> SupabaseStorage:
    storage = SupabaseStorage()
    await storage.init_pool()
    return storage


@router.get("/stats")
async def get_stats() -> dict:
    storage = await get_storage()
    return await storage.get_stats()


@router.get("/export")
async def export_jobs() -> Response:
    storage = await get_storage()
    jobs = await storage.get_all_jobs()

    jobs_data = []
    for job in jobs:
        jobs_data.append(job)

    content = json.dumps(jobs_data, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="jobs.json"'},
    )
