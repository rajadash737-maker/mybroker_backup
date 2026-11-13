from pathlib import Path
import secrets

from fastapi import UploadFile
from app.core.config import settings

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _max_upload_bytes() -> int:
    value = settings.max_upload_size_bytes
    if value <= 0:
        raise RuntimeError("MAX_UPLOAD_SIZE_BYTES must be a positive integer")
    return value


def _matches_signature(extension: str, content: bytes) -> bool:
    return {
        ".jpg": content.startswith(b"\xff\xd8\xff"),
        ".jpeg": content.startswith(b"\xff\xd8\xff"),
        ".png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        ".webp": len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
        ".pdf": content.startswith(b"%PDF-"),
    }.get(extension, False)


def validate_upload(file: UploadFile, allowed_extensions: set[str]) -> str:
    extension = get_file_extension(file.filename or "")
    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValueError(f"Unsupported file type. Allowed: {allowed}")

    content_type = (file.content_type or "").lower()
    expected_types = {
        ".jpg": {"image/jpeg", "image/jpg"},
        ".jpeg": {"image/jpeg", "image/jpg"},
        ".png": {"image/png"},
        ".webp": {"image/webp"},
        ".pdf": {"application/pdf"},
    }
    if content_type not in expected_types[extension]:
        raise ValueError("Invalid file type")

    stream = file.file
    position = stream.tell()
    content = stream.read(_max_upload_bytes() + 1)
    stream.seek(position)
    if len(content) > _max_upload_bytes():
        raise ValueError("File exceeds the configured upload size limit")
    if not _matches_signature(extension, content):
        raise ValueError("File content does not match its declared type")

    return extension


def validate_image_upload(file: UploadFile) -> str:
    return validate_upload(file, ALLOWED_IMAGE_EXTENSIONS)


def generate_profile_filename(user_id: int, extension: str) -> str:
    return f"user_{user_id}_{secrets.token_hex(8)}{extension}"


def remove_file_if_exists(path: Path) -> None:
    if path.exists() and path.is_file():
        path.unlink()
