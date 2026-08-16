"""
AI Pipeline End-to-End and Transmission-Point Security Boundary Tests.
"""

from __future__ import annotations

from typing import Any
import httpx
import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import DiaryMessage
from tests.conftest import (
    helper_create_diary_entry,
    helper_get_auth_headers,
)

pytestmark = pytest.mark.asyncio

class TestPIITransmissionSecurityBoundary:
    """
    Proves that the AI pipeline strictly scrubs PII BEFORE transmitting payloads
    over the wire to external AI providers (Gemini, OpenAI, Anthropic).
    """

    async def test_gemini_transmission_scrubbed_payload(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        captured_requests: list[dict[str, Any]] = []
        original_post = httpx.AsyncClient.post

        async def fake_gemini_post(self_client, url, *args, **kwargs):
            url_str = str(url)
            if "googleapis.com" in url_str:
                captured_requests.append({
                    "url": url_str,
                    "json": kwargs.get("json"),
                })
                mock_response = {
                    "candidates": [{"content": {"parts": [{"text": "Gemini analyzed your scrubbed entry successfully."}]}}]
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
        diary = await helper_create_diary_entry(client, headers=headers, title="Thread", content="Initial content")
        entry_id = diary["id"]

        resp = await client.post(
            f"/api/v1/ai/diary/{entry_id}/chat",
            headers=headers,
            json={"content": sensitive_entry_text, "selected_agents": ["mindfulness_guide"]},
        )
        assert resp.status_code == 201

        assert len(captured_requests) == 1
        req = captured_requests[0]
        transmitted_text = req["json"]["contents"][0]["parts"][0]["text"]

        assert "watson.sherlock" not in transmitted_text
        assert "415) 555-2671" not in transmitted_text
        assert "Dr. John Watson" not in transmitted_text
        assert "000-12-3456" not in transmitted_text
        assert "123 Baker Street" not in transmitted_text

        assert "[EMAIL]" in transmitted_text
        assert "[PHONE]" in transmitted_text
        assert "[NAME]" in transmitted_text
        assert "[SSN]" in transmitted_text
        assert "[ADDRESS]" in transmitted_text
