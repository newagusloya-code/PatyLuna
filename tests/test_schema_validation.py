"""
Schema Validation, Boundary Conditions, and Malformed Input Tests.

Verifies that FastAPI / Pydantic validation rejects out-of-spec payloads
with 422 Unprocessable Entity and standard error schema.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import helper_create_diary_entry, helper_get_auth_headers

pytestmark = pytest.mark.asyncio


class TestAuthSchemaValidation:
    async def test_register_missing_required_fields(self, client: AsyncClient):
        # Empty payload
        resp = await client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422
        errors = resp.json()["detail"]
        missing_fields = {e["loc"][-1] for e in errors}
        assert {"email", "username", "password"}.issubset(missing_fields)

    async def test_register_invalid_username_characters(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "u@test.com", "username": "user!name#bad", "password": "SecurePassword1!"},
        )
        assert resp.status_code == 422
        assert "letters, numbers, and underscores" in resp.text

    async def test_register_username_length_boundaries(self, client: AsyncClient):
        # Too short (< 3 chars)
        short_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "short@test.com", "username": "ab", "password": "SecurePassword1!"},
        )
        assert short_resp.status_code == 422

        # Too long (> 64 chars)
        long_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "long@test.com", "username": "a" * 65, "password": "SecurePassword1!"},
        )
        assert long_resp.status_code == 422

    async def test_register_password_length_boundaries(self, client: AsyncClient):
        # Too short (< 8 chars)
        short_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "p_short@test.com", "username": "pshort", "password": "Ab1!"},
        )
        assert short_resp.status_code == 422

        # Too long (> 128 chars)
        long_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "p_long@test.com", "username": "plong", "password": "A1!" + "a" * 130},
        )
        assert long_resp.status_code == 422


class TestDiarySchemaValidation:
    async def test_diary_create_empty_or_missing_content(self, client: AsyncClient):
        headers = await helper_get_auth_headers(client, "diary_val@test.com", "diary_val")

        # Missing content
        resp1 = await client.post("/api/v1/diary/", headers=headers, json={"title": "No content"})
        assert resp1.status_code == 422

        # Empty string content (min_length=1)
        resp2 = await client.post("/api/v1/diary/", headers=headers, json={"content": ""})
        assert resp2.status_code == 422

    async def test_diary_oversized_fields(self, client: AsyncClient):
        headers = await helper_get_auth_headers(client, "diary_val2@test.com", "diary_val2")

        # Title > 256 chars
        resp = await client.post(
            "/api/v1/diary/",
            headers=headers,
            json={"title": "X" * 257, "content": "Valid content"},
        )
        assert resp.status_code == 422


class TestAISchemaValidation:
    async def test_ai_invalid_agent_type_enum(self, client: AsyncClient):
        headers = await helper_get_auth_headers(client, "ai_val@test.com", "ai_val")
        diary = await helper_create_diary_entry(
            client, headers=headers, title="Entry", content="Valid content for AI"
        )
        entry_id = diary["id"]

        # Invalid agent_type string
        resp = await client.post(
            f"/api/v1/ai/diary/{entry_id}/chat",
            headers=headers,
            json={"content": "test message", "selected_agents": ["evil_hacker_agent"]},
        )
        assert resp.status_code == 422
        assert "agent_type" in resp.text

    async def test_ai_malformed_entry_id_path_param(self, client: AsyncClient):
        headers = await helper_get_auth_headers(client, "ai_val2@test.com", "ai_val2")

        # Non-integer path param
        resp = await client.post(
            "/api/v1/ai/diary/not-an-integer-id/chat",
            headers=headers,
            json={"content": "test message", "selected_agents": ["tough_coach"]},
        )
        assert resp.status_code == 422


class TestPomodoroAndSleepSchemaValidation:
    async def test_pomodoro_duration_boundaries(self, client: AsyncClient):
        headers = await helper_get_auth_headers(client, "pomo_val@test.com", "pomo_val")

        # Duration < 1
        resp_low = await client.post(
            "/api/v1/pomodoro/",
            headers=headers,
            json={"task_description": "Work", "duration_minutes": 0},
        )
        assert resp_low.status_code == 422

        # Duration > 240
        resp_high = await client.post(
            "/api/v1/pomodoro/",
            headers=headers,
            json={"task_description": "Work", "duration_minutes": 241},
        )
        assert resp_high.status_code == 422

        # Duration wrong type
        resp_type = await client.post(
            "/api/v1/pomodoro/",
            headers=headers,
            json={"task_description": "Work", "duration_minutes": "twenty-five"},
        )
        assert resp_type.status_code == 422

    async def test_sleep_rating_boundaries(self, client: AsyncClient):
        headers = await helper_get_auth_headers(client, "sleep_val@test.com", "sleep_val")

        # Start session
        start_resp = await client.post("/api/v1/sleep/", headers=headers, json={})
        assert start_resp.status_code == 201
        session_id = start_resp.json()["id"]

        # Quality rating < 1
        resp_low = await client.patch(
            f"/api/v1/sleep/{session_id}/end",
            headers=headers,
            json={"quality_rating": 0},
        )
        assert resp_low.status_code == 422

        # Quality rating > 10
        resp_high = await client.patch(
            f"/api/v1/sleep/{session_id}/end",
            headers=headers,
            json={"quality_rating": 11},
        )
        assert resp_high.status_code == 422
