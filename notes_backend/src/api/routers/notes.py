from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user_id
from src.api.schemas import NoteCreateRequest, NoteDTO, NoteUpdateRequest
from src.db.session import get_db_session
from src.services.notes_service import (
    ListNotesParams,
    create_note_flow,
    delete_note_flow,
    get_note_flow,
    list_notes_flow,
    update_note_flow,
)

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get(
    "",
    response_model=list[NoteDTO],
    summary="List notes",
    description="List notes with optional query, tag filter, and pinned filter. Excludes deleted notes by default.",
    operation_id="listNotes",
)
async def list_notes(
    q: str | None = Query(default=None, description="Search query (title/content/full-text)."),
    tag: str | None = Query(default=None, description="Filter by tag name."),
    pinned: bool | None = Query(default=None, description="Filter pinned/unpinned."),
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> list[NoteDTO]:
    params = ListNotesParams(q=q, tag=tag, pinned=pinned, include_deleted=False)
    items = await list_notes_flow(session, params=params, user_id=user_id)
    return [NoteDTO(**i) for i in items]


@router.post(
    "",
    response_model=NoteDTO,
    summary="Create note",
    description="Create a new note.",
    operation_id="createNote",
)
async def create_note(
    body: NoteCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> NoteDTO:
    item = await create_note_flow(
        session,
        title=body.title,
        content=body.content,
        tags=body.tags,
        pinned=body.pinned,
        favorited=body.favorited,
        user_id=user_id,
    )
    return NoteDTO(**item)


@router.get(
    "/{note_id}",
    response_model=NoteDTO,
    summary="Get note",
    description="Fetch a note by ID.",
    operation_id="getNote",
)
async def get_note(
    note_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> NoteDTO:
    item = await get_note_flow(session, note_id=note_id, user_id=user_id)
    return NoteDTO(**item)


@router.patch(
    "/{note_id}",
    response_model=NoteDTO,
    summary="Update note",
    description="Patch a note. Any provided fields are updated.",
    operation_id="updateNote",
)
async def update_note(
    note_id: uuid.UUID,
    body: NoteUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> NoteDTO:
    item = await update_note_flow(
        session,
        note_id=note_id,
        user_id=user_id,
        title=body.title,
        content=body.content,
        tags=body.tags,
        pinned=body.pinned,
        favorited=body.favorited,
        deleted=body.deleted,
    )
    return NoteDTO(**item)


@router.delete(
    "/{note_id}",
    summary="Delete note",
    description="Soft-delete a note (sets is_deleted=true).",
    operation_id="deleteNote",
)
async def delete_note(
    note_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> dict:
    await delete_note_flow(session, note_id=note_id, user_id=user_id)
    return {"ok": True}
