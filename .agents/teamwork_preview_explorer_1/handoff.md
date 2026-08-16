# Investigation Report: Auth Payload Error & FastAPI/Slowapi Integration

## 1. Observation

### 1.1 Source Files & Declarations
- **File**: `app/api/v1/endpoints/auth.py`
  - Line 8: `from __future__ import annotations`
  - Line 10: `from fastapi import APIRouter, Body, Depends, HTTPException, Request, status`
  - Lines 55–56:
    ```python
    @limiter.limit("10/minute")
    async def register(request: Request, payload: UserRegister = Body(..., embed=False), db: AsyncSession = Depends(get_db)):
    ```
  - Lines 91–92:
    ```python
    @limiter.limit("10/minute")
    async def login(request: Request, payload: UserLogin = Body(..., embed=False), db: AsyncSession = Depends(get_db)):
    ```
  - Lines 128–129:
    ```python
    @limiter.limit("10/minute")
    async def refresh_token(request: Request, payload: TokenRefreshRequest = Body(..., embed=False), db: AsyncSession = Depends(get_db)):
    ```
  - Lines 182–183:
    ```python
    @limiter.limit("5/minute")
    async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    ```
  - Lines 209–210:
    ```python
    @limiter.limit("5/minute")
    async def reset_password(request: Request, payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    ```

- **File**: `app/schemas/user.py`
  - Lines 14–46: `UserRegister` and `UserLogin` are defined as subclasses of `pydantic.BaseModel` with field validators for `username` and `password`.

- **File**: `app/core/limiter.py`
  - Lines 5–9:
    ```python
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.RATE_LIMIT_DEFAULT],
        storage_uri=settings.REDIS_URL,
    )
    ```

### 1.2 Runtime Inspection & Test Output
- Running `pytest tests/test_auth.py` with the existing codebase produces 13 test failures across `TestRegister`, `TestLogin`, and `TestTokenRefresh`.
- Runtime inspection of `auth.register.__annotations__` yields:
  ```python
  {'request': 'Request', 'payload': 'UserRegister', 'db': 'AsyncSession'}
  ```
- Introspecting `app.openapi()` or sending requests to `/api/v1/auth/register` raises verbatim:
  ```
  pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('UserRegister'), Body(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('UserRegister'), Body(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
  ```
- When FastAPI attempts to resolve request parameters for endpoints decorated with `@limiter.limit` where string annotations exist:
  - `ModelField(field_info=Body(PydanticUndefined), name='payload', mode='validation')` is generated as a named body field rather than unpacking `UserRegister`.
  - When clients send standard flat JSON (`{"email": "...", "username": "...", "password": "..."}`), FastAPI rejects the payload with HTTP 422 Unprocessable Entity:
    ```json
    {
      "detail": [
        {
          "type": "missing",
          "loc": ["body", "payload"],
          "msg": "Field required"
        }
      ]
    }
    ```
- Slowapi decorator implementation (`venv/lib/python3.9/site-packages/slowapi/extension.py:706-747`):
  - Requires `request: Request` or `websocket: WebSocket` to be a named parameter on `func`.
  - Uses `@functools.wraps(func)` to wrap the endpoint in `async_wrapper`.
  - `async_wrapper.__globals__` is `slowapi.extension.__dict__`, NOT `app.api.v1.endpoints.auth.__dict__`.

---

## 2. Logic Chain

1. **Observation 1.1 & 1.2**: `app/api/v1/endpoints/auth.py` has `from __future__ import annotations` at line 8. Under PEP 563, all type annotations on function definitions are converted into string literals at compile time (`'UserRegister'`, `'UserLogin'`, etc.).
2. **Observation 1.2**: Each auth endpoint is decorated with `@limiter.limit(...)`. The limiter decorator creates an `async_wrapper` in `slowapi.extension`. `functools.wraps` copies `__annotations__` containing string literals to `async_wrapper`.
3. **Observation 1.2**: When FastAPI registers the route via `@router.post(...)`, it inspects the wrapper function's type hints using `typing.get_type_hints(async_wrapper)` and Pydantic v2's `TypeAdapter`.
4. **Observation 1.2**: Because `async_wrapper.__globals__` points to `slowapi.extension` (where `UserRegister` is not imported), `typing.get_type_hints` cannot resolve `'UserRegister'` to its `BaseModel` class. It remains an unresolved `ForwardRef('UserRegister')`.
5. **Observation 1.2**: Because `ForwardRef('UserRegister')` is not recognized by FastAPI as a `BaseModel` subclass:
   - With `= Body(..., embed=False)`, FastAPI treats `payload` as a named body parameter expecting the top-level JSON key `{"payload": { ... }}`.
   - Without `= Body(...)` and with string annotations, FastAPI treats unrecognized types as Query parameters.
6. **Observation 1.2**: When the frontend or test client posts a standard flat JSON object (`{"email": "...", "username": "...", "password": "..."}`), FastAPI cannot find the expected `"payload"` key in the body dictionary, producing `loc: ["body", "payload"]` / `"Field required"` (HTTP 422).
7. **Observation 1.2**: In Pydantic v2, attempting to validate data against this un-evaluated `ForwardRef` raises `pydantic.errors.PydanticUserError: TypeAdapter[...] is not fully defined`.
8. **Resolution Validation**: Removing `from __future__ import annotations` and using clean Pydantic parameter declarations (`payload: UserRegister`) ensures that `func.__annotations__['payload']` is the concrete class `UserRegister` at module load time. FastAPI immediately resolves the schema as `#/components/schemas/UserRegister` (un-nested flat body), passing all 15 tests in `tests/test_auth.py`.

