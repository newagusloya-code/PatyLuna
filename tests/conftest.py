"""
Shared pytest fixtures and strict contract verification helpers.

Uses an isolated SQLite database so tests run cleanly and deterministically.
"""

from __future__ import annotations

import os
from typing import Any, Dict
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Must be set BEFORE importing app modules so config doesn't crash
os.environ["ENCRYPTION_KEY"] = "54302cb818b5555cbf4050d58614804e9fc5d8d77963c65c81ac5f7a4385b4cc"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production-use-abcdef123456"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["AI_PROVIDER"] = "mock"
os.environ["REDIS_URL"] = "memory://"

import app.db.database as db_module
from app.core.limiter import limiter
from app.db.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///./test.db?timeout=30"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestSessionFactory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Patch the app's default session factory to use TestSessionFactory during tests
db_module.async_session_factory = TestSessionFactory
db_module.engine = test_engine


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Create all tables before each test and drop them after, resetting rate limits."""
    try:
        limiter.reset()
    except Exception:
        pass
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    try:
        limiter.reset()
    except Exception:
        pass


@pytest_asyncio.fixture
async def db_session():
    """Yield a standalone session for tests that inspect DB state directly."""
    async with TestSessionFactory() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    async def override_get_db():
        async with TestSessionFactory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testclient"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def valid_user_payload():
    return {
        "email": "cadet@sleepwell.io",
        "username": "cadet_one",
        "password": "SecurePass1!",
    }


# ────────────────────────────────────────────────────────────────────────────
# Strict Failure Locality Helpers
# ────────────────────────────────────────────────────────────────────────────

async def helper_register_user(
    client: AsyncClient,
    email: str,
    username: str,
    password: str = "SecurePass1!",
) -> dict[str, Any]:
    """
    Registers a new user and validates the contract immediately.
    Never allows registration failure to propagate downstream as an unhandled KeyError.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert resp.status_code == 201, f"Registration prerequisite failed ({resp.status_code}): {resp.text}"
    data = resp.json()
    assert "id" in data, f"Malformed register response, missing 'id': {data}"
    assert data["email"] == email, f"Email mismatch in register response: {data}"
    assert data["username"] == username, f"Username mismatch in register response: {data}"
    assert "hashed_password" not in data, "Security breach: hashed_password leaked in register response"
    return data


async def helper_login_user(
    client: AsyncClient,
    email: str,
    password: str = "SecurePass1!",
) -> dict[str, Any]:
    """
    Logs in a user and validates the token response contract immediately.
    """
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login prerequisite failed ({resp.status_code}): {resp.text}"
    data = resp.json()
    assert "access_token" in data, f"Malformed login response, missing 'access_token': {data}"
    assert "refresh_token" in data, f"Malformed login response, missing 'refresh_token': {data}"
    assert data.get("token_type") == "bearer", f"Expected token_type 'bearer', got: {data.get('token_type')}"
    return data


async def helper_get_auth_headers(
    client: AsyncClient,
    email: str,
    username: str,
    password: str = "SecurePass1!",
) -> dict[str, str]:
    """
    Combines registration and login with strict assertions at each phase.
    """
    await helper_register_user(client, email, username, password)
    tokens = await helper_login_user(client, email, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def helper_create_diary_entry(
    client: AsyncClient,
    headers: dict[str, str],
    content: str,
    title: str = "Test Entry",
    mood: str | None = "calm",
    tags: str | None = "test",
) -> dict[str, Any]:
    """
    Creates a diary entry and verifies the creation response contract immediately.
    """
    resp = await client.post(
        "/api/v1/diary/",
        headers=headers,
        json={"title": title, "content": content, "mood": mood, "tags": tags},
    )
    assert resp.status_code == 201, f"Diary creation prerequisite failed ({resp.status_code}): {resp.text}"
    data = resp.json()
    assert "id" in data, f"Malformed diary response, missing 'id': {data}"
    assert data["content"] == content, "Decrypted content mismatch on diary creation"
    return data
