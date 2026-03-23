from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import Settings

_ENGINE: AsyncEngine | None = None
_SESSIONMAKER: async_sessionmaker[AsyncSession] | None = None


def _to_asyncpg_url(url: str) -> str:
    """Convert a postgres URL to an asyncpg-compatible SQLAlchemy URL."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # allow already-prefixed or other SQLAlchemy URLs
    return url


# PUBLIC_INTERFACE
def init_engine(settings: Settings) -> None:
    """Initialize the global async SQLAlchemy engine and sessionmaker.

    Contract:
      - Inputs: Settings with database_url
      - Outputs: none (initializes module-level engine/sessionmaker)
      - Errors: propagates SQLAlchemy engine creation errors
      - Side effects: creates a connection pool (lazy connections)
    """
    global _ENGINE, _SESSIONMAKER
    async_url = _to_asyncpg_url(settings.database_url)

    _ENGINE = create_async_engine(
        async_url,
        pool_pre_ping=True,
        future=True,
    )
    _SESSIONMAKER = async_sessionmaker(
        bind=_ENGINE,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# PUBLIC_INTERFACE
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an AsyncSession per-request."""
    if _SESSIONMAKER is None:
        raise RuntimeError("Database engine is not initialized. Call init_engine().")

    async with _SESSIONMAKER() as session:
        yield session
