from __future__ import annotations

from fastapi import APIRouter

from app.services.scrape_run_service import get_scrape_run_service
from app.services.scheduler import get_scheduler_service

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get("/status")
async def scheduler_status() -> dict:
    svc = get_scheduler_service()
    next_run = svc.get_next_run_time()
    return {
        "running": svc.is_running,
        "paused": svc.is_paused,
        "next_run_time": next_run.isoformat() if next_run else None,
    }


@router.post("/pause")
async def pause_scheduler() -> dict:
    svc = get_scheduler_service()
    svc.pause()
    return {"paused": True}


@router.post("/resume")
async def resume_scheduler() -> dict:
    svc = get_scheduler_service()
    svc.resume()
    return {"paused": False}


@router.get("/runs")
async def list_runs(limit: int = 20) -> dict:
    run_service = get_scrape_run_service()
    runs = await run_service.list_runs(limit=limit)
    return {"runs": [r.model_dump(mode="json") for r in runs]}


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    run_service = get_scrape_run_service()
    run = await run_service.get_run(run_id)
    if run is None:
        return {"run_id": run_id, "status": "not_found"}
    return run.model_dump(mode="json")
