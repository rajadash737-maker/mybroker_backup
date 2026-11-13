from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets

import jwt
from jwt import InvalidTokenError

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
_environment = os.getenv("ENVIRONMENT", "local").strip().lower()


def _validate_signing_secret(secret: str, environment: str) -> None:
    if environment.strip().lower() in {"prod", "production"} and (
        secret == "change-me-in-production" or len(secret.encode("utf-8")) < 32
    ):
        raise RuntimeError("Production requires a JWT_SECRET_KEY of at least 32 bytes")


_validate_signing_secret(JWT_SECRET_KEY, _environment)
JWT_ISSUER = os.getenv("JWT_ISSUER", "mybroker-backend")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "mybroker-client")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "10"))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _build_claims(user_id: int, token_type: str, expires_delta: timedelta, jti: str | None = None) -> dict:
    now = _utcnow()
    return {
        "sub": str(user_id),
        "type": token_type,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": jti or secrets.token_urlsafe(24),
    }


def create_access_token(user_id: int) -> str:
    claims = _build_claims(
        user_id=user_id,
        token_type="access",
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return jwt.encode(claims, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int, jti: str | None = None) -> tuple[str, str]:
    claims = _build_claims(
        user_id=user_id,
        token_type="refresh",
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        jti=jti,
    )
    token = jwt.encode(claims, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, claims["jti"]


def decode_token(token: str, expected_type: str | None = None) -> dict:
    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
    )
    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise InvalidTokenError("Invalid token type")
    return payload


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
