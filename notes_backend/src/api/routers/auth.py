from __future__ import annotations

from fastapi import APIRouter, Depends

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.errors import ForbiddenError
from src.api.schemas import AuthLoginRequest, AuthSignupRequest, AuthTokenResponse
from src.core.config import Settings, get_settings
from src.db.session import get_db_session
from src.services.auth_service import login_flow, signup_flow

router = APIRouter(prefix="/auth", tags=["auth"])


def _require_auth_enabled(settings: Settings) -> None:
    if not settings.auth_enabled:
        raise ForbiddenError("Auth is disabled on this deployment. Set AUTH_ENABLED=true to enable.")


@router.post(
    "/signup",
    response_model=AuthTokenResponse,
    summary="Sign up",
    description="Create a user account and return a bearer token (JWT). Enabled only when AUTH_ENABLED=true.",
    operation_id="signup",
)
async def signup(
    body: AuthSignupRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthTokenResponse:
    _require_auth_enabled(settings)
    res = await signup_flow(session, settings=settings, email=body.email, password=body.password)
    return AuthTokenResponse(token=res.token)


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Log in",
    description="Authenticate and return a bearer token (JWT). Enabled only when AUTH_ENABLED=true.",
    operation_id="login",
)
async def login(
    body: AuthLoginRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthTokenResponse:
    _require_auth_enabled(settings)
    res = await login_flow(session, settings=settings, email=body.email, password=body.password)
    return AuthTokenResponse(token=res.token)
