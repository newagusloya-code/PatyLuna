"""
Tests for AI Feedback personas and core feedback request flow.
Enforces failure locality and validates agent list contracts.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import helper_create_diary_entry, helper_get_auth_headers

pytestmark = pytest.mark.asyncio


class TestAIEngine:
    async def test_list_agents_contract(self, client: AsyncClient):
        """
        Validates the AI Agent persona contract.
        Contract definition: Exactly 5 personas defined by AgentType and _SYSTEM_PROMPTS.
        Each object must adhere to the shape: {"type": str, "description": str}.
        """
        resp = await client.get("/api/v1/ai/agents")
        assert resp.status_code == 200, f"Failed fetching agents: {resp.text}"
        data = resp.json()
        assert "agents" in data, f"Missing 'agents' list in response: {data}"
        agents = data["agents"]
        assert isinstance(agents, list), f"Expected list of agents, got: {type(agents)}"

        # The API contract specifies exactly these 5 supported persona types
        expected_agents = {
            "empathetic_listener",
            "tough_coach",
            "sleep_analyst",
            "mindfulness_guide",
            "productivity_mentor",
        }
        assert len(agents) == len(expected_agents), (
            f"API contract violation: expected {len(expected_agents)} agents, got {len(agents)}"
        )

        returned_types = set()
        for agent in agents:
            assert isinstance(agent, dict), f"Agent entry must be an object: {agent}"
            assert "type" in agent, f"Missing 'type' in agent: {agent}"
            assert "description" in agent, f"Missing 'description' in agent: {agent}"
            assert isinstance(agent["type"], str) and agent["type"] in expected_agents
            assert isinstance(agent["description"], str) and len(agent["description"].strip()) > 0
            returned_types.add(agent["type"])

        assert returned_types == expected_agents, f"Mismatch in agent types: {returned_types} vs {expected_agents}"

    async def test_request_ai_feedback_flow(self, client: AsyncClient):
        # 1. Prerequisite Auth with strict failure locality
        headers = await helper_get_auth_headers(client, "ai_user_core@test.com", "ai_user_core")

        # 2. Prerequisite Diary creation with strict failure locality
        entry = await helper_create_diary_entry(
            client,
            headers=headers,
            title="Hard Day",
            content="I worked 14 hours and feel exhausted.",
            mood="exhausted",
            tags="work,burnout",
        )
        entry_id = entry["id"]

        # 3. Request feedback from empathetic_listener
        ai_resp = await client.post(
            f"/api/v1/ai/diary/{entry_id}/feedback",
            headers=headers,
            json={"agent_type": "empathetic_listener"},
        )
        assert ai_resp.status_code == 202, f"AI feedback request failed: {ai_resp.text}"
        resp_data = ai_resp.json()
        assert resp_data["status"] == "accepted"
        assert resp_data["entry_id"] == entry_id
        assert resp_data["agent_type"] == "empathetic_listener"
        assert "message" in resp_data

        # 4. Verify feedback was generated, persisted, and retrievable via GET /ai/diary/{entry_id}/feedback
        feedbacks_resp = await client.get(f"/api/v1/ai/diary/{entry_id}/feedback", headers=headers)
        assert feedbacks_resp.status_code == 200
        feedbacks = feedbacks_resp.json()
        assert len(feedbacks) == 1
        assert feedbacks[0]["agent_type"] == "empathetic_listener"
        assert "feedback" in feedbacks[0]
        assert len(feedbacks[0]["feedback"]) > 0

        # 5. Verify feedback is also attached to the diary entry GET response
        diary_resp = await client.get(f"/api/v1/diary/{entry_id}", headers=headers)
        assert diary_resp.status_code == 200
        diary_data = diary_resp.json()
        assert len(diary_data["ai_feedbacks"]) == 1
        assert diary_data["ai_feedbacks"][0]["agent_type"] == "empathetic_listener"
