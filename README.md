# Paty Luna (SleepWell) 🌙 🎧

> **Paty Luna (SleepWell API) is a full-stack web app providing therapeutic sound frequencies and a digital sleep sanctuary. It features a secure, high-performance backend built with FastAPI, SQLAlchemy, and JWT Auth, paired with a lightning-fast Vanilla JS SPA frontend powered by Vite and a custom audio playback engine.**

A holistic full-stack web application designed to provide therapeutic sound frequencies, relief for tinnitus, and a digital sleep sanctuary. This platform delivers a seamless, responsive auditory experience securely backed by a modern Python API.

## ✨ Features

- **Therapeutic Audio Engine:** Custom audio playback capabilities designed for sleep induction and tinnitus relief (built with Vanilla JS).
- **Secure Authentication:** Robust JWT-based user authentication, password hashing (bcrypt), and secure session management.
- **Rate Limiting & Security:** Integrated API rate-limiting via Redis (`slowapi`), restrictive CORS, and strict security headers to prevent XSS and Host header attacks.
- **Modern SPA Frontend:** Lightning-fast, lightweight Vanilla JavaScript frontend bundled with Vite.
- **Robust Backend:** High-performance, asynchronous REST API powered by FastAPI and SQLAlchemy 2.0.
- **End-to-End Tested:** Includes comprehensive automated integration testing for auth lifecycles.

## 🛠️ Technology Stack

**Frontend**
- Vanilla JavaScript (ES6 Modules)
- Vite (Build Tool & Dev Server)
- HTML5 / Native CSS

**Backend**
- Python 3.x
- [FastAPI](https://fastapi.tiangolo.com/) (REST API framework)
- [SQLAlchemy](https://www.sqlalchemy.org/) + Alembic (Async ORM & Database Migrations)
- PostgreSQL / SQLite (Database)
- Redis (Rate Limiting)

**Deployment / DevOps**
- Docker (Containerization)
- `fly.toml` / `render.yaml` (Pre-configured for cloud deployments)
- Uvicorn / Gunicorn (ASGI Servers)

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js & npm
- Redis (Optional, for rate-limiting)

### Backend Setup
1. Navigate to the root directory and create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables by copying the example file:
   ```bash
   cp .env.example .env
   ```
4. Run the database migrations (if configured) or let the startup script create the local `test.db`.
5. Start the FastAPI backend:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

## 🧪 Testing

The repository includes end-to-end (E2E) integration tests to ensure the stability of critical paths like Authentication.

To run the verification suite:
```bash
pytest
# or run the standalone script:
python verify_auth_e2e.py
```