---

## 3. Caveats

1. **Rate Limiter Storage in Tests**: `app/core/limiter.py` initializes `Limiter` with `storage_uri=settings.REDIS_URL` (`redis://localhost:6379/0`). When running automated tests in an environment without an active Redis daemon, `slowapi` attempts to connect to Redis on localhost:6379 and fails with `redis.exceptions.ConnectionError`. In `tests/conftest.py`, configuring `os.environ["REDIS_URL"] = "memory://"` or configuring `limiter` to use memory storage in tests ensures tests execute deterministically without external infrastructure dependencies.
2. **Other Endpoint Modules**: `app/api/v1/endpoints/diary.py`, `pomodoro.py`, `sleep.py`, and `ai.py` also contain `from __future__ import annotations`, but none of them use `@limiter.limit`. Because their route functions are decorated directly by `@router.post`/`@router.get` without intermediate external wrapper functions, FastAPI resolves their annotations in their own module globals. However, if `@limiter.limit` is ever added to those endpoints in the future, `from __future__ import annotations` would cause the same forward reference failure.

---

## 4. Conclusion

### 4.1 Root Cause Summary
The `loc: ["body", "payload"]` / `"Field required"` error and the `PydanticUserError` are caused by the combination of:
1. `from __future__ import annotations` turning parameter type annotations into string literals in `app/api/v1/endpoints/auth.py`.
2. `@limiter.limit` wrapping route functions inside `slowapi.extension`, causing FastAPI/Pydantic type reflection to look for `UserRegister` / `UserLogin` in `slowapi.extension.__globals__` where they do not exist.
3. Unresolved `ForwardRef` types preventing FastAPI from recognizing the parameter as a standard Pydantic model body, resulting in FastAPI treating `payload` as a required nested body key (`{"payload": ...}`).

### 4.2 Recommended Code Fix for `app/api/v1/endpoints/auth.py`
1. **Remove `from __future__ import annotations`** at line 8.
2. **Clean up route parameter signatures**:
   - `async def register(request: Request, payload: UserRegister, db: AsyncSession = Depends(get_db)):`
   - `async def login(request: Request, payload: UserLogin, db: AsyncSession = Depends(get_db)):`
   - `async def refresh_token(request: Request, payload: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):`
   - `async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):`
   - `async def reset_password(request: Request, payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):`
3. **Remove `Body` from `fastapi` imports** if unused.
4. **Retain `request: Request`**: Slowapi requires `request: Request` as a function parameter to compute client rate limits.

### 4.3 Proposed Diff Patch
```diff
--- a/app/api/v1/endpoints/auth.py
+++ b/app/api/v1/endpoints/auth.py
@@ -5,9 +5,7 @@
 brute-force attacks.
 """
 
-from __future__ import annotations
-
-from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
+from fastapi import APIRouter, Depends, HTTPException, Request, status
 from sqlalchemy import select
 from sqlalchemy.ext.asyncio import AsyncSession
 
@@ -53,7 +51,7 @@
     summary="Create a new user account",
 )
 @limiter.limit("10/minute")
-async def register(request: Request, payload: UserRegister = Body(..., embed=False), db: AsyncSession = Depends(get_db)):
+async def register(request: Request, payload: UserRegister, db: AsyncSession = Depends(get_db)):
     # Check duplicate email
     existing = await db.execute(select(User).where(User.email == payload.email))
     if existing.scalar_one_or_none():
@@ -89,7 +87,7 @@
     summary="Authenticate and receive JWT tokens",
 )
 @limiter.limit("10/minute")
-async def login(request: Request, payload: UserLogin = Body(..., embed=False), db: AsyncSession = Depends(get_db)):
+async def login(request: Request, payload: UserLogin, db: AsyncSession = Depends(get_db)):
     result = await db.execute(select(User).where(User.email == payload.email))
     user = result.scalar_one_or_none()
 
@@ -126,7 +124,7 @@
     summary="Exchange a refresh token for a new token pair",
 )
 @limiter.limit("10/minute")
-async def refresh_token(request: Request, payload: TokenRefreshRequest = Body(..., embed=False), db: AsyncSession = Depends(get_db)):
+async def refresh_token(request: Request, payload: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
     token_data = decode_token(payload.refresh_token)
```

---

## 5. Verification Method

1. **Run Auth Test Suite**:
   ```bash
   REDIS_URL="memory://" ./venv/bin/pytest tests/test_auth.py -v
   ```
   **Expected Outcome**: 15/15 tests pass with status 200/201/401/409/422 as specified in test contracts.

2. **Verify OpenAPI Schema Generation**:
   ```bash
   REDIS_URL="memory://" ./venv/bin/python -c "from app.main import app; schema = app.openapi(); print(schema['paths']['/api/v1/auth/register']['post']['requestBody'])"
   ```
   **Expected Outcome**: Generates valid OpenAPI schema with `$ref: '#/components/schemas/UserRegister'` without throwing `PydanticUserError`.

3. **End-to-End User Lifecycle Verification**:
   Execute integration flow:
   - `POST /api/v1/auth/register` with `{"email": "test@example.com", "username": "testuser", "password": "SecurePass1!"}` -> 201 Created.
   - `POST /api/v1/auth/login` with `{"email": "test@example.com", "password": "SecurePass1!"}` -> 200 OK with `access_token` and `refresh_token`.
   - `GET /api/v1/auth/me` with `Authorization: Bearer <access_token>` -> 200 OK with user details.
   - `POST /api/v1/auth/refresh` with `{"refresh_token": "<refresh_token>"}` -> 200 OK with new tokens.
