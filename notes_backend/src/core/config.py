from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables.

    Contract:
      - Inputs: environment variables (read once at startup)
      - Outputs: strongly-typed settings object
      - Errors: raises ValueError for missing required config
      - Side effects: none
    """

    database_url: str
    cors_allow_origins: list[str]
    auth_enabled: bool
    jwt_secret: str | None
    jwt_algorithm: str
    jwt_access_token_exp_minutes: int


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    return int(value)


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load settings from environment.

    Required env vars:
      - POSTGRES_URL (preferred) OR DATABASE_URL

    Optional:
      - CORS_ALLOW_ORIGINS (comma-separated; default "*")
      - AUTH_ENABLED (default false)
      - JWT_SECRET (required when AUTH_ENABLED=true)
      - JWT_ALGORITHM (default HS256)
      - JWT_ACCESS_TOKEN_EXP_MINUTES (default 60)
    """
    database_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("Missing required env var POSTGRES_URL (or DATABASE_URL).")

    cors_origins = _parse_csv(os.getenv("CORS_ALLOW_ORIGINS"))
    if not cors_origins:
        cors_origins = ["*"]

    auth_enabled = _parse_bool(os.getenv("AUTH_ENABLED"), default=False)
    jwt_secret = os.getenv("JWT_SECRET")
    if auth_enabled and not jwt_secret:
        raise ValueError("AUTH_ENABLED=true requires JWT_SECRET to be set.")

    return Settings(
        database_url=database_url,
        cors_allow_origins=cors_origins,
        auth_enabled=auth_enabled,
        jwt_secret=jwt_secret,
        jwt_algorithm=os.getenv("JWT_ALGORITHM") or "HS256",
        jwt_access_token_exp_minutes=_parse_int(
            os.getenv("JWT_ACCESS_TOKEN_EXP_MINUTES"), default=60
        ),
    )
