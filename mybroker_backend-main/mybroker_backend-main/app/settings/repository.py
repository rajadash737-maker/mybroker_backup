from decimal import Decimal

from sqlalchemy.orm import Session

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.settings.models import SocialLinks, Banner, ProcessingFeeSettings


def get_social_links(db: Session) -> SocialLinks | None:
    return db.query(SocialLinks).first()


def create_social_links(db: Session) -> SocialLinks:
    record = SocialLinks()
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def save_social_links(db: Session, record: SocialLinks) -> SocialLinks:
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_banners(db: Session) -> list[Banner]:
    return (
        db.query(Banner)
        .filter(Banner.is_active.is_(True))
        .order_by(Banner.sort_order.asc(), Banner.id.asc())
        .all()
    )


def get_banner(db: Session, banner_id: int) -> Banner | None:
    return db.query(Banner).filter(Banner.id == banner_id).first()


def get_next_sort_order(db: Session) -> int:
    current = db.query(func.max(Banner.sort_order)).scalar()
    return int(current or 0) + 1


def create_banner(db: Session, image_url: str, sort_order: int) -> Banner:
    banner = Banner(image_url=image_url, sort_order=sort_order)
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


def delete_banner(db: Session, banner: Banner) -> None:
    db.delete(banner)
    db.commit()


def get_processing_fee_settings(db: Session) -> ProcessingFeeSettings | None:
    return db.query(ProcessingFeeSettings).first()


def create_processing_fee_settings(
    db: Session,
    seller_processing_fee: float,
    buyer_processing_fee: float,
    site_visit_fee: Decimal = Decimal("0.00"),
) -> ProcessingFeeSettings:
    record = ProcessingFeeSettings(
        seller_processing_fee=seller_processing_fee,
        buyer_processing_fee=buyer_processing_fee,
        site_visit_fee=site_visit_fee,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def save_processing_fee_settings(db: Session, record: ProcessingFeeSettings) -> ProcessingFeeSettings:
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
