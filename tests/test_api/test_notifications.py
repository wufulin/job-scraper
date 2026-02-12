from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.responses import (
    NotificationListResponse,
    NotificationResponse,
    PaginationMeta,
    UnreadCountResponse,
    UserPayload,
)
from app.dependencies import get_current_user
from app.routers.notifications import get_notification_service


def _make_user(user_id: str = "user-123", email: str = "user@example.com") -> UserPayload:
    return UserPayload(sub=user_id, email=email, role="user")


def _make_notification(
    id: str = "notif-1",
    user_id: str = "user-123",
    type: str = "new_match",
    title: str = "New match: AI Engineer",
    body: str = "Acme Corp — AI Engineer",
    job_id: str = "job-1",
    is_read: bool = False,
    email_sent: bool = False,
) -> NotificationResponse:
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    return NotificationResponse(
        id=id,
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        job_id=job_id,
        is_read=is_read,
        email_sent=email_sent,
        created_at=now,
    )


class TestListNotifications:

    async def test_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/notifications")
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_returns_200_empty(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.get_notifications = AsyncMock(
            return_value=NotificationListResponse(
                data=[],
                pagination=PaginationMeta(page=1, per_page=20, total=0, total_pages=1),
            )
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_notification_service] = lambda: mock_svc

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/notifications",
                    headers={"Authorization": "Bearer token123"},
                )
            assert response.status_code == 200
            data = response.json()
            assert data["data"] == []
            assert data["pagination"]["total"] == 0
        finally:
            app.dependency_overrides.clear()

    async def test_returns_200_with_data(self) -> None:
        user = _make_user()
        notifications = [
            _make_notification(id="n1", job_id="job-1"),
            _make_notification(id="n2", job_id="job-2"),
        ]
        mock_svc = AsyncMock()
        mock_svc.get_notifications = AsyncMock(
            return_value=NotificationListResponse(
                data=notifications,
                pagination=PaginationMeta(page=1, per_page=20, total=2, total_pages=1),
            )
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_notification_service] = lambda: mock_svc

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/notifications",
                    headers={"Authorization": "Bearer token123"},
                )
            data = response.json()
            assert response.status_code == 200
            assert len(data["data"]) == 2
            assert data["data"][0]["id"] == "n1"
            assert data["data"][0]["type"] == "new_match"
        finally:
            app.dependency_overrides.clear()

    async def test_pagination_params_forwarded(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.get_notifications = AsyncMock(
            return_value=NotificationListResponse(
                data=[],
                pagination=PaginationMeta(page=2, per_page=10, total=15, total_pages=2),
            )
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_notification_service] = lambda: mock_svc

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/notifications?page=2&per_page=10&unread_only=true",
                    headers={"Authorization": "Bearer token123"},
                )
            assert response.status_code == 200
            mock_svc.get_notifications.assert_called_once_with(
                user_id="user-123", page=2, per_page=10, unread_only=True
            )
        finally:
            app.dependency_overrides.clear()


class TestUnreadCount:

    async def test_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/notifications/unread-count")
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_returns_count(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.get_unread_count = AsyncMock(
            return_value=UnreadCountResponse(count=5)
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_notification_service] = lambda: mock_svc

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/notifications/unread-count",
                    headers={"Authorization": "Bearer token123"},
                )
            assert response.status_code == 200
            assert response.json()["count"] == 5
        finally:
            app.dependency_overrides.clear()

    async def test_returns_zero_when_all_read(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.get_unread_count = AsyncMock(
            return_value=UnreadCountResponse(count=0)
        )

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_notification_service] = lambda: mock_svc

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/notifications/unread-count",
                    headers={"Authorization": "Bearer token123"},
                )
            assert response.status_code == 200
            assert response.json()["count"] == 0
        finally:
            app.dependency_overrides.clear()


