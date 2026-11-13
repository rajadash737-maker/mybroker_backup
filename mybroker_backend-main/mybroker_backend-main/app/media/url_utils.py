from app.core.config import settings
from app.core.request_context import get_request_base_url


def to_public_url(value: str | None) -> str | None:
    if not value:
        return value
    lowered = value.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return value

    # Prefer explicit configuration, then fall back to the current request host.
    base = settings.public_base_url.strip().rstrip("/") or (get_request_base_url() or "")
    if not base:
        return value

    path = value if value.startswith("/") else f"/{value}"
    return f"{base}{path}"
