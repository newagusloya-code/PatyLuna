"""
AI Execution Engine for Multi-Agent Orchestration.

Supports:
- Google GenAI SDK (Gemini 3.6 Flash / Gemini 3.1 Flash)
- HTTP REST API fallbacks
- OpenAI & Anthropic providers
- Mock mode for local testing without API keys / quotas
- Concurrent multi-agent response generation
"""

import asyncio
import logging
from typing import Optional

import httpx

from standalone_agents.config import settings
from standalone_agents.personas import AGENT_PERSONAS
from standalone_agents.security import scrub_pii

logger = logging.getLogger("standalone_agents.engine")


async def call_ai_provider(system_prompt: str, user_content: str) -> str:
    """Invokes the configured AI provider with PII scrubbing and graceful fallback."""
    provider = settings.AI_PROVIDER.lower()
    sanitized_content = scrub_pii(user_content)

    if not settings.AI_API_KEY and provider != "mock":
        return (
            "💖 [Modo Simulado / Quota Safe]\n"
            f"Como {system_prompt.split('.')[0]}, he analizado tu mensaje de forma segura. "
            "Para respuestas reales, configura tu AI_API_KEY en las variables de entorno."
        )

    try:
        if provider == "gemini":
            return await _call_gemini(system_prompt, sanitized_content)
        elif provider == "openai":
            return await _call_openai(system_prompt, sanitized_content)
        elif provider == "anthropic":
            return await _call_anthropic(system_prompt, sanitized_content)
        else:
            return (
                f"[Respuesta Simulada / Mock Persona]\n"
                f"Prompt Rol: {system_prompt[:80]}...\n"
                f"Contenido recibido (sanitizado): {sanitized_content}"
            )
    except Exception as e:
        logger.error(f"AI API Execution Error: {e}")
        return f"[Aviso: Servicio de IA no disponible temporalmente o cuota excedida. Error: {str(e)[:80]}]"


async def _call_gemini(system_prompt: str, content: str) -> str:
    """Primary caller using google-genai SDK with HTTP fallback."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.AI_API_KEY)
        response = await client.aio.models.generate_content(
            model=settings.AI_MODEL,
            contents=content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                max_output_tokens=800,
            ),
        )
        if response and response.text:
            return response.text.strip()
    except Exception as sdk_err:
        logger.warning(f"google-genai SDK call fallback: {sdk_err}")

    # Fallback to HTTP REST endpoint
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
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _call_openai(system_prompt: str, content: str) -> str:
    payload = {
        "model": settings.AI_MODEL if not settings.AI_MODEL.startswith("gemini") else "gpt-4o-mini",
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
        return resp.json()["choices"][0]["message"]["content"].strip()


async def _call_anthropic(system_prompt: str, content: str) -> str:
    payload = {
        "model": settings.AI_MODEL if not settings.AI_MODEL.startswith("gemini") else "claude-3-5-sonnet-20241022",
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
        return resp.json()["content"][0]["text"].strip()


async def execute_agent_reply(agent_type: str, conversation_context: str) -> tuple[str, str]:
    """Runs a single agent persona against the conversation context."""
    if agent_type not in AGENT_PERSONAS:
        return agent_type, f"[Agente no reconocido: {agent_type}]"

    meta = AGENT_PERSONAS[agent_type]
    full_prompt = (
        meta["system_prompt"]
        + "\n\nIMPORTANTE: Lee el historial de conversación y responde al último mensaje del usuario como este personaje."
    )
    reply = await call_ai_provider(full_prompt, conversation_context)
    return agent_type, reply


async def run_multi_agent_session(
    selected_agents: list[str],
    conversation_context: str
) -> dict[str, str]:
    """Runs multiple agent personas concurrently and returns a dictionary of responses."""
    unique_agents = list(dict.fromkeys(selected_agents))
    tasks = [execute_agent_reply(agent, conversation_context) for agent in unique_agents]
    results = await asyncio.gather(*tasks)
    return {agent_type: reply for agent_type, reply in results}
