from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.responses import UserPayload


def _admin_user() -> UserPayload:
    return UserPayload(sub="admin-uuid", email="admin@example.com", role="admin")


def _regular_user() -> UserPayload:
    return UserPayload(sub="user-uuid", email="user@example.com", role="user")


SAMPLE_SITE_ROWS = [
    {
        "id": "remoteok",
        "name": "RemoteOK",
        "url": "https://remoteok.com/api",
        "adapter": "api",
        "enabled": True,
        "skip_location_match": True,
        "rate_limit_seconds": 2,
        "max_pages": None,
        "config_json": '{"headers": {"User-Agent": "Mozilla/5.0"}}',
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    },
    {
        "id": "eleduck",
        "name": "电鸭",
        "url": "https://svc.eleduck.com/api/v1/posts",
        "adapter": "api",
        "enabled": True,
        "skip_location_match": False,
        "rate_limit_seconds": 2,
        "max_pages": 5,
        "config_json": '{"params": {"category": 5}}',
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    },
]

SAMPLE_KEYWORD_ROWS = [
    {
        "id": 1,
        "group_name": "location",
        "keyword": "remote",
        "enabled": True,
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    },
    {
        "id": 2,
        "group_name": "location",
        "keyword": "远程",
        "enabled": True,
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    },
    {
        "id": 3,
        "group_name": "technology",
        "keyword": "AI",
        "enabled": True,
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    },
    {
        "id": 4,
        "group_name": "technology",
        "keyword": "LLM",
        "enabled": False,
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    },
]


def _mock_pool(*, site_rows=None, keyword_rows=None) -> AsyncMock:
    pool = AsyncMock()
    site_rows = site_rows if site_rows is not None else SAMPLE_SITE_ROWS
    keyword_rows = keyword_rows if keyword_rows is not None else SAMPLE_KEYWORD_ROWS

    async def mock_fetch(sql, *args):
        if "site_configs" in sql:
            return [MagicMock(**{k: v for k, v in r.items()}) for r in site_rows]
        if "keyword_configs" in sql:
            return [MagicMock(**{k: v for k, v in r.items()}) for r in keyword_rows]
        return []

    async def mock_fetchrow(sql, *args):
        if "site_configs" in sql and args:
            for r in site_rows:
                if r["id"] == args[0]:
                    return MagicMock(**{k: v for k, v in r.items()})
        if "keyword_configs" in sql and args:
            for r in keyword_rows:
                if r["id"] == args[0]:
                    return MagicMock(**{k: v for k, v in r.items()})
        return None

    async def mock_execute(sql, *args):
        return "UPDATE 1"

    pool.fetch = AsyncMock(side_effect=mock_fetch)
    pool.fetchrow = AsyncMock(side_effect=mock_fetchrow)
    pool.execute = AsyncMock(side_effect=mock_execute)
    return pool


class TestConfigServiceGetSites:

    async def test_get_site_configs_returns_list(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool)
        result = await svc.get_site_configs()

        assert len(result) == 2
        assert result[0]["id"] == "remoteok"
        assert result[1]["id"] == "eleduck"

    async def test_get_site_configs_uses_cache(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool)

        await svc.get_site_configs()
        await svc.get_site_configs()

        assert pool.fetch.call_count == 1

    async def test_get_site_configs_cache_expires(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool, cache_ttl_seconds=0)

        await svc.get_site_configs()
        await svc.get_site_configs()

        assert pool.fetch.call_count == 2


class TestConfigServiceGetKeywords:

    async def test_get_keyword_configs_returns_list(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool)
        result = await svc.get_keyword_configs()

        assert len(result) == 4
        assert result[0]["group_name"] == "location"

    async def test_get_keyword_configs_uses_cache(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool)

        await svc.get_keyword_configs()
        await svc.get_keyword_configs()

        assert pool.fetch.call_count == 1

    async def test_get_keyword_configs_cache_expires(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool, cache_ttl_seconds=0)

        await svc.get_keyword_configs()
        await svc.get_keyword_configs()

        assert pool.fetch.call_count == 2


class TestConfigServiceUpdate:

    async def test_update_site_config_invalidates_cache(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool)

        await svc.get_site_configs()
        assert pool.fetch.call_count == 1

        await svc.update_site_config("remoteok", enabled=False)

        await svc.get_site_configs()
        assert pool.fetch.call_count == 2

    async def test_update_site_config_calls_execute(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool)

        await svc.update_site_config("remoteok", enabled=False, rate_limit_seconds=5)
        assert pool.execute.called

    async def test_update_keyword_invalidates_cache(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool)

        await svc.get_keyword_configs()
        assert pool.fetch.call_count == 1

        await svc.update_keyword(1, enabled=False)

        await svc.get_keyword_configs()
        assert pool.fetch.call_count == 2

    async def test_update_keyword_calls_execute(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool)

        await svc.update_keyword(1, enabled=False)
        assert pool.execute.called

    async def test_add_keyword_calls_execute(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool)

        await svc.add_keyword(group_name="technology", keyword="GPT")
        assert pool.execute.called

    async def test_add_keyword_invalidates_cache(self) -> None:
        from app.services.config_service import ConfigService

        pool = _mock_pool()
        svc = ConfigService(pool=pool)

        await svc.get_keyword_configs()
        assert pool.fetch.call_count == 1

        await svc.add_keyword(group_name="technology", keyword="GPT")

        await svc.get_keyword_configs()
        assert pool.fetch.call_count == 2


