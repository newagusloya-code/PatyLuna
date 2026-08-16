"""
Application configuration.

All secrets and environment-specific settings are loaded from environment
variables (or a .env file) via pydantic-settings.  Nothing is hardcoded.
"""

from __future__ import annotations

import secrets
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "SleepWell API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sleepwell"
    DATABASE_ECHO: bool = False  # SQLAlchemy query logging

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif v.startswith("sqlite://") and not v.startswith("sqlite+aiosqlite://"):
                return v.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return v

    # ── JWT / Auth ───────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = secrets.token_urlsafe(64)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Encryption (AES-256-GCM for diary entries) ───────────────────────
    # Generate with: python -c "import os; print(os.urandom(32).hex())"
    ENCRYPTION_KEY: str = ""

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── CORS & Hosts ─────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_ORIGIN_REGEX: Optional[str] = r"^https:\/\/.*\.vercel\.app$"
    ALLOWED_HOSTS: List[str] = ["*"]

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    # ── AI Agents ────────────────────────────────────────────────────────
    AI_PROVIDER: str = "gemini"  # gemini | openai | anthropic | local
    AI_API_KEY: str = ""
    AI_MODEL: str = "gemini-2.5-flash"


settings = Settings()

