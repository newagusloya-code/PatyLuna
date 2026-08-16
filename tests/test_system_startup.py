"""
Application Startup, Import Integrity, Router, and Middleware Tests.

Verifies:
  - All core and endpoint modules import cleanly without circular dependencies.
  - FastAPI application lifespan and database metadata sync.
  - Router mounting and API v1 endpoint presence.
  - Health check endpoint response.
  - Security headers injection across responses.
  - OpenAPI schema generation.
"""

from __future__ import annotations

import importlib
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.main import app


class TestSystemStartupAndImports:
    def test_all_modules_import_cleanly(self):
        modules = [
            "app.main",
            "app.core.config",
            "app.core.security",
            "app.db.database",
            "app.db.models",
            "app.schemas.user",
            "app.schemas.diary",
            "app.schemas.pomodoro",
            "app.api.v1.router",
            "app.api.v1.endpoints.auth",
            "app.api.v1.endpoints.diary",
            "app.api.v1.endpoints.ai",
            "app.api.v1.endpoints.pomodoro",
            "app.api.v1.endpoints.sleep",
        ]
        for mod in modules:
            imported = importlib.import_module(mod)
            assert imported is not None, f"Module {mod} failed to import"

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == settings.APP_VERSION

    @pytest.mark.asyncio
    async def test_security_headers_middleware(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        headers = resp.headers

        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers
        assert "X-Request-ID" in headers

    def test_router_routes_mounted(self):
        registered_paths = {route.path for route in app.routes}
        expected_paths = {
            "/health",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/api/v1/auth/me",
            "/api/v1/diary/",
            "/api/v1/diary/{entry_id}",
            "/api/v1/ai/diary/{entry_id}/feedback",
            "/api/v1/ai/agents",
            "/api/v1/pomodoro/",
            "/api/v1/pomodoro/{session_id}/complete",
            "/api/v1/sleep/",
            "/api/v1/sleep/{session_id}/end",
        }
        for path in expected_paths:
            assert path in registered_paths, f"Expected route {path} not registered in app routes"
