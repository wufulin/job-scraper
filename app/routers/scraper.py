from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.services.scraper_service import get_scraper_service

router = APIRouter(prefix="/api", tags=["scraper"])


class ScrapeRequest(BaseModel):
    sites: Optional[list[str]] = None
    dry_run: bool = False


@router.post("/scrape", status_code=202)
async def trigger_scrape(
    body: ScrapeRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    service = get_scraper_service()
    run_id = service.trigger_scrape(
        background_tasks,
        sites=body.sites,
        dry_run=body.dry_run,
    )
    return {"run_id": run_id, "status": "started"}


@router.get("/scrape/status/{run_id}")
async def scrape_status(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "status": "unknown",
        "message": "Status tracking will be available in Phase 3",
    }
