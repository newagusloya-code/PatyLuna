"""
CLI Interactive Demo for Standalone Multi-Agent Kit.

Run directly in terminal:
    python -m standalone_agents.demo_chat
"""

import asyncio
from standalone_agents.config import settings
from standalone_agents.personas import AGENT_PERSONAS
from standalone_agents.engine import run_multi_agent_session


async def main():
    print("\n" + "=" * 60)
    print("🤖 Standalone Multi-Agent Consultation Engine")
    print(f"Provider: {settings.AI_PROVIDER} | Model: {settings.AI_MODEL}")
    print("=" * 60 + "\n")

    print("Agentes disponibles:")
    for idx, (key, data) in enumerate(AGENT_PERSONAS.items(), 1):
        print(f"  [{idx}] {data['icon']} {data['name']} ({key})")

    print("\nSelecciona los agentes por número separados por comas (ej. 1,2,3) o Enter para todos:")
    selection = input("> ").strip()

    keys = list(AGENT_PERSONAS.keys())
    if not selection:
        selected_keys = keys
    else:
        indices = [int(s.strip()) - 1 for s in selection.split(",") if s.strip().isdigit()]
        selected_keys = [keys[i] for i in indices if 0 <= i < len(keys)]

    print(f"\nAgentes activos: {', '.join(selected_keys)}")
    print("Escribe tu consulta (o 'salir' para terminar):\n")

    while True:
        try:
            user_input = input("Usuario > ").strip()
            if not user_input or user_input.lower() in ("salir", "exit", "quit"):
                break

            print("\n⏳ Consultando agentes en paralelo...")
            responses = await run_multi_agent_session(selected_keys, user_input)

            print("\n--- Respuestas de los Agentes ---")
            for agent_type, text in responses.items():
                meta = AGENT_PERSONAS[agent_type]
                print(f"\n{meta['icon']} {meta['name']} ({agent_type}):")
                print(f"{text}\n")
            print("-" * 40 + "\n")

        except KeyboardInterrupt:
            break

    print("\n👋 Sesión finalizada.")


if __name__ == "__main__":
    asyncio.run(main())
