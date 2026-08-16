"""
Authentication and Authorization Security Tests.

Covers:
  - Timing-safe login failure on wrong password and nonexistent user.
  - Deactivated user access block (403 Forbidden).
  - Missing and malformed Authorization headers.
  - Invalid, expired, and tampered JWT tokens.
  - Token type enforcement (access vs refresh token isolation).
  - Malformed token claims (missing/non-integer sub).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from jose import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.db.models import User
from tests.conftest import helper_get_auth_headers, helper_login_user, helper_register_user

pytestmark = pytest.mark.asyncio


class TestAuthenticationSecurity:
    async def test_login_invalid_password_returns_generic_401(self, client: AsyncClient):
        await helper_register_user(client, "auth_sec1@test.com", "auth_sec1", "SecurePass1!")
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "auth_sec1@test.com", "password": "WrongPassword123!"},
        )
        assert resp.status_code == 401
        assert "Invalid email or password" in resp.json()["detail"]

    async def test_login_nonexistent_user_returns_identical_generic_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent_ghost@test.com", "password": "SecurePass1!"},
        )
        assert resp.status_code == 401
        # Generic message ensures no username/email enumeration oracle
        assert "Invalid email or password" in resp.json()["detail"]

    async def test_deactivated_user_cannot_login(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user_data = await helper_register_user(client, "deactivated@test.com", "deactivated_user")
        user_id = user_data["id"]

        # Deactivate user directly in DB
        await db_session.execute(
            update(User).where(User.id == user_id).values(is_active=False)
        )
        await db_session.commit()

        # Login attempt must be forbidden (403)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "deactivated@test.com", "password": "SecurePass1!"},
        )
        assert resp.status_code == 403
        assert "deactivated" in resp.json()["detail"].lower()

    async def test_deactivated_user_cannot_refresh_token(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user_data = await helper_register_user(client, "deact_refresh@test.com", "deact_refresh")
        tokens = await helper_login_user(client, "deact_refresh@test.com")
        user_id = user_data["id"]

        # Deactivate user after login
        await db_session.execute(
            update(User).where(User.id == user_id).values(is_active=False)
        )
        await db_session.commit()

        # Attempt token refresh
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 401
        assert "User not found or inactive" in resp.json()["detail"]


class TestTokenValidationSecurity:
    async def test_missing_authorization_header(self, client: AsyncClient):
        endpoints = [
            ("GET", "/api/v1/auth/me"),
            ("GET", "/api/v1/diary/"),
            ("POST", "/api/v1/diary/"),
            ("GET", "/api/v1/pomodoro/"),
            ("GET", "/api/v1/sleep/"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = await client.get(path)
            else:
                resp = await client.post(path, json={"content": "test"})
            assert resp.status_code == 401, f"Expected 401 for unauthenticated {method} {path}, got {resp.status_code}"

    async def test_malformed_authorization_headers(self, client: AsyncClient):
        bad_headers = [
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer "},
            {"Authorization": "Basic dXNlcjpwYXNz"},
            {"Authorization": "Token 12345"},
            {"Authorization": "Bearer not-a-valid-jwt-token"},
        ]
        for headers in bad_headers:
            resp = await client.get("/api/v1/auth/me", headers=headers)
            assert resp.status_code == 401

    async def test_expired_access_token_rejected(self, client: AsyncClient):
        # Create token that expired 1 hour ago
        expired_payload = {
            "sub": "1",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    async def test_tampered_token_signature_rejected(self, client: AsyncClient):
        # Token signed with wrong secret key
        tampered_token = jwt.encode(
            {"sub": "1", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret-key-attacker-guess",
            algorithm="HS256",
        )
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert resp.status_code == 401

    async def test_refresh_token_rejected_on_access_endpoint(self, client: AsyncClient):
        """
        Refresh tokens MUST NOT be accepted on endpoints expecting an access token.
        """
        refresh_token = create_refresh_token(subject=1)
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert resp.status_code == 401
        assert "access token required" in resp.json()["detail"]

    async def test_access_token_rejected_on_refresh_endpoint(self, client: AsyncClient):
        """
        Access tokens MUST NOT be accepted on the /refresh endpoint.
        """
        access_token = create_access_token(subject=1)
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401
        assert "refresh token required" in resp.json()["detail"]

    async def test_token_with_non_integer_sub_rejected(self, client: AsyncClient):
        """
        Malformed token subject claim handling.
        """
        bad_token = jwt.encode(
            {"sub": "not-an-int-user-id", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code == 401
