from __future__ import annotations

from unittest.mock import MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app


class TestPostScrape:

    async def test_scrape_returns_202(self) -> None:
        with patch("app.routers.scraper.get_scraper_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.trigger_scrape.return_value = "test-run-id"
            mock_get_svc.return_value = mock_svc

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/scrape", json={})

        assert response.status_code == 202

    async def test_scrape_returns_run_id(self) -> None:
        with patch("app.routers.scraper.get_scraper_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.trigger_scrape.return_value = "abc-123"
            mock_get_svc.return_value = mock_svc

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/scrape", json={})

        data = response.json()
        assert data["run_id"] == "abc-123"
        assert data["status"] == "started"

    async def test_scrape_with_sites_filter(self) -> None:
        with patch("app.routers.scraper.get_scraper_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.trigger_scrape.return_value = "run-1"
            mock_get_svc.return_value = mock_svc

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/scrape",
                    json={"sites": ["remoteok", "eleduck"]},
                )

        assert response.status_code == 202
        mock_svc.trigger_scrape.assert_called_once()
        call_kwargs = mock_svc.trigger_scrape.call_args
        assert call_kwargs.kwargs.get("sites") == ["remoteok", "eleduck"]

    async def test_scrape_with_dry_run(self) -> None:
        with patch("app.routers.scraper.get_scraper_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.trigger_scrape.return_value = "run-dry"
            mock_get_svc.return_value = mock_svc

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/scrape",
                    json={"dry_run": True},
                )

        assert response.status_code == 202
        call_kwargs = mock_svc.trigger_scrape.call_args
        assert call_kwargs.kwargs.get("dry_run") is True

    async def test_scrape_empty_body_defaults(self) -> None:
        with patch("app.routers.scraper.get_scraper_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_svc.trigger_scrape.return_value = "run-default"
            mock_get_svc.return_value = mock_svc

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/scrape", json={})

        assert response.status_code == 202
        call_kwargs = mock_svc.trigger_scrape.call_args
        assert call_kwargs.kwargs.get("sites") is None
        assert call_kwargs.kwargs.get("dry_run") is False


class TestGetScrapeStatus:

    async def test_status_returns_200(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/scrape/status/some-run-id")

        assert response.status_code == 200

    async def test_status_returns_placeholder(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/scrape/status/some-run-id")

        data = response.json()
        assert data["run_id"] == "some-run-id"
        assert "status" in data
        assert data["status"] == "unknown"
        assert "message" in data

    async def test_status_echoes_run_id(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/scrape/status/my-unique-id-42")

        data = response.json()
        assert data["run_id"] == "my-unique-id-42"
