"""Encryption helpers for buyer UPI details stored in the Site Visit refund ledger."""

import base64
import os
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


class RefundEncryptionConfigurationError(RuntimeError):
    pass


def _key() -> bytes:
    value = settings.site_visit_refund_encryption_key
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise RefundEncryptionConfigurationError from None
    return bytes.fromhex(value)


def encrypt_buyer_upi(refund_id: int, upi_id: str) -> str:
    nonce = os.urandom(12)
    aad = f"mybrokerr:site-visit-refund:v1:{refund_id}".encode("ascii")
    ciphertext = AESGCM(_key()).encrypt(nonce, upi_id.encode("utf-8"), aad)
    return "v1:" + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_buyer_upi(refund_id: int, encrypted: str) -> str:
    if not encrypted.startswith("v1:"):
        raise ValueError("Unsupported refund UPI ciphertext version")
    try:
        value = base64.urlsafe_b64decode(encrypted[3:].encode("ascii"))
        nonce, ciphertext = value[:12], value[12:]
        aad = f"mybrokerr:site-visit-refund:v1:{refund_id}".encode("ascii")
        return AESGCM(_key()).decrypt(nonce, ciphertext, aad).decode("utf-8")
    except RefundEncryptionConfigurationError:
        raise
    except Exception:
        raise ValueError("Refund UPI details could not be decrypted") from None
