from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.responses import SubscriptionResponse, UserPayload, SubscriptionListResponse, PaginationMeta
from app.routers.subscriptions import get_subscription_service
from app.dependencies import get_current_user


def _make_user(user_id: str = "user-123", email: str = "user@example.com") -> UserPayload:
    return UserPayload(sub=user_id, email=email, role="user")


def _make_subscription(
    id: int = 1,
    user_id: str = "user-123",
    name: str = "AI Jobs",
    keywords: list[str] | None = None,
    match_mode: str = "any",
    sources: list[str] | None = None,
    is_active: bool = True,
) -> SubscriptionResponse:
    now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    return SubscriptionResponse(
        id=id,
        user_id=user_id,
        name=name,
        keywords=keywords or ["AI", "ML"],
        match_mode=match_mode,
        sources=sources or ["email"],
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


class TestListSubscriptions:

    async def test_list_subscriptions_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/subscriptions")

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_list_subscriptions_returns_200(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.list_subscriptions = AsyncMock(
            return_value=SubscriptionListResponse(
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
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/subscriptions",
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    async def test_list_subscriptions_with_pagination(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        subscriptions = [
            _make_subscription(id=1, name="AI Jobs"),
            _make_subscription(id=2, name="Remote Jobs"),
        ]
        mock_svc.list_subscriptions = AsyncMock(
            return_value=SubscriptionListResponse(
                data=subscriptions,
                pagination=PaginationMeta(
                    page=1,
                    per_page=20,
                    total=2,
                    total_pages=1,
                ),
            )
        )
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/subscriptions?page=1&per_page=20",
                    headers={"Authorization": "Bearer token123"},
                )

            data = response.json()
            assert response.status_code == 200
            assert len(data["data"]) == 2
            assert data["pagination"]["total"] == 2
        finally:
            app.dependency_overrides.clear()


class TestCreateSubscription:

    async def test_create_subscription_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/subscriptions",
                    json={
                        "name": "AI Jobs",
                        "keywords": ["AI", "ML"],
                        "match_mode": "any",
                        "sources": ["email"],
                    },
                )

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_create_subscription_returns_201(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.create_subscription = AsyncMock(
            return_value=_make_subscription(id=1, name="AI Jobs")
        )
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/subscriptions",
                    json={
                        "name": "AI Jobs",
                        "keywords": ["AI", "ML"],
                        "match_mode": "any",
                        "sources": ["email"],
                    },
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "AI Jobs"
        finally:
            app.dependency_overrides.clear()

    async def test_create_subscription_calls_service(self) -> None:
        user = _make_user(user_id="user-456")
        mock_svc = AsyncMock()
        mock_svc.create_subscription = AsyncMock(
            return_value=_make_subscription(id=1, name="Remote Jobs")
        )
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/subscriptions",
                    json={
                        "name": "Remote Jobs",
                        "keywords": ["remote"],
                        "match_mode": "all",
                        "sources": ["telegram"],
                    },
                    headers={"Authorization": "Bearer token123"},
                )

            mock_svc.create_subscription.assert_called_once_with(
                user_id="user-456",
                name="Remote Jobs",
                keywords=["remote"],
                match_mode="all",
                sources=["telegram"],
            )
        finally:
            app.dependency_overrides.clear()


class TestGetSubscription:

    async def test_get_subscription_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/subscriptions/1")

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_get_subscription_returns_200(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.get_subscription = AsyncMock(
            return_value=_make_subscription(id=1, name="AI Jobs")
        )
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/subscriptions/1",
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "AI Jobs"
        finally:
            app.dependency_overrides.clear()

    async def test_get_subscription_not_found(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.get_subscription = AsyncMock(return_value=None)
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/subscriptions/999",
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestUpdateSubscription:

    async def test_update_subscription_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/subscriptions/1",
                    json={"name": "Updated Name"},
                )

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_update_subscription_returns_200(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.update_subscription = AsyncMock(
            return_value=_make_subscription(id=1, name="Updated Name")
        )
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/subscriptions/1",
                    json={"name": "Updated Name"},
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Name"
        finally:
            app.dependency_overrides.clear()

    async def test_update_subscription_not_found(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.update_subscription = AsyncMock(return_value=None)
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/subscriptions/999",
                    json={"name": "Updated Name"},
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestDeleteSubscription:

    async def test_delete_subscription_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete("/api/subscriptions/1")

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_delete_subscription_returns_204(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.delete_subscription = AsyncMock(return_value=True)
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    "/api/subscriptions/1",
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_delete_subscription_not_found(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.delete_subscription = AsyncMock(return_value=False)
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    "/api/subscriptions/999",
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestToggleSubscription:

    async def test_toggle_subscription_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/subscriptions/1/toggle",
                    json={"is_active": False},
                )

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_toggle_subscription_returns_200(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.toggle_subscription = AsyncMock(
            return_value=_make_subscription(id=1, is_active=False)
        )
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/subscriptions/1/toggle",
                    json={"is_active": False},
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["is_active"] is False
        finally:
            app.dependency_overrides.clear()

    async def test_toggle_subscription_not_found(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.toggle_subscription = AsyncMock(return_value=None)
        
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_subscription_service] = lambda: mock_svc
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/subscriptions/999/toggle",
                    json={"is_active": True},
                    headers={"Authorization": "Bearer token123"},
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
