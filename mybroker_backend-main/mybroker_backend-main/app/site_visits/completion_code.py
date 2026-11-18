"""Cryptographic helpers for Site Visit completion codes."""

import base64
import hashlib
import hmac
import os
import re
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


class CompletionCodeConfigurationError(RuntimeError):
    """Raised when dedicated OTP key material is missing or malformed."""


ENCRYPTION_KEY_ENV = "SITE_VISIT_OTP_ENCRYPTION_KEY"
HMAC_KEY_ENV = "SITE_VISIT_OTP_HMAC_KEY"


def _decode_hex_key(value: str | None) -> bytes | None:
    if not isinstance(value, str) or not re.fullmatch(r"(?:[0-9a-fA-F]{2})+", value):
        return None
    try:
        return bytes.fromhex(value)
    except ValueError:
        return None


def completion_code_configuration_issues() -> tuple[str, ...]:
    """Return only environment variable names whose key configuration is invalid."""
    encryption_key = _decode_hex_key(settings.site_visit_otp_encryption_key)
    hmac_key = _decode_hex_key(settings.site_visit_otp_hmac_key)
    issues: list[str] = []
    if encryption_key is None or len(encryption_key) != 32:
        issues.append(ENCRYPTION_KEY_ENV)
    if hmac_key is None or len(hmac_key) < 32:
        issues.append(HMAC_KEY_ENV)
    if encryption_key is not None and hmac_key is not None and encryption_key == hmac_key:
        issues.extend((ENCRYPTION_KEY_ENV, HMAC_KEY_ENV))
    return tuple(dict.fromkeys(issues))


def _keys() -> tuple[bytes, bytes]:
    if completion_code_configuration_issues():
        raise CompletionCodeConfigurationError from None
    encryption_key = bytes.fromhex(settings.site_visit_otp_encryption_key)
    hmac_key = bytes.fromhex(settings.site_visit_otp_hmac_key)
    return encryption_key, hmac_key


def generate_completion_code() -> str:
    """Generate a six digit string, retaining any leading zeroes."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_completion_code(request_id: int, code: str) -> str:
    _, key = _keys()
    message = f"site-visit-completion:v1:{request_id}:{code}".encode("ascii")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_completion_code_hash(request_id: int, code: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_completion_code(request_id, code), expected_hash)


def encrypt_completion_code(request_id: int, code: str) -> str:
    key, _ = _keys()
    nonce = os.urandom(12)
    aad = f"site-visit-completion:v1:{request_id}".encode("ascii")
    ciphertext = AESGCM(key).encrypt(nonce, code.encode("ascii"), aad)
    return "v1:" + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_completion_code(request_id: int, encrypted: str) -> str:
    key, _ = _keys()
    if not encrypted.startswith("v1:"):
        raise ValueError("Unsupported completion-code ciphertext version")
    try:
        payload = base64.urlsafe_b64decode(encrypted[3:].encode("ascii"))
        nonce, ciphertext = payload[:12], payload[12:]
        if len(nonce) != 12 or len(ciphertext) < 16:
            raise ValueError
        aad = f"site-visit-completion:v1:{request_id}".encode("ascii")
        return AESGCM(key).decrypt(nonce, ciphertext, aad).decode("ascii")
    except Exception:
        # Do not expose cryptography/provider details or ciphertext to callers.
        raise ValueError("Completion code could not be decrypted") from None
