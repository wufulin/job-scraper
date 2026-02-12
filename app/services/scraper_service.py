from __future__ import annotations

import uuid

from fastapi import BackgroundTasks
from loguru import logger

from app.scraper.orchestrator import ScraperOrchestrator
from app.services.config_service import ConfigService
from app.services.scrape_run_service import get_scrape_run_service
from app.services.storage import SupabaseStorage, get_storage


class ScraperService:

    def __init__(self, storage: SupabaseStorage | None = None) -> None:
        self._storage = storage or get_storage()

    def trigger_scrape(
        self,
        background_tasks: BackgroundTasks,
        *,
        sites: list[str] | None = None,
        dry_run: bool = False,
    ) -> str:
        run_id = uuid.uuid4().hex[:12]

        if sites:
            for site in sites:
                background_tasks.add_task(
                    self._tracked_scrape, run_id=run_id, site=site, dry_run=dry_run,
                    sites_list=sites,
                )
        else:
            background_tasks.add_task(
                self._tracked_scrape, run_id=run_id, site=None, dry_run=dry_run,
                sites_list=None,
            )

        logger.info("Scrape triggered — run_id={}, sites={}, dry_run={}", run_id, sites, dry_run)
        return run_id

    async def _tracked_scrape(
        self,
        *,
        run_id: str,
        site: str | None,
        dry_run: bool,
        sites_list: list[str] | None,
    ) -> dict:
        run_service = get_scrape_run_service()
        await run_service.start_run(
            run_id, trigger="manual", sites=sites_list, dry_run=dry_run
        )
        try:
            summary = await self._run_scrape(run_id=run_id, site=site, dry_run=dry_run)
            await run_service.complete_run(
                run_id,
                matched=summary.get("matched", 0),
                new=summary.get("new", 0),
                updated=summary.get("updated", 0),
            )
            return summary
        except Exception as exc:
            await run_service.fail_run(run_id, error=str(exc))
            raise

    # ------------------------------------------------------------------
    # Config helpers — transform DB rows → orchestrator config dicts
    # ------------------------------------------------------------------

    @staticmethod
    def _build_sites_config(site_rows: list[dict]) -> dict:
        sites: dict = {}
        for row in site_rows:
            key = row["site_key"]
            cfg: dict = {
                "name": row.get("name", key),
                "url": row["url"],
                "adapter": row["adapter"],
                "enabled": row.get("enabled", True),
            }
            if row.get("skip_location_match") is not None:
                cfg["skip_location_match"] = row["skip_location_match"]
            if row.get("rate_limit_seconds") is not None:
                cfg["rate_limit_seconds"] = row["rate_limit_seconds"]
            if row.get("max_pages") is not None:
                cfg["max_pages"] = row["max_pages"]
            extra = row.get("extra_config")
            if extra and isinstance(extra, dict):
                cfg.update(extra)
            sites[key] = cfg
        return sites

    @staticmethod
    def _build_keywords_config(
        keyword_rows: list[dict],
        match_rules: list[dict],
    ) -> dict:
        keyword_groups: dict[str, list[str]] = {}
        for row in keyword_rows:
            if not row.get("enabled", True):
                continue
            group = row["group_name"]
            keyword_groups.setdefault(group, []).append(row["keyword"])

        rule = match_rules[0] if match_rules else {}
        return {
            "keyword_groups": keyword_groups,
            "match_rules": {
                "default": rule.get("expression", "location AND technology"),
                "skip_location_for": rule.get("skip_location_for", []),
            },
        }

    async def _run_scrape(
        self, *, run_id: str, site: str | None, dry_run: bool
    ) -> dict:
        logger.info("Background scrape started — run_id={}, site={}", run_id, site)
        try:
            if self._storage is None:
                self._storage = get_storage()
            config_svc = ConfigService(pool=self._storage._pool)  # noqa: SLF001
            site_rows = await config_svc.get_site_configs()
            keyword_rows = await config_svc.get_keyword_configs()
            match_rules = await config_svc.get_match_rules()

            sites_config = self._build_sites_config(site_rows)
            keywords_config = self._build_keywords_config(keyword_rows, match_rules)

            orchestrator = ScraperOrchestrator(
                sites_config=sites_config,
                keywords_config=keywords_config,
                storage=self._storage,
            )
            summary = await orchestrator.run(site=site, dry_run=dry_run)
            logger.info("Background scrape finished — run_id={}, summary={}", run_id, summary)
            return summary
        except Exception as exc:
            logger.error("Background scrape failed — run_id={}, error={}", run_id, exc)
            raise


_scraper_service: ScraperService | None = None


def get_scraper_service() -> ScraperService:
    global _scraper_service  # noqa: PLW0603
    if _scraper_service is None:
        _scraper_service = ScraperService()
    return _scraper_service
