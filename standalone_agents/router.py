"""
FastAPI Router for Standalone Agents.

Mount this in any FastAPI application:
```python
from fastapi import FastAPI
from standalone_agents.router import router as agents_router

app = FastAPI()
app.include_router(agents_router)
```
"""

from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from standalone_agents.config import settings
from standalone_agents.personas import AGENT_PERSONAS, AgentType
from standalone_agents.engine import call_ai_provider, execute_agent_reply, run_multi_agent_session

router = APIRouter(prefix="/ai-agents", tags=["Standalone AI Agents"])


# ── Pydantic Request / Response Models ───────────────────────────────────────

class AgentMetadataResponse(BaseModel):
    type: str
    name: str
    description: str
    icon: str


class SingleAgentChatRequest(BaseModel):
    agent_type: AgentType
    message: str = Field(..., min_length=1, max_length=10_000)
    history: Optional[str] = None


class SingleAgentChatResponse(BaseModel):
    agent_type: str
    response: str
    model: str


class MultiAgentChatRequest(BaseModel):
    selected_agents: list[AgentType] = Field(..., min_length=1, max_length=5)
    message: str = Field(..., min_length=1, max_length=10_000)
    history: Optional[str] = None


class MultiAgentChatResponse(BaseModel):
    responses: dict[str, str]
    model: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/list", response_model=list[AgentMetadataResponse], summary="List all available agent personas")
async def list_available_agents():
    """Returns the list and metadata of all 5 available agent personas."""
    return [
        AgentMetadataResponse(
            type=meta["type"],
            name=meta["name"],
            description=meta["description"],
            icon=meta["icon"],
        )
        for meta in AGENT_PERSONAS.values()
    ]


@router.post("/chat/single", response_model=SingleAgentChatResponse, summary="Chat with a single agent persona")
async def chat_single(payload: SingleAgentChatRequest):
    """Direct single-turn or context-aware chat with one selected agent."""
    context = payload.message
    if payload.history:
        context = f"HISTORIAL:\n{payload.history}\n\nMENSAJE ACTUAL:\n{payload.message}"

    _, reply = await execute_agent_reply(payload.agent_type, context)
    return SingleAgentChatResponse(
        agent_type=payload.agent_type,
        response=reply,
        model=settings.AI_MODEL,
    )


@router.post("/chat/multi", response_model=MultiAgentChatResponse, summary="Concurrent multi-agent consultation")
async def chat_multi(payload: MultiAgentChatRequest):
    """Broadcasts a user message to multiple selected agents concurrently."""
    context = payload.message
    if payload.history:
        context = f"HISTORIAL:\n{payload.history}\n\nMENSAJE ACTUAL:\n{payload.message}"

    results = await run_multi_agent_session(payload.selected_agents, context)
    return MultiAgentChatResponse(
        responses=results,
        model=settings.AI_MODEL,
    )


@router.get("/live-config", summary="Get Gemini Live API session config for real-time audio/streaming")
async def get_live_config(agent_type: AgentType = "tough_coach"):
    """Returns the recommended configuration for Gemini Live API WebSocket sessions."""
    meta = AGENT_PERSONAS.get(agent_type, AGENT_PERSONAS["tough_coach"])
    return {
        "model": settings.LIVE_AI_MODEL,
        "audio_input_format": "audio/pcm;rate=16000",
        "audio_output_format": "audio/pcm;rate=24000",
        "response_modalities": ["AUDIO"],
        "system_instruction": meta["system_prompt"],
        "thinking_level": "minimal",
        "agent_type": agent_type,
    }
