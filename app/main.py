"""
SleepWell API – FastAPI application entry point.

Security middlewares applied here:
  • CORS (restrictive origins)
  • Rate limiting (via slowapi)
  • Trusted host enforcement
  • Request ID injection for traceability
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.limiter import limiter
from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.database import engine, Base


# ────────────────────────────────────────────────────────────────────────────
# Lifespan – startup / shutdown events
# ────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup (dev only). Use Alembic migrations in prod."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        import logging
        logging.getLogger("uvicorn.error").warning("Database table auto-creation notice: %s", exc)
    yield
    await engine.dispose()


# ────────────────────────────────────────────────────────────────────────────
# Rate Limiter
# ────────────────────────────────────────────────────────────────────────────

# Limiter is imported from app.core.limiter


# ────────────────────────────────────────────────────────────────────────────
# App
# ────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,       # Swagger UI only in dev
    redoc_url="/redoc" if settings.DEBUG else None,      # ReDoc only in dev
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

app.state.limiter = limiter
from slowapi import _rate_limit_exceeded_handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from fastapi.responses import JSONResponse
import logging

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import traceback
    logging.getLogger("uvicorn.error").error(
        "Unhandled error on %s %s: %s\n%s",
        request.method,
        request.url.path,
        exc,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Por favor intenta de nuevo o revisa la conexión."},
    )


# ────────────────────────────────────────────────────────────────────────────
# Middlewares (order matters – outermost first)
# ────────────────────────────────────────────────────────────────────────────

# 1. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# 2. Trusted Hosts (prevents Host header attacks)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)


# 3. Request ID middleware (traceability)
@app.middleware("http")
async def add_request_id(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# 4. Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    return response


# ────────────────────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────────────────────

app.include_router(v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check for uptime monitoring."""
    return {"status": "healthy", "version": settings.APP_VERSION}


# ────────────────────────────────────────────────────────────────────────────
# Static Files & SPA Catch-all (Must be last)
# ────────────────────────────────────────────────────────────────────────────

import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Check if the frontend build directory exists
# In Docker: /app/frontend/dist
# In dev: ./frontend/dist or ../frontend/dist
FRONTEND_DIST = os.environ.get("FRONTEND_DIST", "/app/frontend/dist")

# Fallback to relative paths if /app doesn't exist (local dev)
if not os.path.exists(FRONTEND_DIST):
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    FRONTEND_DIST = str(_PROJECT_ROOT / "frontend" / "dist")
    if not os.path.exists(FRONTEND_DIST):
        FRONTEND_DIST = os.path.join(os.getcwd(), "frontend", "dist")

if os.path.exists(FRONTEND_DIST):
    # Mount static files (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")
    
    # Optional: mount public files like favicon.ico if they are in root of dist
    # But usually a catch-all handles this, or we can mount the whole dir on a path
    # However, mounting whole dir on "/" overrides API routes if not careful.
    
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        # Serve specific files if requested directly and they exist
        target_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(target_path):
            return FileResponse(target_path)
            
        # Otherwise, return index.html for SPA client-side routing
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
else:
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_fallback(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        # Fallback if frontend is not built
        return {"error": "Frontend build not found. Please run 'npm run build' in the frontend directory."}