class TestGetSitesEndpoint:

    async def test_get_sites_requires_auth(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/config/sites")
        assert response.status_code == 401

    async def test_get_sites_returns_200_for_user(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_site_configs = AsyncMock(return_value=[
            {"id": "remoteok", "name": "RemoteOK", "url": "https://remoteok.com/api",
             "adapter": "api", "enabled": True, "skip_location_match": True,
             "rate_limit_seconds": 2, "max_pages": None, "config_json": "{}"},
        ])

        with (
            patch("app.dependencies.verify_jwt", return_value=_regular_user()),
            patch("app.routers.config.get_config_service", return_value=mock_svc),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/config/sites",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "remoteok"


class TestUpdateSiteEndpoint:

    async def test_update_site_requires_admin(self) -> None:
        with patch("app.dependencies.verify_jwt", return_value=_regular_user()):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/config/sites/remoteok",
                    json={"enabled": False},
                    headers={"Authorization": "Bearer fake-token"},
                )
        assert response.status_code == 403

    async def test_update_site_returns_200_for_admin(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.update_site_config = AsyncMock(return_value=None)
        mock_svc.get_site_config_by_id = AsyncMock(return_value={
            "id": "remoteok", "name": "RemoteOK", "url": "https://remoteok.com/api",
            "adapter": "api", "enabled": False, "skip_location_match": True,
            "rate_limit_seconds": 2, "max_pages": None, "config_json": "{}",
        })

        with (
            patch("app.dependencies.verify_jwt", return_value=_admin_user()),
            patch("app.routers.config.get_config_service", return_value=mock_svc),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/config/sites/remoteok",
                    json={"enabled": False},
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "remoteok"

    async def test_update_site_not_found_returns_404(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.update_site_config = AsyncMock(return_value=None)
        mock_svc.get_site_config_by_id = AsyncMock(return_value=None)

        with (
            patch("app.dependencies.verify_jwt", return_value=_admin_user()),
            patch("app.routers.config.get_config_service", return_value=mock_svc),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/config/sites/nonexistent",
                    json={"enabled": False},
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 404


class TestGetKeywordsEndpoint:

    async def test_get_keywords_requires_auth(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/config/keywords")
        assert response.status_code == 401

    async def test_get_keywords_returns_200_for_user(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_keyword_configs = AsyncMock(return_value=[
            {"id": 1, "group_name": "location", "keyword": "remote",
             "enabled": True},
        ])

        with (
            patch("app.dependencies.verify_jwt", return_value=_regular_user()),
            patch("app.routers.config.get_config_service", return_value=mock_svc),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/config/keywords",
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["keyword"] == "remote"


class TestAddKeywordEndpoint:

    async def test_add_keyword_requires_admin(self) -> None:
        with patch("app.dependencies.verify_jwt", return_value=_regular_user()):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/config/keywords",
                    json={"group_name": "technology", "keyword": "GPT"},
                    headers={"Authorization": "Bearer fake-token"},
                )
        assert response.status_code == 403

    async def test_add_keyword_returns_201_for_admin(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.add_keyword = AsyncMock(return_value={
            "id": 5, "group_name": "technology", "keyword": "GPT", "enabled": True,
        })

        with (
            patch("app.dependencies.verify_jwt", return_value=_admin_user()),
            patch("app.routers.config.get_config_service", return_value=mock_svc),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/config/keywords",
                    json={"group_name": "technology", "keyword": "GPT"},
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 201
        data = response.json()
        assert data["keyword"] == "GPT"
        assert data["group_name"] == "technology"

    async def test_add_keyword_missing_fields_returns_422(self) -> None:
        with patch("app.dependencies.verify_jwt", return_value=_admin_user()):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/config/keywords",
                    json={"keyword": "GPT"},
                    headers={"Authorization": "Bearer fake-token"},
                )
        assert response.status_code == 422


class TestUpdateKeywordEndpoint:

    async def test_update_keyword_requires_admin(self) -> None:
        with patch("app.dependencies.verify_jwt", return_value=_regular_user()):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/config/keywords/1",
                    json={"enabled": False},
                    headers={"Authorization": "Bearer fake-token"},
                )
        assert response.status_code == 403

    async def test_update_keyword_returns_200_for_admin(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.update_keyword = AsyncMock(return_value=None)
        mock_svc.get_keyword_by_id = AsyncMock(return_value={
            "id": 1, "group_name": "location", "keyword": "remote", "enabled": False,
        })

        with (
            patch("app.dependencies.verify_jwt", return_value=_admin_user()),
            patch("app.routers.config.get_config_service", return_value=mock_svc),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/config/keywords/1",
                    json={"enabled": False},
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200

    async def test_update_keyword_not_found_returns_404(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.update_keyword = AsyncMock(return_value=None)
        mock_svc.get_keyword_by_id = AsyncMock(return_value=None)

        with (
            patch("app.dependencies.verify_jwt", return_value=_admin_user()),
            patch("app.routers.config.get_config_service", return_value=mock_svc),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/config/keywords/999",
                    json={"enabled": False},
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 404
