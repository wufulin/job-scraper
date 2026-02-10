from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.responses import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPayload,
    UserResponse,
)


class TestRegisterRequest:

    def test_valid_register(self) -> None:
        req = RegisterRequest(email="user@example.com", password="secret123")
        assert req.email == "user@example.com"
        assert req.password == "secret123"

    def test_missing_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(password="secret123")  # type: ignore[call-arg]

    def test_missing_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com")  # type: ignore[call-arg]


class TestLoginRequest:

    def test_valid_login(self) -> None:
        req = LoginRequest(email="user@example.com", password="secret123")
        assert req.email == "user@example.com"
        assert req.password == "secret123"

    def test_missing_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(password="secret123")  # type: ignore[call-arg]

    def test_missing_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com")  # type: ignore[call-arg]


class TestTokenResponse:

    def test_valid_token_response(self) -> None:
        resp = TokenResponse(
            access_token="eyJ...",
            refresh_token="eyR...",
            expires_in=3600,
        )
        assert resp.access_token == "eyJ..."
        assert resp.refresh_token == "eyR..."
        assert resp.token_type == "bearer"
        assert resp.expires_in == 3600

    def test_custom_token_type(self) -> None:
        resp = TokenResponse(
            access_token="a",
            refresh_token="b",
            token_type="mac",
            expires_in=7200,
        )
        assert resp.token_type == "mac"

    def test_missing_access_token_raises(self) -> None:
        with pytest.raises(ValidationError):
            TokenResponse(refresh_token="b", expires_in=3600)  # type: ignore[call-arg]


class TestUserResponse:

    def test_valid_user_response(self) -> None:
        now = datetime.now(tz=timezone.utc)
        resp = UserResponse(id="abc-123", email="user@example.com", created_at=now)
        assert resp.id == "abc-123"
        assert resp.email == "user@example.com"
        assert resp.created_at == now

    def test_missing_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            UserResponse(email="user@example.com", created_at=datetime.now(tz=timezone.utc))  # type: ignore[call-arg]


class TestUserPayload:

    def test_valid_payload(self) -> None:
        payload = UserPayload(sub="uuid-1", email="user@example.com")
        assert payload.sub == "uuid-1"
        assert payload.email == "user@example.com"
        assert payload.role == "user"

    def test_custom_role(self) -> None:
        payload = UserPayload(sub="uuid-1", email="admin@example.com", role="admin")
        assert payload.role == "admin"

    def test_missing_sub_raises(self) -> None:
        with pytest.raises(ValidationError):
            UserPayload(email="user@example.com")  # type: ignore[call-arg]

    def test_missing_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            UserPayload(sub="uuid-1")  # type: ignore[call-arg]


class TestAuthEndpoints:
    """Endpoint tests — will fail until auth router is implemented."""

    @pytest.mark.skip(reason="auth router not yet implemented")
    async def test_register_returns_201(self) -> None:
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/register",
                json={"email": "new@example.com", "password": "password123"},
            )
        assert response.status_code == 201

    @pytest.mark.skip(reason="auth router not yet implemented")
    async def test_login_returns_token(self) -> None:
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/login",
                json={"email": "user@example.com", "password": "password123"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.skip(reason="auth router not yet implemented")
    async def test_me_requires_auth(self) -> None:
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/me")
        assert response.status_code == 401

    @pytest.mark.skip(reason="auth router not yet implemented")
    async def test_refresh_returns_new_token(self) -> None:
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/refresh",
                json={"refresh_token": "some-refresh-token"},
            )
        assert response.status_code == 200

    @pytest.mark.skip(reason="auth router not yet implemented")
    async def test_logout_returns_204(self) -> None:
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/logout",
                headers={"Authorization": "Bearer fake-token"},
            )
        assert response.status_code == 204
