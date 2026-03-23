from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user_id
from src.api.schemas import TagCreateRequest, TagDTO
from src.db.session import get_db_session
from src.services.tags_service import create_tag_flow, delete_tag_flow, list_tags_flow

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=list[TagDTO],
    summary="List tags",
    description="List all tags with optional note counts.",
    operation_id="listTags",
)
async def list_tags(
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> list[TagDTO]:
    items = await list_tags_flow(session, user_id=user_id)
    return [
        TagDTO(id=i.id, name=i.name, color=i.color, noteCount=i.note_count) for i in items
    ]


@router.post(
    "",
    response_model=TagDTO,
    summary="Create tag",
    description="Create a new tag (unique per user).",
    operation_id="createTag",
)
async def create_tag(
    body: TagCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> TagDTO:
    tag = await create_tag_flow(session, name=body.name, color=body.color, user_id=user_id)
    return TagDTO(id=tag.id, name=tag.name, color=tag.color, noteCount=0)


@router.delete(
    "/{tag_id}",
    summary="Delete tag",
    description="Delete a tag by ID.",
    operation_id="deleteTag",
)
async def delete_tag(
    tag_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> dict:
    await delete_tag_flow(session, tag_id=tag_id, user_id=user_id)
    return {"ok": True}
