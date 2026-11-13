import re
from urllib.parse import urlsplit, urlunsplit


_ALLOWED_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
_SHORTCODE = re.compile(r"^[A-Za-z0-9_-]+$")
_USERNAME = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def normalize_instagram_url(value: str | None) -> str | None:
    """Return a normalized supported Instagram HTTPS URL, or None if invalid."""
    if value is None:
        return None
    value = value.strip()
    if not value or any(char.isspace() for char in value) or "\\" in value:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() != "https" or parsed.hostname is None:
            return None
        if parsed.hostname.lower() not in _ALLOWED_HOSTS:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        if parsed.port not in (None, 443):
            return None
    except ValueError:
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) == 1:
        if not _USERNAME.fullmatch(parts[0]) or parts[0].lower() in {
            "p", "reel", "reels", "stories", "explore", "accounts", "direct"
        }:
            return None
    elif len(parts) == 2 and parts[0].lower() in {"p", "reel", "reels"}:
        if not _SHORTCODE.fullmatch(parts[1]):
            return None
    else:
        return None

    return urlunsplit(("https", parsed.netloc.lower(), parsed.path or "/", parsed.query, parsed.fragment))
