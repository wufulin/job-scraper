from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.scrape_run_service import RunStatus, ScrapeRun, ScrapeRunService


class TestScrapeRunService:

    async def test_start_run_creates_entry(self) -> None:
        svc = ScrapeRunService()
        run = await svc.start_run("run-1", trigger="manual")

        assert run.run_id == "run-1"
        assert run.status == RunStatus.STARTED
        assert run.trigger == "manual"

    async def test_start_run_with_sites_and_dry_run(self) -> None:
        svc = ScrapeRunService()
        run = await svc.start_run(
            "run-2", trigger="scheduled", sites=["remoteok"], dry_run=True
        )

        assert run.sites == ["remoteok"]
        assert run.dry_run is True
        assert run.trigger == "scheduled"

    async def test_complete_run_updates_status(self) -> None:
        svc = ScrapeRunService()
        await svc.start_run("run-1")

        result = await svc.complete_run("run-1", matched=10, new=5, updated=3)

        assert result is not None
        assert result.status == RunStatus.COMPLETED
        assert result.matched == 10
        assert result.new == 5
        assert result.updated == 3
        assert result.finished_at is not None

    async def test_complete_run_returns_none_for_unknown(self) -> None:
        svc = ScrapeRunService()
        result = await svc.complete_run("nonexistent")
        assert result is None

    async def test_fail_run_updates_status(self) -> None:
        svc = ScrapeRunService()
        await svc.start_run("run-1")

        result = await svc.fail_run("run-1", error="Connection timeout")

        assert result is not None
        assert result.status == RunStatus.FAILED
        assert "Connection timeout" in result.errors
        assert result.finished_at is not None

    async def test_fail_run_returns_none_for_unknown(self) -> None:
        svc = ScrapeRunService()
        result = await svc.fail_run("nonexistent", error="err")
        assert result is None

    async def test_get_run_returns_existing(self) -> None:
        svc = ScrapeRunService()
        await svc.start_run("run-1")

        run = await svc.get_run("run-1")
        assert run is not None
        assert run.run_id == "run-1"

    async def test_get_run_returns_none_for_missing(self) -> None:
        svc = ScrapeRunService()
        run = await svc.get_run("missing")
        assert run is None

    async def test_list_runs_returns_newest_first(self) -> None:
        from datetime import timedelta

        svc = ScrapeRunService()
        await svc.start_run("run-1")
        await svc.start_run("run-2")
        await svc.start_run("run-3")

        async with svc._lock:
            base = datetime(2025, 1, 1, tzinfo=timezone.utc)
            svc._runs["run-1"].started_at = base
            svc._runs["run-2"].started_at = base + timedelta(hours=1)
            svc._runs["run-3"].started_at = base + timedelta(hours=2)

        runs = await svc.list_runs()

        assert len(runs) == 3
        assert runs[0].run_id == "run-3"
        assert runs[2].run_id == "run-1"

    async def test_list_runs_respects_limit(self) -> None:
        svc = ScrapeRunService()
        for i in range(10):
            await svc.start_run(f"run-{i}")

        runs = await svc.list_runs(limit=3)
        assert len(runs) == 3

    async def test_eviction_removes_oldest(self) -> None:
        svc = ScrapeRunService(max_history=3)
        await svc.start_run("run-1")
        await svc.start_run("run-2")
        await svc.start_run("run-3")
        await svc.start_run("run-4")

        assert await svc.get_run("run-1") is None
        assert await svc.get_run("run-4") is not None


