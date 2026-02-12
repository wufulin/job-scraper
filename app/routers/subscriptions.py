from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_current_user
from app.models.responses import (
    CreateSubscriptionRequest,
    SubscriptionListResponse,
    SubscriptionResponse,
    ToggleSubscriptionRequest,
    UpdateSubscriptionRequest,
    UserPayload,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api", tags=["subscriptions"])


def get_subscription_service() -> SubscriptionService:
    return SubscriptionService()


@router.get("/subscriptions", response_model=SubscriptionListResponse)
async def list_subscriptions(
    user: UserPayload = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionListResponse:
    return await service.list_subscriptions(user_id=user.sub, page=page, per_page=per_page)


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    request: CreateSubscriptionRequest,
    user: UserPayload = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    return await service.create_subscription(
        user_id=user.sub,
        name=request.name,
        keywords=request.keywords,
        match_mode=request.match_mode,
        sources=request.sources,
    )


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    user: UserPayload = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    subscription = await service.get_subscription(user_id=user.sub, subscription_id=subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


@router.put("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    request: UpdateSubscriptionRequest,
    user: UserPayload = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    subscription = await service.update_subscription(
        user_id=user.sub,
        subscription_id=subscription_id,
        name=request.name,
        keywords=request.keywords,
        match_mode=request.match_mode,
        sources=request.sources,
        is_active=request.is_active,
    )
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


@router.delete("/subscriptions/{subscription_id}", status_code=204)
async def delete_subscription(
    subscription_id: int,
    user: UserPayload = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> None:
    success = await service.delete_subscription(user_id=user.sub, subscription_id=subscription_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")


@router.post("/subscriptions/{subscription_id}/toggle", response_model=SubscriptionResponse)
async def toggle_subscription(
    subscription_id: int,
    request: ToggleSubscriptionRequest,
    user: UserPayload = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    subscription = await service.toggle_subscription(
        user_id=user.sub,
        subscription_id=subscription_id,
        is_active=request.is_active,
    )
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription
