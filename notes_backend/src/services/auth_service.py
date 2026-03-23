from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.errors import ConflictError, UnauthorizedError
from src.core.config import Settings
from src.db.models import User

logger = logging.getLogger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AuthResult:
    token: str
    user_id: uuid.UUID


def _create_access_token(*, settings: Settings, user_id: uuid.UUID) -> str:
    now = _utcnow()
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_access_token_exp_minutes)).timestamp()),
    }
    assert settings.jwt_secret is not None
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# PUBLIC_INTERFACE
async def signup_flow(
    session: AsyncSession, *, settings: Settings, email: str, password: str
) -> AuthResult:
    """Create a user and return an auth token."""
    email_n = email.strip().lower()
    existing = (await session.execute(select(User).where(User.email == email_n))).scalars().first()
    if existing:
        raise ConflictError("Email already in use", details={"email": email_n})

    pw_hash = _pwd_context.hash(password)
    now = _utcnow()
    user = User(
        email=email_n,
        display_name=None,
        password_hash=pw_hash,
        is_active=True,
        created_at=now,
        updated_at=now,
        last_login_at=now,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = _create_access_token(settings=settings, user_id=user.id)
    logger.info("signup_flow created user_id=%s", user.id)
    return AuthResult(token=token, user_id=user.id)


# PUBLIC_INTERFACE
async def login_flow(
    session: AsyncSession, *, settings: Settings, email: str, password: str
) -> AuthResult:
    """Authenticate user credentials and return an auth token."""
    email_n = email.strip().lower()
    user = (await session.execute(select(User).where(User.email == email_n))).scalars().first()
    if not user or not user.password_hash:
        raise UnauthorizedError("Invalid credentials")

    if not _pwd_context.verify(password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")

    user.last_login_at = _utcnow()
    user.updated_at = _utcnow()
    await session.commit()

    token = _create_access_token(settings=settings, user_id=user.id)
    logger.info("login_flow ok user_id=%s", user.id)
    return AuthResult(token=token, user_id=user.id)
