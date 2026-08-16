"""
Sleep session endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.db.models import SleepSession
from app.schemas.pomodoro import SleepSessionCreate, SleepSessionEnd, SleepSessionResponse

router = APIRouter(prefix="/sleep", tags=["Sleep"])


# ── Start Sleep Session ──────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=SleepSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a sleep session with optional sound preset",
)
async def start_sleep(
    payload: SleepSessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    session = SleepSession(
        user_id=user_id,
        started_at=datetime.now(timezone.utc),
        sound_preset=payload.sound_preset,
        meditation_type=payload.meditation_type,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


# ── End Sleep Session ────────────────────────────────────────────────────────

@router.patch(
    "/{session_id}/end",
    response_model=SleepSessionResponse,
    summary="End a sleep session and optionally rate quality",
)
async def end_sleep(
    session_id: int,
    payload: SleepSessionEnd,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SleepSession).where(
            SleepSession.id == session_id,
            SleepSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session.ended_at = datetime.now(timezone.utc)
    session.quality_rating = payload.quality_rating
    session.notes = payload.notes
    await db.flush()
    await db.refresh(session)
    return session


# ── List Sleep Sessions ──────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[SleepSessionResponse],
    summary="List sleep sessions for the current user",
)
async def list_sessions(
    skip: int = 0,
    limit: int = 30,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SleepSession)
        .where(SleepSession.user_id == user_id)
        .order_by(SleepSession.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


# ── Get Session ──────────────────────────────────────────────────────────────

@router.get(
    "/{session_id}",
    response_model=SleepSessionResponse,
    summary="Get a specific sleep session",
)
async def get_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SleepSession).where(
            SleepSession.id == session_id,
            SleepSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session
