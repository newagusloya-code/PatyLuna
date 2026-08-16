"""
SQLAlchemy ORM models.

Every table that touches personal data stores it encrypted at rest.
Timestamps are always UTC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ────────────────────────────────────────────────────────────────────────────
# User
# ────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    diary_entries: Mapped[list["DiaryEntry"]] = relationship(back_populates="author", cascade="all, delete-orphan")
    pomodoro_sessions: Mapped[list["PomodoroSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sleep_sessions: Mapped[list["SleepSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ────────────────────────────────────────────────────────────────────────────
# Diary Entry (encrypted at rest)
# ────────────────────────────────────────────────────────────────────────────

class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Content is AES-256-GCM encrypted – stored as raw bytes
    encrypted_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # Optional plaintext metadata (not sensitive)
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # e.g. "calm", "anxious", "happy"
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # comma-separated tags

    is_public: Mapped[bool] = mapped_column(Boolean, default=False)  # personal diary = private by default

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    author: Mapped["User"] = relationship(back_populates="diary_entries")
    messages: Mapped[list["DiaryMessage"]] = relationship(back_populates="diary_entry", cascade="all, delete-orphan", order_by="DiaryMessage.created_at")

    __table_args__ = (
        Index("ix_diary_user_created", "user_id", "created_at"),
    )


# ────────────────────────────────────────────────────────────────────────────
# Diary Message (Chat thread)
# ────────────────────────────────────────────────────────────────────────────

class DiaryMessage(Base):
    __tablename__ = "diary_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    diary_entry_id: Mapped[int] = mapped_column(ForeignKey("diary_entries.id", ondelete="CASCADE"), nullable=False)

    role: Mapped[str] = mapped_column(String(16), nullable=False) # "user" or "agent"
    agent_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # e.g. "tough_coach", null if user

    # Content is AES-256-GCM encrypted
    encrypted_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    diary_entry: Mapped["DiaryEntry"] = relationship(back_populates="messages")


# ────────────────────────────────────────────────────────────────────────────
# Pomodoro Session
# ────────────────────────────────────────────────────────────────────────────

class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    task_description: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # e.g. "work", "study", "creative"

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=25)

    # What background sound / music was playing
    background_sound: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    completed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="pomodoro_sessions")

    __table_args__ = (
        Index("ix_pomodoro_user_started", "user_id", "started_at"),
    )


# ────────────────────────────────────────────────────────────────────────────
# Sleep Session (for tracking sleep quality + sounds used)
# ────────────────────────────────────────────────────────────────────────────

class SleepSession(Base):
    __tablename__ = "sleep_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # What sounds / meditation technique was used
    sound_preset: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    meditation_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Self-reported quality (1-10)
    quality_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sleep_sessions")

    __table_args__ = (
        Index("ix_sleep_user_started", "user_id", "started_at"),
    )
