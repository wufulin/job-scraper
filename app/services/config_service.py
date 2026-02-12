from __future__ import annotations

import time
from typing import Any, Optional

from loguru import logger

_DEFAULT_CACHE_TTL = 300


class ConfigService:

    def __init__(
        self,
        pool: Any = None,
        cache_ttl_seconds: int = _DEFAULT_CACHE_TTL,
    ) -> None:
        self._pool = pool
        self._cache_ttl = cache_ttl_seconds
        self._site_cache: Optional[list[dict]] = None
        self._site_cache_ts: float = 0.0
        self._keyword_cache: Optional[list[dict]] = None
        self._keyword_cache_ts: float = 0.0

    def _is_fresh(self, ts: float) -> bool:
        return (time.monotonic() - ts) < self._cache_ttl

    async def get_site_configs(self) -> list[dict]:
        if self._site_cache is not None and self._is_fresh(self._site_cache_ts):
            return self._site_cache

        rows = await self._pool.fetch(
            "SELECT id, site_key, name, url, adapter, enabled, skip_location_match, "
            "rate_limit_seconds, max_pages, extra_config, created_at, updated_at "
            "FROM site_configs ORDER BY id"
        )
        self._site_cache = [
            {
                "id": r["id"],
                "site_key": r["site_key"],
                "name": r["name"],
                "url": r["url"],
                "adapter": r["adapter"],
                "enabled": r["enabled"],
                "skip_location_match": r["skip_location_match"],
                "rate_limit_seconds": r["rate_limit_seconds"],
                "max_pages": r["max_pages"],
                "extra_config": r["extra_config"],
            }
            for r in rows
        ]
        self._site_cache_ts = time.monotonic()
        return self._site_cache

    async def get_site_config_by_id(self, site_id: str) -> Optional[dict]:
        row = await self._pool.fetchrow(
            "SELECT id, site_key, name, url, adapter, enabled, skip_location_match, "
            "rate_limit_seconds, max_pages, extra_config "
            "FROM site_configs WHERE id = $1",
            site_id,
        )
        if row is None:
            return None
        return {
            "id": row["id"],
            "site_key": row["site_key"],
            "name": row["name"],
            "url": row["url"],
            "adapter": row["adapter"],
            "enabled": row["enabled"],
            "skip_location_match": row["skip_location_match"],
            "rate_limit_seconds": row["rate_limit_seconds"],
            "max_pages": row["max_pages"],
            "extra_config": row["extra_config"],
        }

    async def update_site_config(self, site_id: str, **kwargs: Any) -> None:
        set_clauses: list[str] = []
        values: list[Any] = []
        idx = 1

        field_map = {
            "enabled": "enabled",
            "rate_limit_seconds": "rate_limit_seconds",
            "max_pages": "max_pages",
            "skip_location_match": "skip_location_match",
            "extra_config": "extra_config",
        }

        for key, column in field_map.items():
            if key in kwargs:
                set_clauses.append(f"{column} = ${idx}")
                values.append(kwargs[key])
                idx += 1

        if not set_clauses:
            return

        set_clauses.append(f"updated_at = ${idx}")
        from datetime import datetime, timezone
        values.append(datetime.now(tz=timezone.utc))
        idx += 1

        values.append(site_id)
        sql = f"UPDATE site_configs SET {', '.join(set_clauses)} WHERE id = ${idx}"
        await self._pool.execute(sql, *values)
        self._invalidate_site_cache()
        logger.info("Updated site config: {}", site_id)

    async def get_keyword_configs(self) -> list[dict]:
        if self._keyword_cache is not None and self._is_fresh(self._keyword_cache_ts):
            return self._keyword_cache

        rows = await self._pool.fetch(
            "SELECT id, group_name, keyword, enabled, created_at "
            "FROM keyword_configs ORDER BY group_name, id"
        )
        self._keyword_cache = [
            {
                "id": r["id"],
                "group_name": r["group_name"],
                "keyword": r["keyword"],
                "enabled": r["enabled"],
            }
            for r in rows
        ]
        self._keyword_cache_ts = time.monotonic()
        return self._keyword_cache

    async def get_keyword_by_id(self, keyword_id: int) -> Optional[dict]:
        row = await self._pool.fetchrow(
            "SELECT id, group_name, keyword, enabled "
            "FROM keyword_configs WHERE id = $1",
            keyword_id,
        )
        if row is None:
            return None
        return {
            "id": row["id"],
            "group_name": row["group_name"],
            "keyword": row["keyword"],
            "enabled": row["enabled"],
        }

    async def update_keyword(self, keyword_id: int, **kwargs: Any) -> None:
        set_clauses: list[str] = []
        values: list[Any] = []
        idx = 1

        if "enabled" in kwargs:
            set_clauses.append(f"enabled = ${idx}")
            values.append(kwargs["enabled"])
            idx += 1

        if not set_clauses:
            return

        values.append(keyword_id)
        sql = f"UPDATE keyword_configs SET {', '.join(set_clauses)} WHERE id = ${idx}"
        await self._pool.execute(sql, *values)
        self._invalidate_keyword_cache()
        logger.info("Updated keyword config: {}", keyword_id)

    async def add_keyword(self, group_name: str, keyword: str) -> dict:
        await self._pool.execute(
            "INSERT INTO keyword_configs (group_name, keyword, enabled) "
            "VALUES ($1, $2, true)",
            group_name,
            keyword,
        )
        self._invalidate_keyword_cache()
        logger.info("Added keyword: {} / {}", group_name, keyword)
        return {"id": 0, "group_name": group_name, "keyword": keyword, "enabled": True}

    async def get_match_rules(self) -> list[dict]:
        rows = await self._pool.fetch(
            "SELECT id, rule_name, expression, skip_location_for "
            "FROM match_rules ORDER BY id"
        )
        return [
            {
                "rule_name": r["rule_name"],
                "expression": r["expression"],
                "skip_location_for": list(r["skip_location_for"]),
            }
            for r in rows
        ]

    def _invalidate_site_cache(self) -> None:
        self._site_cache = None
        self._site_cache_ts = 0.0

    def _invalidate_keyword_cache(self) -> None:
        self._keyword_cache = None
        self._keyword_cache_ts = 0.0
