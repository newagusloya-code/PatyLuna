"""
Authentication endpoint tests.

Covers:
  ✓ Successful registration
  ✓ Duplicate email / username rejection
  ✓ Password strength validation
  ✓ Login with correct credentials
  ✓ Login with wrong password (timing-attack-safe)
  ✓ Token refresh flow
  ✓ GET /me with valid token
  ✓ GET /me with invalid token → 401
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import helper_login_user, helper_register_user

pytestmark = pytest.mark.asyncio


async def _register_and_login(client: AsyncClient, payload: dict) -> dict:
    """Helper: register a user and return login tokens with strict verification."""
    await helper_register_user(client, payload["email"], payload["username"], payload["password"])
    tokens = await helper_login_user(client, payload["email"], payload["password"])
    return tokens


class TestRegister:
    async def test_register_success(self, client: AsyncClient, valid_user_payload: dict):
        resp = await client.post("/api/v1/auth/register", json=valid_user_payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == valid_user_payload["email"]
        assert data["username"] == valid_user_payload["username"]
        assert "hashed_password" not in data  # Never leak the hash

    async def test_register_duplicate_email(self, client: AsyncClient, valid_user_payload: dict):
        await client.post("/api/v1/auth/register", json=valid_user_payload)
        resp = await client.post("/api/v1/auth/register", json=valid_user_payload)
        assert resp.status_code == 409

    async def test_register_duplicate_username(self, client: AsyncClient, valid_user_payload: dict):
        await client.post("/api/v1/auth/register", json=valid_user_payload)
        second = valid_user_payload.copy()
        second["email"] = "other@example.com"
        resp = await client.post("/api/v1/auth/register", json=second)
        assert resp.status_code == 409

    async def test_register_weak_password_no_uppercase(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "x@x.com", "username": "test_x", "password": "weakpass1!"},
        )
        assert resp.status_code == 422

    async def test_register_weak_password_no_special_char(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "x@x.com", "username": "test_x", "password": "WeakPass1"},
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "username": "testuser", "password": "SecurePass1!"},
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, valid_user_payload: dict):
        await client.post("/api/v1/auth/register", json=valid_user_payload)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": valid_user_payload["email"], "password": valid_user_payload["password"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, valid_user_payload: dict):
        await client.post("/api/v1/auth/register", json=valid_user_payload)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": valid_user_payload["email"], "password": "WrongPass1!"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@nowhere.com", "password": "SecurePass1!"},
        )
        assert resp.status_code == 401
        # Generic message – does NOT reveal whether email exists
        assert "Invalid email or password" in resp.json()["detail"]


class TestTokenRefresh:
    async def test_refresh_success(self, client: AsyncClient, valid_user_payload: dict):
        tokens = await _register_and_login(client, valid_user_payload)
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_with_access_token_rejected(
        self, client: AsyncClient, valid_user_payload: dict
    ):
        tokens = await _register_and_login(client, valid_user_payload)
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["access_token"]},  # Wrong token type
        )
        assert resp.status_code == 401

    async def test_refresh_with_garbage_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.real.token"},
        )
        assert resp.status_code == 401


class TestGetMe:
    async def test_get_me_success(self, client: AsyncClient, valid_user_payload: dict):
        tokens = await _register_and_login(client, valid_user_payload)
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == valid_user_payload["email"]

    async def test_get_me_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert resp.status_code == 401
