from pathlib import Path

from fastapi import UploadFile

from app.media.utils import ensure_directory, generate_profile_filename, remove_file_if_exists, validate_image_upload


def save_profile_file_local(file: UploadFile, destination_root: Path, user_id: int, old_file_url: str | None = None) -> str:
    ensure_directory(destination_root)
    extension = validate_image_upload(file)
    filename = generate_profile_filename(user_id, extension)
    destination = destination_root / filename

    if old_file_url and old_file_url.startswith("/uploads/profiles/"):
        old_filename = old_file_url.split("/uploads/profiles/", 1)[1]
        remove_file_if_exists(destination_root / old_filename)

    with destination.open("wb") as out:
        out.write(file.file.read())
    return f"/uploads/profiles/{filename}"
