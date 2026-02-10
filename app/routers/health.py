from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config.settings import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
