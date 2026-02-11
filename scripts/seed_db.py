"""Seed site_configs and keyword_configs tables from YAML config files."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import asyncpg
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SITES_YAML = PROJECT_ROOT / "config" / "sites.yaml"
KEYWORDS_YAML = PROJECT_ROOT / "config" / "keywords.yaml"

CREATE_SITE_CONFIGS = """
CREATE TABLE IF NOT EXISTS site_configs (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    url             TEXT NOT NULL,
    adapter         TEXT NOT NULL,
    enabled         BOOLEAN NOT NULL DEFAULT true,
    skip_location_match BOOLEAN NOT NULL DEFAULT false,
    rate_limit_seconds INTEGER NOT NULL DEFAULT 2,
    max_pages       INTEGER,
    config_json     TEXT NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

CREATE_KEYWORD_CONFIGS = """
CREATE TABLE IF NOT EXISTS keyword_configs (
    id              SERIAL PRIMARY KEY,
    group_name      TEXT NOT NULL,
    keyword         TEXT NOT NULL,
    enabled         BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (group_name, keyword)
);
"""

UPSERT_SITE = """
INSERT INTO site_configs (id, name, url, adapter, enabled, skip_location_match,
                          rate_limit_seconds, max_pages, config_json)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    url = EXCLUDED.url,
    adapter = EXCLUDED.adapter,
    enabled = EXCLUDED.enabled,
    skip_location_match = EXCLUDED.skip_location_match,
    rate_limit_seconds = EXCLUDED.rate_limit_seconds,
    max_pages = EXCLUDED.max_pages,
    config_json = EXCLUDED.config_json,
    updated_at = now()
"""

UPSERT_KEYWORD = """
INSERT INTO keyword_configs (group_name, keyword, enabled)
VALUES ($1, $2, true)
ON CONFLICT (group_name, keyword) DO NOTHING
"""


def _build_config_json(site_data: dict) -> str:
    extra: dict = {}
    passthrough_keys = {"headers", "params", "api_url", "api_base", "clerk_base", "page_size"}
    for key in passthrough_keys:
        if key in site_data:
            extra[key] = site_data[key]
    return json.dumps(extra, ensure_ascii=False)


async def seed(database_url: str) -> None:
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(CREATE_SITE_CONFIGS)
        await conn.execute(CREATE_KEYWORD_CONFIGS)

        with open(SITES_YAML, encoding="utf-8") as f:
            sites_data = yaml.safe_load(f)

        site_count = 0
        for site_id, site_data in sites_data.get("sites", {}).items():
            await conn.execute(
                UPSERT_SITE,
                site_id,
                site_data.get("name", site_id),
                site_data["url"],
                site_data["adapter"],
                site_data.get("enabled", True),
                site_data.get("skip_location_match", False),
                site_data.get("rate_limit_seconds", 2),
                site_data.get("max_pages"),
                _build_config_json(site_data),
            )
            site_count += 1

        with open(KEYWORDS_YAML, encoding="utf-8") as f:
            keywords_data = yaml.safe_load(f)

        keyword_count = 0
        for group_name, keywords in keywords_data.get("keyword_groups", {}).items():
            for keyword in keywords:
                await conn.execute(UPSERT_KEYWORD, group_name, keyword)
                keyword_count += 1

        print(f"Seeded {site_count} sites and {keyword_count} keywords")
    finally:
        await conn.close()


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <DATABASE_URL>")
        sys.exit(1)

    database_url = sys.argv[1]
    asyncio.run(seed(database_url))


if __name__ == "__main__":
    main()
