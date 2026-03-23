from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user_id
from src.api.schemas import ShareCreateRequest, ShareDTO
from src.db.session import get_db_session
from src.services.shares_service import create_share_flow, list_shares_flow

router = APIRouter(prefix="/notes/{note_id}", tags=["sharing"])


@router.post(
    "/share",
    response_model=ShareDTO,
    summary="Share a note",
    description="Share a note with another existing user (by email).",
    operation_id="shareNote",
)
async def share_note(
    note_id: uuid.UUID,
    body: ShareCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> ShareDTO:
    share = await create_share_flow(
        session,
        note_id=note_id,
        owner_user_id=user_id,
        email=body.email,
        permission=body.permission,
    )
    # If email exists, service resolves it; we echo requested email.
    return ShareDTO(
        id=share.id,
        noteId=share.note_id,
        sharedWithEmail=body.email,
        permission=share.permission,  # type: ignore[arg-type]
        createdAt=share.created_at,
    )


@router.get(
    "/shares",
    response_model=list[ShareDTO],
    summary="List note shares",
    description="List shares for a note.",
    operation_id="listShares",
)
async def list_shares(
    note_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> list[ShareDTO]:
    items = await list_shares_flow(session, note_id=note_id, owner_user_id=user_id)
    return [
        ShareDTO(
            id=i.id,
            noteId=i.note_id,
            sharedWithEmail=i.shared_with_email,
            permission=i.permission,  # type: ignore[arg-type]
            createdAt=i.created_at,
        )
        for i in items
    ]
