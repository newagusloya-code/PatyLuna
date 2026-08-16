"""Pydantic schemas for Diary operations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────────────────────────────────

class DiaryEntryCreate(BaseModel):
    """Payload for ``POST /diary``."""
    content: str = Field(min_length=1, max_length=50_000)
    title: Optional[str] = Field(None, max_length=256)
    mood: Optional[str] = Field(None, max_length=32)
    tags: Optional[str] = Field(None, max_length=512)


class DiaryEntryUpdate(BaseModel):
    """Payload for ``PATCH /diary/{id}``."""
    content: Optional[str] = Field(None, min_length=1, max_length=50_000)
    title: Optional[str] = Field(None, max_length=256)
    mood: Optional[str] = Field(None, max_length=32)
    tags: Optional[str] = Field(None, max_length=512)


# ── Response Schemas ─────────────────────────────────────────────────────────

class DiaryEntryResponse(BaseModel):
    """Returned from diary endpoints – content is **decrypted** server-side."""
    id: int
    title: Optional[str] = None
    content: str  # decrypted for the authenticated owner
    mood: Optional[str] = None
    tags: Optional[str] = None
    is_public: bool
    created_at: datetime
    updated_at: datetime
    messages: list["DiaryMessageResponse"] = []


class DiaryMessageResponse(BaseModel):
    """A message in a diary chat thread (either from user or AI)."""
    id: int
    role: str
    agent_type: Optional[str] = None
    content: str  # decrypted
    created_at: datetime


class AIChatRequest(BaseModel):
    """Payload for POST /diary/{id}/chat"""
    content: str = Field(..., min_length=1, max_length=10_000)
    selected_agents: list[str] = Field(..., min_items=1, max_items=5)


# Rebuild model to resolve forward references
DiaryEntryResponse.model_rebuild()