class TestMarkRead:

    async def test_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/notifications/notif-1/read")
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_returns_204(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.mark_read = AsyncMock(return_value=True)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_notification_service] = lambda: mock_svc

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/notifications/notif-1/read",
                    headers={"Authorization": "Bearer token123"},
                )
            assert response.status_code == 204
            mock_svc.mark_read.assert_called_once_with(
                notification_id="notif-1", user_id="user-123"
            )
        finally:
            app.dependency_overrides.clear()

    async def test_returns_404_when_not_found(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.mark_read = AsyncMock(return_value=False)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_notification_service] = lambda: mock_svc

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/notifications/nonexistent/read",
                    headers={"Authorization": "Bearer token123"},
                )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestMarkAllRead:

    async def test_requires_auth(self) -> None:
        app.dependency_overrides.clear()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/notifications/read-all")
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_returns_204(self) -> None:
        user = _make_user()
        mock_svc = AsyncMock()
        mock_svc.mark_all_read = AsyncMock(return_value=3)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_notification_service] = lambda: mock_svc

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/notifications/read-all",
                    headers={"Authorization": "Bearer token123"},
                )
            assert response.status_code == 204
            mock_svc.mark_all_read.assert_called_once_with(user_id="user-123")
        finally:
            app.dependency_overrides.clear()


class TestNotificationServiceSubscriptionMatching:

    async def test_any_mode_matches_single_keyword(self) -> None:
        from app.services.notification_service import NotificationService

        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "user_id": "user-1",
                    "keywords": ["python", "AI"],
                    "match_mode": "any",
                    "sources": [],
                }
            ]
        )

        notification_row = {
            "id": "notif-uuid-1",
            "user_id": "user-1",
            "type": "new_match",
            "title": "New match: AI Developer",
            "body": "TestCo — AI Developer",
            "job_id": "job-1",
            "is_read": False,
            "email_sent": False,
            "created_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
        }
        mock_pool.fetchrow = AsyncMock(return_value=notification_row)

        svc = NotificationService(pool=mock_pool)
        new_jobs = [
            {"id": "job-1", "title": "AI Developer", "description": "Work with machine learning", "source": "remoteok", "company": "TestCo"},
        ]

        created = await svc.check_subscriptions_after_scrape(new_jobs)
        assert created == 1
        mock_pool.fetchrow.assert_called_once()

    async def test_all_mode_requires_all_keywords(self) -> None:
        from app.services.notification_service import NotificationService

        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "user_id": "user-1",
                    "keywords": ["python", "AI"],
                    "match_mode": "all",
                    "sources": [],
                }
            ]
        )
        mock_pool.fetchrow = AsyncMock()

        svc = NotificationService(pool=mock_pool)

        jobs_partial = [
            {"id": "job-1", "title": "Python Developer", "description": "Build web apps", "source": "remoteok", "company": "Co"},
        ]
        created = await svc.check_subscriptions_after_scrape(jobs_partial)
        assert created == 0

    async def test_all_mode_matches_when_all_present(self) -> None:
        from app.services.notification_service import NotificationService

        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "user_id": "user-1",
                    "keywords": ["python", "AI"],
                    "match_mode": "all",
                    "sources": [],
                }
            ]
        )
        notification_row = {
            "id": "notif-uuid-1",
            "user_id": "user-1",
            "type": "new_match",
            "title": "New match: Python AI Engineer",
            "body": "Co — Python AI Engineer",
            "job_id": "job-1",
            "is_read": False,
            "email_sent": False,
            "created_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
        }
        mock_pool.fetchrow = AsyncMock(return_value=notification_row)

        svc = NotificationService(pool=mock_pool)

        jobs_both = [
            {"id": "job-1", "title": "Python AI Engineer", "description": "Build AI tools", "source": "remoteok", "company": "Co"},
        ]
        created = await svc.check_subscriptions_after_scrape(jobs_both)
        assert created == 1

    async def test_source_filter_excludes_non_matching_source(self) -> None:
        from app.services.notification_service import NotificationService

        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "user_id": "user-1",
                    "keywords": ["AI"],
                    "match_mode": "any",
                    "sources": ["eleduck"],
                }
            ]
        )
        mock_pool.fetchrow = AsyncMock()

        svc = NotificationService(pool=mock_pool)

        jobs = [
            {"id": "job-1", "title": "AI Developer", "description": "", "source": "remoteok", "company": "Co"},
        ]
        created = await svc.check_subscriptions_after_scrape(jobs)
        assert created == 0

    async def test_source_filter_includes_matching_source(self) -> None:
        from app.services.notification_service import NotificationService

        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "user_id": "user-1",
                    "keywords": ["AI"],
                    "match_mode": "any",
                    "sources": ["remoteok"],
                }
            ]
        )
        notification_row = {
            "id": "notif-uuid-1",
            "user_id": "user-1",
            "type": "new_match",
            "title": "New match: AI Developer",
            "body": "Co — AI Developer",
            "job_id": "job-1",
            "is_read": False,
            "email_sent": False,
            "created_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
        }
        mock_pool.fetchrow = AsyncMock(return_value=notification_row)

        svc = NotificationService(pool=mock_pool)

        jobs = [
            {"id": "job-1", "title": "AI Developer", "description": "", "source": "remoteok", "company": "Co"},
        ]
        created = await svc.check_subscriptions_after_scrape(jobs)
        assert created == 1

    async def test_no_active_subscriptions_returns_zero(self) -> None:
        from app.services.notification_service import NotificationService

        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[])

        svc = NotificationService(pool=mock_pool)
        created = await svc.check_subscriptions_after_scrape(
            [{"id": "j1", "title": "AI Dev", "description": "", "source": "remoteok", "company": "Co"}]
        )
        assert created == 0

    async def test_empty_keywords_skips_subscription(self) -> None:
        from app.services.notification_service import NotificationService

        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "user_id": "user-1",
                    "keywords": [],
                    "match_mode": "any",
                    "sources": [],
                }
            ]
        )

        svc = NotificationService(pool=mock_pool)
        created = await svc.check_subscriptions_after_scrape(
            [{"id": "j1", "title": "AI Dev", "description": "", "source": "remoteok", "company": "Co"}]
        )
        assert created == 0


