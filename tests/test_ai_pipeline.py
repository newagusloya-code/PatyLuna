"""
AI Pipeline End-to-End and Transmission-Point Security Boundary Tests.

Verifies:
  1. Complete Async Lifecycle:
     request accepted -> background task -> provider -> encryption -> DB persistence -> retrieval.
  2. Transmission-Point PII Security Boundary:
     inspects exact payload sent to external AI providers (Gemini, OpenAI, Anthropic).
  3. Provider Error Handling & Rollback.
  4. Duplicate Feedback Prevention (409 Conflict).
"""

from __future__ import annotations

from typing import Any
import httpx
import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import AIFeedback
from tests.conftest import (
    helper_create_diary_entry,
    helper_get_auth_headers,
)

pytestmark = pytest.mark.asyncio


class TestAILifecyclePipeline:
    """
    Validates the end-to-end asynchronous AI feedback pipeline.
    """

    async def test_full_pipeline_lifecycle_mock_provider(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Tests the entire lifecycle using the configured mock provider:
        1. Register + Login
        2. Create encrypted diary entry
        3. POST /ai/diary/{id}/feedback -> 202 Accepted
        4. Verify background task execution and DB persistence
        5. GET /ai/diary/{id}/feedback -> returns decrypted feedback
        6. GET /diary/{id} -> returns diary with nested decrypted feedback
        """
        headers = await helper_get_auth_headers(client, "lifecycle_user@test.com", "lifecycle_user")
        diary = await helper_create_diary_entry(
            client,
            headers=headers,
            title="Async Lifecycle Test",
            content="Today I experienced deep focus and accomplished my goals.",
            mood="focused",
            tags="productivity,flow",
        )
        entry_id = diary["id"]

        # 1. Trigger AI feedback
        resp = await client.post(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=headers,
            json={"agent_type": "productivity_mentor"},
        )
        assert resp.status_code == 202, f"Failed initiating feedback: {resp.text}"
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["entry_id"] == entry_id
        assert data["agent_type"] == "productivity_mentor"

        # 2. Verify direct database persistence and encryption
        result = await db_session.execute(
            select(AIFeedback).where(
                AIFeedback.diary_entry_id == entry_id,
                AIFeedback.agent_type == "productivity_mentor",
            )
        )
        fb_record = result.scalar_one_or_none()
        assert fb_record is not None, "AI feedback was NOT persisted in the database by background task!"
        assert isinstance(fb_record.encrypted_feedback, bytes)
        assert b"[Mock AI Response]" not in fb_record.encrypted_feedback, "Feedback was NOT encrypted in database!"

        # 3. Retrieve via GET /ai/diary/{id}/feedback
        fb_resp = await client.get(f"/api/v1/ai/diary/{entry_id}/feedback", headers=headers)
        assert fb_resp.status_code == 200
        fb_list = fb_resp.json()
        assert len(fb_list) == 1
        assert fb_list[0]["agent_type"] == "productivity_mentor"
        assert "[Mock AI Response]" in fb_list[0]["feedback"]

        # 4. Retrieve via GET /diary/{id}
        diary_resp = await client.get(f"/api/v1/diary/{entry_id}", headers=headers)
        assert diary_resp.status_code == 200
        diary_data = diary_resp.json()
        assert len(diary_data["ai_feedbacks"]) == 1
        assert diary_data["ai_feedbacks"][0]["agent_type"] == "productivity_mentor"
        assert "[Mock AI Response]" in diary_data["ai_feedbacks"][0]["feedback"]

    async def test_duplicate_agent_feedback_conflict(self, client: AsyncClient):
        """
        Asserts that requesting feedback from the same agent on the same entry returns 409 Conflict.
        """
        headers = await helper_get_auth_headers(client, "conflict_user@test.com", "conflict_user")
        diary = await helper_create_diary_entry(
            client,
            headers=headers,
            title="Conflict Check",
            content="Testing duplicate request prevention.",
        )
        entry_id = diary["id"]

        # First request -> 202 Accepted
        first = await client.post(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=headers,
            json={"agent_type": "tough_coach"},
        )
        assert first.status_code == 202

        # Second request from same agent -> 409 Conflict
        second = await client.post(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=headers,
            json={"agent_type": "tough_coach"},
        )
        assert second.status_code == 409, f"Expected 409 Conflict, got {second.status_code}: {second.text}"
        assert "already exists" in second.json()["detail"]


class TestPIITransmissionSecurityBoundary:
    """
    Proves that the AI pipeline strictly scrubs PII BEFORE transmitting payloads
    over the wire to external AI providers (Gemini, OpenAI, Anthropic).
    """

    async def test_gemini_transmission_scrubbed_payload(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        """
        Intercepts the outbound HTTP request to Gemini API and asserts that:
        - raw PII (email, phone, name, ssn, address) is ABSENT
        - replacement markers are present
        - non-PII content is preserved
        """
        captured_requests: list[dict[str, Any]] = []
        original_post = httpx.AsyncClient.post

        async def fake_gemini_post(self_client, url, *args, **kwargs):
            url_str = str(url)
            if "googleapis.com" in url_str:
                captured_requests.append({
                    "url": url_str,
                    "json": kwargs.get("json"),
                    "params": kwargs.get("params"),
                    "headers": kwargs.get("headers"),
                })
                mock_response = {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": "Gemini analyzed your scrubbed entry successfully."
                                    }
                                ]
                            }
                        }
                    ]
                }
                return Response(200, json=mock_response, request=httpx.Request("POST", url))
            return await original_post(self_client, url, *args, **kwargs)

        monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
        monkeypatch.setattr(settings, "AI_API_KEY", "fake-gemini-key-12345")
        monkeypatch.setattr(httpx.AsyncClient, "post", fake_gemini_post)

        headers = await helper_get_auth_headers(client, "gemini_pii@test.com", "gemini_pii")
        sensitive_entry_text = (
            "Dear diary, I met with Dr. John Watson at 123 Baker Street, CA 94105. "
            "His confidential email is watson.sherlock+cases@sub.investigations.org.uk and "
            "his mobile number is +1 (415) 555-2671. My SSN is 000-12-3456. "
            "I felt calm and focused during our meditation session."
        )
        diary = await helper_create_diary_entry(
            client,
            headers=headers,
            title="Sensitive Diary Entry",
            content=sensitive_entry_text,
        )
        entry_id = diary["id"]

        # Request AI feedback
        resp = await client.post(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=headers,
            json={"agent_type": "mindfulness_guide"},
        )
        assert resp.status_code == 202

        # Verify captured outbound wire payload
        assert len(captured_requests) == 1, "Expected exactly 1 external Gemini API request"
        req = captured_requests[0]
        outbound_payload = req["json"]
        transmitted_text = outbound_payload["contents"][0]["parts"][0]["text"]

        # Security boundary assertions: RAW PII MUST NOT LEAK
        assert "watson.sherlock+cases@sub.investigations.org.uk" not in transmitted_text
        assert "415) 555-2671" not in transmitted_text
        assert "4155552671" not in transmitted_text
        assert "Dr. John Watson" not in transmitted_text
        assert "000-12-3456" not in transmitted_text
        assert "123 Baker Street, CA 94105" not in transmitted_text

        # Replacement markers MUST be present
        assert "[EMAIL]" in transmitted_text
        assert "[PHONE]" in transmitted_text
        assert "[NAME]" in transmitted_text
        assert "[SSN]" in transmitted_text
        assert "[ADDRESS]" in transmitted_text

        # Non-PII content MUST be preserved
        assert "Dear diary" in transmitted_text
        assert "I felt calm and focused during our meditation session." in transmitted_text

        # Verify feedback was stored in database
        fb_resp = await client.get(f"/api/v1/ai/diary/{entry_id}/feedback", headers=headers)
        assert fb_resp.status_code == 200
        feedbacks = fb_resp.json()
        assert len(feedbacks) == 1
        assert "Gemini analyzed your scrubbed entry successfully." in feedbacks[0]["feedback"]

    async def test_openai_transmission_scrubbed_payload(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        """
        Intercepts outbound HTTP request to OpenAI API and asserts PII scrubbing at the wire.
        """
        captured_requests: list[dict[str, Any]] = []
        original_post = httpx.AsyncClient.post

        async def fake_openai_post(self_client, url, *args, **kwargs):
            url_str = str(url)
            if "api.openai.com" in url_str:
                captured_requests.append({
                    "url": url_str,
                    "json": kwargs.get("json"),
                    "headers": kwargs.get("headers"),
                })
                mock_response = {
                    "choices": [
                        {
                            "message": {
                                "content": "OpenAI feedback based on scrubbed data."
                            }
                        }
                    ]
                }
                return Response(200, json=mock_response, request=httpx.Request("POST", url))
            return await original_post(self_client, url, *args, **kwargs)

        monkeypatch.setattr(settings, "AI_PROVIDER", "openai")
        monkeypatch.setattr(settings, "AI_API_KEY", "sk-fake-openai-key")
        monkeypatch.setattr(httpx.AsyncClient, "post", fake_openai_post)

        headers = await helper_get_auth_headers(client, "openai_pii@test.com", "openai_pii")
        entry_text = "Call Alice Smith at 415.555.2671 or email ALICE_DEV@CORP.COMPANY.COM regarding sprint goals."
        diary = await helper_create_diary_entry(
            client, headers=headers, title="Sprint Goals", content=entry_text
        )
        entry_id = diary["id"]

        resp = await client.post(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=headers,
            json={"agent_type": "tough_coach"},
        )
        assert resp.status_code == 202

        assert len(captured_requests) == 1
        transmitted_user_message = captured_requests[0]["json"]["messages"][1]["content"]

        assert "Alice Smith" not in transmitted_user_message
        assert "415.555.2671" not in transmitted_user_message
        assert "ALICE_DEV@CORP.COMPANY.COM" not in transmitted_user_message

        assert "[NAME]" in transmitted_user_message
        assert "[PHONE]" in transmitted_user_message
        assert "[EMAIL]" in transmitted_user_message
        assert "regarding sprint goals." in transmitted_user_message

    async def test_anthropic_transmission_scrubbed_payload(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        """
        Intercepts outbound HTTP request to Anthropic API and asserts PII scrubbing at the wire.
        """
        captured_requests: list[dict[str, Any]] = []
        original_post = httpx.AsyncClient.post

        async def fake_anthropic_post(self_client, url, *args, **kwargs):
            url_str = str(url)
            if "api.anthropic.com" in url_str:
                captured_requests.append({
                    "url": url_str,
                    "json": kwargs.get("json"),
                    "headers": kwargs.get("headers"),
                })
                mock_response = {
                    "content": [{"text": "Anthropic sleep analysis on scrubbed text."}]
                }
                return Response(200, json=mock_response, request=httpx.Request("POST", url))
            return await original_post(self_client, url, *args, **kwargs)

        monkeypatch.setattr(settings, "AI_PROVIDER", "anthropic")
        monkeypatch.setattr(settings, "AI_API_KEY", "ant-fake-key")
        monkeypatch.setattr(httpx.AsyncClient, "post", fake_anthropic_post)

        headers = await helper_get_auth_headers(client, "anthropic_pii@test.com", "anthropic_pii")
        entry_text = "I talked with Jane Doe today. Her number is +44 20 7946 0958. I slept poorly."
        diary = await helper_create_diary_entry(
            client, headers=headers, title="Sleep Note", content=entry_text
        )
        entry_id = diary["id"]

        resp = await client.post(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=headers,
            json={"agent_type": "sleep_analyst"},
        )
        assert resp.status_code == 202

        assert len(captured_requests) == 1
        transmitted_text = captured_requests[0]["json"]["messages"][0]["content"]

        assert "Jane Doe" not in transmitted_text
        assert "+44 20 7946 0958" not in transmitted_text
        assert "[NAME]" in transmitted_text
        assert "[PHONE]" in transmitted_text
        assert "I slept poorly." in transmitted_text


class TestAIErrorHandlingAndResilience:
    """
    Verifies error paths: upstream AI failure, DB rollback, missing key graceful handling.
    """

    async def test_upstream_ai_failure_does_not_corrupt_database(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ):
        """
        When external AI provider throws a 500 error or network timeout,
        the background task logs the failure, rolls back cleanly, and does NOT insert corrupt rows.
        """
        original_post = httpx.AsyncClient.post

        async def failing_post(self_client, url, *args, **kwargs):
            url_str = str(url)
            if "googleapis.com" in url_str:
                raise httpx.ConnectTimeout("Connection timed out to AI provider")
            return await original_post(self_client, url, *args, **kwargs)

        monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
        monkeypatch.setattr(settings, "AI_API_KEY", "fake-key")
        monkeypatch.setattr(httpx.AsyncClient, "post", failing_post)

        headers = await helper_get_auth_headers(client, "ai_err@test.com", "ai_err")
        diary = await helper_create_diary_entry(
            client, headers=headers, title="Error Entry", content="Testing error resilience"
        )
        entry_id = diary["id"]

        # The endpoint returns 202 because dispatch is async
        resp = await client.post(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=headers,
            json={"agent_type": "empathetic_listener"},
        )
        assert resp.status_code == 202

        # Verify no corrupt feedback row exists in database
        result = await db_session.execute(
            select(AIFeedback).where(AIFeedback.diary_entry_id == entry_id)
        )
        assert result.scalar_one_or_none() is None

        # Verify GET feedback returns empty list gracefully without error
        fb_resp = await client.get(f"/api/v1/ai/diary/{entry_id}/feedback", headers=headers)
        assert fb_resp.status_code == 200
        assert fb_resp.json() == []

    async def test_no_api_key_graceful_degradation(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        """
        When AI_PROVIDER is 'gemini' but AI_API_KEY is empty,
        a graceful placeholder message is stored instead of crashing.
        """
        monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
        monkeypatch.setattr(settings, "AI_API_KEY", "")

        headers = await helper_get_auth_headers(client, "no_key@test.com", "no_key")
        diary = await helper_create_diary_entry(
            client, headers=headers, title="No Key Entry", content="Just a regular diary note."
        )
        entry_id = diary["id"]

        resp = await client.post(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=headers,
            json={"agent_type": "productivity_mentor"},
        )
        assert resp.status_code == 202

        fb_resp = await client.get(f"/api/v1/ai/diary/{entry_id}/feedback", headers=headers)
        assert fb_resp.status_code == 200
        feedbacks = fb_resp.json()
        assert len(feedbacks) == 1
        assert "no API key configured" in feedbacks[0]["feedback"]
