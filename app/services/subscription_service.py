from __future__ import annotations

import math
from typing import Any, Optional

import asyncpg

from app.models.responses import (
    SubscriptionListResponse,
    SubscriptionResponse,
    PaginationMeta,
)


class SubscriptionService:

    def __init__(self, pool: Optional[asyncpg.Pool] = None) -> None:
        self._pool = pool

    async def list_subscriptions(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
    ) -> SubscriptionListResponse:
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        pool = self._pool
        
        total = await pool.fetchval(
            "SELECT COUNT(*) FROM subscriptions WHERE user_id = $1",
            user_id,
        )
        
        total_pages = max(1, math.ceil(total / per_page))
        offset = (page - 1) * per_page
        
        rows = await pool.fetch(
            "SELECT id, user_id, name, keywords, match_mode, sources, is_active, created_at, updated_at "
            "FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            user_id,
            per_page,
            offset,
        )
        
        subscriptions = [
            SubscriptionResponse(
                id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                keywords=row["keywords"] or [],
                match_mode=row["match_mode"],
                sources=row["sources"] or [],
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
        
        return SubscriptionListResponse(
            data=subscriptions,
            pagination=PaginationMeta(
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def create_subscription(
        self,
        user_id: str,
        name: str,
        keywords: list[str],
        match_mode: str = "any",
        sources: list[str] | None = None,
    ) -> SubscriptionResponse:
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        pool = self._pool
        sources = sources or []
        
        row = await pool.fetchrow(
            "INSERT INTO subscriptions (user_id, name, keywords, match_mode, sources, is_active) "
            "VALUES ($1, $2, $3, $4, $5, true) "
            "RETURNING id, user_id, name, keywords, match_mode, sources, is_active, created_at, updated_at",
            user_id,
            name,
            keywords,
            match_mode,
            sources,
        )
        
        return SubscriptionResponse(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            keywords=row["keywords"] or [],
            match_mode=row["match_mode"],
            sources=row["sources"] or [],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_subscription(self, user_id: str, subscription_id: int) -> Optional[SubscriptionResponse]:
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        pool = self._pool
        
        row = await pool.fetchrow(
            "SELECT id, user_id, name, keywords, match_mode, sources, is_active, created_at, updated_at "
            "FROM subscriptions WHERE id = $1 AND user_id = $2",
            subscription_id,
            user_id,
        )
        
        if not row:
            return None
        
        return SubscriptionResponse(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            keywords=row["keywords"] or [],
            match_mode=row["match_mode"],
            sources=row["sources"] or [],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def update_subscription(
        self,
        user_id: str,
        subscription_id: int,
        name: Optional[str] = None,
        keywords: Optional[list[str]] = None,
        match_mode: Optional[str] = None,
        sources: Optional[list[str]] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[SubscriptionResponse]:
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        pool = self._pool
        
        updates = []
        params: list[Any] = [subscription_id, user_id]
        
        if name is not None:
            updates.append(f"name = ${len(params) + 1}")
            params.append(name)
        
        if keywords is not None:
            updates.append(f"keywords = ${len(params) + 1}")
            params.append(keywords)
        
        if match_mode is not None:
            updates.append(f"match_mode = ${len(params) + 1}")
            params.append(match_mode)
        
        if sources is not None:
            updates.append(f"sources = ${len(params) + 1}")
            params.append(sources)
        
        if is_active is not None:
            updates.append(f"is_active = ${len(params) + 1}")
            params.append(is_active)
        
        if not updates:
            return await self.get_subscription(user_id, subscription_id)
        
        query = (
            "UPDATE subscriptions SET " + ", ".join(updates) + " "
            "WHERE id = $1 AND user_id = $2 "
            "RETURNING id, user_id, name, keywords, match_mode, sources, is_active, created_at, updated_at"
        )
        
        row = await pool.fetchrow(query, *params)
        
        if not row:
            return None
        
        return SubscriptionResponse(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            keywords=row["keywords"] or [],
            match_mode=row["match_mode"],
            sources=row["sources"] or [],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def delete_subscription(self, user_id: str, subscription_id: int) -> bool:
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        pool = self._pool
        
        result = await pool.execute(
            "DELETE FROM subscriptions WHERE id = $1 AND user_id = $2",
            subscription_id,
            user_id,
        )
        
        return result == "DELETE 1"

    async def toggle_subscription(self, user_id: str, subscription_id: int, is_active: bool) -> Optional[SubscriptionResponse]:
        return await self.update_subscription(
            user_id=user_id,
            subscription_id=subscription_id,
            is_active=is_active,
        )
