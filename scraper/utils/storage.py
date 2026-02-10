"""SQLite storage manager for job postings."""

import json

import aiosqlite
import aiosqlite.core
from datetime import datetime
from pathlib import Path
from typing import Optional

from scraper.models import JobPosting


# Schema DDL statements
_CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        company TEXT,
        url TEXT,
        source TEXT NOT NULL,
        published_at TEXT,
        salary TEXT,
        location TEXT,
        description TEXT,
        tags TEXT,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        last_updated TEXT NOT NULL,
        update_count INTEGER DEFAULT 1,
        is_active INTEGER DEFAULT 1
    )
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_source ON jobs(source)",
    "CREATE INDEX IF NOT EXISTS idx_company ON jobs(company)",
    "CREATE INDEX IF NOT EXISTS idx_is_active ON jobs(is_active)",
    "CREATE INDEX IF NOT EXISTS idx_first_seen ON jobs(first_seen)",
]


class StorageManager:
    """Manages SQLite storage for job postings.
    
    Handles:
    - Database initialization with proper schema and indexes
    - Upserting jobs (insert new, update existing)
    - Querying jobs with filters
    - Statistics and reporting
    - JSON export
    """
    
    def __init__(self, db_path: str = "data/jobs.db"):
        """Initialize storage manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Create data directory if needed
        db_dir = Path(db_path).parent
        if db_dir != Path(".") and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
        
        # Use aiosqlite's internal db module for synchronous schema init
        _sql3 = aiosqlite.core.sqlite3
        with _sql3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(_CREATE_TABLE)
            for idx_sql in _CREATE_INDEXES:
                cursor.execute(idx_sql)
            conn.commit()
    
    async def upsert_job(self, job: JobPosting) -> tuple[int, int]:
        """Insert new job or update existing one.
        
        On conflict (same id):
        - Updates last_seen, last_updated
        - Increments update_count
        - Preserves first_seen
        - Sets is_active=1
        
        Args:
            job: JobPosting instance to upsert
            
        Returns:
            Tuple of (new_count, updated_count)
        """
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.cursor()
            
            # Check if job exists
            await cursor.execute("SELECT id FROM jobs WHERE id = ?", (job.id,))
            exists = await cursor.fetchone() is not None
            
            # Get serialized data
            data = job.to_db_dict()
            
            if exists:
                # Update existing job
                await cursor.execute("""
                    UPDATE jobs SET
                        title = ?,
                        company = ?,
                        url = ?,
                        source = ?,
                        published_at = ?,
                        salary = ?,
                        location = ?,
                        description = ?,
                        tags = ?,
                        last_seen = ?,
                        last_updated = ?,
                        update_count = update_count + 1,
                        is_active = 1
                    WHERE id = ?
                """, (
                    data["title"],
                    data["company"],
                    data["url"],
                    data["source"],
                    data["published_at"],
                    data["salary"],
                    data["location"],
                    data["description"],
                    data["tags"],
                    data["last_seen"],
                    data["last_updated"],
                    data["id"]
                ))
                await conn.commit()
                return (0, 1)
            else:
                # Insert new job
                await cursor.execute("""
                    INSERT INTO jobs (
                        id, title, company, url, source, published_at,
                        salary, location, description, tags,
                        first_seen, last_seen, last_updated, update_count, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    data["id"],
                    data["title"],
                    data["company"],
                    data["url"],
                    data["source"],
                    data["published_at"],
                    data["salary"],
                    data["location"],
                    data["description"],
                    data["tags"],
                    data["first_seen"],
                    data["last_seen"],
                    data["last_updated"],
                    data["update_count"]
                ))
                await conn.commit()
                return (1, 0)
    
    async def get_all_jobs(self, active_only: bool = True) -> list[JobPosting]:
        """Retrieve all jobs from database.
        
        Args:
            active_only: If True, only return jobs with is_active=1
            
        Returns:
            List of JobPosting instances
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.cursor()
            
            if active_only:
                await cursor.execute("""
                    SELECT * FROM jobs 
                    WHERE is_active = 1
                    ORDER BY first_seen DESC
                """)
            else:
                await cursor.execute("""
                    SELECT * FROM jobs 
                    ORDER BY first_seen DESC
                """)
            
            rows = await cursor.fetchall()
            
            # Convert rows to JobPosting instances
            jobs = []
            for row in rows:
                # Convert Row to dict
                row_dict = dict(row)
                jobs.append(JobPosting.from_db_row(row_dict))
            
            return jobs
    
    async def get_stats(self) -> dict:
        """Get statistics about stored jobs.
        
        Returns:
            Dictionary with:
            - total: Total number of jobs
            - active: Number of active jobs
            - inactive: Number of inactive jobs
            - by_source: Dict mapping source name to count
        """
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.cursor()
            
            # Total count
            await cursor.execute("SELECT COUNT(*) FROM jobs")
            row = await cursor.fetchone()
            total = row[0]
            
            # Active count
            await cursor.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1")
            row = await cursor.fetchone()
            active = row[0]
            
            # Inactive count
            inactive = total - active
            
            # Count by source
            await cursor.execute("""
                SELECT source, COUNT(*) as count 
                FROM jobs 
                WHERE is_active = 1
                GROUP BY source
            """)
            rows = await cursor.fetchall()
            by_source = {row[0]: row[1] for row in rows}
            
            return {
                "total": total,
                "active": active,
                "inactive": inactive,
                "by_source": by_source
            }
    
    async def export_json(self, filepath: str) -> None:
        """Export active jobs to JSON file.
        
        Args:
            filepath: Path to output JSON file
        """
        jobs = await self.get_all_jobs(active_only=True)
        
        # Convert to serializable dicts
        jobs_data = [job.model_dump(mode="json") for job in jobs]
        
        # Ensure parent directory exists
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSON file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(jobs_data, f, ensure_ascii=False, indent=2)