class TestSchedulerService:

    async def test_start_and_shutdown(self) -> None:
        from app.services.scheduler import SchedulerService

        svc = SchedulerService(interval_hours=1)
        svc.start()

        assert svc.is_running is True
        assert svc.is_paused is False

        svc.shutdown()
        assert svc.is_running is False

    async def test_pause_and_resume(self) -> None:
        from app.services.scheduler import SchedulerService

        svc = SchedulerService()
        svc.start()

        svc.pause()
        assert svc.is_paused is True

        svc.resume()
        assert svc.is_paused is False

        svc.shutdown()

    async def test_pause_idempotent(self) -> None:
        from app.services.scheduler import SchedulerService

        svc = SchedulerService()
        svc.start()

        svc.pause()
        svc.pause()
        assert svc.is_paused is True

        svc.shutdown()

    async def test_resume_idempotent(self) -> None:
        from app.services.scheduler import SchedulerService

        svc = SchedulerService()
        svc.start()

        svc.resume()
        assert svc.is_paused is False

        svc.shutdown()

    async def test_get_next_run_time(self) -> None:
        from app.services.scheduler import SchedulerService

        svc = SchedulerService(interval_hours=1)
        svc.start()

        next_time = svc.get_next_run_time()
        assert next_time is not None

        svc.shutdown()

    async def test_get_next_run_time_after_shutdown(self) -> None:
        from app.services.scheduler import SchedulerService

        svc = SchedulerService()
        assert svc.get_next_run_time() is None

    async def test_mutex_prevents_overlapping_runs(self) -> None:
        from app.services.scheduler import SchedulerService

        svc = SchedulerService()

        await svc._mutex.acquire()

        with patch("app.services.scheduler.get_scrape_run_service") as mock_run_svc, \
             patch("app.services.scheduler.get_scraper_service"):
            await svc._scheduled_scrape()
            mock_run_svc.assert_not_called()

        svc._mutex.release()

    async def test_scheduled_scrape_records_run(self) -> None:
        from app.services.scheduler import SchedulerService

        svc = SchedulerService()
        mock_run_service = MagicMock()
        mock_run_service.start_run = AsyncMock()
        mock_run_service.complete_run = AsyncMock()

        mock_scraper_service = MagicMock()
        mock_scraper_service._run_scrape = AsyncMock(
            return_value={"matched": 5, "new": 3, "updated": 1}
        )

        with patch("app.services.scheduler.get_scrape_run_service", return_value=mock_run_service), \
             patch("app.services.scheduler.get_scraper_service", return_value=mock_scraper_service):
            await svc._scheduled_scrape()

        mock_run_service.start_run.assert_awaited_once()
        call_kwargs = mock_run_service.start_run.call_args
        assert call_kwargs.kwargs.get("trigger") == "scheduled" or call_kwargs[1].get("trigger") == "scheduled"

        mock_run_service.complete_run.assert_awaited_once()

    async def test_scheduled_scrape_records_failure(self) -> None:
        from app.services.scheduler import SchedulerService

        svc = SchedulerService()
        mock_run_service = MagicMock()
        mock_run_service.start_run = AsyncMock()
        mock_run_service.fail_run = AsyncMock()

        mock_scraper_service = MagicMock()
        mock_scraper_service._run_scrape = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("app.services.scheduler.get_scrape_run_service", return_value=mock_run_service), \
             patch("app.services.scheduler.get_scraper_service", return_value=mock_scraper_service):
            await svc._scheduled_scrape()

        mock_run_service.fail_run.assert_awaited_once()


