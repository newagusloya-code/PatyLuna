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
    ai_feedbacks: list["AIFeedbackResponse"] = []


class AIFeedbackResponse(BaseModel):
    """AI agent feedback attached to a diary entry."""
    id: int
    agent_type: str
    feedback: str  # decrypted
    created_at: datetime


# Rebuild model to resolve forward references
DiaryEntryResponse.model_rebuild()
