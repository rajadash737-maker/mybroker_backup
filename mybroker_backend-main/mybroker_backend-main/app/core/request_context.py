from contextvars import ContextVar


_request_base_url: ContextVar[str | None] = ContextVar("request_base_url", default=None)


def set_request_base_url(value: str | None) -> None:
    normalized = value.strip().rstrip("/") if value else None
    _request_base_url.set(normalized)


def get_request_base_url() -> str | None:
    return _request_base_url.get()
