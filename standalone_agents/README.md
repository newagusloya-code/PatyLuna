# 🤖 Standalone Multi-Agent AI System

Un paquete completamente modular, autónomo y desacoplado para integrar un sistema multi-agente de coaching, productividad, mindfulness y bienestar en cualquier proyecto Python / FastAPI / Next.js / Node.

---

## 📦 ¿Qué incluye este paquete?

```
standalone_agents/
├── personas.py          # Definición de los 5 agentes con sus system prompts y metadatos
├── security.py          # Sanitizador PII automático y encriptación AES-256-GCM
├── config.py            # Gestión de configuraciones y variables de entorno (.env)
├── engine.py            # Motor de ejecución (Gemini 3.6 Flash / Live API / OpenAI / Claude / Mock)
├── router.py            # Router de FastAPI listo para montar con 1 línea de código
├── demo_chat.py         # Script CLI interactivo para probar los agentes en terminal
├── requirements.txt     # Dependencias mínimas
└── .env.example         # Plantilla de variables de entorno
```

---

## 🎭 Agentes Incluidos

| Agente | Nombre | Ícono | Especialidad |
|---|---|---|---|
| `tough_coach` | Coach de Rendimiento | 🥊 | Rendición de cuentas directa, acción inmediata y anti-postergación |
| `sleep_analyst` | Analista de Sueño | 😴 | Ciencia circadiana, latencia de sueño y descanso profundo/REM |
| `productivity_mentor` | Mentor de Productividad | 🚀 | Enfoque profundo, técnica Pomodoro y reducción de carga cognitiva |
| `empathetic_listener` | Escucha Empática | 💖 | Contención emocional, validación sin juicio y espacio seguro |
| `mindfulness_guide` | Guía de Mindfulness | 🧘 | Técnicas somáticas, respiración 4-7-8/caja y anclaje sensorial |

---

## 🚀 Cómo usarlo en tu nueva aplicación

### Opción 1: En una API FastAPI existente

Copia la carpeta `standalone_agents/` a tu proyecto e inclúyela en tu `main.py`:

```python
from fastapi import FastAPI
from standalone_agents.router import router as agents_router

app = FastAPI(title="Mi Nueva App con Agentes")
app.include_router(agents_router)
```

Esto habilitará automáticamente los siguientes endpoints:
- `GET /ai-agents/list` – Lista todos los agentes y sus descripciones.
- `POST /ai-agents/chat/single` – Chat directo con un agente específico.
- `POST /ai-agents/chat/multi` – Consulta concurrente a múltiples agentes en paralelo.
- `GET /ai-agents/live-config` – Configuración para sesiones WebSocket con Gemini Live API.

---

### Opción 2: Usarlo como módulo en Python (sin FastAPI)

```python
import asyncio
from standalone_agents.engine import run_multi_agent_session, execute_agent_reply

async def ejemplo():
    # Consultar un solo agente
    _, respuesta = await execute_agent_reply("tough_coach", "Tengo pereza de empezar a programar hoy.")
    print(respuesta)

    # Consultar varios agentes a la vez concurrentemente
    respuestas = await run_multi_agent_session(
        ["tough_coach", "productivity_mentor", "sleep_analyst"],
        "Siento que trabajo muchas horas pero no avanzo y duermo mal."
    )
    for agente, texto in respuestas.items():
        print(f"[{agente}]:\n{texto}\n")

asyncio.run(ejemplo())
```

---

### Opción 3: Probarlo directamente desde la Terminal (CLI)

```bash
python -m standalone_agents.demo_chat
```

---

## ⚙️ Configuración y Variables de Entorno

Crea un archivo `.env` o define las siguientes variables:

```bash
# Proveedor: gemini | openai | anthropic | mock
AI_PROVIDER=gemini
AI_API_KEY=tu_api_key_aqui

# Modelos recomendados
AI_MODEL=gemini-3.6-flash
LIVE_AI_MODEL=gemini-3.1-flash-live-preview
```

> **Nota sobre Cuotas / Modo Mock**: Si te quedas sin cuota de API, puedes definir `AI_PROVIDER=mock` para continuar desarrollando y probando la interfaz sin costo ni llamadas externas.
