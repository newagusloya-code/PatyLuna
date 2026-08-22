"""
Security utilities for AI Agents:
- Automatic PII scrubber (removes emails, phone numbers, SSNs, addresses, names before transmission).
- AES-256-GCM zero-knowledge symmetric encryption/decryption for local storage.
"""

import base64
import os
import re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ── PII Sanitizer ────────────────────────────────────────────────────────────

_PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"(?:(?<=\s)|^|\()\+(?:[0-9][\s.-]?|\(\d{1,4}\)[\s.-]?){6,14}[0-9]\b"), "[PHONE]"),
    (re.compile(r"(?:\b1[\s.-]?)?(?:\(\d{3}\)|\b[2-9]\d{2})[\s.-]?\d{3}[\s.-]?\d{4}\b"), "[PHONE]"),
    (re.compile(r"\b\d{1,5}\s+[A-Za-z0-9.]+(?:\s+[A-Za-z0-9.]+){0,4},\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?\b"), "[ADDRESS]"),
    (re.compile(r"\b(?:Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"), "[NAME]"),
    (re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"), "[NAME]"),
]


def scrub_pii(text: str) -> str:
    """Scrub personally identifiable information from text before sending to AI APIs."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── AES-256-GCM Encryption Vault ───────────────────────────────────────────

def encrypt_text(plaintext: str, key_hex: str) -> str:
    """
    Encrypts a string using AES-256-GCM.
    Returns: base64-encoded string containing [12-byte IV + ciphertext + 16-byte Auth Tag].
    """
    key = bytes.fromhex(key_hex)
    aesgcm = AESGCM(key)
    iv = os.urandom(12)  # NIST recommended 96-bit nonce
    ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    return base64.b64encode(iv + ciphertext).decode("utf-8")


def decrypt_text(encrypted_b64: str, key_hex: str) -> str:
    """
    Decrypts an AES-256-GCM encrypted base64 payload.
    Raises ValueError if tampering or authentication tag mismatch occurs.
    """
    key = bytes.fromhex(key_hex)
    raw = base64.b64decode(encrypted_b64)
    iv = raw[:12]
    ciphertext = raw[12:]
    aesgcm = AESGCM(key)
    decrypted_bytes = aesgcm.decrypt(iv, ciphertext, None)
    return decrypted_bytes.decode("utf-8")
