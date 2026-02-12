"""Pydantic response models for the Jobs API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobResponse(BaseModel):
    """Single job response matching JobPosting fields."""

    id: str
    title: str
    company: Optional[str] = None
    url: str
    source: str
    published_at: Optional[datetime] = None
    salary: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = []
    first_seen: datetime
    last_seen: datetime
    last_updated: datetime
    update_count: int = 1


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    per_page: int
    total: int
    total_pages: int


class JobListResponse(BaseModel):
    """Paginated list of jobs with metadata."""

    data: list[JobResponse]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: str
    password: str


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response after successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Public user profile response."""

    id: str
    email: str
    created_at: datetime


class UserPayload(BaseModel):
    """Decoded JWT payload for the current user."""

    sub: str
    email: str
    role: str = "user"


class SiteConfigResponse(BaseModel):
    id: str
    name: str
    url: str
    adapter: str
    enabled: bool
    skip_location_match: bool = False
    rate_limit_seconds: int = 2
    max_pages: Optional[int] = None
    config_json: str = "{}"


class SiteConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    rate_limit_seconds: Optional[int] = None
    max_pages: Optional[int] = None
    skip_location_match: Optional[bool] = None
    config_json: Optional[str] = None


class KeywordConfigResponse(BaseModel):
    id: int
    group_name: str
    keyword: str
    enabled: bool


class KeywordCreate(BaseModel):
    group_name: str
    keyword: str


class KeywordUpdate(BaseModel):
    enabled: Optional[bool] = None


# ---------------------------------------------------------------------------
# Favorites models
# ---------------------------------------------------------------------------


class FavoriteResponse(BaseModel):
    """Single favorite response."""

    id: int
    user_id: str
    job_id: str
    created_at: datetime


class FavoriteListResponse(BaseModel):
    """Paginated list of favorites with metadata."""

    data: list[FavoriteResponse]
    pagination: PaginationMeta


class AddFavoriteRequest(BaseModel):
    """Request body to add a job to favorites."""

    job_id: str


# ---------------------------------------------------------------------------
# Subscriptions models
# ---------------------------------------------------------------------------


class SubscriptionResponse(BaseModel):
    """Single subscription response."""

    id: int
    user_id: str
    name: str
    keywords: list[str]
    match_mode: str = "any"
    sources: list[str] = []
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class SubscriptionListResponse(BaseModel):
    """Paginated list of subscriptions with metadata."""

    data: list[SubscriptionResponse]
    pagination: PaginationMeta


class CreateSubscriptionRequest(BaseModel):
    """Request body to create a subscription."""

    name: str
    keywords: list[str]
    match_mode: str = "any"
    sources: list[str] = []


class UpdateSubscriptionRequest(BaseModel):
    """Request body to update a subscription."""

    name: Optional[str] = None
    keywords: Optional[list[str]] = None
    match_mode: Optional[str] = None
    sources: Optional[list[str]] = None
    is_active: Optional[bool] = None


class ToggleSubscriptionRequest(BaseModel):
    """Request body to toggle subscription active status."""

    is_active: bool


# ---------------------------------------------------------------------------
# Notifications models
# ---------------------------------------------------------------------------


class NotificationResponse(BaseModel):
    """Single notification response."""

    id: str
    user_id: str
    type: str
    title: str
    body: Optional[str] = None
    job_id: Optional[str] = None
    is_read: bool = False
    email_sent: bool = False
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated list of notifications with metadata."""

    data: list[NotificationResponse]
    pagination: PaginationMeta


class UnreadCountResponse(BaseModel):
    count: int
