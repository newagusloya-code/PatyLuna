"""
Security utilities – the "Vault" layer.

Responsibilities:
  1. Password hashing  (bcrypt via passlib)
  2. JWT access / refresh token creation & verification
  3. AES-256-GCM encryption / decryption for diary entries
  4. Dependency helpers for FastAPI route protection
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ────────────────────────────────────────────────────────────────────────────
# 1. Password Hashing
# ────────────────────────────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if *plain* matches the *hashed* password."""
    return _pwd_context.verify(plain, hashed)


# ────────────────────────────────────────────────────────────────────────────
# 2. JWT Tokens
# ────────────────────────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def create_access_token(
    subject: Union[str, int],
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a short-lived access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: Union[str, int]) -> str:
    """Create a long-lived refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Raises ``HTTPException 401`` on any failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("sub") is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


# ────────────────────────────────────────────────────────────────────────────
# 3. AES-256-GCM Encryption (Diary Entries)
# ────────────────────────────────────────────────────────────────────────────

def _get_aes_key() -> bytes:
    """
    Derive the 256-bit AES key from the configured ENCRYPTION_KEY.

    The key should be a 32-byte value, stored as a 64-char hex string in the
    environment. If missing, invalid, or arbitrary string, falls back safely to
    SHA-256 derived key (from raw string or JWT_SECRET_KEY).
    """
    import hashlib
    raw = settings.ENCRYPTION_KEY
    if not raw or len(raw.strip()) < 16:
        # Safe fallback derived from JWT secret key to prevent 500 internal server errors
        return hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
    try:
        key = bytes.fromhex(raw.strip())
        if len(key) == 32:
            return key
        return hashlib.sha256(raw.encode("utf-8")).digest()
    except ValueError:
        return hashlib.sha256(raw.encode("utf-8")).digest()



def encrypt_text(plaintext: str) -> bytes:
    """
    Encrypt *plaintext* with AES-256-GCM.

    Returns ``nonce (12 bytes) || ciphertext+tag``.
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ct  # store both together


def decrypt_text(blob: bytes) -> str:
    """
    Decrypt a blob produced by :func:`encrypt_text`.
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce, ct = blob[:12], blob[12:]
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")


# ────────────────────────────────────────────────────────────────────────────
# 4. FastAPI Dependencies
# ────────────────────────────────────────────────────────────────────────────

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """
    Dependency that extracts and returns the authenticated user's ID from the
    JWT bearer token.  Raises 401 on failure.
    """
    payload = decode_token(token)
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type – access token required",
        )
    try:
        return int(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
