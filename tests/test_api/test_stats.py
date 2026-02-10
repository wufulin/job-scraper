from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app


class TestGetStats:

    async def test_stats_returns_200(self) -> None:
        mock_stats = {"total": 10, "active": 8, "inactive": 2, "by_source": {"remoteok": 5, "eleduck": 3}}
        with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
            mock_storage = AsyncMock()
            mock_storage.get_stats.return_value = mock_stats
            mock_get.return_value = mock_storage

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/stats")

        assert response.status_code == 200

    async def test_stats_returns_correct_shape(self) -> None:
        mock_stats = {"total": 42, "active": 30, "inactive": 12, "by_source": {"v2ex": 10, "remoteok": 20}}
        with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
            mock_storage = AsyncMock()
            mock_storage.get_stats.return_value = mock_stats
            mock_get.return_value = mock_storage

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/stats")

        data = response.json()
        assert data["total"] == 42
        assert data["active"] == 30
        assert data["inactive"] == 12
        assert data["by_source"]["v2ex"] == 10
        assert data["by_source"]["remoteok"] == 20

    async def test_stats_empty_database(self) -> None:
        mock_stats = {"total": 0, "active": 0, "inactive": 0, "by_source": {}}
        with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
            mock_storage = AsyncMock()
            mock_storage.get_stats.return_value = mock_stats
            mock_get.return_value = mock_storage

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/stats")

        data = response.json()
        assert data["total"] == 0
        assert data["by_source"] == {}


class TestGetExport:

    async def test_export_returns_200(self) -> None:
        mock_jobs = [
            {"id": "abc", "title": "ML Engineer", "source": "remoteok", "url": "https://example.com/1"},
        ]
        with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
            mock_storage = AsyncMock()
            mock_storage.get_all_jobs.return_value = mock_jobs
            mock_get.return_value = mock_storage

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/export")

        assert response.status_code == 200

    async def test_export_returns_json_content_type(self) -> None:
        with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
            mock_storage = AsyncMock()
            mock_storage.get_all_jobs.return_value = []
            mock_get.return_value = mock_storage

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/export")

        assert "application/json" in response.headers["content-type"]

    async def test_export_returns_job_list(self) -> None:
        mock_jobs = [
            {"id": "1", "title": "AI Engineer", "source": "remoteok"},
            {"id": "2", "title": "ML Ops", "source": "eleduck"},
        ]
        with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
            mock_storage = AsyncMock()
            mock_storage.get_all_jobs.return_value = mock_jobs
            mock_get.return_value = mock_storage

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/export")

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    async def test_export_empty_database(self) -> None:
        with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
            mock_storage = AsyncMock()
            mock_storage.get_all_jobs.return_value = []
            mock_get.return_value = mock_storage

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/export")

        data = response.json()
        assert data == []

    async def test_export_has_attachment_header(self) -> None:
        with patch("app.routers.stats.get_storage", new_callable=AsyncMock) as mock_get:
            mock_storage = AsyncMock()
            mock_storage.get_all_jobs.return_value = []
            mock_get.return_value = mock_storage

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/export")

        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert "jobs.json" in response.headers["content-disposition"]
