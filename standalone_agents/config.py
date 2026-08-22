"""
Configuration settings for Standalone Agents Package.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    AI_PROVIDER: str = "gemini"  # gemini | openai | anthropic | mock
    AI_API_KEY: str = ""
    AI_MODEL: str = "gemini-3.6-flash"
    LIVE_AI_MODEL: str = "gemini-3.1-flash-live-preview"
    ENCRYPTION_KEY_HEX: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = AgentSettings()
