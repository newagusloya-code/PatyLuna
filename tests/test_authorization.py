"""
Multi-User Object Ownership and Cross-Tenant Isolation Tests.

Proves that valid authenticated users CANNOT view, modify, delete,
or trigger AI operations on resources belonging to other users.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import helper_create_diary_entry, helper_get_auth_headers

pytestmark = pytest.mark.asyncio


class TestCrossUserDiaryAndAIIsolation:
    async def test_user_cannot_request_ai_feedback_for_another_users_diary(self, client: AsyncClient):
        """
        Security requirement: User B must not be able to trigger AI analysis
        on User A's private diary entry.
        """
        user_a_headers = await helper_get_auth_headers(client, "usera@test.com", "user_a")
        user_b_headers = await helper_get_auth_headers(client, "userb@test.com", "user_b")

        # User A creates a confidential diary entry
        entry = await helper_create_diary_entry(
            client,
            headers=user_a_headers,
            title="User A Diary",
            content="Confidential reflection from User A.",
        )
        user_a_entry_id = entry["id"]

        # User B attempts to request AI feedback on User A's diary entry
        attack_resp = await client.post(
            f"/api/v1/ai/diary/{user_a_entry_id}/feedback",
            headers=user_b_headers,
            json={"agent_type": "empathetic_listener"},
        )
        assert attack_resp.status_code == 404, (
            f"Expected 404 Not Found to prevent data leakage, got: {attack_resp.status_code}"
        )
        assert "not found" in attack_resp.json()["detail"].lower()

    async def test_user_cannot_read_another_users_ai_feedback(self, client: AsyncClient):
        """
        User B must not be able to read AI feedback generated for User A's diary entry.
        """
        user_a_headers = await helper_get_auth_headers(client, "usera2@test.com", "user_a2")
        user_b_headers = await helper_get_auth_headers(client, "userb2@test.com", "user_b2")

        # User A creates entry & requests feedback
        entry = await helper_create_diary_entry(
            client,
            headers=user_a_headers,
            title="User A Private",
            content="User A feeling tired.",
        )
        entry_id = entry["id"]

        ai_req = await client.post(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=user_a_headers,
            json={"agent_type": "sleep_analyst"},
        )
        assert ai_req.status_code == 202

        # User B attempts to list AI feedbacks for User A's entry
        attack_resp = await client.get(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=user_b_headers,
        )
        assert attack_resp.status_code == 404, f"Expected 404, got: {attack_resp.status_code}"

    async def test_diary_cross_user_crud_isolation(self, client: AsyncClient):
        user_a_headers = await helper_get_auth_headers(client, "usera3@test.com", "user_a3")
        user_b_headers = await helper_get_auth_headers(client, "userb3@test.com", "user_b3")

        entry = await helper_create_diary_entry(
            client, headers=user_a_headers, title="Owned by A", content="A secret content"
        )
        entry_id = entry["id"]

        # GET by B -> 404
        get_b = await client.get(f"/api/v1/diary/{entry_id}", headers=user_b_headers)
        assert get_b.status_code == 404

        # PATCH by B -> 404
        patch_b = await client.patch(
            f"/api/v1/diary/{entry_id}",
            headers=user_b_headers,
            json={"title": "Hacked Title"},
        )
        assert patch_b.status_code == 404

        # DELETE by B -> 404
        del_b = await client.delete(f"/api/v1/diary/{entry_id}", headers=user_b_headers)
        assert del_b.status_code == 404

        # Verify A still owns it
        get_a = await client.get(f"/api/v1/diary/{entry_id}", headers=user_a_headers)
        assert get_a.status_code == 200
        assert get_a.json()["title"] == "Owned by A"


class TestCrossUserPomodoroAndSleepIsolation:
    async def test_pomodoro_cross_user_isolation(self, client: AsyncClient):
        user_a_headers = await helper_get_auth_headers(client, "usera_pomo@test.com", "usera_pomo")
        user_b_headers = await helper_get_auth_headers(client, "userb_pomo@test.com", "userb_pomo")

        # User A starts session
        pomo_resp = await client.post(
            "/api/v1/pomodoro/",
            headers=user_a_headers,
            json={"task_description": "User A confidential task", "duration_minutes": 25},
        )
        assert pomo_resp.status_code == 201
        session_id = pomo_resp.json()["id"]

        # User B attempts to get User A's session
        get_b = await client.get(f"/api/v1/pomodoro/{session_id}", headers=user_b_headers)
        assert get_b.status_code == 404

        # User B attempts to complete User A's session
        comp_b = await client.patch(
            f"/api/v1/pomodoro/{session_id}/complete",
            headers=user_b_headers,
        )
        assert comp_b.status_code == 404

        # User B attempts to delete User A's session
        del_b = await client.delete(f"/api/v1/pomodoro/{session_id}", headers=user_b_headers)
        assert del_b.status_code == 404

    async def test_sleep_cross_user_isolation(self, client: AsyncClient):
        user_a_headers = await helper_get_auth_headers(client, "usera_sleep@test.com", "usera_sleep")
        user_b_headers = await helper_get_auth_headers(client, "userb_sleep@test.com", "userb_sleep")

        # User A starts sleep session
        sleep_resp = await client.post(
            "/api/v1/sleep/",
            headers=user_a_headers,
            json={"sound_preset": "rain"},
        )
        assert sleep_resp.status_code == 201
        session_id = sleep_resp.json()["id"]

        # User B attempts to get User A's sleep session
        get_b = await client.get(f"/api/v1/sleep/{session_id}", headers=user_b_headers)
        assert get_b.status_code == 404

        # User B attempts to end/rate User A's sleep session
        end_b = await client.patch(
            f"/api/v1/sleep/{session_id}/end",
            headers=user_b_headers,
            json={"quality_rating": 1, "notes": "Hacked rating"},
        )
        assert end_b.status_code == 404
