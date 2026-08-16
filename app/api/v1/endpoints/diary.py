"""
Diary endpoints – encrypted personal entries with AI feedback.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decrypt_text, encrypt_text, get_current_user_id
from app.db.database import get_db
from app.db.models import AIFeedback, DiaryEntry
from app.schemas.diary import (
    AIFeedbackResponse,
    DiaryEntryCreate,
    DiaryEntryResponse,
    DiaryEntryUpdate,
)

router = APIRouter(prefix="/diary", tags=["Diary"])


def _entry_to_response(entry: DiaryEntry) -> DiaryEntryResponse:
    """Decrypt content & feedback, then build the response model."""
    feedbacks = []
    for fb in entry.ai_feedbacks:
        feedbacks.append(
            AIFeedbackResponse(
                id=fb.id,
                agent_type=fb.agent_type,
                feedback=decrypt_text(fb.encrypted_feedback),
                created_at=fb.created_at,
            )
        )

    return DiaryEntryResponse(
        id=entry.id,
        title=entry.title,
        content=decrypt_text(entry.encrypted_content),
        mood=entry.mood,
        tags=entry.tags,
        is_public=entry.is_public,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        ai_feedbacks=feedbacks,
    )


# ── Create ───────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=DiaryEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new encrypted diary entry",
)
async def create_entry(
    payload: DiaryEntryCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    entry = DiaryEntry(
        user_id=user_id,
        encrypted_content=encrypt_text(payload.content),
        title=payload.title,
        mood=payload.mood,
        tags=payload.tags,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry, attribute_names=["ai_feedbacks"])
    return _entry_to_response(entry)


# ── List ─────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[DiaryEntryResponse],
    summary="List all diary entries for the current user",
)
async def list_entries(
    skip: int = 0,
    limit: int = 20,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.user_id == user_id)
        .options(selectinload(DiaryEntry.ai_feedbacks))
        .order_by(DiaryEntry.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    entries = result.scalars().all()
    return [_entry_to_response(e) for e in entries]


# ── Get One ──────────────────────────────────────────────────────────────────

@router.get(
    "/{entry_id}",
    response_model=DiaryEntryResponse,
    summary="Get a single diary entry",
)
async def get_entry(
    entry_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.id == entry_id, DiaryEntry.user_id == user_id)
        .options(selectinload(DiaryEntry.ai_feedbacks))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return _entry_to_response(entry)


# ── Update ───────────────────────────────────────────────────────────────────

@router.patch(
    "/{entry_id}",
    response_model=DiaryEntryResponse,
    summary="Update a diary entry",
)
async def update_entry(
    entry_id: int,
    payload: DiaryEntryUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.id == entry_id, DiaryEntry.user_id == user_id)
        .options(selectinload(DiaryEntry.ai_feedbacks))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    if payload.content is not None:
        entry.encrypted_content = encrypt_text(payload.content)
    if payload.title is not None:
        entry.title = payload.title
    if payload.mood is not None:
        entry.mood = payload.mood
    if payload.tags is not None:
        entry.tags = payload.tags

    await db.flush()
    await db.refresh(entry, attribute_names=["ai_feedbacks"])
    return _entry_to_response(entry)


# ── Delete ───────────────────────────────────────────────────────────────────

@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a diary entry",
)
async def delete_entry(
    entry_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DiaryEntry).where(DiaryEntry.id == entry_id, DiaryEntry.user_id == user_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    await db.delete(entry)
