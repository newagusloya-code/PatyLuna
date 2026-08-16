"""
Tests for cryptographic operations (AES-256-GCM, password hashing, JWTs).
"""

from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag

from app.core.config import settings
from app.core.security import (
    _get_aes_key,
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_text,
    encrypt_text,
    hash_password,
    verify_password,
)


class TestAES256GCM:
    def test_encrypt_decrypt_roundtrip(self):
        secret = "Personal thoughts: Today was productive and calm."
        encrypted = encrypt_text(secret)
        assert isinstance(encrypted, bytes)
        assert encrypted != secret.encode("utf-8")
        assert len(encrypted) > 12  # 12-byte nonce + ciphertext + 16-byte tag

        decrypted = decrypt_text(encrypted)
        assert decrypted == secret

    def test_encrypt_unique_nonces(self):
        secret = "Same text twice"
        enc1 = encrypt_text(secret)
        enc2 = encrypt_text(secret)
        assert enc1 != enc2, "Identical plaintexts MUST have different ciphertexts (random IV/nonce)"

    def test_decrypt_tampered_ciphertext(self):
        secret = "Confidential diary entry"
        encrypted = bytearray(encrypt_text(secret))
        # Tamper with the last byte
        encrypted[-1] ^= 0xFF
        with pytest.raises(InvalidTag):
            decrypt_text(bytes(encrypted))

    def test_key_derivation_hex_32_bytes(self, monkeypatch):
        # 64-char hex key (32 bytes)
        hex_key = "a" * 64
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", hex_key)
        key = _get_aes_key()
        assert len(key) == 32
        assert key == bytes.fromhex(hex_key)

    def test_key_derivation_fallback_when_empty_or_none(self, monkeypatch):
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", "")
        key = _get_aes_key()
        assert len(key) == 32

        # Roundtrip works even with fallback key
        secret = "Secret with fallback key"
        enc = encrypt_text(secret)
        assert decrypt_text(enc) == secret

    def test_key_derivation_fallback_when_short(self, monkeypatch):
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", "shortkey123")
        key = _get_aes_key()
        assert len(key) == 32

        secret = "Short key fallback"
        enc = encrypt_text(secret)
        assert decrypt_text(enc) == secret

    def test_key_derivation_fallback_when_non_hex_passphrase(self, monkeypatch):
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", "This is an arbitrary passphrase string with non-hex chars!")
        key = _get_aes_key()
        assert len(key) == 32

        secret = "Passphrase encryption test"
        enc = encrypt_text(secret)
        assert decrypt_text(enc) == secret

    def test_key_derivation_fallback_when_hex_wrong_length(self, monkeypatch):
        # 32-char hex (16 bytes, not 32 bytes)
        monkeypatch.setattr(settings, "ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef")
        key = _get_aes_key()
        assert len(key) == 32

        secret = "16-byte hex fallback test"
        enc = encrypt_text(secret)
        assert decrypt_text(enc) == secret



class TestPasswordHashing:
    def test_password_hash_and_verify(self):
        raw = "MySecurePassword123!"
        hashed = hash_password(raw)
        assert hashed != raw
        assert verify_password(raw, hashed) is True
        assert verify_password("WrongPassword123!", hashed) is False


class TestJWTTokenSecurity:
    def test_access_token_creation_and_decode(self):
        token = create_access_token(subject=42)
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_refresh_token_creation_and_decode(self):
        token = create_refresh_token(subject=42)
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["type"] == "refresh"
