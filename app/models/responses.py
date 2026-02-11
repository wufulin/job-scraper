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
