"""
Authentication endpoints.

All auth routes are rate-limited more aggressively (10/min) to prevent
brute-force attacks.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.core.limiter import limiter
from app.db.models import User
from app.schemas.user import (
    TokenRefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
import logging
from datetime import timedelta

logger = logging.getLogger("sleepwell.auth")


router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pre-computed dummy hash used in login to prevent timing attacks.
# Computed once at startup so it's always a valid bcrypt hash.
_DUMMY_HASH = hash_password("dummy-constant-value-prevents-timing-oracle")


# ── Register ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
@limiter.limit("10/minute")
async def register(
    request: Request,
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Check duplicate username
    existing = await db.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken",
        )

    from fastapi.concurrency import run_in_threadpool
    hashed_pwd = await run_in_threadpool(hash_password, payload.password)

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hashed_pwd,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or username already exists",
        )
    await db.refresh(user)
    return user


# ── Login ────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT tokens",
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    from fastapi.concurrency import run_in_threadpool

    # Always run verify_password even if user is None to prevent timing attacks
    # that could reveal whether an email address is registered.
    password_ok = await run_in_threadpool(
        verify_password,
        payload.password,
        user.hashed_password if user else _DUMMY_HASH,
    )

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# ── Refresh Token ────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new token pair",
)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    token_data = decode_token(payload.refresh_token)

    if token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type – refresh token required",
        )

    user_id = int(token_data["sub"])

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# ── Current User ─────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
@limiter.limit("10/minute")
async def get_me(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# ── Password Reset ───────────────────────────────────────────────────────────

@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a password reset link",
)
@limiter.limit("5/minute")
async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        # Create a short-lived token (15 mins) specifically for password reset
        reset_token = create_access_token(
            subject=user.id,
            extra_claims={"type": "password_reset"},
            expires_delta=timedelta(minutes=15)
        )
        
        # In a real app, send an email here. For now, log it securely.
        logger.info("Password reset requested for user_id=%s. Token generated.", user.id)
        # Note: We don't print the token in production logs, this is just to simulate the email sending.
        print(f"--- MOCK EMAIL --- \\nTo: {user.email}\\nReset Token: {reset_token}\\n------------------")

    # Always return 202 to prevent email enumeration
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password using a valid token",
)
@limiter.limit("5/minute")
async def reset_password(request: Request, payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    # decode_token will raise 401 if invalid or expired
    token_data = decode_token(payload.token)

    if token_data.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type – password reset token required",
        )

    user_id = int(token_data["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user",
        )

    user.hashed_password = hash_password(payload.new_password)
    await db.commit()

    return {"message": "Password has been successfully reset."}
