"""
AI Feedback Engine – Multi-Agent Chat Therapy Room.

Supported agent types:
  • empathetic_listener   – warm, compassionate reflection
  • tough_coach           – direct, no-nonsense accountability
  • sleep_analyst         – links entry themes to sleep quality
  • mindfulness_guide     – meditation / breathing suggestions
  • productivity_mentor   – focus & energy management tips

Security:
  • PII is scrubbed before sending text to external AI APIs.
  • AI feedback is encrypted before storage (same AES-256-GCM vault).
  • Each persona has an immutable system prompt the user cannot override.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import decrypt_text, encrypt_text, get_current_user_id
from app.db.database import get_db
from app.db.models import DiaryMessage, DiaryEntry
from app.schemas.diary import AIChatRequest, DiaryMessageResponse

logger = logging.getLogger("sleepwell.ai")

router = APIRouter(prefix="/ai", tags=["AI Feedback"])

# ── Agent Type Literal ───────────────────────────────────────────────────────

AgentType = Literal[
    "empathetic_listener",
    "tough_coach",
    "sleep_analyst",
    "mindfulness_guide",
    "productivity_mentor",
]

# ── Immutable System Prompts (cannot be overridden by users) ─────────────────

_SYSTEM_PROMPTS: dict[str, str] = {
    "empathetic_listener": (
        "You are a warm, compassionate listener. The user has shared their feelings. "
        "Reflect their feelings back to them with empathy, validate their emotions, and offer "
        "gentle encouragement. Keep your response to 1-2 short paragraphs. Do not give advice unless asked."
    ),
    "tough_coach": (
        "You are a direct, results-oriented life coach. The user has shared their feelings. "
        "Identify patterns of self-sabotage or avoidance, then provide clear, actionable steps "
        "to improve. Be honest but not harsh. Keep it to 2-3 bullet points."
    ),
    "sleep_analyst": (
        "You are a sleep science expert. The user has shared their feelings. "
        "Analyze how the emotions, stress levels, or activities described might affect their sleep quality. "
        "Suggest 1-2 science-backed adjustments to their evening routine. Keep it concise."
    ),
    "mindfulness_guide": (
        "You are a mindfulness and meditation teacher. The user has shared their feelings. "
        "Suggest a specific breathing technique, body scan, or short meditation practice that "
        "addresses their emotional state. Provide simple, step-by-step instructions."
    ),
    "productivity_mentor": (
        "You are a productivity and focus coach. The user has shared their feelings. "
        "Identify energy drains or focus blockers, then suggest 1-2 practical strategies "
        "to improve their workflow and mental clarity. Be specific and actionable."
    ),
}

# ── PII Scrubber ─────────────────────────────────────────────────────────────

_PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"(?:(?<=\s)|^|\()\+(?:[0-9][\s.-]?|\(\d{1,4}\)[\s.-]?){6,14}[0-9]\b"), "[PHONE]"),
    (re.compile(r"(?:\b1[\s.-]?)?(?:\(\d{3}\)|\b[2-9]\d{2})[\s.-]?\d{3}[\s.-]?\d{4}\b"), "[PHONE]"),
    (re.compile(r"\b\d{1,5}\s+[A-Za-z0-9.]+(?:\s+[A-Za-z0-9.]+){0,4},\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?\b"), "[ADDRESS]"),
    (re.compile(r"\b(?:Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"), "[NAME]"),
    (re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"), "[NAME]"),
]


def _scrub_pii(text: str) -> str:
    """Remove personally identifiable information before sending to external AI."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── AI Call (provider-agnostic) ──────────────────────────────────────────────

async def _call_ai(system_prompt: str, user_content: str) -> str:
    """Call the configured AI provider and return the response text."""
    provider = settings.AI_PROVIDER.lower()
    scrubbed = _scrub_pii(user_content)

    if not settings.AI_API_KEY and provider != "mock":
        return "[AI feedback unavailable – no API key configured. Set AI_API_KEY in your .env file.]"

    try:
        if provider == "gemini":
            return await _call_gemini(system_prompt, scrubbed)
        elif provider == "openai":
            return await _call_openai(system_prompt, scrubbed)
        elif provider == "anthropic":
            return await _call_anthropic(system_prompt, scrubbed)
        else:
            return f"[Mock AI]\nSystem: {system_prompt[:40]}...\nContent: {scrubbed[:40]}..."
    except Exception as e:
        logger.error(f"AI API Error: {e}")
        return "[AI service is currently unavailable. Please try again later.]"


