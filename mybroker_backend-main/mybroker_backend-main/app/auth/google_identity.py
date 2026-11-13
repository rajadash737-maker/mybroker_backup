"""Google OAuth ID-token verification for backend authentication."""

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from email_validator import EmailNotValidError, validate_email

from app.core.config import settings


def verify_google_id_token(raw_token: str) -> dict[str, Any]:
    """Verify a Google OAuth ID token and return its trusted identity claims."""
    audiences = settings.google_oauth_client_ids
    if not audiences:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured",
        )
    if not raw_token or not raw_token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google ID token")

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        request = google_requests.Request()
        claims = None
        # google-auth validates signature, issuer, expiry, and the supplied audience.
        for audience in audiences:
            try:
                claims = id_token.verify_oauth2_token(raw_token, request, audience=audience)
                break
            except ValueError:
                continue
        if claims is None:
            raise ValueError("Token verification failed")

        issuer = claims.get("iss")
        if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
            raise ValueError("Invalid issuer")

        # Enforce these claims explicitly as defense in depth and for clarity.
        token_audiences = claims.get("aud")
        token_audiences = {token_audiences} if isinstance(token_audiences, str) else set(token_audiences or [])
        if not token_audiences.intersection(audiences):
            raise ValueError("Invalid audience")
        exp = claims.get("exp")
        if not isinstance(exp, (int, float)) or exp <= datetime.now(timezone.utc).timestamp():
            raise ValueError("Expired token")
        email = claims.get("email")
        if not isinstance(email, str) or not email.strip():
            raise ValueError("Missing or invalid email")
        try:
            validate_email(email.strip(), check_deliverability=False)
        except EmailNotValidError as exc:
            raise ValueError("Missing or invalid email") from exc
        if claims.get("email_verified") is not True:
            raise ValueError("Email is not verified")
        return claims
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        ) from exc
