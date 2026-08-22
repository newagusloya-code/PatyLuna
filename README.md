# Paty Luna (SleepWell) 🌙 🎧

Paty Luna is a full-stack wellness app with a Therapy Room powered by five AI agents - empathetic listener, tough coach, sleep analyst, mindfulness guide, and productivity mentor - plus a private diary, therapeutic audio, sleep tools, and Pomodoro sessions. The backend uses FastAPI, SQLAlchemy, and JWT authentication; the frontend is a Vanilla JavaScript SPA bundled with Vite. (Until next update maybe I will upload the agents again.) 

## Features

- **Therapy Room:** chat with five AI agents - an empathetic listener, tough coach, sleep analyst, mindfulness guide, and productivity mentor.
- **Private Diary:** encrypted entries and AI conversation history scoped to the authenticated user.
- **Sleep & Focus Tools:** therapeutic audio, a sleep sanctuary, and Pomodoro sessions.
- **Security:** JWT auth, bcrypt passwords, rate limiting, restrictive CORS, security headers, and ownership checks.
- **Async API:** FastAPI and SQLAlchemy 2.0 with PostgreSQL or SQLite.

## Stack

- Frontend: Vanilla JavaScript, Vite, HTML5, CSS
- Backend: Python 3.10+, FastAPI, SQLAlchemy, Alembic
- Services: PostgreSQL/SQLite, Redis (optional for rate limiting)
- Deployment: Docker, Render (`render.yaml`), Fly.io (`fly.toml`), or Vercel for the frontend

## Local development

Prerequisites: Python 3.10+, Node.js/npm, and optionally Redis.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

For local SQLite, set `DATABASE_URL=sqlite+aiosqlite:///./test.db` in `.env`. Use PostgreSQL for production. The app creates development tables on startup.

Start the backend on port `8000`:

```bash
uvicorn app.main:app --reload
```

Start the frontend on port `3000` in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

##Fact before you read 
THE APP HAS NO LONGER AGENTS AVAILABLE UNTIL NEXT UPDATE, I REMOVE IT FOR THE FRONTEND AND PROJECT UNTIL I HAVE MORE REVENUE AND BE ABLE TO SUPPORT THE API SERVICE.

The Therapy Room is available at `http://localhost:3000/#/therapy` after signing in. It loads the five agents from `/api/v1/ai/agents`; a conversation creates a diary entry and uses `/api/v1/ai/diary/{id}/chat`. Set `AI_PROVIDER=mock` for a local smoke test without an API key. If the API is hosted separately, set `VITE_API_BASE_URL` to its public URL before building.

## Verification

From the repository root:

```bash
venv/bin/python -m pytest -q
```

Build the frontend bundle:

```bash
cd frontend
npm run build
```

## Deployment

The repository includes `Dockerfile`, `render.yaml`, and `fly.toml` for backend/monolith deployment. For a separate Vercel frontend project, set the project root to `frontend`, build with `npm run build`, publish `dist`, and configure `VITE_API_BASE_URL` to the deployed API URL. Store `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, database credentials, and AI keys in the platform secret manager. Never commit `.env`.

## Repository hygiene

Do not commit `.env`, secrets, `test.db`, `venv`, `node_modules`, or `frontend/dist`.
