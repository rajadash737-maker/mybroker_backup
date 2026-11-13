import logging

from sqlalchemy.orm import Session
from sqlalchemy import or_
from pathlib import Path

from fastapi import UploadFile

from app.media.service import save_profile_file_local
from app.users.model import User
from app.users.schemas import UpdateProfileRequest

PROFILE_UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads" / "profiles"
logger = logging.getLogger(__name__)


def get_profile_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_profile_by_user_id(db: Session, user_id: int) -> User | None:
    return get_profile_by_id(db, user_id)


def _conflict_exists(db: Session, user_id: int, email: str | None, username: str | None, mobile: str | None) -> bool:
    checks = []
    if email is not None:
        checks.append(User.email == email)
    if username is not None:
        checks.append(User.username == username)
    if mobile is not None:
        checks.append(User.mobile == mobile)

    if not checks:
        return False

    existing = db.query(User).filter(User.id != user_id, or_(*checks)).first()
    return existing is not None


def update_profile_by_user_id(db: Session, user_id: int, payload: UpdateProfileRequest) -> tuple[User | None, str | None]:
    user = get_profile_by_user_id(db, user_id)
    if not user:
        return None, "User not found"

    if _conflict_exists(db, user_id, payload.email, payload.username, payload.mobile):
        return None, "Email, username, or mobile already in use"

    if payload.fullname is not None:
        user.fullname = payload.fullname.strip()
    if payload.username is not None:
        user.username = payload.username
    if payload.email is not None:
        user.email = payload.email
    if payload.mobile is not None:
        user.mobile = payload.mobile
    if payload.address is not None:
        user.address = payload.address.strip() or None
    if payload.date_of_birth is not None:
        user.date_of_birth = payload.date_of_birth
    if payload.gender is not None:
        user.gender = payload.gender.value

    db.commit()
    db.refresh(user)
    return user, None


def update_profile_photo_by_user_id(db: Session, user_id: int, file: UploadFile) -> tuple[User | None, str | None]:
    user = get_profile_by_user_id(db, user_id)
    if not user:
        return None, "User not found"

    try:
        photo_url = save_profile_file_local(file, PROFILE_UPLOADS_DIR, user_id, user.profile_image_url)
    except ValueError as exc:
        return None, str(exc)

    user.profile_image_url = photo_url
    db.commit()
    db.refresh(user)
    return user, None


def update_fcm_token(db: Session, user_id: int, token: str) -> tuple[User | None, str | None]:
    user = get_profile_by_user_id(db, user_id)
    if not user:
        return None, "User not found"

    user.fcm_token = token.strip() or None
    db.commit()
    db.refresh(user)
    logger.info("FCM token updated for user_id=%s", user_id)
    return user, None
