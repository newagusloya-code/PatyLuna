# Project Plan: Teamwork Auth Debugging & E2E Verification

## Objective
Fix the FastAPI `loc: ["body", "payload"]` / "Field required" payload error in `app/api/v1/endpoints/auth.py`, and implement a robust automated E2E test suite covering user registration, login, `/api/v1/auth/me` verification, logout/token discard, and repeated login stress testing.

## Plan Steps
1. **Survey & Technical Investigation (Phase 0)**
   - Dispatch 3 Explorers in parallel to inspect:
     - `app/api/v1/endpoints/auth.py`, schemas (`app/schemas/`), and slowapi rate limiting decorators.
     - Existing tests, environment setup, DB dependencies, and FastAPI application structure.
     - Auth flow requirements, JWT generation, and integration test runner options.
2. **Decomposition & Architecture Specification**
   - Synthesize survey findings into `PROJECT.md`.
   - Define exact interface contracts, payload models, and test requirements.
3. **Milestone 1: Fix Auth Endpoints (Phase 1)**
   - Dispatch Worker to implement the fix in `app/api/v1/endpoints/auth.py` (and any related schema updates).
   - Ensure `request: Request` parameter positioning and Pydantic body model parameter conventions are strictly aligned with FastAPI and SlowAPI best practices without nesting "payload".
4. **Milestone 2: Build Automated E2E Auth Verification Suite (Phase 2)**
   - Dispatch Worker / Test Writer to implement an end-to-end test script using `pytest` and `httpx` (or TestClient).
   - Execute full lifecycle: register -> login -> /me -> logout -> repeat login multiple times.
5. **Verification & Hardening (Phase 3)**
   - Dispatch 2 Reviewers independently to verify code quality, contract conformance, and error handling.
   - Dispatch 2 Challengers to perform adversarial edge case testing, invalid payload rejection, token expiry/tampering, and rate limit stress tests.
   - Dispatch 1 Forensic Auditor (`teamwork_preview_auditor`) to verify zero integrity violations / no dummy or hardcoded mocks.
6. **Gate Evaluation & Final Delivery (Phase 4)**
   - Evaluate all gate criteria strictly.
   - Produce final completion report and notify caller.
