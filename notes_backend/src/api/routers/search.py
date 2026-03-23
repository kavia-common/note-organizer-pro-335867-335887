from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user_id
from src.api.schemas import NoteDTO
from src.db.session import get_db_session
from src.services.notes_service import ListNotesParams, list_notes_flow

router = APIRouter(tags=["search"])


@router.get(
    "/search",
    response_model=list[NoteDTO],
    summary="Search notes",
    description="Search notes by query across title/content/full-text index. Equivalent to GET /notes?q=...",
    operation_id="searchNotes",
)
async def search_notes(
    q: str = Query(..., min_length=1, description="Search query."),
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> list[NoteDTO]:
    items = await list_notes_flow(session, params=ListNotesParams(q=q), user_id=user_id)
    return [NoteDTO(**i) for i in items]
