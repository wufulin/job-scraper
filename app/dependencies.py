from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import Settings, settings
from app.models.responses import UserPayload
from app.services.auth import verify_jwt

security = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    return settings


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserPayload:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return verify_jwt(credentials.credentials)


def require_admin(
    user: UserPayload = Depends(get_current_user),
) -> UserPayload:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
