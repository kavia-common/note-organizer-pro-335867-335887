from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class NoteDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Note ID (UUID).")
    title: str = Field(..., description="Note title.")
    content: str = Field(..., description="Note content.")
    tags: list[str] = Field(..., description="List of tag names attached to the note.")
    pinned: bool = Field(..., description="True if note is pinned.")
    favorited: bool = Field(..., description="True if note is favorited.")
    updatedAt: datetime = Field(..., description="Last updated timestamp (ISO).")
    createdAt: datetime = Field(..., description="Creation timestamp (ISO).")
    deleted: bool | None = Field(default=None, description="Soft-deleted flag (optional).")


class NoteCreateRequest(BaseModel):
    title: str = Field("", description="Initial title.")
    content: str = Field("", description="Initial content.")
    tags: list[str] = Field(default_factory=list, description="Initial tag names.")
    pinned: bool = Field(False, description="Whether the note should start pinned.")
    favorited: bool = Field(False, description="Whether the note should start favorited.")


class NoteUpdateRequest(BaseModel):
    title: str | None = Field(None, description="New title.")
    content: str | None = Field(None, description="New content.")
    tags: list[str] | None = Field(None, description="Replace tags with these names.")
    pinned: bool | None = Field(None, description="Set pinned/unpinned.")
    favorited: bool | None = Field(None, description="Set favorited/unfavorited.")
    deleted: bool | None = Field(None, description="Soft delete / restore.")


class TagDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Tag ID.")
    name: str = Field(..., description="Tag name (case-insensitive).")
    color: str | None = Field(default=None, description="Optional color string.")
    noteCount: int | None = Field(default=None, description="Number of notes using this tag.")


class TagCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="Tag name.")
    color: str | None = Field(default=None, description="Optional color.")


class SharePermission(str):
    """Share permission enum for frontend compatibility."""
    # kept as str wrapper to match frontend union typing


class ShareDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Share record ID.")
    noteId: uuid.UUID = Field(..., description="Shared note ID.")
    sharedWithEmail: str = Field(..., description="Email shared with (if available).")
    permission: Literal["read", "comment", "edit"] = Field(..., description="Permission level.")
    createdAt: datetime = Field(..., description="Share created timestamp.")


class ShareCreateRequest(BaseModel):
    email: str = Field(..., description="Recipient email.")
    permission: Literal["read", "comment", "edit"] = Field("read", description="Permission.")

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class AuthSignupRequest(BaseModel):
    email: str = Field(..., description="Email.")
    password: str = Field(..., min_length=6, max_length=200, description="Password.")


class AuthLoginRequest(BaseModel):
    email: str = Field(..., description="Email.")
    password: str = Field(..., description="Password.")


class AuthTokenResponse(BaseModel):
    token: str = Field(..., description="Bearer token (JWT).")
