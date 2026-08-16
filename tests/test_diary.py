"""
Tests for Diary CRUD endpoints and data isolation.
Enforces failure locality and strict response contracts.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DiaryEntry
from tests.conftest import helper_get_auth_headers

pytestmark = pytest.mark.asyncio


class TestDiary:
    async def test_create_and_read_diary_entry(self, client: AsyncClient, db_session: AsyncSession):
        headers = await helper_get_auth_headers(client, "alice@test.com", "alice_test")
        secret_content = "Super secret diary reflection for today."

        # Create entry
        create_resp = await client.post(
            "/api/v1/diary/",
            headers=headers,
            json={
                "title": "Day 1 Thoughts",
                "content": secret_content,
                "mood": "calm",
                "tags": "reflection,focus",
            },
        )
        assert create_resp.status_code == 201, f"Failed creating diary entry: {create_resp.text}"
        data = create_resp.json()
        assert "id" in data
        entry_id = data["id"]
        assert data["content"] == secret_content
        assert data["title"] == "Day 1 Thoughts"
        assert data["mood"] == "calm"

        # Verify database record actually stores ciphertext (NOT plaintext)
        db_res = await db_session.execute(select(DiaryEntry).where(DiaryEntry.id == entry_id))
        raw_entry = db_res.scalar_one()
        assert raw_entry.encrypted_content != secret_content.encode("utf-8")
        assert secret_content.encode("utf-8") not in raw_entry.encrypted_content

        # Read back via GET /diary/{id}
        get_resp = await client.get(f"/api/v1/diary/{entry_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["content"] == secret_content

    async def test_diary_cross_user_isolation(self, client: AsyncClient):
        alice_headers = await helper_get_auth_headers(client, "alice2@test.com", "alice2_test")
        bob_headers = await helper_get_auth_headers(client, "bob2@test.com", "bob2_test")

        # Alice creates an entry
        create_resp = await client.post(
            "/api/v1/diary/",
            headers=alice_headers,
            json={"title": "Alice's Secret", "content": "Bob must not see this."},
        )
        assert create_resp.status_code == 201
        entry_id = create_resp.json()["id"]

        # Bob attempts to read Alice's entry
        bob_resp = await client.get(f"/api/v1/diary/{entry_id}", headers=bob_headers)
        assert bob_resp.status_code == 404

        # Bob attempts to update Alice's entry
        bob_update = await client.patch(
            f"/api/v1/diary/{entry_id}",
            headers=bob_headers,
            json={"title": "Hacked Title"},
        )
        assert bob_update.status_code == 404

        # Bob attempts to delete Alice's entry
        bob_del = await client.delete(f"/api/v1/diary/{entry_id}", headers=bob_headers)
        assert bob_del.status_code == 404

    async def test_update_and_delete_entry(self, client: AsyncClient):
        headers = await helper_get_auth_headers(client, "carol@test.com", "carol_test")

        # Create
        create_resp = await client.post(
            "/api/v1/diary/",
            headers=headers,
            json={"title": "Initial", "content": "Initial text", "mood": "neutral"},
        )
        assert create_resp.status_code == 201
        entry_id = create_resp.json()["id"]

        # Update
        patch_resp = await client.patch(
            f"/api/v1/diary/{entry_id}",
            headers=headers,
            json={"content": "Updated secret text", "mood": "inspired"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["content"] == "Updated secret text"
        assert patch_resp.json()["mood"] == "inspired"

        # Delete
        del_resp = await client.delete(f"/api/v1/diary/{entry_id}", headers=headers)
        assert del_resp.status_code == 204

        # Verify gone
        get_resp = await client.get(f"/api/v1/diary/{entry_id}", headers=headers)
        assert get_resp.status_code == 404
