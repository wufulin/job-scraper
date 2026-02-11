"""Authentication service – Supabase Auth + JWT verification."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from jose import JWTError, jwt
from loguru import logger
from supabase import Client, create_client

from app.config.settings import settings
from app.models.responses import TokenResponse, UserPayload, UserResponse

_supabase_client: Optional[Client] = None


def _get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        )
    return _supabase_client


def register(email: str, password: str) -> UserResponse:
    client = _get_supabase_client()
    try:
        result = client.auth.sign_up({"email": email, "password": password})
    except Exception as exc:
        logger.error("Supabase sign_up failed: {}", exc)
        raise HTTPException(status_code=400, detail="Registration failed") from exc

    user = result.user
    if user is None:
        raise HTTPException(status_code=400, detail="Registration failed")

    created_at = user.created_at
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    if created_at is None:
        created_at = datetime.now(tz=timezone.utc)

    return UserResponse(
        id=user.id,
        email=user.email or email,
        created_at=created_at,
    )


def login(email: str, password: str) -> TokenResponse:
    client = _get_supabase_client()
    try:
        result = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        logger.error("Supabase sign_in failed: {}", exc)
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc

    session = result.session
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in or 3600,
    )


def verify_jwt(token: str) -> UserPayload:
    # Audience "authenticated" is required by Supabase-issued JWTs
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    return UserPayload(
        sub=payload.get("sub", ""),
        email=payload.get("email", ""),
        role=payload.get("role", "user"),
    )


def refresh(refresh_token: str) -> TokenResponse:
    client = _get_supabase_client()
    try:
        client.auth.refresh_session(refresh_token)
        session = client.auth.get_session()
    except Exception as exc:
        logger.error("Supabase refresh failed: {}", exc)
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    if session is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in or 3600,
    )


def get_current_user(token: str) -> UserPayload:
    return verify_jwt(token)
