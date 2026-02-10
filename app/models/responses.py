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
