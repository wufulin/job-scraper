from __future__ import annotations

import json
from typing import Optional, Protocol, runtime_checkable

import asyncpg
from loguru import logger

from app.config.settings import settings
from scraper.models import JobPosting

_BATCH_SIZE = 100

_UPSERT_SQL = """
    INSERT INTO jobs (
        id, title, company, url, source, published_at,
        salary, location, description, tags,
        first_seen, last_seen, last_updated, update_count, is_active
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11, $12, $13, $14, true)
    ON CONFLICT (id) DO UPDATE SET
        title        = EXCLUDED.title,
        company      = EXCLUDED.company,
        url          = EXCLUDED.url,
        source       = EXCLUDED.source,
        published_at = EXCLUDED.published_at,
        salary       = EXCLUDED.salary,
        location     = EXCLUDED.location,
        description  = EXCLUDED.description,
        tags         = EXCLUDED.tags,
        last_seen    = EXCLUDED.last_seen,
        last_updated = EXCLUDED.last_updated,
        update_count = jobs.update_count + 1,
        is_active    = true
    RETURNING (xmax = 0) AS inserted
"""


@runtime_checkable
class StorageProtocol(Protocol):

    async def init_pool(self) -> None: ...
    async def close_pool(self) -> None: ...
    async def upsert_job(self, job: JobPosting) -> tuple[int, int]: ...
    async def upsert_jobs_batch(self, jobs: list[JobPosting]) -> tuple[int, int]: ...
    async def get_all_jobs(self, source: Optional[str] = None) -> list[dict]: ...
    async def get_job_by_id(self, job_id: str) -> Optional[dict]: ...
    async def get_stats(self) -> dict: ...
    async def export_jobs(self, source: Optional[str] = None) -> list[dict]: ...
    async def health_check(self) -> bool: ...


class SupabaseStorage:

    def __init__(self, database_url: Optional[str] = None) -> None:
        self._database_url = database_url or settings.DATABASE_URL
        self._pool: Optional[asyncpg.Pool] = None

    async def init_pool(self) -> None:
        self._pool = await asyncpg.create_pool(self._database_url)
        logger.info("asyncpg connection pool created")

    async def close_pool(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("asyncpg connection pool closed")

    async def upsert_job(self, job: JobPosting) -> tuple[int, int]:
        assert self._pool is not None, "Pool not initialised — call init_pool() first"
        params = self._job_to_params(job)
        row = await self._pool.fetchrow(_UPSERT_SQL, *params)
        if row and row["inserted"]:
            return (1, 0)
        return (0, 1)

    async def upsert_jobs_batch(self, jobs: list[JobPosting]) -> tuple[int, int]:
        assert self._pool is not None, "Pool not initialised — call init_pool() first"
        total_new = 0
        total_updated = 0

        for i in range(0, len(jobs), _BATCH_SIZE):
            batch = jobs[i : i + _BATCH_SIZE]
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    for job in batch:
                        params = self._job_to_params(job)
                        row = await conn.fetchrow(_UPSERT_SQL, *params)
                        if row and row["inserted"]:
                            total_new += 1
                        else:
                            total_updated += 1

        return (total_new, total_updated)

    async def get_all_jobs(self, source: Optional[str] = None) -> list[dict]:
        assert self._pool is not None, "Pool not initialised — call init_pool() first"
        if source:
            rows = await self._pool.fetch(
                "SELECT * FROM jobs WHERE is_active = true AND source = $1 "
                "ORDER BY first_seen DESC",
                source,
            )
        else:
            rows = await self._pool.fetch(
                "SELECT * FROM jobs WHERE is_active = true ORDER BY first_seen DESC"
            )
        return [dict(r) for r in rows]

    async def get_job_by_id(self, job_id: str) -> Optional[dict]:
        assert self._pool is not None, "Pool not initialised — call init_pool() first"
        row = await self._pool.fetchrow(
            "SELECT * FROM jobs WHERE id = $1", job_id
        )
        return dict(row) if row else None

    async def get_stats(self) -> dict:
        assert self._pool is not None, "Pool not initialised — call init_pool() first"
        total = await self._pool.fetchval("SELECT COUNT(*) FROM jobs")
        rows = await self._pool.fetch(
            "SELECT source, COUNT(*) AS count FROM jobs "
            "WHERE is_active = true GROUP BY source"
        )
        by_source = {r["source"]: r["count"] for r in rows}
        return {
            "total": total,
            "by_source": by_source,
        }

    async def export_jobs(self, source: Optional[str] = None) -> list[dict]:
        return await self.get_all_jobs(source=source)

    async def health_check(self) -> bool:
        if not self._pool:
            return False
        try:
            result = await self._pool.fetchval("SELECT 1")
            return result == 1
        except Exception:
            logger.exception("Health check failed")
            return False

    @staticmethod
    def _job_to_params(job: JobPosting) -> tuple:
        return (
            job.id,
            job.title,
            job.company,
            job.url,
            job.source,
            job.published_at,
            job.salary,
            job.location,
            job.description,
            json.dumps(job.tags),
            job.first_seen,
            job.last_seen,
            job.last_updated,
            job.update_count,
        )
