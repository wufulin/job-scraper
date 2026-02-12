"""Data models for job scraper."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, field_validator


def _load_valid_sources() -> set[str]:
    """Load valid sources from database or fallback to hardcoded set.
    
    Returns:
        Set of valid site_ids. Falls back to hardcoded set if DB unavailable.
    """
    try:
        import asyncio
        import asyncpg
        from app.config.settings import settings
        
        async def _fetch_from_db() -> set[str]:
            try:
                conn = await asyncpg.connect(settings.database_url)
                rows = await conn.fetch("SELECT site_id FROM site_configs WHERE enabled = true")
                await conn.close()
                return {row["site_id"] for row in rows}
            except Exception:
                return None
        
        result = asyncio.run(_fetch_from_db())
        if result:
            return result
    except Exception:
        pass
    
    return {"remoteok", "eleduck", "weworkremotely", "workgo", "v2ex", "arcdev", "yuancheng"}


VALID_SOURCES = _load_valid_sources()


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
    def from_pg_row(cls, row) -> JobPosting:
        """Deserialize from PostgreSQL row (asyncpg.Record).
        
        Accepts:
        - asyncpg.Record with timezone-aware datetime objects
        - list[str] for tags (native PostgreSQL array)
        
        Args:
            row: asyncpg.Record with columns matching JobPosting fields
            
        Returns:
            JobPosting instance
        """
        return cls(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            url=row["url"],
            source=row["source"],
            published_at=row["published_at"],
            salary=row["salary"],
            location=row["location"],
            description=row["description"],
            tags=row["tags"] if row["tags"] else [],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            last_updated=row["last_updated"],
            update_count=row["update_count"],
        )
    
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
