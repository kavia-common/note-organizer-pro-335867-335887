from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.errors import NotFoundError
from src.db.models import Note, Tag

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ListNotesParams:
    q: str | None = None
    tag: str | None = None
    pinned: bool | None = None
    include_deleted: bool = False


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _ensure_tags(
    session: AsyncSession, *, names: list[str], user_id: uuid.UUID | None
) -> list[Tag]:
    """Get or create tags for given names (case-insensitive).

    Invariant: returned tags correspond 1:1 to unique normalized names.
    """
    normalized = []
    seen = set()
    for n in names:
        nn = n.strip()
        if not nn:
            continue
        key = nn.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(nn)

    if not normalized:
        return []

    existing = (
        await session.execute(
            select(Tag).where(
                func.lower(Tag.name).in_([n.lower() for n in normalized]),
                Tag.user_id.is_(user_id) if user_id is None else Tag.user_id == user_id,
            )
        )
    ).scalars().all()

    by_lower = {t.name.lower(): t for t in existing}
    created: list[Tag] = []
    for n in normalized:
        if n.lower() in by_lower:
            continue
        t = Tag(user_id=user_id, name=n, color=None, created_at=_utcnow())
        session.add(t)
        created.append(t)

    if created:
        await session.flush()

    tags = [by_lower.get(n.lower()) or next(t for t in created if t.name.lower() == n.lower()) for n in normalized]
    return tags


def _note_to_dto_dict(note: Note) -> dict:
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "tags": [t.name for t in (note.tags or [])],
        "pinned": note.pinned_at is not None,
        "favorited": note.favorited_at is not None,
        "updatedAt": note.updated_at,
        "createdAt": note.created_at,
        "deleted": note.is_deleted or None,
    }


# PUBLIC_INTERFACE
async def list_notes_flow(
    session: AsyncSession, *, params: ListNotesParams, user_id: uuid.UUID | None
) -> list[dict]:
    """List notes with optional filters and full-text-ish search.

    Contract:
      - Inputs: ListNotesParams + optional user_id
      - Output: list of NoteDTO-compatible dicts
      - Errors: none expected (empty list ok)
      - Side effects: DB reads
    """
    logger.info("list_notes_flow start q=%s tag=%s pinned=%s", params.q, params.tag, params.pinned)

    stmt = select(Note).options(selectinload(Note.tags))

    if user_id is not None:
        stmt = stmt.where(Note.user_id == user_id)

    if not params.include_deleted:
        stmt = stmt.where(Note.is_deleted.is_(False))

    if params.pinned is True:
        stmt = stmt.where(Note.pinned_at.is_not(None))
    elif params.pinned is False:
        stmt = stmt.where(Note.pinned_at.is_(None))

    if params.tag:
        tag_name = params.tag.strip().lower()
        stmt = stmt.join(Note.tags).where(func.lower(Tag.name) == tag_name)

    if params.q:
        q = params.q.strip()
        if q:
            # Prefer DB full-text search if configured; fallback to ILIKE.
            # We keep this logic centralized to avoid duplicated search behavior.
            stmt = stmt.where(
                text(
                    "(notes.search_tsv @@ plainto_tsquery('english', :q)) OR (notes.title ILIKE :likeq) OR (notes.content ILIKE :likeq)"
                )
            ).params(q=q, likeq=f"%{q}%")

    stmt = stmt.order_by(Note.updated_at.desc())

    notes = (await session.execute(stmt)).scalars().unique().all()
    out = [_note_to_dto_dict(n) for n in notes]

    logger.info("list_notes_flow end count=%d", len(out))
    return out


# PUBLIC_INTERFACE
async def get_note_flow(
    session: AsyncSession, *, note_id: uuid.UUID, user_id: uuid.UUID | None
) -> dict:
    """Fetch a single note.

    Errors:
      - NotFoundError if note not found / inaccessible
    """
    stmt = (
        select(Note)
        .options(selectinload(Note.tags))
        .where(Note.id == note_id)
    )
    if user_id is not None:
        stmt = stmt.where(Note.user_id == user_id)

    note = (await session.execute(stmt)).scalars().first()
    if not note:
        raise NotFoundError("Note not found", details={"note_id": str(note_id)})

    return _note_to_dto_dict(note)


# PUBLIC_INTERFACE
async def create_note_flow(
    session: AsyncSession,
    *,
    title: str,
    content: str,
    tags: list[str],
    pinned: bool,
    favorited: bool,
    user_id: uuid.UUID | None,
) -> dict:
    """Create a note and attach tags."""
    now = _utcnow()
    note = Note(
        user_id=user_id,
        title=title or "",
        content=content or "",
        content_format="markdown",
        is_archived=False,
        is_deleted=False,
        pinned_at=now if pinned else None,
        favorited_at=now if favorited else None,
        created_at=now,
        updated_at=now,
    )
    session.add(note)
    await session.flush()

    note.tags = await _ensure_tags(session, names=tags, user_id=user_id)
    note.updated_at = _utcnow()
    await session.commit()
    await session.refresh(note)

    # reload tags relationship
    note = (await session.execute(
        select(Note).options(selectinload(Note.tags)).where(Note.id == note.id)
    )).scalars().first()
    return _note_to_dto_dict(note)


# PUBLIC_INTERFACE
async def update_note_flow(
    session: AsyncSession,
    *,
    note_id: uuid.UUID,
    user_id: uuid.UUID | None,
    title: str | None = None,
    content: str | None = None,
    tags: list[str] | None = None,
    pinned: bool | None = None,
    favorited: bool | None = None,
    deleted: bool | None = None,
) -> dict:
    """Update mutable fields for a note (PATCH semantics)."""
    stmt = select(Note).options(selectinload(Note.tags)).where(Note.id == note_id)
    if user_id is not None:
        stmt = stmt.where(Note.user_id == user_id)

    note = (await session.execute(stmt)).scalars().first()
    if not note:
        raise NotFoundError("Note not found", details={"note_id": str(note_id)})

    if title is not None:
        note.title = title
    if content is not None:
        note.content = content
    if pinned is not None:
        note.pinned_at = _utcnow() if pinned else None
    if favorited is not None:
        note.favorited_at = _utcnow() if favorited else None
    if deleted is not None:
        note.is_deleted = bool(deleted)

    if tags is not None:
        note.tags = await _ensure_tags(session, names=tags, user_id=user_id)

    note.updated_at = _utcnow()
    await session.commit()
    await session.refresh(note)

    note = (await session.execute(
        select(Note).options(selectinload(Note.tags)).where(Note.id == note.id)
    )).scalars().first()
    return _note_to_dto_dict(note)


# PUBLIC_INTERFACE
async def delete_note_flow(
    session: AsyncSession, *, note_id: uuid.UUID, user_id: uuid.UUID | None
) -> None:
    """Soft-delete a note (is_deleted=true)."""
    stmt = select(Note).where(Note.id == note_id)
    if user_id is not None:
        stmt = stmt.where(Note.user_id == user_id)

    note = (await session.execute(stmt)).scalars().first()
    if not note:
        raise NotFoundError("Note not found", details={"note_id": str(note_id)})

    note.is_deleted = True
    note.updated_at = _utcnow()
    await session.commit()
