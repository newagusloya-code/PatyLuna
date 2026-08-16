# Project: Teamwork Auth Debugging & E2E Verification

## Architecture
- Framework: FastAPI with Pydantic v2 and SlowAPI rate limiting
- Core Auth Endpoint: `app/api/v1/endpoints/auth.py`
- Test Infrastructure: `pytest`, `pytest-asyncio`, `httpx` (AsyncClient with ASGITransport)
- Root Cause Identified: PEP 563 `from __future__ import annotations` stringifies annotations; `@limiter.limit` decorator moves wrapper `__globals__` to `slowapi.extension`, causing unresolved `ForwardRef` in Pydantic v2 and falling back to expecting nested `{"payload": {...}}` instead of flat JSON.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Standard JSON Register | `POST /api/v1/auth/register` accepts flat JSON `{"email", "username", "password"}` | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Standard JSON Login | `POST /api/v1/auth/login` accepts flat JSON `{"email", "password"}` | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Standard JSON Refresh | `POST /api/v1/auth/refresh` accepts flat JSON `{"refresh_token"}` | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Session Verification | `GET /api/v1/auth/me` with Bearer token returns current user profile | M1 | ORIGINAL_REQUEST §R2 |
| 5 | E2E Registration & Login Test | Automated script registers fresh user and logs in | M2 | ORIGINAL_REQUEST §R2 |
| 6 | E2E Session & Logout Test | Automated script verifies `/me` and token discard/logout | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Multi-cycle Login Stability Test | Repeated login testing verifying rate limit & token stability | M2 | ORIGINAL_REQUEST §R2 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 0 | Survey | Codebase exploration and root cause identification | None | DONE |
| 1 | Auth Endpoint & Test Fixture Fix | Fix `app/api/v1/endpoints/auth.py` and `tests/conftest.py` table teardown | M0 | IN_PROGRESS |
| 2 | E2E Verification Suite | Implement `tests/test_e2e_auth_lifecycle.py` with complete lifecycle tests | M1 | IN_PROGRESS |
| 3 | Multi-Agent Review & Hardening | Reviewers (2), Challengers (2), and Forensic Auditor (1) | M1, M2 | PLANNED |

## Interface Contracts
### Auth Endpoints
- `POST /api/v1/auth/register`: Body `{ "email": "...", "username": "...", "password": "..." }` -> `201 Created` with UserResponse
- `POST /api/v1/auth/login`: Body `{ "email": "...", "password": "..." }` -> `200 OK` `{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }`
- `POST /api/v1/auth/refresh`: Body `{ "refresh_token": "..." }` -> `200 OK` `{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }`
- `GET /api/v1/auth/me`: Header `Authorization: Bearer <access_token>` -> `200 OK` `{ "id": ..., "email": "...", "username": "...", "is_active": true }`

## Code Layout
- `app/api/v1/endpoints/auth.py`: Primary endpoint implementation
- `tests/conftest.py`: Test fixtures and database lifecycle
- `tests/test_auth.py`: Unit and route tests
- `tests/test_e2e_auth_lifecycle.py`: Dedicated E2E lifecycle and stability verification
