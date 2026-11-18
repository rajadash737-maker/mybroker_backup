from pathlib import Path
import secrets
from decimal import Decimal

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.settings.repository import create_social_links, get_social_links, save_social_links
from app.settings.schemas import ProcessingFeeSettingsUpdateRequest, SocialLinksUpdateRequest
from app.settings.repository import (
    create_banner,
    delete_banner,
    get_banner,
    get_next_sort_order,
    list_banners,
    create_processing_fee_settings,
    get_processing_fee_settings,
    save_processing_fee_settings,
)
from app.media.utils import ensure_directory, remove_file_if_exists, validate_image_upload


def get_or_create_links(db: Session):
    record = get_social_links(db)
    if record:
        return record
    return create_social_links(db)


def update_links(db: Session, payload: SocialLinksUpdateRequest):
    record = get_or_create_links(db)

    record.whatsapp = _normalize(payload.whatsapp)
    record.instagram = _normalize(payload.instagram)
    record.telegram = _normalize(payload.telegram)
    record.youtube = _normalize(payload.youtube)
    record.facebook = _normalize(payload.facebook)
    record.linkedin = _normalize(payload.linkedin)

    return save_social_links(db, record)


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


BANNER_UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads" / "banners"


def get_banners(db: Session):
    return list_banners(db)


def create_banner_from_upload(db: Session, file: UploadFile):
    ensure_directory(BANNER_UPLOADS_DIR)
    extension = validate_image_upload(file)
    filename = f"banner_{secrets.token_hex(8)}{extension}"
    destination = BANNER_UPLOADS_DIR / filename

    with destination.open("wb") as out:
        out.write(file.file.read())

    image_url = f"/uploads/banners/{filename}"
    sort_order = get_next_sort_order(db)
    return create_banner(db, image_url=image_url, sort_order=sort_order)


def remove_banner(db: Session, banner_id: int) -> bool:
    banner = get_banner(db, banner_id)
    if not banner:
        return False

    if banner.image_url.startswith("/uploads/banners/"):
        filename = banner.image_url.split("/uploads/banners/", 1)[1]
        remove_file_if_exists(BANNER_UPLOADS_DIR / filename)

    delete_banner(db, banner)
    return True


DEFAULT_SELLER_PROCESSING_FEE = 999.0
DEFAULT_BUYER_PROCESSING_FEE = 1000.0
DEFAULT_SITE_VISIT_FEE = Decimal("0.00")


def get_or_create_processing_fees(db: Session):
    record = get_processing_fee_settings(db)
    if record:
        return record
    return create_processing_fee_settings(
        db,
        seller_processing_fee=DEFAULT_SELLER_PROCESSING_FEE,
        buyer_processing_fee=DEFAULT_BUYER_PROCESSING_FEE,
        site_visit_fee=DEFAULT_SITE_VISIT_FEE,
    )


def update_processing_fees(db: Session, payload: ProcessingFeeSettingsUpdateRequest):
    record = get_or_create_processing_fees(db)
    record.seller_processing_fee = payload.seller_processing_fee
    record.buyer_processing_fee = payload.buyer_processing_fee
    if payload.site_visit_fee is not None:
        record.site_visit_fee = payload.site_visit_fee
    return save_processing_fee_settings(db, record)


def get_processing_fees(db: Session) -> tuple[float, float]:
    record = get_or_create_processing_fees(db)
    return float(record.seller_processing_fee), float(record.buyer_processing_fee)
