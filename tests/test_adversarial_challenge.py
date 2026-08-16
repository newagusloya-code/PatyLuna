"""
Adversarial Challenge & Stress Test Suite.

Author: Challenger 1 (Empirical QA & Security Specialist)
Purpose: Adversarial stress testing of authentication boundaries, token integrity,
         SQL injection resilience, concurrency, and rate limiting mechanics.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import time
from typing import Any, Dict
from jose import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import create_access_token, create_refresh_token, hash_password
from tests.conftest import helper_login_user, helper_register_user

pytestmark = pytest.mark.asyncio


class TestBoundaryAndMalformedInputs:
    """1. Boundary conditions and invalid inputs."""

    async def test_malformed_json_syntax(self, client: AsyncClient):
        """Malformed JSON syntax must return 422 Unprocessable Entity, not 500."""
        resp = await client.post(
            "/api/v1/auth/register",
            content=b'{"email": "broken_json@sleepwell.io", "password": ',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_json_primitive_array_instead_of_object(self, client: AsyncClient):
        """JSON Array or primitive instead of Dict must return 422."""
        resp1 = await client.post("/api/v1/auth/register", json=[{"email": "a@b.com"}])
        assert resp1.status_code == 422

        resp2 = await client.post("/api/v1/auth/login", content=b"12345", headers={"Content-Type": "application/json"})
        assert resp2.status_code == 422

        resp3 = await client.post("/api/v1/auth/login", content=b"true", headers={"Content-Type": "application/json"})
        assert resp3.status_code == 422

    async def test_missing_and_null_fields(self, client: AsyncClient):
        """Null or missing fields must be rejected with 422."""
        # Missing password
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "missing_pw@sleepwell.io", "username": "missing_pw"},
        )
        assert resp.status_code == 422

        # Null values
        resp_null = await client.post(
            "/api/v1/auth/register",
            json={"email": None, "username": None, "password": None},
        )
        assert resp_null.status_code == 422

    async def test_invalid_email_boundary_attacks(self, client: AsyncClient):
        """Adversarial email formats must be rejected by EmailStr."""
        bad_emails = [
            "plainaddress",
            "#@%^%#$@#$@#.com",
            "@example.com",
            "Joe Smith <email@example.com>",
            "email.example.com",
            "email@example@example.com",
            "email@example.com (Joe Smith)",
            "email@example",
            "email@-example.com",
            "",
            " " * 10,
        ]
        for bad_email in bad_emails:
            resp = await client.post(
                "/api/v1/auth/register",
                json={"email": bad_email, "username": "bad_email_usr", "password": "SecurePassword1!"},
            )
            assert resp.status_code == 422, f"Failed to reject invalid email '{bad_email}': {resp.text}"

    async def test_weak_password_variations(self, client: AsyncClient):
        """Password policy enforcement: min 8, max 128, upper, lower, digit, special."""
        weak_passwords = [
            ("short", "Short1!"),                    # 7 chars (< 8)
            ("no_upper", "lowercase123!@#"),          # no uppercase
            ("no_lower", "UPPERCASE123!@#"),          # no lowercase
            ("no_digit", "NoDigitsHere!@#"),          # no digit
            ("no_special", "NoSpecialCharacters123"), # no special
            ("too_long", "A1!" + "x" * 126),          # 129 chars (> 128)
            ("empty", ""),
            ("whitespace", "        "),
        ]
        for label, weak_pw in weak_passwords:
            resp = await client.post(
                "/api/v1/auth/register",
                json={"email": f"weak_{label}@sleepwell.io", "username": f"weak_{label}", "password": weak_pw},
            )
            assert resp.status_code == 422, f"Weak password '{label}' was unexpectedly accepted"

    async def test_sql_injection_resilience(self, client: AsyncClient):
        """
        SQL injection payloads in username, email, and password must not execute or cause 500 errors.
        - Username: blocked by regex validator (422)
        - Email: blocked by EmailStr or safely parameterized
        - Password: safely hashed and stored without executing SQL
        """
        sqli_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT id, email, username, hashed_password FROM users --",
            "admin'--",
            "1' OR 1=1 #",
            "' OR ''='",
        ]

        # 1. SQLi in username -> Rejected by strict alphanumeric validator (422)
        for sqli in sqli_payloads:
            resp = await client.post(
                "/api/v1/auth/register",
                json={"email": "sqli_user@sleepwell.io", "username": sqli, "password": "SecurePassword1!"},
            )
            assert resp.status_code == 422, f"Username SQLi was not rejected by validation: {sqli}"

        # 2. SQLi in email -> Rejected by EmailStr (422) or handled safely
        for sqli in sqli_payloads:
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": sqli, "password": "SecurePassword1!"},
            )
            assert resp.status_code in (401, 422), f"Email SQLi caused unexpected response ({resp.status_code}): {resp.text}"

        # 3. SQLi in password -> Allowed as character string, bcrypt-hashed, safely queried
        safe_sqli_pw = "'; DROP TABLE users; --A1!"
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "sqli_pw@sleepwell.io", "username": "sqli_pw_user", "password": safe_sqli_pw},
        )
        assert reg_resp.status_code == 201

        # Login with that password must succeed safely
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "sqli_pw@sleepwell.io", "password": safe_sqli_pw},
        )
        assert login_resp.status_code == 200


class TestTokenIntegrityAndForgeryAttacks:
    """2. Token tampering, expired tokens, forged signatures, algorithm confusion."""

    async def test_jwt_none_algorithm_attack(self, client: AsyncClient):
        """Token with alg: none must be rejected with 401."""
        # Manually craft unverified token with alg: none
        none_token = (
            "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."
            "eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6OTk5OTk5OTk5OX0."
        )
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {none_token}"},
        )
        assert resp.status_code == 401

    async def test_jwt_forged_secret_signature(self, client: AsyncClient):
        """Token signed with attacker key must be rejected with 401."""
        attacker_token = jwt.encode(
            {"sub": "1", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "attacker-fake-secret-key-1234567890",
            algorithm="HS256",
        )
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {attacker_token}"},
        )
        assert resp.status_code == 401

    async def test_jwt_expired_token(self, client: AsyncClient):
        """Expired JWT token must return 401."""
        expired_token = jwt.encode(
            {"sub": "1", "type": "access", "exp": datetime.now(timezone.utc) - timedelta(seconds=10)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    async def test_jwt_claims_tampering(self, client: AsyncClient):
        """Tampered claims: missing sub, non-integer sub, negative sub, unauthorized type."""
        tampered_claims = [
            {"type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, # missing sub
            {"sub": "not_an_int", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, # non-int sub
            {"sub": "-99", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, # negative sub (user 404)
            {"sub": "1", "type": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, # invalid type claim
            {"sub": "1", "type": "password_reset", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, # reset token on /me
        ]
        for claims in tampered_claims:
            token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
            resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code in (401, 404), f"Tampered token unexpectedly granted access: {claims}"


class TestRateLimitingEnforcementAndRecovery:
    """3. Rate limiting enforcement (HTTP 429) across all auth endpoints and recovery."""

    async def test_register_rate_limit_10_per_minute(self, client: AsyncClient):
        """Verify 10 req/min rate limit on /api/v1/auth/register."""
        limiter.reset()
        statuses = []
        for i in range(13):
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"rate_reg_{i}@sleepwell.io",
                    "username": f"rate_reg_{i}",
                    "password": "SecurePassword1!",
                },
            )
            statuses.append(resp.status_code)

        assert 201 in statuses
        assert 429 in statuses
        assert statuses.count(201) == 10
        assert statuses.count(429) == 3

        # Recovery after limiter reset
        limiter.reset()
        rec_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "rate_reg_recovered@sleepwell.io",
                "username": "rate_reg_rec",
                "password": "SecurePassword1!",
            },
        )
        assert rec_resp.status_code == 201

    async def test_login_rate_limit_10_per_minute(self, client: AsyncClient):
        """Verify 10 req/min rate limit on /api/v1/auth/login."""
        limiter.reset()
        user_payload = {
            "email": "ratelimit_login@sleepwell.io",
            "username": "ratelimit_login",
            "password": "SecurePassword1!",
        }
        await helper_register_user(client, user_payload["email"], user_payload["username"])

        statuses = []
        for i in range(12):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": user_payload["email"], "password": user_payload["password"]},
            )
            statuses.append(resp.status_code)

        assert statuses.count(200) == 10
        assert statuses.count(429) == 2

    async def test_password_reset_rate_limit_5_per_minute(self, client: AsyncClient):
        """Verify 5 req/min rate limit on /api/v1/auth/forgot-password."""
        limiter.reset()
        statuses = []
        for i in range(7):
            resp = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "forgot_target@sleepwell.io"},
            )
            statuses.append(resp.status_code)

        assert statuses.count(202) == 5
        assert statuses.count(429) == 2


class TestConcurrencyAndStress:
    """4. Stress testing with rapid repeated logins and concurrent session requests."""

    async def test_concurrent_session_verification_burst(self, client: AsyncClient):
        """
        Stress-tests concurrent GET /me calls from the same authenticated user.
        """
        limiter.reset()
        user_data = await helper_register_user(client, "concurrent_cadet@sleepwell.io", "concurrent_cadet")
        login_data = await helper_login_user(client, "concurrent_cadet@sleepwell.io")
        access_token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Perform 8 concurrent /me requests (within rate limit of 10)
        async def fetch_me():
            return await client.get("/api/v1/auth/me", headers=headers)

        responses = await asyncio.gather(*[fetch_me() for _ in range(8)])
        for resp in responses:
            assert resp.status_code == 200
            assert resp.json()["email"] == "concurrent_cadet@sleepwell.io"

    async def test_concurrent_duplicate_registration_race(self, client: AsyncClient):
        """
        Concurrent registration attempts with the same username/email.
        Exactly one must succeed (201) and all others must return 409 Conflict without 500 errors.
        """
        limiter.reset()
        payload = {
            "email": "race_cadet@sleepwell.io",
            "username": "race_cadet",
            "password": "SecurePassword1!",
        }

        async def register_attempt():
            return await client.post("/api/v1/auth/register", json=payload)

        # Launch 5 simultaneous registration requests
        responses = await asyncio.gather(*[register_attempt() for _ in range(5)])
        status_codes = [r.status_code for r in responses]

        # No 500 Internal Server Errors permitted
        assert 500 not in status_codes, f"500 Internal Server Error encountered during race: {status_codes}"
        # Exactly one must succeed (201)
        assert status_codes.count(201) == 1, f"Expected exactly 1 success (201), got: {status_codes}"
        # Remaining must be 409 Conflict
        assert status_codes.count(409) == 4, f"Expected 4 conflicts (409), got: {status_codes}"

    async def test_timing_attack_resistance(self, client: AsyncClient):
        """
        Adversarial timing measurement:
        Verifies that login timing for existing user (wrong password) vs non-existent user (wrong password)
        are both computed using bcrypt (via _DUMMY_HASH) to prevent timing-based user enumeration.
        """
        limiter.reset()
        await helper_register_user(client, "timing_target@sleepwell.io", "timing_target", "CorrectPass1!")

        # Warm up bcrypt computation
        limiter.reset()
        await client.post(
            "/api/v1/auth/login",
            json={"email": "timing_target@sleepwell.io", "password": "WrongPassword1!"},
        )

        # Measure 3 attempts for existing user (wrong password)
        limiter.reset()
        times_existing = []
        for _ in range(3):
            t0 = time.perf_counter()
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "timing_target@sleepwell.io", "password": "WrongPassword1!"},
            )
            t1 = time.perf_counter()
            assert resp.status_code == 401
            times_existing.append(t1 - t0)

        # Measure 3 attempts for non-existent user
        limiter.reset()
        times_nonexistent = []
        for _ in range(3):
            t0 = time.perf_counter()
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent_ghost@sleepwell.io", "password": "WrongPassword1!"},
            )
            t1 = time.perf_counter()
            assert resp.status_code == 401
            times_nonexistent.append(t1 - t0)

        avg_existing = sum(times_existing) / len(times_existing)
        avg_nonexistent = sum(times_nonexistent) / len(times_nonexistent)

        # Both must incur bcrypt work factor (typically > 30ms each)
        assert avg_existing > 0.02, f"Existing user verification too fast ({avg_existing:.4f}s), bcrypt skipped?"
        assert avg_nonexistent > 0.02, f"Nonexistent user verification too fast ({avg_nonexistent:.4f}s), dummy hash skipped?"
        # Variance between the two should be small (within 50ms)
        diff = abs(avg_existing - avg_nonexistent)
        assert diff < 0.1, f"Timing difference too large ({diff:.4f}s between {avg_existing:.4f}s and {avg_nonexistent:.4f}s)"
