from pathlib import Path
import secrets

from fastapi import UploadFile

from app.media.utils import validate_upload

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_DOC_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _validate(file: UploadFile, allowed_extensions: set[str]) -> str:
    return validate_upload(file, allowed_extensions)


def save_listing_media_file(
    file: UploadFile,
    request_id: int,
    media_root: Path,
    allowed_extensions: set[str],
    private: bool = False,
) -> tuple[str, str]:
    extension = _validate(file, allowed_extensions)
    subdirectory = "listing" if private else ""
    destination_dir = _ensure_dir(media_root / subdirectory / f"request_{request_id}")
    file_name = f"{secrets.token_hex(10)}{extension}"
    destination = destination_dir / file_name
    with destination.open("wb") as out:
        out.write(file.file.read())
    if private:
        return file_name, f"/media/private/listing/request_{request_id}/{file_name}"
    return file_name, f"/uploads/sell-land/request_{request_id}/{file_name}"


def save_booking_doc_file(
    file: UploadFile,
    booking_id: int,
    media_root: Path,
    allowed_extensions: set[str],
    doc_label: str,
) -> tuple[str, str]:
    extension = _validate(file, allowed_extensions)
    destination_dir = _ensure_dir(media_root / "booking" / f"booking_{booking_id}")
    file_name = f"{doc_label}_{secrets.token_hex(8)}{extension}"
    destination = destination_dir / file_name
    with destination.open("wb") as out:
        out.write(file.file.read())
    return file_name, f"/media/private/booking/booking_{booking_id}/{file_name}"


def save_registry_proof_file(
    file: UploadFile,
    booking_id: int,
    media_root: Path,
    allowed_extensions: set[str],
) -> tuple[str, str]:
    extension = _validate(file, allowed_extensions)
    destination_dir = _ensure_dir(media_root / "registry" / f"booking_{booking_id}")
    file_name = f"registry_{secrets.token_hex(8)}{extension}"
    destination = destination_dir / file_name
    with destination.open("wb") as out:
        out.write(file.file.read())
    return file_name, f"/media/private/registry/booking_{booking_id}/{file_name}"
