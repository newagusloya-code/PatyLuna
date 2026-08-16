"""
Pomodoro session endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.models import PomodoroSession
from app.schemas.pomodoro import PomodoroCreate, PomodoroResponse

router = APIRouter(prefix="/pomodoro", tags=["Pomodoro"])


# ── Start Session ────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=PomodoroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new Pomodoro session",
)
async def start_session(
    payload: PomodoroCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    session = PomodoroSession(
        user_id=user_id,
        task_description=payload.task_description,
        category=payload.category,
        duration_minutes=payload.duration_minutes,
        background_sound=payload.background_sound,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


# ── Complete Session ─────────────────────────────────────────────────────────

@router.patch(
    "/{session_id}/complete",
    response_model=PomodoroResponse,
    summary="Mark a Pomodoro session as completed",
)
async def complete_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PomodoroSession).where(
            PomodoroSession.id == session_id,
            PomodoroSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session.completed = True
    session.ended_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(session)
    return session


# ── List Sessions ────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[PomodoroResponse],
    summary="List Pomodoro sessions for the current user",
)
async def list_sessions(
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(PomodoroSession)
        .where(PomodoroSession.user_id == user_id)
        .order_by(PomodoroSession.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if category:
        query = query.where(PomodoroSession.category == category)

    result = await db.execute(query)
    return result.scalars().all()


# ── Get Session ──────────────────────────────────────────────────────────────

@router.get(
    "/{session_id}",
    response_model=PomodoroResponse,
    summary="Get a specific Pomodoro session",
)
async def get_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PomodoroSession).where(
            PomodoroSession.id == session_id,
            PomodoroSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


# ── Delete Session ───────────────────────────────────────────────────────────

@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Pomodoro session",
)
async def delete_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PomodoroSession).where(
            PomodoroSession.id == session_id,
            PomodoroSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await db.delete(session)
