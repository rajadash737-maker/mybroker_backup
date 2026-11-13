import json
import logging
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings

logger = logging.getLogger(__name__)


def _load_credentials() -> credentials.Base:
    raw_json = settings.firebase_credentials_json.strip()
    if raw_json:
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid FIREBASE_CREDENTIALS_JSON") from exc
        return credentials.Certificate(payload)

    cred_path = Path(settings.firebase_credentials_path)
    if not cred_path.is_absolute():
        cred_path = Path.cwd() / cred_path
    if not cred_path.exists():
        raise FileNotFoundError(f"Firebase credentials file not found: {cred_path}")
    return credentials.Certificate(str(cred_path))


def _ensure_firebase_initialized() -> None:
    if firebase_admin._apps:
        return
    cred = _load_credentials()
    firebase_admin.initialize_app(cred)


def send_notification(token: str, title: str, body: str, data: dict[str, str] | None = None) -> dict[str, Any]:
    if not token:
        logger.debug("FCM token missing; skipping notification")
        return {"success": False, "skipped": True, "error": "missing_token"}

    try:
        _ensure_firebase_initialized()
    except Exception as exc:  # noqa: BLE001 - log and return error
        logger.exception("Failed to initialize Firebase Admin SDK: %s", exc)
        return {"success": False, "skipped": True, "error": "firebase_init_failed"}

    payload = dict(data or {})
    payload.setdefault("title", title)
    payload.setdefault("body", body)

    message = messaging.Message(
        data=payload,
        token=token,
        notification=messaging.Notification(title=title, body=body),
        android=messaging.AndroidConfig(priority="high"),
    )

    try:
        message_id = messaging.send(message)
        logger.debug("FCM message sent: %s", message_id)
        return {"success": True, "message_id": message_id}
    except Exception as exc:  # noqa: BLE001 - log and return error
        logger.exception("FCM send failed: %s", exc)
        return {"success": False, "error": "fcm_send_failed"}
