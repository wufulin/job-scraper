from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.responses import FavoriteResponse, UserPayload
from app.routers.favorites import get_favorite_service
from app.dependencies import get_current_user


def _make_user(user_id: str = "user-123", email: str = "user@example.com") -> UserPayload:
    return UserPayload(sub=user_id, email=email, role="user")


def _make_favorite(
    id: int = 1,
    user_id: str = "user-123",
    job_id: str = "job-1",
) -> FavoriteResponse:
    now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    return FavoriteResponse(
        id=id,
        user_id=user_id,
        job_id=job_id,
        created_at=now,
    )


class TestListFavorites:

    async def test_list_favorites_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/favorites")

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_list_favorites_returns_200(self) -> None:
        from app.models.responses import FavoriteListResponse, PaginationMeta
        
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.list_favorites = AsyncMock(
            return_value=FavoriteListResponse(
                data=[],
                pagination=PaginationMeta(
                    page=1,
                    per_page=20,
                    total=0,
                    total_pages=0,
                ),
            )
        )
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_favorite_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/favorites",
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    async def test_list_favorites_with_pagination(self) -> None:
        from app.models.responses import FavoriteListResponse, PaginationMeta
        
        user = _make_user()
        mock_svc = AsyncMock()
        favorites = [
            _make_favorite(id=1, job_id="job-1"),
            _make_favorite(id=2, job_id="job-2"),
        ]
        mock_svc.list_favorites = AsyncMock(
            return_value=FavoriteListResponse(
                data=favorites,
                pagination=PaginationMeta(
                    page=1,
                    per_page=20,
                    total=2,
                    total_pages=1,
                ),
            )
        )
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_favorite_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/favorites?page=1&per_page=20",
                    headers={"Authorization": "Bearer token123"},
                )

            data = response.json()
            assert response.status_code == 200
            assert len(data["data"]) == 2
            assert data["pagination"]["total"] == 2
        finally:
            app.dependency_overrides.clear()


class TestAddFavorite:

    async def test_add_favorite_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/favorites",
                    json={"job_id": "job-1"},
                )

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_add_favorite_returns_201(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.add_favorite = AsyncMock(
            return_value=_make_favorite(id=1, job_id="job-1")
        )
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_favorite_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/favorites",
                    json={"job_id": "job-1"},
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 201
            data = response.json()
            assert data["job_id"] == "job-1"
        finally:
            app.dependency_overrides.clear()

    async def test_add_favorite_calls_service(self) -> None:
        user = _make_user(user_id="user-456")
        mock_svc = AsyncMock()
        mock_svc.add_favorite = AsyncMock(
            return_value=_make_favorite(id=1, job_id="job-99")
        )
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_favorite_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/favorites",
                    json={"job_id": "job-99"},
                    headers={"Authorization": "Bearer token123"},
                )

            mock_svc.add_favorite.assert_called_once_with(user_id="user-456", job_id="job-99")
        finally:
            app.dependency_overrides.clear()


class TestRemoveFavorite:

    async def test_remove_favorite_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete("/api/favorites/job-1")

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_remove_favorite_returns_204(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.remove_favorite = AsyncMock(return_value=True)
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_favorite_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    "/api/favorites/job-1",
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_remove_favorite_not_found(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.remove_favorite = AsyncMock(return_value=False)
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_favorite_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    "/api/favorites/nonexistent",
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
