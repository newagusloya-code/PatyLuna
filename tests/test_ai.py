"""
Tests for AI Feedback personas and core multi-agent chat flow.
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

    async def test_request_ai_chat_flow(self, client: AsyncClient):
        # 1. Prerequisite Auth with strict failure locality
        headers = await helper_get_auth_headers(client, "ai_user_core@test.com", "ai_user_core")

        # 2. Prerequisite Diary creation (Thread creation)
        entry = await helper_create_diary_entry(
            client,
            headers=headers,
            title="Chat Session",
            content="Initial context",
            mood="anxious",
            tags="test",
        )
        entry_id = entry["id"]

        # 3. Post a chat message and select empathetic_listener
        ai_resp = await client.post(
            f"/api/v1/ai/diary/{entry_id}/chat",
            headers=headers,
            json={
                "content": "I worked 14 hours and feel exhausted.",
                "selected_agents": ["empathetic_listener"]
            },
        )
        assert ai_resp.status_code == 201, f"AI chat request failed: {ai_resp.text}"
        resp_data = ai_resp.json()
        
        # It should return a list of messages (1 user msg + 1 agent msg)
        assert isinstance(resp_data, list)
        assert len(resp_data) == 2
        
        user_msg = resp_data[0]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == "I worked 14 hours and feel exhausted."

        agent_msg = resp_data[1]
        assert agent_msg["role"] == "agent"
        assert agent_msg["agent_type"] == "empathetic_listener"
        assert len(agent_msg["content"]) > 0

        # 4. Verify messages are attached to the diary entry GET response
        diary_resp = await client.get(f"/api/v1/diary/{entry_id}", headers=headers)
        assert diary_resp.status_code == 200
        diary_data = diary_resp.json()
        assert len(diary_data["messages"]) == 2
        assert diary_data["messages"][0]["role"] == "user"
        assert diary_data["messages"][1]["role"] == "agent"
