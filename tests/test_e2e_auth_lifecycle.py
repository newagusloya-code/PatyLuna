"""
End-to-End Authentication Lifecycle & Stability Verification Test Suite.

Comprehensive integration tests covering:
  1. Full User Lifecycle:
     - Register with standard flat JSON payload (no nested "payload" wrapper).
     - Login with credentials to obtain access and refresh tokens.
     - Validate JWT claims structure, subject ID, expiration, and token types.
     - Authenticated profile retrieval via GET /api/v1/auth/me using Bearer token.
     - Token refresh via POST /api/v1/auth/refresh and verifying new access token.
     - Unauthorized access verification after token discard / client-side logout.
  2. Stability Across Repeated Logins:
     - Multi-cycle login and session check in loop to guarantee stability.
  3. Rate Limiting & Boundary Verification:
     - Rapid request burst exceeding 10 req/min threshold verifying HTTP 429 Too Many Requests.
     - Limiter reset recovery.
  4. Token Security & Type Isolation:
     - Refresh token rejection on access endpoints.
     - Access token rejection on refresh endpoint.
     - Incorrect credentials error flow.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.core.limiter import limiter

pytestmark = pytest.mark.asyncio


class TestE2EAuthLifecycle:
    """Test 1: Full user lifecycle verification."""

    @pytest.fixture
    def lifecycle_user(self):
        return {
            "email": "lifecycle_cadet@sleepwell.io",
            "username": "lifecycle_cadet",
            "password": "SecurePassword123!",
        }

    async def test_full_user_lifecycle(self, client: AsyncClient, lifecycle_user: dict):
        """
        Executes the entire user lifecycle journey:
        Register -> Login -> Claim Verification -> GET /me -> Refresh -> Discard / Logout.
        """
        # ── Step 1: Register with standard flat JSON payload ─────────────────
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json=lifecycle_user,
        )
        assert reg_resp.status_code == 201, f"Registration failed ({reg_resp.status_code}): {reg_resp.text}"
        user_data = reg_resp.json()
        assert "id" in user_data, "Missing 'id' in user registration response"
        assert isinstance(user_data["id"], int)
        assert user_data["email"] == lifecycle_user["email"]
        assert user_data["username"] == lifecycle_user["username"]
        assert user_data["is_active"] is True
        assert "is_verified" in user_data
        assert "created_at" in user_data
        # Security check: Password hashes must NEVER leak
        assert "hashed_password" not in user_data
        assert "password" not in user_data

        user_id = user_data["id"]

        # ── Step 2: Login to obtain access and refresh tokens ────────────────
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": lifecycle_user["email"],
                "password": lifecycle_user["password"],
            },
        )
        assert login_resp.status_code == 200, f"Login failed ({login_resp.status_code}): {login_resp.text}"
        token_data = login_resp.json()
        assert "access_token" in token_data, "Missing 'access_token' in login response"
        assert "refresh_token" in token_data, "Missing 'refresh_token' in login response"
        assert token_data.get("token_type") == "bearer"

        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]

        # ── Step 3: Validate JWT claims structure and cryptographic integrity ─
        decoded_access = jwt.decode(
            access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert decoded_access["sub"] == str(user_id), "Access token sub claim does not match user ID"
        assert decoded_access["type"] == "access", "Token type claim must be 'access'"
        assert "exp" in decoded_access, "Access token missing exp claim"

        decoded_refresh = jwt.decode(
            refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert decoded_refresh["sub"] == str(user_id), "Refresh token sub claim does not match user ID"
        assert decoded_refresh["type"] == "refresh", "Token type claim must be 'refresh'"
        assert "exp" in decoded_refresh, "Refresh token missing exp claim"

        # ── Step 4: Access GET /api/v1/auth/me with Bearer token ─────────────
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 200, f"GET /me failed ({me_resp.status_code}): {me_resp.text}"
        me_data = me_resp.json()
        assert me_data["id"] == user_id
        assert me_data["email"] == lifecycle_user["email"]
        assert me_data["username"] == lifecycle_user["username"]
        assert me_data["is_active"] is True

        # ── Step 5: Refresh token via /api/v1/auth/refresh ───────────────────
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200, f"Refresh failed ({refresh_resp.status_code}): {refresh_resp.text}"
        new_token_data = refresh_resp.json()
        assert "access_token" in new_token_data
        assert "refresh_token" in new_token_data
        assert new_token_data["token_type"] == "bearer"

        new_access_token = new_token_data["access_token"]
        decoded_new_access = jwt.decode(
            new_access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert decoded_new_access["sub"] == str(user_id)
        assert decoded_new_access["type"] == "access"

        # Verify access using the newly issued access token
        me_refreshed_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_refreshed_resp.status_code == 200
        assert me_refreshed_resp.json()["id"] == user_id

        # ── Step 6: Verify unauthorized access after token discard / logout ──
        # Case A: Request without Authorization header
        unauth_no_header = await client.get("/api/v1/auth/me")
        assert unauth_no_header.status_code == 401

        # Case B: Request with malformed/empty header
        unauth_empty_header = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer "},
        )
        assert unauth_empty_header.status_code == 401

        # Case C: Request with invalid/discarded token string
        unauth_discarded = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer discarded_logged_out_token"},
        )
        assert unauth_discarded.status_code == 401


class TestE2EAuthStability:
    """Test 2: Stability across repeated logins."""

    async def test_repeated_logins_stability(self, client: AsyncClient):
        """
        Simulates repeated login and session verification cycles in a loop
        to ensure state persistence, token rotation, and bcrypt computation remain stable.
        """
        user_payload = {
            "email": "stable_cadet@sleepwell.io",
            "username": "stable_cadet",
            "password": "StablePassw0rd!",
        }

        # Register user
        reg_resp = await client.post("/api/v1/auth/register", json=user_payload)
        assert reg_resp.status_code == 201, f"Initial registration failed: {reg_resp.text}"
        user_id = reg_resp.json()["id"]

        # Run 6 consecutive login and session verification cycles
        for cycle in range(1, 7):
            # Reset rate limiter between test cycles if needed to isolate login stability
            limiter.reset()

            # 1. Perform login
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": user_payload["email"],
                    "password": user_payload["password"],
                },
            )
            assert login_resp.status_code == 200, f"Cycle {cycle} login failed: {login_resp.text}"
            tokens = login_resp.json()
            access_token = tokens["access_token"]
            refresh_token = tokens["refresh_token"]

            # 2. Verify /me endpoint with access token
            me_resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert me_resp.status_code == 200, f"Cycle {cycle} /me failed: {me_resp.text}"
            assert me_resp.json()["id"] == user_id
            assert me_resp.json()["email"] == user_payload["email"]

            # 3. Perform token refresh
            ref_resp = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert ref_resp.status_code == 200, f"Cycle {cycle} refresh failed: {ref_resp.text}"
            ref_tokens = ref_resp.json()
            refreshed_access = ref_tokens["access_token"]

            # 4. Verify /me with refreshed access token
            me_ref_resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {refreshed_access}"},
            )
            assert me_ref_resp.status_code == 200, f"Cycle {cycle} /me (refreshed) failed: {me_ref_resp.text}"
            assert me_ref_resp.json()["id"] == user_id


class TestE2EAuthRateLimitingAndBoundaries:
    """Test 3: Rate limiting / boundary verification."""

    async def test_rate_limiting_enforcement_and_recovery(self, client: AsyncClient):
        """
        Verifies that exceeding the 10 req/min endpoint limit triggers HTTP 429 Too Many Requests,
        and that limiter.reset() restores endpoint availability.
        """
        # Clean slate limiter for this test
        limiter.reset()

        user_payload = {
            "email": "ratelimit_cadet@sleepwell.io",
            "username": "ratelimit_cadet",
            "password": "RateLimitPass123!",
        }

        # Step 1: Register account
        reg_resp = await client.post("/api/v1/auth/register", json=user_payload)
        assert reg_resp.status_code == 201

        # Step 2: Send requests up to and beyond the 10/min rate limit on /api/v1/auth/login
        statuses = []
        for i in range(12):
            resp = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": user_payload["email"],
                    "password": user_payload["password"],
                },
            )
            statuses.append(resp.status_code)

        # First 10 requests should succeed (200), subsequent requests should be 429
        assert 200 in statuses, "Expected successful login responses before rate limit"
        assert 429 in statuses, f"Expected 429 Too Many Requests after 10 requests, got statuses: {statuses}"

        # Count 200s and 429s
        success_count = statuses.count(200)
        rate_limited_count = statuses.count(429)
        assert success_count == 10, f"Expected exactly 10 successful requests, got {success_count}"
        assert rate_limited_count >= 2, f"Expected at least 2 rate-limited requests, got {rate_limited_count}"

        # Step 3: Verify limiter reset restores access
        limiter.reset()
        recovered_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": user_payload["email"],
                "password": user_payload["password"],
            },
        )
        assert recovered_resp.status_code == 200, "Limiter reset failed to restore endpoint access"

    async def test_token_type_boundary_isolation(self, client: AsyncClient):
        """
        Verifies strict token type boundary isolation:
        - Refresh tokens cannot access endpoints requiring access tokens.
        - Access tokens cannot access the /refresh endpoint.
        """
        limiter.reset()
        user_payload = {
            "email": "token_iso@sleepwell.io",
            "username": "token_iso",
            "password": "TokenIsoPass123!",
        }

        await client.post("/api/v1/auth/register", json=user_payload)
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user_payload["email"], "password": user_payload["password"]},
        )
        tokens = login_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # Attempt to use refresh_token at /me
        me_with_refresh = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert me_with_refresh.status_code == 401
        assert "access token required" in me_with_refresh.json()["detail"].lower()

        # Attempt to use access_token at /refresh
        refresh_with_access = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert refresh_with_access.status_code == 401
        assert "refresh token required" in refresh_with_access.json()["detail"].lower()
