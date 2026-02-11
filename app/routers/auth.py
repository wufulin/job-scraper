from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.models.responses import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPayload,
    UserResponse,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=UserResponse, status_code=201)
def register_user(body: RegisterRequest) -> UserResponse:
    return auth_service.register(body.email, body.password)


@router.post("/login", response_model=TokenResponse)
def login_user(body: LoginRequest) -> TokenResponse:
    return auth_service.login(body.email, body.password)


@router.get("/me", response_model=UserPayload)
def get_me(user: UserPayload = Depends(get_current_user)) -> UserPayload:
    return user


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest) -> TokenResponse:
    return auth_service.refresh(body.refresh_token)


@router.post("/logout", status_code=204)
def logout(user: UserPayload = Depends(get_current_user)) -> Response:
    return Response(status_code=204)