class TestSchedulerRouter:

    async def test_status_endpoint(self) -> None:
        mock_svc = MagicMock()
        mock_svc.is_running = True
        mock_svc.is_paused = False
        mock_svc.get_next_run_time.return_value = datetime(
            2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc
        )

        with patch("app.routers.scheduler.get_scheduler_service", return_value=mock_svc), \
             patch("app.main.init_scheduler"), \
             patch("app.main.shutdown_scheduler"):
            from app.main import app

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/scheduler/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["running"] is True
        assert data["paused"] is False
        assert data["next_run_time"] is not None

    async def test_pause_endpoint(self) -> None:
        mock_svc = MagicMock()

        with patch("app.routers.scheduler.get_scheduler_service", return_value=mock_svc), \
             patch("app.main.init_scheduler"), \
             patch("app.main.shutdown_scheduler"):
            from app.main import app

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/scheduler/pause")

        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is True
        mock_svc.pause.assert_called_once()

    async def test_resume_endpoint(self) -> None:
        mock_svc = MagicMock()

        with patch("app.routers.scheduler.get_scheduler_service", return_value=mock_svc), \
             patch("app.main.init_scheduler"), \
             patch("app.main.shutdown_scheduler"):
            from app.main import app

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/scheduler/resume")

        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is False
        mock_svc.resume.assert_called_once()

    async def test_list_runs_endpoint(self) -> None:
        mock_run_svc = MagicMock()
        run = ScrapeRun(
            run_id="run-abc",
            status=RunStatus.COMPLETED,
            trigger="scheduled",
            started_at=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            finished_at=datetime(2025, 6, 1, 12, 5, 0, tzinfo=timezone.utc),
            matched=10,
            new=5,
            updated=3,
        )
        mock_run_svc.list_runs = AsyncMock(return_value=[run])

        with patch("app.routers.scheduler.get_scrape_run_service", return_value=mock_run_svc), \
             patch("app.main.init_scheduler"), \
             patch("app.main.shutdown_scheduler"):
            from app.main import app

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/scheduler/runs")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runs"]) == 1
        assert data["runs"][0]["run_id"] == "run-abc"
        assert data["runs"][0]["status"] == "completed"

    async def test_get_run_endpoint(self) -> None:
        mock_run_svc = MagicMock()
        run = ScrapeRun(
            run_id="run-xyz",
            status=RunStatus.STARTED,
            trigger="manual",
            started_at=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        mock_run_svc.get_run = AsyncMock(return_value=run)

        with patch("app.routers.scheduler.get_scrape_run_service", return_value=mock_run_svc), \
             patch("app.main.init_scheduler"), \
             patch("app.main.shutdown_scheduler"):
            from app.main import app

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/scheduler/runs/run-xyz")

        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == "run-xyz"
        assert data["status"] == "started"

    async def test_get_run_not_found(self) -> None:
        mock_run_svc = MagicMock()
        mock_run_svc.get_run = AsyncMock(return_value=None)

        with patch("app.routers.scheduler.get_scrape_run_service", return_value=mock_run_svc), \
             patch("app.main.init_scheduler"), \
             patch("app.main.shutdown_scheduler"):
            from app.main import app

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/scheduler/runs/nope")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_found"


class TestScrapeStatusEndpointTracking:

    async def test_status_returns_tracked_run(self) -> None:
        mock_run_svc = MagicMock()
        run = ScrapeRun(
            run_id="track-1",
            status=RunStatus.COMPLETED,
            trigger="manual",
            started_at=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            matched=8,
            new=4,
        )
        mock_run_svc.get_run = AsyncMock(return_value=run)

        with patch("app.routers.scraper.get_scrape_run_service", return_value=mock_run_svc), \
             patch("app.routers.scraper.get_scraper_service") as mock_scraper, \
             patch("app.main.init_scheduler"), \
             patch("app.main.shutdown_scheduler"):
            from app.main import app

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/scrape/status/track-1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == "track-1"
        assert data["status"] == "completed"

    async def test_status_returns_not_found(self) -> None:
        mock_run_svc = MagicMock()
        mock_run_svc.get_run = AsyncMock(return_value=None)

        with patch("app.routers.scraper.get_scrape_run_service", return_value=mock_run_svc), \
             patch("app.main.init_scheduler"), \
             patch("app.main.shutdown_scheduler"):
            from app.main import app

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/scrape/status/unknown-id")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_found"


class TestLifespanWithScheduler:

    async def test_lifespan_starts_and_shuts_down_scheduler(self) -> None:
        with patch("app.main.init_scraper_storage", new_callable=AsyncMock) as mock_init_storage, \
             patch("app.main.close_scraper_storage", new_callable=AsyncMock) as mock_close_storage, \
             patch("app.main.init_scheduler") as mock_init_sched, \
             patch("app.main.shutdown_scheduler") as mock_shutdown_sched:
            from app.main import lifespan, app

            async with lifespan(app):
                mock_init_storage.assert_awaited_once()
                mock_init_sched.assert_called_once()
                mock_shutdown_sched.assert_not_called()

            mock_shutdown_sched.assert_called_once()
            mock_close_storage.assert_awaited_once()


class TestInitShutdownModule:

    def test_init_scheduler_starts_service(self) -> None:
        import app.services.scheduler as mod

        original = mod._scheduler
        try:
            mod._scheduler = None
            with patch.object(mod.SchedulerService, "start") as mock_start:
                svc = mod.init_scheduler()
                mock_start.assert_called_once()
                assert svc is not None
        finally:
            mod._scheduler = original

    def test_shutdown_scheduler_cleans_up(self) -> None:
        import app.services.scheduler as mod

        mock_svc = MagicMock()
        original = mod._scheduler
        try:
            mod._scheduler = mock_svc
            mod.shutdown_scheduler()
            mock_svc.shutdown.assert_called_once()
            assert mod._scheduler is None
        finally:
            mod._scheduler = original

    def test_shutdown_scheduler_noop_when_none(self) -> None:
        import app.services.scheduler as mod

        original = mod._scheduler
        try:
            mod._scheduler = None
            mod.shutdown_scheduler()
            assert mod._scheduler is None
        finally:
            mod._scheduler = original
