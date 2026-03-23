from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.errors import ConflictError, NotFoundError
from src.db.models import Note, NoteShare, User

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ShareListItem:
    id: uuid.UUID
    note_id: uuid.UUID
    shared_with_email: str
    permission: str
    created_at: datetime


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return (await session.execute(stmt)).scalars().first()


# PUBLIC_INTERFACE
async def create_share_flow(
    session: AsyncSession,
    *,
    note_id: uuid.UUID,
    owner_user_id: uuid.UUID | None,
    email: str,
    permission: str,
) -> NoteShare:
    """Share a note with a user identified by email.

    Errors:
      - NotFoundError if note not found
      - ConflictError if email user doesn't exist OR duplicate share constraint
    """
    logger.info("create_share_flow start note_id=%s email=%s", note_id, email)

    note = (await session.execute(select(Note).where(Note.id == note_id))).scalars().first()
    if not note:
        raise NotFoundError("Note not found", details={"note_id": str(note_id)})

    recipient = await _get_user_by_email(session, email)
    if not recipient:
        raise ConflictError(
            "Cannot share with this email (no user exists).",
            details={"email": email},
        )

    share = NoteShare(
        note_id=note_id,
        owner_user_id=owner_user_id,
        shared_with_user_id=recipient.id,
        share_token=uuid.uuid4(),
        permission=permission,
        created_at=_utcnow(),
        expires_at=None,
        revoked_at=None,
    )
    session.add(share)
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        # likely unique constraint note_id + shared_with_user_id
        raise ConflictError("Share already exists", details={"note_id": str(note_id), "email": email}) from e

    await session.refresh(share)
    logger.info("create_share_flow end share_id=%s", share.id)
    return share


# PUBLIC_INTERFACE
async def list_shares_flow(
    session: AsyncSession, *, note_id: uuid.UUID, owner_user_id: uuid.UUID | None
) -> list[ShareListItem]:
    """List shares for a note."""
    stmt = (
        select(NoteShare, User.email)
        .join(User, User.id == NoteShare.shared_with_user_id)
        .where(NoteShare.note_id == note_id, NoteShare.revoked_at.is_(None))
        .order_by(NoteShare.created_at.desc())
    )

    # If owner_user_id provided, we can enforce ownership by note.user_id.
    if owner_user_id is not None:
        note = (await session.execute(select(Note).where(Note.id == note_id))).scalars().first()
        if not note:
            raise NotFoundError("Note not found", details={"note_id": str(note_id)})
        if note.user_id != owner_user_id:
            # We keep behavior conservative and avoid leaking shares.
            raise NotFoundError("Note not found", details={"note_id": str(note_id)})

    rows = (await session.execute(stmt)).all()
    return [
        ShareListItem(
            id=share.id,
            note_id=share.note_id,
            shared_with_email=email,
            permission=share.permission,
            created_at=share.created_at,
        )
        for (share, email) in rows
    ]
