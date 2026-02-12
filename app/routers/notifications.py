from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_current_user
from app.models.responses import (
    NotificationListResponse,
    UnreadCountResponse,
    UserPayload,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api", tags=["notifications"])


def get_notification_service() -> NotificationService:
    return NotificationService()


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    user: UserPayload = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    return await service.get_notifications(
        user_id=user.sub, page=page, per_page=per_page, unread_only=unread_only
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    user: UserPayload = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> UnreadCountResponse:
    return await service.get_unread_count(user_id=user.sub)


@router.post("/notifications/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: str,
    user: UserPayload = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> None:
    success = await service.mark_read(notification_id=notification_id, user_id=user.sub)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.post("/notifications/read-all", status_code=204)
async def mark_all_notifications_read(
    user: UserPayload = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> None:
    await service.mark_all_read(user_id=user.sub)
