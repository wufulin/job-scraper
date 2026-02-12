from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scraper.models import JobPosting
from scraper.orchestrator import ScraperOrchestrator
from tests.fakes.storage import FakeStorage


def _make_job(
    *,
    title: str = "AI Engineer",
    company: str = "TestCorp",
    source: str = "remoteok",
    url: str = "https://example.com/job/1",
) -> JobPosting:
    now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    return JobPosting(
        id=JobPosting.generate_id(url, title),
        title=title,
        company=company,
        url=url,
        source=source,
        description=f"Remote {title} position with AI and LLM experience",
        tags=["AI", "remote"],
        first_seen=now,
        last_seen=now,
        last_updated=now,
    )


class TestOrchestratorWithFakeStorage:

    async def test_batch_upsert_called_on_run(self) -> None:
        storage = FakeStorage()

        fake_jobs = [_make_job()]

        original_create = ScraperOrchestrator._create_adapter

        def mock_create(self_orch, site_id, site_config):
            adapter = original_create(self_orch, site_id, site_config)
            adapter.fetch_jobs = AsyncMock(return_value=fake_jobs if site_id == "remoteok" else [])
            return adapter

        with patch.object(ScraperOrchestrator, "_create_adapter", mock_create):
            orch = ScraperOrchestrator(storage=storage)
            summary = await orch.run(site="remoteok")

        assert summary["new"] >= 1
        assert len(storage._jobs) >= 1

    async def test_batch_upsert_counts_new_and_updated(self) -> None:
        storage = FakeStorage()

        job = _make_job()
        await storage.upsert_job(job)

        job2 = _make_job(
            title="LLM Developer",
            url="https://example.com/job/2",
        )

        def mock_create(self_orch, site_id, site_config):
            adapter = MagicMock()
            adapter.source_id = site_id
            adapter.fetch_jobs = AsyncMock(return_value=[job, job2])
            adapter.config = site_config
            return adapter

        with patch.object(ScraperOrchestrator, "_create_adapter", mock_create):
            orch = ScraperOrchestrator(storage=storage)
            summary = await orch.run(site="remoteok")

        assert summary["new"] >= 1
        assert summary["updated"] >= 1

    async def test_dry_run_skips_storage(self) -> None:
        storage = FakeStorage()

        fake_jobs = [_make_job()]

        original_create = ScraperOrchestrator._create_adapter

        def mock_create(self_orch, site_id, site_config):
            adapter = original_create(self_orch, site_id, site_config)
            adapter.fetch_jobs = AsyncMock(return_value=fake_jobs if site_id == "remoteok" else [])
            return adapter

        with patch.object(ScraperOrchestrator, "_create_adapter", mock_create):
            orch = ScraperOrchestrator(storage=storage)
            summary = await orch.run(site="remoteok", dry_run=True)

        assert summary["new"] == 0
        assert summary["updated"] == 0
        assert len(storage._jobs) == 0

    async def test_empty_deduped_skips_batch(self) -> None:
        storage = FakeStorage()
        storage.upsert_jobs_batch = AsyncMock(return_value=(0, 0))

        original_create = ScraperOrchestrator._create_adapter

        def mock_create(self_orch, site_id, site_config):
            adapter = original_create(self_orch, site_id, site_config)
            adapter.fetch_jobs = AsyncMock(return_value=[])
            return adapter

        with patch.object(ScraperOrchestrator, "_create_adapter", mock_create):
            orch = ScraperOrchestrator(storage=storage)
            summary = await orch.run(site="remoteok")

        storage.upsert_jobs_batch.assert_not_called()
        assert summary["new"] == 0


class TestScraperServiceStorageInjection:

    def test_service_passes_storage_to_orchestrator(self) -> None:
        from app.services.scraper_service import ScraperService

        storage = FakeStorage()
        svc = ScraperService(storage=storage)
        assert svc._orchestrator.storage is storage

    def test_service_requires_storage_or_module_storage(self) -> None:
        import app.services.scraper_service as mod

        original_storage = mod._storage
        try:
            mod._storage = None
            with pytest.raises(ValueError):
                from app.services.scraper_service import ScraperService
                ScraperService()
        finally:
            mod._storage = original_storage

    def test_get_scraper_service_uses_module_storage(self) -> None:
        import app.services.scraper_service as mod

        fake = FakeStorage()
        original_storage = mod._storage
        original_service = mod._scraper_service
        try:
            mod._storage = fake
            mod._scraper_service = None
            svc = mod.get_scraper_service()
            assert svc._orchestrator.storage is fake
        finally:
            mod._storage = original_storage
            mod._scraper_service = original_service


class TestInitCloseScraperStorage:

    async def test_init_creates_pool_when_database_url_set(self) -> None:
        from app.services.scraper_service import init_scraper_storage
        import app.services.scraper_service as mod

        original_storage = mod._storage
        try:
            mod._storage = None
            with patch.object(mod.settings, "DATABASE_URL", "postgresql://fake"):
                mock_supa = MagicMock()
                mock_supa.init_pool = AsyncMock()
                with patch("app.services.scraper_service.SupabaseStorage", return_value=mock_supa):
                    await init_scraper_storage()

                mock_supa.init_pool.assert_awaited_once()
                assert mod._storage is mock_supa
        finally:
            mod._storage = original_storage

    async def test_init_skips_when_no_database_url(self) -> None:
        from app.services.scraper_service import init_scraper_storage
        import app.services.scraper_service as mod

        original_storage = mod._storage
        try:
            mod._storage = None
            with patch.object(mod.settings, "DATABASE_URL", ""):
                await init_scraper_storage()

            assert mod._storage is None
        finally:
            mod._storage = original_storage

    async def test_close_pool_called(self) -> None:
        from app.services.scraper_service import close_scraper_storage
        import app.services.scraper_service as mod

        mock_supa = MagicMock()
        mock_supa.close_pool = AsyncMock()
        original_storage = mod._storage
        try:
            mod._storage = mock_supa
            await close_scraper_storage()

            mock_supa.close_pool.assert_awaited_once()
            assert mod._storage is None
        finally:
            mod._storage = original_storage

    async def test_close_noop_when_no_storage(self) -> None:
        from app.services.scraper_service import close_scraper_storage
        import app.services.scraper_service as mod

        original_storage = mod._storage
        try:
            mod._storage = None
            await close_scraper_storage()
            assert mod._storage is None
        finally:
            mod._storage = original_storage


class TestLifespanCallsStorageInit:

    async def test_lifespan_calls_init_and_close(self) -> None:
        with patch("app.main.init_scraper_storage", new_callable=AsyncMock) as mock_init, \
             patch("app.main.close_scraper_storage", new_callable=AsyncMock) as mock_close:
            from app.main import lifespan, app

            async with lifespan(app):
                mock_init.assert_awaited_once()
                mock_close.assert_not_awaited()

            mock_close.assert_awaited_once()
