"""Data models for job scraper."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


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
    first_seen: datetime
    last_seen: datetime
    last_updated: datetime
    update_count: int = 1
    
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
        """Ensure source is one of the valid Phase 1 sources."""
        valid_sources = {"remoteok", "eleduck", "weworkremotely"}
        if v not in valid_sources:
            raise ValueError(
                f"Source must be one of {valid_sources}, got: {v}"
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
    
    def to_db_dict(self) -> dict:
        """Serialize model to SQLite-compatible dict.
        
        Converts:
        - datetime fields → ISO format strings
        - list fields (tags) → JSON strings
        - None values → None (not "None")
        
        Returns:
            Dictionary with SQLite-compatible types
        """
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "salary": self.salary,
            "location": self.location,
            "description": self.description,
            "tags": json.dumps(self.tags),
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
        }
    
    @classmethod
    def from_db_row(cls, row: dict) -> JobPosting:
        """Deserialize from SQLite row dict.
        
        Converts:
        - ISO format strings → datetime objects
        - JSON strings → lists
        
        Args:
            row: Dictionary from SQLite row (column name → value)
            
        Returns:
            JobPosting instance
        """
        return cls(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            url=row["url"],
            source=row["source"],
            published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
            salary=row["salary"],
            location=row["location"],
            description=row["description"],
            tags=json.loads(row["tags"]),
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]),
            last_updated=datetime.fromisoformat(row["last_updated"]),
            update_count=row["update_count"],
        )
