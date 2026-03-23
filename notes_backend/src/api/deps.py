from __future__ import annotations

import uuid

from fastapi import Depends, Header
from jose import JWTError, jwt

from src.api.errors import UnauthorizedError
from src.core.config import Settings, get_settings


# PUBLIC_INTERFACE
def get_current_user_id(
    authorization: str | None = Header(default=None, description="Bearer token"),
    settings: Settings = Depends(get_settings),
) -> uuid.UUID | None:
    """Get current user_id from Authorization header if AUTH_ENABLED=true.

    Contract:
      - If auth disabled: returns None always
      - If enabled: requires valid Bearer JWT; returns UUID user_id
      - Errors: UnauthorizedError when enabled and token missing/invalid
    """
    if not settings.auth_enabled:
        return None

    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        assert settings.jwt_secret is not None
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedError("Invalid token")
        return uuid.UUID(str(sub))
    except (JWTError, ValueError) as e:
        raise UnauthorizedError("Invalid token") from e
