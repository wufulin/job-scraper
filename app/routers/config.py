from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user, require_admin
from app.models.responses import (
    KeywordConfigResponse,
    KeywordCreate,
    KeywordUpdate,
    SiteConfigResponse,
    SiteConfigUpdate,
    UserPayload,
)
from app.services.config_service import ConfigService

router = APIRouter(prefix="/api/config", tags=["config"])

_config_service: ConfigService | None = None


def get_config_service() -> ConfigService:
    global _config_service  # noqa: PLW0603
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service


@router.get("/sites", response_model=list[SiteConfigResponse])
async def list_sites(
    _user: UserPayload = Depends(get_current_user),
) -> list[dict]:
    svc = get_config_service()
    return await svc.get_site_configs()


@router.put("/sites/{site_id}", response_model=SiteConfigResponse)
async def update_site(
    site_id: str,
    body: SiteConfigUpdate,
    _admin: UserPayload = Depends(require_admin),
) -> dict:
    svc = get_config_service()
    update_fields = body.model_dump(exclude_none=True)
    if update_fields:
        await svc.update_site_config(site_id, **update_fields)
    result = await svc.get_site_config_by_id(site_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
    return result


@router.get("/keywords", response_model=list[KeywordConfigResponse])
async def list_keywords(
    _user: UserPayload = Depends(get_current_user),
) -> list[dict]:
    svc = get_config_service()
    return await svc.get_keyword_configs()


@router.post("/keywords", response_model=KeywordConfigResponse, status_code=201)
async def add_keyword(
    body: KeywordCreate,
    _admin: UserPayload = Depends(require_admin),
) -> dict:
    svc = get_config_service()
    return await svc.add_keyword(group_name=body.group_name, keyword=body.keyword)


@router.put("/keywords/{keyword_id}", response_model=KeywordConfigResponse)
async def update_keyword(
    keyword_id: int,
    body: KeywordUpdate,
    _admin: UserPayload = Depends(require_admin),
) -> dict:
    svc = get_config_service()
    update_fields = body.model_dump(exclude_none=True)
    if update_fields:
        await svc.update_keyword(keyword_id, **update_fields)
    result = await svc.get_keyword_by_id(keyword_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Keyword {keyword_id} not found")
    return result
