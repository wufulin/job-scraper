from __future__ import annotations

import math
from typing import Optional

import asyncpg

from app.models.responses import FavoriteListResponse, FavoriteResponse, PaginationMeta


class FakeFavoriteService:

    async def list_favorites(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
    ) -> FavoriteListResponse:
        return FavoriteListResponse(
            data=[],
            pagination=PaginationMeta(
                page=page,
                per_page=per_page,
                total=0,
                total_pages=0,
            ),
        )

    async def add_favorite(self, user_id: str, job_id: str) -> FavoriteResponse:
        raise NotImplementedError()

    async def remove_favorite(self, user_id: str, job_id: str) -> bool:
        raise NotImplementedError()

    async def is_favorite(self, user_id: str, job_id: str) -> bool:
        raise NotImplementedError()


class FavoriteService:

    def __init__(self, pool: Optional[asyncpg.Pool] = None) -> None:
        self._pool = pool

    async def list_favorites(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
    ) -> FavoriteListResponse:
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        pool = self._pool
        
        total = await pool.fetchval(
            "SELECT COUNT(*) FROM favorites WHERE user_id = $1",
            user_id,
        )
        
        total_pages = max(1, math.ceil(total / per_page))
        offset = (page - 1) * per_page
        
        rows = await pool.fetch(
            "SELECT id, user_id, job_id, created_at FROM favorites "
            "WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            user_id,
            per_page,
            offset,
        )
        
        favorites = [
            FavoriteResponse(
                id=row["id"],
                user_id=row["user_id"],
                job_id=row["job_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
        
        return FavoriteListResponse(
            data=favorites,
            pagination=PaginationMeta(
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def add_favorite(self, user_id: str, job_id: str) -> FavoriteResponse:
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        pool = self._pool
        
        row = await pool.fetchrow(
            "INSERT INTO favorites (user_id, job_id) VALUES ($1, $2) "
            "ON CONFLICT (user_id, job_id) DO UPDATE SET user_id = EXCLUDED.user_id "
            "RETURNING id, user_id, job_id, created_at",
            user_id,
            job_id,
        )
        
        return FavoriteResponse(
            id=row["id"],
            user_id=row["user_id"],
            job_id=row["job_id"],
            created_at=row["created_at"],
        )

    async def remove_favorite(self, user_id: str, job_id: str) -> bool:
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        pool = self._pool
        
        result = await pool.execute(
            "DELETE FROM favorites WHERE user_id = $1 AND job_id = $2",
            user_id,
            job_id,
        )
        
        return result == "DELETE 1"

    async def is_favorite(self, user_id: str, job_id: str) -> bool:
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        pool = self._pool
        
        count = await pool.fetchval(
            "SELECT COUNT(*) FROM favorites WHERE user_id = $1 AND job_id = $2",
            user_id,
            job_id,
        )
        
        return count > 0
