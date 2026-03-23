from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.errors import ConflictError, NotFoundError
from src.db.models import NoteTag, Tag

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TagListItem:
    id: uuid.UUID
    name: str
    color: str | None
    note_count: int


# PUBLIC_INTERFACE
async def list_tags_flow(
    session: AsyncSession, *, user_id: uuid.UUID | None
) -> list[TagListItem]:
    """List tags with note counts."""
    logger.info("list_tags_flow start")

    stmt = (
        select(
            Tag.id,
            Tag.name,
            Tag.color,
            func.count(NoteTag.note_id).label("note_count"),
        )
        .outerjoin(NoteTag, NoteTag.tag_id == Tag.id)
        .group_by(Tag.id, Tag.name, Tag.color)
        .order_by(func.lower(Tag.name).asc())
    )
    if user_id is not None:
        stmt = stmt.where(Tag.user_id == user_id)

    rows = (await session.execute(stmt)).all()
    out = [TagListItem(id=r.id, name=r.name, color=r.color, note_count=int(r.note_count)) for r in rows]
    logger.info("list_tags_flow end count=%d", len(out))
    return out


# PUBLIC_INTERFACE
async def create_tag_flow(
    session: AsyncSession, *, name: str, color: str | None, user_id: uuid.UUID | None
) -> Tag:
    """Create a tag; raises ConflictError if it already exists for the user."""
    nn = name.strip()
    if not nn:
        raise ConflictError("Tag name cannot be empty")

    # Check unique constraint proactively for nicer error.
    stmt = select(Tag).where(func.lower(Tag.name) == nn.lower())
    if user_id is None:
        stmt = stmt.where(Tag.user_id.is_(None))
    else:
        stmt = stmt.where(Tag.user_id == user_id)

    existing = (await session.execute(stmt)).scalars().first()
    if existing:
        raise ConflictError("Tag already exists", details={"name": nn})

    tag = Tag(user_id=user_id, name=nn, color=color, created_at=_utcnow())
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag


# PUBLIC_INTERFACE
async def delete_tag_flow(
    session: AsyncSession, *, tag_id: uuid.UUID, user_id: uuid.UUID | None
) -> None:
    """Delete a tag (hard delete)."""
    stmt = select(Tag).where(Tag.id == tag_id)
    if user_id is not None:
        stmt = stmt.where(Tag.user_id == user_id)

    tag = (await session.execute(stmt)).scalars().first()
    if not tag:
        raise NotFoundError("Tag not found", details={"tag_id": str(tag_id)})

    await session.delete(tag)
    await session.commit()
