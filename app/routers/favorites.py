from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_current_user
from app.models.responses import (
    AddFavoriteRequest,
    FavoriteListResponse,
    FavoriteResponse,
    UserPayload,
)
from app.services.favorite_service import FavoriteService

router = APIRouter(prefix="/api", tags=["favorites"])


def get_favorite_service() -> FavoriteService:
    return FavoriteService()


@router.get("/favorites", response_model=FavoriteListResponse)
async def list_favorites(
    user: UserPayload = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    service: FavoriteService = Depends(get_favorite_service),
) -> FavoriteListResponse:
    return await service.list_favorites(user_id=user.sub, page=page, per_page=per_page)


@router.post("/favorites", response_model=FavoriteResponse, status_code=201)
async def add_favorite(
    request: AddFavoriteRequest,
    user: UserPayload = Depends(get_current_user),
    service: FavoriteService = Depends(get_favorite_service),
) -> FavoriteResponse:
    return await service.add_favorite(user_id=user.sub, job_id=request.job_id)


@router.delete("/favorites/{job_id}", status_code=204)
async def remove_favorite(
    job_id: str,
    user: UserPayload = Depends(get_current_user),
    service: FavoriteService = Depends(get_favorite_service),
) -> None:
    success = await service.remove_favorite(user_id=user.sub, job_id=job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