class TestNotificationServiceEmail:

    def test_send_email_skips_when_smtp_not_configured(self) -> None:
        from app.services.notification_service import NotificationService

        svc = NotificationService()
        notif = _make_notification()

        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.SMTP_HOST = ""
            mock_settings.FROM_EMAIL = ""
            result = svc.send_email_notification("test@example.com", notif)

        assert result is False

    def test_send_email_success(self) -> None:
        from app.services.notification_service import NotificationService

        svc = NotificationService()
        notif = _make_notification()

        with patch("app.services.notification_service.settings") as mock_settings, \
             patch("app.services.notification_service.smtplib.SMTP") as mock_smtp_cls:
            mock_settings.SMTP_HOST = "smtp.test.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USER = "user"
            mock_settings.SMTP_PASSWORD = "pass"
            mock_settings.FROM_EMAIL = "from@test.com"

            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

            result = svc.send_email_notification("to@test.com", notif)

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user", "pass")
        mock_smtp.sendmail.assert_called_once()

    def test_send_email_handles_exception(self) -> None:
        from app.services.notification_service import NotificationService

        svc = NotificationService()
        notif = _make_notification()

        with patch("app.services.notification_service.settings") as mock_settings, \
             patch("app.services.notification_service.smtplib.SMTP") as mock_smtp_cls:
            mock_settings.SMTP_HOST = "smtp.test.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.FROM_EMAIL = "from@test.com"
            mock_settings.SMTP_USER = ""
            mock_settings.SMTP_PASSWORD = ""

            mock_smtp_cls.side_effect = ConnectionRefusedError("refused")

            result = svc.send_email_notification("to@test.com", notif)

        assert result is False
