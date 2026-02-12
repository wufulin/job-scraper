from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import Response

from app.services.storage import get_storage

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats() -> dict:
    storage = get_storage()
    return await storage.get_stats()


@router.get("/export")
async def export_jobs() -> Response:
    storage = get_storage()
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