async def _call_gemini(system_prompt: str, content: str) -> str:
    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": content}]}],
        "generationConfig": {"maxOutputTokens": 800, "temperature": 0.7},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, params={"key": settings.AI_API_KEY})
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _call_openai(system_prompt: str, content: str) -> str:
    import httpx
    payload = {
        "model": settings.AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "max_tokens": 800,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_anthropic(system_prompt: str, content: str) -> str:
    import httpx
    payload = {
        "model": settings.AI_MODEL,
        "max_tokens": 800,
        "system": system_prompt,
        "messages": [{"role": "user", "content": content}],
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers={
                "x-api-key": settings.AI_API_KEY,
                "anthropic-version": "2023-06-01",
            },
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


# ── Concurrent Agent Execution ───────────────────────────────────────────────

async def _get_agent_reply(agent_type: str, conversation_text: str) -> tuple[str, str]:
    """Calls the AI for a specific agent and returns (agent_type, response_text)."""
    if agent_type not in _SYSTEM_PROMPTS:
        return agent_type, "[Unknown agent type]"
    
    system_prompt = _SYSTEM_PROMPTS[agent_type] + "\n\nIMPORTANT: Read the conversation history and respond to the latest message as this specific persona."
    reply = await _call_ai(system_prompt, conversation_text)
    return agent_type, reply


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post(
    "/diary/{entry_id}/chat",
    response_model=list[DiaryMessageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Post a message and get AI agent replies",
)
async def chat_with_agents(
    entry_id: int,
    payload: AIChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # 1. Verify ownership & load existing messages
    result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.id == entry_id, DiaryEntry.user_id == user_id)
        .options(selectinload(DiaryEntry.messages))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found")

    # 2. Save User's Message
    user_msg = DiaryMessage(
        diary_entry_id=entry.id,
        role="user",
        encrypted_content=encrypt_text(payload.content)
    )
    db.add(user_msg)
    await db.flush()  # So it gets an ID

    # 3. Build Conversation History Context
    history_text = "CONVERSATION HISTORY:\n\n"
    # Optional: Include initial diary entry mood/tags if they exist
    if entry.mood:
        history_text += f"Initial Mood: {entry.mood}\n"
    
    for msg in entry.messages:
        role_label = "User" if msg.role == "user" else f"Agent ({msg.agent_type})"
        history_text += f"{role_label}: {decrypt_text(msg.encrypted_content)}\n\n"
    
    history_text += f"User: {payload.content}\n"

    # 4. Request AI responses concurrently for selected agents
    # Deduplicate agents and limit to 5
    unique_agents = list(set(payload.selected_agents))[:5]
    
    tasks = [_get_agent_reply(agent, history_text) for agent in unique_agents]
    results = await asyncio.gather(*tasks)

    # 5. Save Agent Responses
    new_agent_messages = []
    for agent_type, reply_text in results:
        agent_msg = DiaryMessage(
            diary_entry_id=entry.id,
            role="agent",
            agent_type=agent_type,
            encrypted_content=encrypt_text(reply_text)
        )
        db.add(agent_msg)
        new_agent_messages.append(agent_msg)
    
    await db.commit()

    # 6. Return the newly created messages (user + agents)
    response_list = [user_msg] + new_agent_messages
    return [
        DiaryMessageResponse(
            id=m.id,
            role=m.role,
            agent_type=m.agent_type,
            content=decrypt_text(m.encrypted_content),
            created_at=m.created_at
        )
        for m in response_list
    ]


@router.get(
    "/agents",
    summary="List all available AI agent personas",
)
async def list_agents():
    return {
        "agents": [
            {"type": "empathetic_listener", "description": "Warm, compassionate emotional reflection", "icon": "💖"},
            {"type": "tough_coach", "description": "Direct, accountability-driven coaching", "icon": "🥊"},
            {"type": "sleep_analyst", "description": "Links diary themes to sleep quality science", "icon": "😴"},
            {"type": "mindfulness_guide", "description": "Meditation and breathing practice suggestions", "icon": "🧘"},
            {"type": "productivity_mentor", "description": "Focus and energy management strategies", "icon": "🚀"},
        ]
    }
