from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from scraper.models import JobPosting


def _make_job(
    *,
    id: str = "abc123",
    title: str = "AI Engineer",
    company: str = "TestCorp",
    url: str = "https://example.com/job/1",
    source: str = "remoteok",
    description: str = "Build AI models",
    tags: list[str] | None = None,
    salary: str | None = None,
    location: str | None = "Remote",
) -> JobPosting:
    now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    return JobPosting(
        id=id,
        title=title,
        company=company,
        url=url,
        source=source,
        description=description,
        tags=tags or ["ai", "remote"],
        salary=salary,
        location=location,
        published_at=now,
        first_seen=now,
        last_seen=now,
        last_updated=now,
        update_count=1,
    )


SAMPLE_JOBS = [
    _make_job(id="int-1", title="AI Engineer", source="remoteok"),
    _make_job(id="int-2", title="ML Researcher", source="eleduck", company="RemoteCo"),
]


def _mock_storage() -> AsyncMock:
    storage = AsyncMock()
    storage.get_all_jobs = AsyncMock(return_value=SAMPLE_JOBS)
    storage.get_stats = AsyncMock(
        return_value={"total": 2, "active": 2, "inactive": 0, "by_source": {"remoteok": 1, "eleduck": 1}}
    )
    return storage


class TestJSONErrorResponses:

    async def test_404_returns_json_with_detail(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/nonexistent-endpoint")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    async def test_404_content_type_is_json(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/this-does-not-exist")

        assert "application/json" in response.headers["content-type"]

    async def test_405_method_not_allowed_returns_json(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/health")

        assert response.status_code == 405
        data = response.json()
        assert "detail" in data

    async def test_422_validation_error_returns_json(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/jobs?page=-1")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_500_does_not_leak_stack_trace(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            mock_svc = MagicMock()
            mock_svc.list_jobs = AsyncMock(side_effect=RuntimeError("DB connection lost"))
            mock_svc_factory.return_value = mock_svc

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "DB connection lost" not in data["detail"]
        assert "Traceback" not in json.dumps(data)

    async def test_500_content_type_is_json(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            mock_svc = MagicMock()
            mock_svc.list_jobs = AsyncMock(side_effect=RuntimeError("boom"))
            mock_svc_factory.return_value = mock_svc

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs")

        assert response.status_code == 500
        assert "application/json" in response.headers["content-type"]


class TestLoggingMiddleware:

    async def test_successful_request_is_logged(self) -> None:
        with patch("app.main.logger") as mock_logger:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/api/health")

            log_calls = [
                str(c) for c in mock_logger.info.call_args_list
            ]
            log_text = " ".join(log_calls)
            assert "GET" in log_text or "health" in log_text

    async def test_error_request_is_logged(self) -> None:
        with patch("app.main.logger") as mock_logger:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/api/nonexistent")

            all_calls = []
            for method_name in ("info", "warning", "error"):
                method = getattr(mock_logger, method_name, None)
                if method and method.call_args_list:
                    all_calls.extend(str(c) for c in method.call_args_list)
            log_text = " ".join(all_calls)
            assert "404" in log_text or "nonexistent" in log_text


class TestCrossEndpointIntegration:

    async def test_full_api_flow(self) -> None:
        mock_storage = _mock_storage()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "healthy"

            with patch("app.routers.jobs.get_job_service") as mock_svc:
                from app.services.job_service import JobService

                mock_svc.return_value = JobService(storage=mock_storage)
                resp = await client.get("/api/jobs")
            assert resp.status_code == 200
            assert resp.json()["pagination"]["total"] == 2

            with patch("app.routers.jobs.get_job_service") as mock_svc:
                from app.services.job_service import JobService

                mock_svc.return_value = JobService(storage=mock_storage)
                resp = await client.get("/api/jobs/search?q=AI")
            assert resp.status_code == 200
            assert resp.json()["pagination"]["total"] >= 1

            with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_storage
                resp = await client.get("/api/stats")
            assert resp.status_code == 200
            assert resp.json()["total"] == 2

            with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_storage
                resp = await client.get("/api/export")
            assert resp.status_code == 200

    async def test_scrape_trigger_and_status(self) -> None:
        with patch("app.routers.scraper.get_scraper_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.trigger_scrape.return_value = "integration-run-1"
            mock_get_svc.return_value = mock_svc

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/scrape", json={"sites": ["remoteok"]})
                assert resp.status_code == 202
                run_id = resp.json()["run_id"]

                resp = await client.get(f"/api/scrape/status/{run_id}")
                assert resp.status_code == 200
                assert resp.json()["run_id"] == run_id


class TestEdgeCases:

    async def test_root_path_returns_valid_response(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")

        assert response.status_code in (200, 307, 404)
        if response.status_code == 404:
            data = response.json()
            assert "detail" in data

    async def test_trailing_slash_handling(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health/")

        assert response.status_code in (200, 307, 404)

    async def test_large_page_number(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs?page=999999")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []

    async def test_per_page_exceeds_max_returns_422(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/jobs?per_page=101")

        assert response.status_code == 422

    async def test_invalid_json_body_returns_422(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/scrape",
                content="not json",
                headers={"content-type": "application/json"},
            )

        assert response.status_code == 422

    async def test_get_nonexistent_job_returns_json_404(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/does-not-exist")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestResponseFormatConsistency:

    async def test_all_endpoints_return_json(self) -> None:
        mock_storage = _mock_storage()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/health")
            assert "application/json" in resp.headers["content-type"]

            with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_storage
                resp = await client.get("/api/stats")
            assert "application/json" in resp.headers["content-type"]

            with patch("app.routers.jobs.get_job_service") as mock_svc:
                from app.services.job_service import JobService

                mock_svc.return_value = JobService(storage=mock_storage)
                resp = await client.get("/api/jobs")
            assert "application/json" in resp.headers["content-type"]

    async def test_error_responses_have_detail_field(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp_404 = await client.get("/api/nonexistent")
            assert resp_404.status_code >= 400
            assert "detail" in resp_404.json()

            resp_422 = await client.get("/api/jobs?page=-1")
            assert resp_422.status_code >= 400
            assert "detail" in resp_422.json()
