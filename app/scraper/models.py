"""Data models for job scraper."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, field_validator


VALID_SOURCES = {"remoteok", "eleduck", "weworkremotely", "workgo", "v2ex", "arcdev", "yuancheng"}


class JobPosting(BaseModel):
    """Job posting data model for Phase 1.
    
    Represents a job posting with all metadata needed for storage and retrieval.
    Uses str for url field (not HttpUrl) for SQLite compatibility.
    """
    
    id: str
    title: str
    company: Optional[str] = None
    url: str  # NOT HttpUrl - SQLite compatibility
    source: str
    published_at: Optional[datetime] = None
    salary: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = []
    first_seen: datetime = None
    last_seen: datetime = None
    last_updated: datetime = None
    update_count: int = 1
    
    def __init__(self, **data):
        """Initialize JobPosting with timezone-aware datetime defaults."""
        if "first_seen" not in data or data["first_seen"] is None:
            data["first_seen"] = datetime.now(timezone.utc)
        if "last_seen" not in data or data["last_seen"] is None:
            data["last_seen"] = datetime.now(timezone.utc)
        if "last_updated" not in data or data["last_updated"] is None:
            data["last_updated"] = datetime.now(timezone.utc)
        super().__init__(**data)
    
    model_config = {"arbitrary_types_allowed": True}
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Strip whitespace and ensure title is not empty."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Title must not be empty after stripping whitespace")
        return stripped
    
    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Ensure source is one of the valid Phase 1 + Phase 2 sources."""
        if v not in VALID_SOURCES:
            raise ValueError(
                f"Source must be one of {VALID_SOURCES}, got: {v}"
            )
        return v
    
    @staticmethod
    def generate_id(url: str, title: str) -> str:
        """Generate a unique ID for a job posting using MD5 hash.
        
        Args:
            url: Job posting URL
            title: Job posting title
            
        Returns:
            MD5 hash hex string
        """
        content = f"{url}|{title}".lower()
        return hashlib.md5(content.encode()).hexdigest()
    
    def to_pg_dict(self) -> dict:
        """Serialize model to PostgreSQL-compatible dict.
        
        Converts:
        - datetime fields → timezone-aware datetime objects (not ISO strings)
        - list fields (tags) → list[str] (not JSON string)
        - None values → None
        
        Returns:
            Dictionary with PostgreSQL-native types for asyncpg
        """
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at,
            "salary": self.salary,
            "location": self.location,
            "description": self.description,
            "tags": self.tags,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "last_updated": self.last_updated,
            "update_count": self.update_count,
        }

