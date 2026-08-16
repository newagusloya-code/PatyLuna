"""Pydantic schemas for Pomodoro and Sleep operations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Pomodoro ─────────────────────────────────────────────────────────────────

class PomodoroCreate(BaseModel):
    """Payload for ``POST /pomodoro``."""
    task_description: str = Field(min_length=1, max_length=512)
    category: Optional[str] = Field(None, max_length=64)
    duration_minutes: int = Field(default=25, ge=1, le=240)
    background_sound: Optional[str] = Field(None, max_length=128)


class PomodoroComplete(BaseModel):
    """Payload for ``PATCH /pomodoro/{id}/complete``."""
    completed: bool = True


class PomodoroResponse(BaseModel):
    """Returned from pomodoro endpoints."""
    id: int
    task_description: str
    category: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: int
    background_sound: Optional[str] = None
    completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Sleep Session ────────────────────────────────────────────────────────────

class SleepSessionCreate(BaseModel):
    """Payload for ``POST /sleep``."""
    sound_preset: Optional[str] = Field(None, max_length=128)
    meditation_type: Optional[str] = Field(None, max_length=64)


class SleepSessionEnd(BaseModel):
    """Payload for ``PATCH /sleep/{id}/end``."""
    quality_rating: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = Field(None, max_length=2000)


class SleepSessionResponse(BaseModel):
    """Returned from sleep endpoints."""
    id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    sound_preset: Optional[str] = None
    meditation_type: Optional[str] = None
    quality_rating: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
