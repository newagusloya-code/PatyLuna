"""
AI Feedback Engine for the Therapy Room.

The current active contract exposes three personas:
  - tough_coach
  - sleep_analyst
  - productivity_mentor

Sensitive text is scrubbed before being transmitted to external providers.
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
from app.db.models import DiaryEntry, DiaryMessage
from app.schemas.diary import AIChatRequest, DiaryMessageResponse

logger = logging.getLogger("sleepwell.ai")

router = APIRouter(prefix="/ai", tags=["AI Feedback"])

AgentType = Literal["tough_coach", "sleep_analyst", "productivity_mentor"]

ACTIVE_AGENTS: list[dict[str, str]] = [
    {
        "type": "tough_coach",
        "name": "Coach Estricto",
        "description": "Direct feedback, accountability, and practical next steps.",
        "icon": "🧭",
    },
    {
        "type": "sleep_analyst",
        "name": "Especialista de Sueño",
        "description": "Sleep patterns, recovery, and evening routine guidance.",
        "icon": "🌙",
    },
    {
        "type": "productivity_mentor",
        "name": "Mentor Productividad",
        "description": "Focus, planning, and energy-management advice.",
        "icon": "⚡",
    },
]

_SYSTEM_PROMPTS: dict[str, str] = {
    "tough_coach": (
        "You are a direct, results-oriented life coach. The user has shared their feelings. "
        "Identify patterns of avoidance or self-sabotage, then provide clear, actionable steps "
        "to improve. Be honest but not harsh. Keep it concise."
    ),
    "sleep_analyst": (
        "You are a sleep science expert. The user has shared their feelings. "
        "Analyze how the emotions, stress levels, or activities described might affect their sleep quality. "
        "Suggest 1-2 science-backed adjustments to their evening routine. Keep it concise."
    ),
    "productivity_mentor": (
        "You are a productivity and focus coach. The user has shared their feelings. "
        "Identify energy drains or focus blockers, then suggest 1-2 practical strategies "
        "to improve their workflow and mental clarity. Be specific and actionable."
    ),
}

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
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _message_to_response(message: DiaryMessage) -> DiaryMessageResponse:
    return DiaryMessageResponse(
        id=message.id,
        role=message.role,
        agent_type=message.agent_type,
        content=decrypt_text(message.encrypted_content),
        created_at=message.created_at,
    )


def _entry_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found")


async def _load_owned_entry(
    entry_id: int,
    user_id: int,
    db: AsyncSession,
) -> DiaryEntry:
    result = await db.execute(
        select(DiaryEntry)
        .where(DiaryEntry.id == entry_id, DiaryEntry.user_id == user_id)
        .options(selectinload(DiaryEntry.messages))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise _entry_not_found()
    return entry


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
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


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


async def _call_ai(system_prompt: str, user_content: str) -> str:
    provider = settings.AI_PROVIDER.lower()
    scrubbed = _scrub_pii(user_content)

    if provider != "mock" and not settings.AI_API_KEY:
        return "[AI feedback unavailable – no API key configured.]"

    try:
        if provider == "gemini":
            return await _call_gemini(system_prompt, scrubbed)
        if provider == "openai":
            return await _call_openai(system_prompt, scrubbed)
        if provider == "anthropic":
            return await _call_anthropic(system_prompt, scrubbed)
        return f"[Mock AI]\nSystem: {system_prompt[:40]}...\nContent: {scrubbed[:40]}..."
    except Exception as exc:
        logger.error("AI API error: %s", exc)
        return "[AI service is currently unavailable. Please try again later.]"


async def _get_agent_reply(agent_type: str, conversation_text: str) -> tuple[str, str]:
    if agent_type not in _SYSTEM_PROMPTS:
        return agent_type, "[Unknown agent type]"

    system_prompt = _SYSTEM_PROMPTS[agent_type]
    reply = await _call_ai(system_prompt, conversation_text)
    return agent_type, reply


@router.get("/agents", summary="List the active Therapy Room personas")
async def list_agents() -> dict[str, list[dict[str, str]]]:
    return {"agents": ACTIVE_AGENTS}


@router.get(
    "/diary/{entry_id}/chat",
    response_model=list[DiaryMessageResponse],
    summary="List AI chat messages for a diary entry",
)
async def list_chat_messages(
    entry_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    entry = await _load_owned_entry(entry_id, user_id, db)
    return [_message_to_response(message) for message in entry.messages]


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
    entry = await _load_owned_entry(entry_id, user_id, db)

    user_msg = DiaryMessage(
        diary_entry_id=entry.id,
        role="user",
        encrypted_content=encrypt_text(payload.content),
    )
    db.add(user_msg)
    await db.flush()

    history_lines: list[str] = []
    if entry.mood:
        history_lines.append(f"Initial Mood: {entry.mood}")
    for message in entry.messages:
        role_label = "User" if message.role == "user" else f"Agent ({message.agent_type})"
        history_lines.append(f"{role_label}: {decrypt_text(message.encrypted_content)}")
    history_lines.append(f"User: {payload.content}")
    history_text = "\n\n".join(history_lines)

    unique_agents = list(dict.fromkeys(payload.selected_agents))[:5]
    results = await asyncio.gather(*(_get_agent_reply(agent, history_text) for agent in unique_agents))

    agent_messages: list[DiaryMessage] = []
    for agent_type, reply_text in results:
        agent_msg = DiaryMessage(
            diary_entry_id=entry.id,
            role="agent",
            agent_type=agent_type,
            encrypted_content=encrypt_text(reply_text),
        )
        db.add(agent_msg)
        agent_messages.append(agent_msg)

    await db.flush()
    await db.commit()

    return [_message_to_response(user_msg), *(_message_to_response(m) for m in agent_messages)]
