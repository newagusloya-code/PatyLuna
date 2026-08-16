"""
Integration tests for Pomodoro and Sleep endpoints.
Enforces failure locality and strict response contracts.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import helper_get_auth_headers

pytestmark = pytest.mark.asyncio


class TestPomodoroIntegration:
    async def test_pomodoro_lifecycle(self, client: AsyncClient):
        # 1. Prerequisite Auth with strict failure locality
        headers = await helper_get_auth_headers(client, "pomo_user@test.com", "pomo_user")

        # 2. Start Pomodoro session
        start_resp = await client.post(
            "/api/v1/pomodoro/",
            headers=headers,
            json={
                "task_description": "Write system unit tests",
                "category": "deep_work",
                "duration_minutes": 25,
                "background_sound": "rain",
            },
        )
        assert start_resp.status_code == 201, f"Failed starting pomodoro: {start_resp.text}"
        data = start_resp.json()
        assert "id" in data
        session_id = data["id"]
        assert data["task_description"] == "Write system unit tests"
        assert data["category"] == "deep_work"
        assert data["duration_minutes"] == 25
        assert data["background_sound"] == "rain"
        assert data["completed"] is False
        assert data["started_at"] is not None
        assert data["ended_at"] is None

        # 3. Complete session
        complete_resp = await client.patch(
            f"/api/v1/pomodoro/{session_id}/complete",
            headers=headers,
        )
        assert complete_resp.status_code == 200, f"Failed completing pomodoro: {complete_resp.text}"
        comp_data = complete_resp.json()
        assert comp_data["id"] == session_id
        assert comp_data["completed"] is True
        assert comp_data["ended_at"] is not None

        # 4. Get specific session
        get_resp = await client.get(f"/api/v1/pomodoro/{session_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == session_id
        assert get_resp.json()["completed"] is True

        # 5. List sessions
        list_resp = await client.get("/api/v1/pomodoro/", headers=headers)
        assert list_resp.status_code == 200
        sessions = list_resp.json()
        assert isinstance(sessions, list)
        assert len(sessions) >= 1
        assert any(s["id"] == session_id for s in sessions)

        # 6. Delete session
        del_resp = await client.delete(f"/api/v1/pomodoro/{session_id}", headers=headers)
        assert del_resp.status_code == 204

        # 7. Verify deletion
        get_after_del = await client.get(f"/api/v1/pomodoro/{session_id}", headers=headers)
        assert get_after_del.status_code == 404


class TestSleepIntegration:
    async def test_sleep_lifecycle(self, client: AsyncClient):
        # 1. Prerequisite Auth with strict failure locality
        headers = await helper_get_auth_headers(client, "sleep_user@test.com", "sleep_user")

        # 2. Start sleep session
        start_resp = await client.post(
            "/api/v1/sleep/",
            headers=headers,
            json={
                "sound_preset": "delta_waves_432hz",
                "meditation_type": "body_scan",
            },
        )
        assert start_resp.status_code == 201, f"Failed starting sleep session: {start_resp.text}"
        data = start_resp.json()
        assert "id" in data
        session_id = data["id"]
        assert data["sound_preset"] == "delta_waves_432hz"
        assert data["meditation_type"] == "body_scan"
        assert data["started_at"] is not None
        assert data["ended_at"] is None

        # 3. End sleep with rating and notes
        end_resp = await client.patch(
            f"/api/v1/sleep/{session_id}/end",
            headers=headers,
            json={"quality_rating": 9, "notes": "Fell asleep in 10 minutes."},
        )
        assert end_resp.status_code == 200, f"Failed ending sleep session: {end_resp.text}"
        end_data = end_resp.json()
        assert end_data["id"] == session_id
        assert end_data["quality_rating"] == 9
        assert end_data["notes"] == "Fell asleep in 10 minutes."
        assert end_data["ended_at"] is not None

        # 4. Get specific sleep session
        get_resp = await client.get(f"/api/v1/sleep/{session_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == session_id
        assert get_resp.json()["quality_rating"] == 9

        # 5. List sleep sessions
        list_resp = await client.get("/api/v1/sleep/", headers=headers)
        assert list_resp.status_code == 200
        sessions = list_resp.json()
        assert isinstance(sessions, list)
        assert any(s["id"] == session_id for s in sessions)
