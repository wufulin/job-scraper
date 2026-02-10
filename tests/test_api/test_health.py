from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestHealthEndpoint:

    async def test_health_returns_200(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        assert response.status_code == 200

    async def test_health_returns_status_healthy(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        data = response.json()
        assert data["status"] == "healthy"

    async def test_health_returns_version(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)

    async def test_health_returns_timezone_aware_timestamp(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        data = response.json()
        assert "timestamp" in data
        ts = datetime.fromisoformat(data["timestamp"])
        assert ts.tzinfo is not None, "Timestamp must be timezone-aware"

    async def test_health_json_content_type(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        assert "application/json" in response.headers["content-type"]


class TestCORSMiddleware:

    async def test_cors_allows_localhost_3000(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.options(
                "/api/health",
                headers={
                    "origin": "http://localhost:3000",
                    "access-control-request-method": "GET",
                },
            )

        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    async def test_cors_blocks_unknown_origin(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.options(
                "/api/health",
                headers={
                    "origin": "http://evil.com",
                    "access-control-request-method": "GET",
                },
            )

        assert response.headers.get("access-control-allow-origin") != "http://evil.com"


class TestAppMetadata:

    async def test_openapi_docs_available(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/docs")

        assert response.status_code == 200

    async def test_app_title(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/openapi.json")

        data = response.json()
        assert data["info"]["title"] == "Job Scraper API"
