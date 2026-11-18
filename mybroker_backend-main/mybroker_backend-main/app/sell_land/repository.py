import json
from datetime import datetime, timedelta
import secrets
from enum import Enum

from sqlalchemy import exists, func, literal, select, union_all, or_
from sqlalchemy.orm import Session

from app.sell_land.constants import BookingStatus, MediaType, OfferStatus, PaymentStatus, SellLandStatus
from app.sell_land.models import (
    SellLandBooking,
    SellLandFavorite,
    SellLandMedia,
    SellLandOffer,
    SellLandPayment,
    SellLandRegistryProof,
    SellLandRequest,
)
from app.users.model import User
from app.users.roles import UserRole
from app.sell_land.schemas import (
    SellLandBoundaryRequest,
    SellLandCreateRequest,
    SellLandDraftUpsertRequest,
    SellLandPaymentInitRequest,
    SellLandUpdateRequest,
)


def _apply_request_updates(entity: SellLandRequest, updates: dict) -> None:
    nullable_string_fields = {"description", "location"}
    enum_fields = {"land_type", "ownership_type", "area_unit", "price_type", "availability", "owner_category"}

    for key, value in updates.items():
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned and key in nullable_string_fields:
                value = None
            else:
                value = cleaned
        if key in enum_fields and value is not None and isinstance(value, Enum):
            value = value.value
        setattr(entity, key, value)


def create_sell_land_request(
    db: Session,
    user_id: int,
    payload: SellLandCreateRequest,
    payment_required_amount: float | None = None,
) -> SellLandRequest:
    entity = SellLandRequest(
        user_id=user_id,
        title=payload.title.strip(),
        owner_name=payload.owner_name.strip(),
        owner_mobile=payload.owner_mobile.strip(),
        owner_category=payload.owner_category.value if payload.owner_category else None,
        land_type=payload.land_type.value,
        ownership_type=payload.ownership_type.value,
        location=payload.location.strip(),
        city=payload.city.strip(),
        state=payload.state.strip(),
        pincode=payload.pincode.strip(),
        area=payload.area,
        area_unit=payload.area_unit.value,
        price_type=payload.price_type.value,
        expected_price=payload.expected_price,
        pricing_version=payload.pricing_version or 1,
        entered_unit_price=None,
        negotiable=payload.negotiable,
        availability=payload.availability.value,
        description=payload.description.strip() if payload.description else None,
        is_draft=False,
        draft_step=8,
        status=SellLandStatus.PENDING.value,
    )
    if payment_required_amount is not None:
        entity.payment_required_amount = payment_required_amount
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def upsert_sell_land_draft(
    db: Session,
    user_id: int,
    payload: SellLandDraftUpsertRequest,
    request_id: int | None = None,
) -> SellLandRequest:
    if request_id:
        entity = (
            db.query(SellLandRequest)
            .filter(SellLandRequest.id == request_id, SellLandRequest.user_id == user_id)
            .first()
        )
    else:
        entity = None

    if entity is None:
        entity = SellLandRequest(user_id=user_id, status=SellLandStatus.DRAFT.value, is_draft=True, draft_step=1)
        db.add(entity)
        db.flush()

    updates = payload.model_dump(exclude_unset=True)
    _apply_request_updates(entity, updates)
    if updates.get("pricing_version") == 2 and "expected_price" in updates:
        entity.entered_unit_price = None

    if payload.draft_step is not None:
        entity.draft_step = payload.draft_step
    else:
        entity.draft_step = max(entity.draft_step, 1)

    entity.is_draft = True
    entity.status = SellLandStatus.DRAFT.value

    db.commit()
    db.refresh(entity)
    return entity


def list_sell_land_requests_by_user(db: Session, user_id: int) -> list[SellLandRequest]:
    return (
        db.query(SellLandRequest)
        .filter(SellLandRequest.user_id == user_id)
        .order_by(SellLandRequest.created_at.desc())
        .all()
    )


def get_favorite_counts_for_request_ids(db: Session, request_ids: list[int]) -> dict[int, int]:
    if not request_ids:
        return {}

    rows = (
        db.query(
            SellLandFavorite.request_id,
            func.count(SellLandFavorite.id),
        )
        .filter(SellLandFavorite.request_id.in_(request_ids))
        .group_by(SellLandFavorite.request_id)
        .all()
    )
    return {int(request_id): int(count) for request_id, count in rows}


def get_offer_counts_for_request_ids(db: Session, request_ids: list[int]) -> dict[int, int]:
    if not request_ids:
        return {}

    rows = (
        db.query(
            SellLandOffer.request_id,
            func.count(SellLandOffer.id),
        )
        .filter(SellLandOffer.request_id.in_(request_ids))
        .group_by(SellLandOffer.request_id)
        .all()
    )
    return {int(request_id): int(count) for request_id, count in rows}


def get_sell_land_request_by_id(db: Session, request_id: int) -> SellLandRequest | None:
    return db.query(SellLandRequest).filter(SellLandRequest.id == request_id).first()


def update_sell_land_request(
    db: Session,
    entity: SellLandRequest,
    payload: SellLandUpdateRequest,
) -> SellLandRequest:
    updates = payload.model_dump(exclude_unset=True)
    _apply_request_updates(entity, updates)
    if updates.get("pricing_version") == 2 and "expected_price" in updates:
        entity.entered_unit_price = None
    if payload.draft_step is not None:
        entity.draft_step = payload.draft_step

    db.commit()
    db.refresh(entity)
    return entity


def update_boundary(
    db: Session,
    entity: SellLandRequest,
    payload: SellLandBoundaryRequest,
) -> SellLandRequest:
    entity.boundary_points = json.dumps([p.model_dump() for p in payload.points])
    entity.draft_step = max(entity.draft_step, 4)
    db.commit()
    db.refresh(entity)
    return entity


def add_media(
    db: Session,
    request_id: int,
    media_type: MediaType,
    file_url: str,
    file_name: str,
    document_type: str | None,
    is_required: bool,
) -> SellLandMedia:
    entity = SellLandMedia(
        request_id=request_id,
        media_type=media_type.value,
        document_type=document_type,
        file_url=file_url,
        file_name=file_name,
        is_required=is_required,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def list_media(db: Session, request_id: int) -> list[SellLandMedia]:
    return (
        db.query(SellLandMedia)
        .filter(SellLandMedia.request_id == request_id)
        .order_by(SellLandMedia.created_at.asc())
        .all()
    )


def get_media_by_id(db: Session, media_id: int) -> SellLandMedia | None:
    return db.query(SellLandMedia).filter(SellLandMedia.id == media_id).first()


def get_document_media_by_type(
    db: Session,
    request_id: int,
    document_type: str,
) -> SellLandMedia | None:
    return (
        db.query(SellLandMedia)
        .filter(
            SellLandMedia.request_id == request_id,
            SellLandMedia.media_type == MediaType.DOCUMENT.value,
            SellLandMedia.document_type == document_type,
        )
        .order_by(SellLandMedia.created_at.desc())
        .first()
    )


def delete_media(db: Session, entity: SellLandMedia) -> None:
    db.delete(entity)
    db.commit()


def create_payment(db: Session, payload: SellLandPaymentInitRequest, amount: float) -> SellLandPayment:
    entity = SellLandPayment(
        request_id=payload.request_id,
        method=payload.method.value,
        amount=amount,
        status=PaymentStatus.INITIATED.value,
        provider_ref=payload.provider_ref.strip() if payload.provider_ref else None,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def get_payment_by_id(db: Session, payment_id: int) -> SellLandPayment | None:
    return db.query(SellLandPayment).filter(SellLandPayment.id == payment_id).first()


def get_payment_by_provider_ref(
    db: Session, provider_ref: str, *, for_update: bool = False
) -> SellLandPayment | None:
    query = db.query(SellLandPayment).filter(SellLandPayment.provider_ref == provider_ref)
    if for_update:
        query = query.with_for_update()
    return query.first()


def get_latest_payment_by_request_id(db: Session, request_id: int) -> SellLandPayment | None:
    return (
        db.query(SellLandPayment)
        .filter(SellLandPayment.request_id == request_id)
        .order_by(
            SellLandPayment.paid_at.is_(None),
            SellLandPayment.paid_at.desc(),
            SellLandPayment.created_at.desc(),
            SellLandPayment.id.desc(),
        )
        .first()
    )


def mark_payment_success(
    db: Session,
    payment: SellLandPayment,
    provider_ref: str | None = None,
    gateway_payment_id: str | None = None,
    *,
    commit: bool = True,
) -> SellLandPayment:
    payment.status = PaymentStatus.SUCCESS.value
    payment.paid_at = datetime.utcnow()
    if provider_ref:
        payment.provider_ref = provider_ref.strip()
    if gateway_payment_id:
        payment.gateway_payment_id = gateway_payment_id.strip()

    request = get_sell_land_request_by_id(db, payment.request_id)
    if request:
        request.payment_status = PaymentStatus.SUCCESS.value

    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(payment)
    return payment


def mark_payment_failed(
    db: Session,
    payment: SellLandPayment,
    *,
    commit: bool = True,
) -> SellLandPayment:
    payment.status = PaymentStatus.FAILED.value
    payment.paid_at = datetime.utcnow()

    request = get_sell_land_request_by_id(db, payment.request_id)
    if request:
        request.payment_status = PaymentStatus.FAILED.value

    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(payment)
    return payment


def create_payment_for_razorpay(
    db: Session,
    request_id: int,
    amount: float,
    order_id: str,
) -> SellLandPayment:
    entity = SellLandPayment(
        request_id=request_id,
        method="razorpay",
        amount=amount,
        status=PaymentStatus.INITIATED.value,
        provider_ref=order_id,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def delete_sell_land_request(db: Session, entity: SellLandRequest) -> None:
    db.delete(entity)
    db.commit()


def list_sell_land_requests_for_admin_review(
    db: Session,
    status_filter: str | None,
    search: str | None,
    state_filter: str | None,
    city_filter: str | None,
    skip: int,
    limit: int,
    reviewed_by_id: int | None = None,
    listing_id: int | None = None,
) -> tuple[list[SellLandRequest], int]:
    query = db.query(SellLandRequest)

    if status_filter:
        query = query.filter(SellLandRequest.status == status_filter)
    if reviewed_by_id is not None:
        query = query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
    cleaned_state = (state_filter or "").strip()
    if cleaned_state:
        query = query.filter(SellLandRequest.state.ilike(f"%{cleaned_state}%"))
    cleaned_city = (city_filter or "").strip()
    if cleaned_city:
        query = query.filter(SellLandRequest.city.ilike(f"%{cleaned_city}%"))

    if listing_id is not None:
        query = query.filter(SellLandRequest.id == listing_id)
    else:
        cleaned_search = (search or "").strip()
        if cleaned_search:
            pattern = f"%{cleaned_search}%"
            conditions = [
                SellLandRequest.listing_code.ilike(pattern),
                SellLandRequest.title.ilike(pattern),
                SellLandRequest.owner_name.ilike(pattern),
                SellLandRequest.owner_mobile.ilike(pattern),
                User.fullname.ilike(pattern),
                User.mobile.ilike(pattern),
            ]

            normalized = cleaned_search.lower().replace(" ", "")
            if normalized.startswith("lst-"):
                normalized = normalized.replace("lst-", "")
            if normalized.isdigit():
                try:
                    conditions.append(SellLandRequest.id == int(normalized))
                except ValueError:
                    pass

            query = query.join(User, User.id == SellLandRequest.user_id).filter(or_(*conditions))

    total = query.count()
    items = (
        query.order_by(SellLandRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def list_users_by_ids(db: Session, user_ids: list[int]) -> list[User]:
    if not user_ids:
        return []
    return db.query(User).filter(User.id.in_(user_ids)).all()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def list_field_officers(db: Session, only_active: bool = True) -> list[User]:
    query = db.query(User).filter(User.role == UserRole.FIELD_OFFICER.value)
    if only_active:
        query = query.filter(User.is_active.is_(True))
    return query.order_by(User.fullname.asc(), User.id.asc()).all()


def list_media_for_requests(db: Session, request_ids: list[int]) -> list[SellLandMedia]:
    if not request_ids:
        return []
    return (
        db.query(SellLandMedia)
        .filter(SellLandMedia.request_id.in_(request_ids))
        .order_by(SellLandMedia.created_at.asc())
        .all()
    )


def list_live_sell_land_requests(
    db: Session,
    search: str | None,
    min_price: float | None,
    max_price: float | None,
    min_area: float | None,
    max_area: float | None,
    sort_by: str,
    skip: int,
    limit: int,
) -> tuple[list[SellLandRequest], int]:
    release_expired_offer_locks(db)
    blocking_booking_exists = (
        exists()
        .where(SellLandBooking.request_id == SellLandRequest.id)
        .where(SellLandBooking.payment_status == PaymentStatus.SUCCESS.value)
        .where(
            SellLandBooking.booking_status.in_(
                (
                    BookingStatus.BOOKED.value,
                    BookingStatus.CONFIRMED.value,
                    BookingStatus.IN_PROCESS.value,
                    BookingStatus.REGISTRY_SCHEDULED.value,
                    BookingStatus.REGISTRY_DONE.value,
                    BookingStatus.SOLD.value,
                )
            )
        )
    )
    query = (
        db.query(SellLandRequest)
        .filter(SellLandRequest.status == SellLandStatus.LIVE.value)
        .filter(~blocking_booking_exists)
    )

    cleaned_search = (search or "").strip()
    if cleaned_search:
        pattern = f"%{cleaned_search}%"
        query = query.filter(
            SellLandRequest.title.ilike(pattern)
            | SellLandRequest.location.ilike(pattern)
            | SellLandRequest.city.ilike(pattern)
            | SellLandRequest.state.ilike(pattern)
            | SellLandRequest.pincode.ilike(pattern)
        )

    if min_price is not None:
        query = query.filter(SellLandRequest.expected_price.is_not(None), SellLandRequest.expected_price >= min_price)
    if max_price is not None:
        query = query.filter(SellLandRequest.expected_price.is_not(None), SellLandRequest.expected_price <= max_price)
    if min_area is not None:
        query = query.filter(SellLandRequest.area.is_not(None), SellLandRequest.area >= min_area)
    if max_area is not None:
        query = query.filter(SellLandRequest.area.is_not(None), SellLandRequest.area <= max_area)

    # MySQL doesn't support "NULLS LAST", so we emulate it by ordering
    # nulls at the end using a boolean expression first.
    if sort_by == "price_low_to_high":
        query = query.order_by(
            SellLandRequest.expected_price.is_(None),
            SellLandRequest.expected_price.asc(),
            SellLandRequest.created_at.desc(),
        )
    elif sort_by == "price_high_to_low":
        query = query.order_by(
            SellLandRequest.expected_price.is_(None),
            SellLandRequest.expected_price.desc(),
            SellLandRequest.created_at.desc(),
        )
    else:
        query = query.order_by(SellLandRequest.created_at.desc(), SellLandRequest.id.desc())

    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return items, total


def get_live_sell_land_request_by_id(db: Session, request_id: int) -> SellLandRequest | None:
    release_expired_offer_locks(db)
    return (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.id == request_id,
            SellLandRequest.status == SellLandStatus.LIVE.value,
        )
        .first()
    )


def list_favorite_request_ids_for_user(db: Session, user_id: int, request_ids: list[int]) -> set[int]:
    if not request_ids:
        return set()
    rows = (
        db.query(SellLandFavorite.request_id)
        .filter(
            SellLandFavorite.user_id == user_id,
            SellLandFavorite.request_id.in_(request_ids),
        )
        .all()
    )
    return {row[0] for row in rows}


def get_favorite_for_user(db: Session, user_id: int, request_id: int) -> SellLandFavorite | None:
    return (
        db.query(SellLandFavorite)
        .filter(
            SellLandFavorite.user_id == user_id,
            SellLandFavorite.request_id == request_id,
        )
        .first()
    )


def create_favorite(db: Session, user_id: int, request_id: int) -> SellLandFavorite:
    entity = SellLandFavorite(user_id=user_id, request_id=request_id)
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def delete_favorite(db: Session, entity: SellLandFavorite) -> None:
    db.delete(entity)
    db.commit()


def create_offer(db: Session, request_id: int, buyer_id: int, offered_amount: float) -> SellLandOffer:
    entity = SellLandOffer(
        request_id=request_id,
        buyer_id=buyer_id,
        offered_amount=offered_amount,
        status=OfferStatus.PENDING.value,
        counter_amount=None,
        seller_response_at=None,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def create_or_update_offer_for_buyer(db: Session, request_id: int, buyer_id: int, offered_amount: float) -> SellLandOffer:
    existing = (
        db.query(SellLandOffer)
        .filter(
            SellLandOffer.request_id == request_id,
            SellLandOffer.buyer_id == buyer_id,
        )
        .order_by(SellLandOffer.updated_at.desc(), SellLandOffer.id.desc())
        .first()
    )

    if existing and existing.status in {OfferStatus.PENDING.value, OfferStatus.COUNTERED.value}:
        existing.offered_amount = offered_amount
        existing.status = OfferStatus.PENDING.value
        existing.counter_amount = None
        existing.seller_response_at = None
        db.commit()
        db.refresh(existing)
        return existing

    return create_offer(db=db, request_id=request_id, buyer_id=buyer_id, offered_amount=offered_amount)


def release_expired_offer_locks(db: Session, now: datetime | None = None) -> int:
    current_time = now or datetime.utcnow()
    expired_requests = (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.offer_lock_expires_at.is_not(None),
            SellLandRequest.offer_lock_expires_at <= current_time,
        )
        .all()
    )
    if not expired_requests:
        return 0

    accepted_offer_ids = [row.accepted_offer_id for row in expired_requests if row.accepted_offer_id is not None]
    if accepted_offer_ids:
        (
            db.query(SellLandOffer)
            .filter(
                SellLandOffer.id.in_(accepted_offer_ids),
                SellLandOffer.status == OfferStatus.ACCEPTED.value,
            )
            .update(
                {
                    SellLandOffer.status: OfferStatus.EXPIRED.value,
                    SellLandOffer.seller_response_at: current_time,
                },
                synchronize_session=False,
            )
        )

    request_ids = [row.id for row in expired_requests]
    updated = (
        db.query(SellLandRequest)
        .filter(SellLandRequest.id.in_(request_ids))
        .update(
            {
                SellLandRequest.offer_locked_by_buyer_id: None,
                SellLandRequest.offer_lock_expires_at: None,
                SellLandRequest.accepted_offer_id: None,
            },
            synchronize_session=False,
        )
    )
    if updated:
        db.commit()
    return updated


def list_locked_offer_listings_for_admin(
    db: Session,
    skip: int,
    limit: int,
    reviewed_by_id: int | None = None,
) -> tuple[list[SellLandRequest], int]:
    now = datetime.utcnow()
    release_expired_offer_locks(db, now=now)
    query = (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.status == SellLandStatus.LIVE.value,
            SellLandRequest.offer_lock_expires_at.is_not(None),
            SellLandRequest.offer_lock_expires_at > now,
            SellLandRequest.accepted_offer_id.is_not(None),
        )
    )
    if reviewed_by_id is not None:
        query = query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
    total = query.count()
    items = (
        query.order_by(SellLandRequest.offer_lock_expires_at.asc(), SellLandRequest.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def list_booked_listings_for_admin(
    db: Session,
    skip: int,
    limit: int,
    reviewed_by_id: int | None = None,
) -> tuple[list[SellLandRequest], int]:
    query = db.query(SellLandRequest).filter(SellLandRequest.status == SellLandStatus.BOOKED.value)
    if reviewed_by_id is not None:
        query = query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
    total = query.count()
    items = (
        query.order_by(SellLandRequest.updated_at.desc(), SellLandRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def list_sold_listings_for_admin(
    db: Session,
    skip: int,
    limit: int,
    reviewed_by_id: int | None = None,
) -> tuple[list[SellLandRequest], int]:
    query = db.query(SellLandRequest).filter(SellLandRequest.status == SellLandStatus.SOLD.value)
    if reviewed_by_id is not None:
        query = query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
    total = query.count()
    items = (
        query.order_by(SellLandRequest.updated_at.desc(), SellLandRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def list_completed_transactions_for_accounting(
    db: Session,
    skip: int,
    limit: int,
) -> tuple[list[tuple[SellLandRequest, SellLandBooking | None]], int]:
    latest_booking_ids = (
        db.query(
            SellLandBooking.request_id.label("request_id"),
            func.max(SellLandBooking.id).label("booking_id"),
        )
        .filter(SellLandBooking.payment_status == PaymentStatus.SUCCESS.value)
        .group_by(SellLandBooking.request_id)
        .subquery()
    )

    query = (
        db.query(SellLandRequest, SellLandBooking)
        .outerjoin(latest_booking_ids, latest_booking_ids.c.request_id == SellLandRequest.id)
        .outerjoin(SellLandBooking, SellLandBooking.id == latest_booking_ids.c.booking_id)
        .filter(
            SellLandRequest.is_draft.is_(False),
            SellLandRequest.payment_status == PaymentStatus.SUCCESS.value,
            SellLandRequest.status.notin_(
                [
                    SellLandStatus.DRAFT.value,
                    SellLandStatus.REJECTED.value,
                    SellLandStatus.PROCESSING_REFUND.value,
                    SellLandStatus.REFUND_SUCCESSFUL.value,
                ]
            ),
        )
    )

    total = query.count()
    items = (
        query.order_by(SellLandRequest.updated_at.desc(), SellLandRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def get_accounting_dashboard_summary(
    db: Session,
    start_at: datetime,
    end_at: datetime,
) -> tuple[float, int, int, int]:
    active_listing_filter = [
        SellLandRequest.is_draft.is_(False),
        SellLandRequest.payment_status == PaymentStatus.SUCCESS.value,
        SellLandRequest.status.notin_(
            [
                SellLandStatus.DRAFT.value,
                SellLandStatus.REJECTED.value,
                SellLandStatus.PROCESSING_REFUND.value,
                SellLandStatus.REFUND_SUCCESSFUL.value,
            ]
        ),
    ]

    seller_fee_sum = (
        db.query(func.coalesce(func.sum(SellLandPayment.amount), 0.0))
        .filter(
            SellLandPayment.status == PaymentStatus.SUCCESS.value,
            SellLandPayment.paid_at.is_not(None),
            SellLandPayment.paid_at.between(start_at, end_at),
        )
        .scalar()
    )

    buyer_fee_sum = (
        db.query(func.coalesce(func.sum(SellLandBooking.booking_fee_amount), 0.0))
        .filter(
            SellLandBooking.payment_status == PaymentStatus.SUCCESS.value,
            SellLandBooking.paid_at.is_not(None),
            SellLandBooking.paid_at.between(start_at, end_at),
        )
        .scalar()
    )

    pending_payments = (
        db.query(func.count(SellLandRequest.id))
        .filter(*active_listing_filter)
        .filter(
            ~exists()
            .where(SellLandBooking.request_id == SellLandRequest.id)
            .where(SellLandBooking.payment_status == PaymentStatus.SUCCESS.value)
        )
        .scalar()
    )

    completed_transactions = (
        db.query(func.count(SellLandBooking.id))
        .filter(
            SellLandBooking.payment_status == PaymentStatus.SUCCESS.value,
            SellLandBooking.paid_at.is_not(None),
            SellLandBooking.paid_at.between(start_at, end_at),
        )
        .scalar()
    )

    pending_refunds = (
        db.query(func.count(SellLandRequest.id))
        .filter(SellLandRequest.status == SellLandStatus.PROCESSING_REFUND.value)
        .scalar()
    )

    refund_total = (
        db.query(
            func.coalesce(
                func.sum(
                    func.coalesce(SellLandRequest.refund_amount, SellLandRequest.payment_required_amount)
                ),
                0.0,
            )
        )
        .filter(
            SellLandRequest.status == SellLandStatus.REFUND_SUCCESSFUL.value,
            SellLandRequest.refund_completed_at.is_not(None),
            SellLandRequest.refund_completed_at.between(start_at, end_at),
        )
        .scalar()
    )

    total_revenue = float(seller_fee_sum or 0.0) + float(buyer_fee_sum or 0.0) - float(refund_total or 0.0)

    return (
        float(total_revenue),
        int(pending_payments or 0),
        int(completed_transactions or 0),
        int(pending_refunds or 0),
    )


def get_super_admin_revenue_summary(
    db: Session,
    start_at: datetime,
    end_at: datetime,
) -> tuple[float, float, float, list[dict]]:
    seller_revenue = (
        db.query(func.coalesce(func.sum(SellLandPayment.amount), 0.0))
        .filter(
            SellLandPayment.status == PaymentStatus.SUCCESS.value,
            SellLandPayment.paid_at.is_not(None),
            SellLandPayment.paid_at.between(start_at, end_at),
        )
        .scalar()
    )

    buyer_revenue = (
        db.query(func.coalesce(func.sum(SellLandBooking.booking_fee_amount), 0.0))
        .filter(
            SellLandBooking.payment_status == PaymentStatus.SUCCESS.value,
            SellLandBooking.paid_at.is_not(None),
            SellLandBooking.paid_at.between(start_at, end_at),
        )
        .scalar()
    )

    refund_total = (
        db.query(
            func.coalesce(
                func.sum(
                    func.coalesce(SellLandRequest.refund_amount, SellLandRequest.payment_required_amount)
                ),
                0.0,
            )
        )
        .filter(
            SellLandRequest.status == SellLandStatus.REFUND_SUCCESSFUL.value,
            SellLandRequest.refund_completed_at.is_not(None),
            SellLandRequest.refund_completed_at.between(start_at, end_at),
        )
        .scalar()
    )

    seller_txn = (
        select(
            SellLandPayment.paid_at.label("date"),
            literal("seller").label("type"),
            User.fullname.label("user_name"),
            SellLandPayment.amount.label("amount"),
            literal("PAID").label("status"),
        )
        .select_from(SellLandPayment)
        .join(SellLandRequest, SellLandRequest.id == SellLandPayment.request_id)
        .join(User, User.id == SellLandRequest.user_id)
        .where(
            SellLandPayment.status == PaymentStatus.SUCCESS.value,
            SellLandPayment.paid_at.is_not(None),
            SellLandPayment.paid_at.between(start_at, end_at),
        )
    )

    buyer_txn = (
        select(
            SellLandBooking.paid_at.label("date"),
            literal("buyer").label("type"),
            SellLandBooking.buyer_name.label("user_name"),
            SellLandBooking.booking_fee_amount.label("amount"),
            literal("PAID").label("status"),
        )
        .select_from(SellLandBooking)
        .where(
            SellLandBooking.payment_status == PaymentStatus.SUCCESS.value,
            SellLandBooking.paid_at.is_not(None),
            SellLandBooking.paid_at.between(start_at, end_at),
        )
    )

    combined = union_all(seller_txn, buyer_txn).subquery()
    rows = db.execute(
        select(
            combined.c.date,
            combined.c.type,
            combined.c.user_name,
            combined.c.amount,
            combined.c.status,
        )
        .order_by(combined.c.date.desc())
    ).all()

    transactions = [
        {
            "date": row.date,
            "type": row.type,
            "user_name": row.user_name,
            "amount": float(row.amount or 0.0),
            "status": row.status,
        }
        for row in rows
    ]

    seller_value = float(seller_revenue or 0.0)
    buyer_value = float(buyer_revenue or 0.0)
    total_revenue = seller_value + buyer_value - float(refund_total or 0.0)

    return total_revenue, seller_value, buyer_value, transactions


def get_completed_transaction_by_listing_id(
    db: Session,
    listing_id: int,
) -> tuple[SellLandRequest, SellLandBooking | None] | None:
    latest_booking_id = (
        db.query(func.max(SellLandBooking.id))
        .filter(
            SellLandBooking.request_id == listing_id,
            SellLandBooking.payment_status == PaymentStatus.SUCCESS.value,
        )
        .scalar()
    )

    booking = None
    if latest_booking_id:
        booking = db.query(SellLandBooking).filter(SellLandBooking.id == latest_booking_id).first()

    listing = (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.id == listing_id,
            SellLandRequest.is_draft.is_(False),
            SellLandRequest.payment_status == PaymentStatus.SUCCESS.value,
            SellLandRequest.status.notin_(
                [
                    SellLandStatus.DRAFT.value,
                    SellLandStatus.REJECTED.value,
                    SellLandStatus.PROCESSING_REFUND.value,
                    SellLandStatus.REFUND_SUCCESSFUL.value,
                ]
            ),
        )
        .first()
    )
    if not listing:
        return None
    return listing, booking


def force_release_offer_lock_by_admin(
    db: Session,
    request_id: int,
) -> tuple[SellLandRequest | None, str | None]:
    now = datetime.utcnow()
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status != SellLandStatus.LIVE.value:
        return None, "Only live listings can be force released"
    if not entity.offer_lock_expires_at or entity.offer_lock_expires_at <= now:
        return None, "Listing is not locked"

    accepted_offer = None
    if entity.accepted_offer_id is not None:
        accepted_offer = (
            db.query(SellLandOffer)
            .filter(SellLandOffer.id == entity.accepted_offer_id)
            .first()
        )
    if accepted_offer and accepted_offer.status == OfferStatus.ACCEPTED.value:
        accepted_offer.status = OfferStatus.EXPIRED.value
        accepted_offer.seller_response_at = now

    entity.offer_locked_by_buyer_id = None
    entity.offer_lock_expires_at = None
    entity.accepted_offer_id = None
    db.commit()
    db.refresh(entity)
    return entity, None


def list_offers_by_ids(db: Session, offer_ids: list[int]) -> list[SellLandOffer]:
    if not offer_ids:
        return []
    return db.query(SellLandOffer).filter(SellLandOffer.id.in_(offer_ids)).all()


def list_offers_for_request(db: Session, request_id: int) -> list[tuple[SellLandOffer, User]]:
    latest_per_buyer = (
        db.query(func.max(SellLandOffer.id).label("latest_offer_id"))
        .filter(SellLandOffer.request_id == request_id)
        .group_by(SellLandOffer.buyer_id)
        .subquery()
    )

    return (
        db.query(SellLandOffer, User)
        .join(User, User.id == SellLandOffer.buyer_id)
        .join(latest_per_buyer, SellLandOffer.id == latest_per_buyer.c.latest_offer_id)
        .order_by(SellLandOffer.created_at.desc(), SellLandOffer.id.desc())
        .all()
    )


def list_offers_for_buyer(db: Session, buyer_id: int) -> list[tuple[SellLandOffer, SellLandRequest]]:
    latest_per_request = (
        db.query(func.max(SellLandOffer.id).label("latest_offer_id"))
        .filter(SellLandOffer.buyer_id == buyer_id)
        .group_by(SellLandOffer.request_id)
        .subquery()
    )
    return (
        db.query(SellLandOffer, SellLandRequest)
        .join(SellLandRequest, SellLandRequest.id == SellLandOffer.request_id)
        .join(latest_per_request, SellLandOffer.id == latest_per_request.c.latest_offer_id)
        .order_by(SellLandOffer.updated_at.desc(), SellLandOffer.id.desc())
        .all()
    )


def get_incoming_offer_counts(db: Session, user_id: int) -> dict[str, int]:
    latest_offer_ids = (
        db.query(func.max(SellLandOffer.id).label("offer_id"))
        .group_by(SellLandOffer.request_id, SellLandOffer.buyer_id)
        .subquery()
    )
    seller_pending = (
        db.query(func.count(SellLandOffer.id))
        .join(SellLandRequest, SellLandRequest.id == SellLandOffer.request_id)
        .join(latest_offer_ids, SellLandOffer.id == latest_offer_ids.c.offer_id)
        .filter(
            SellLandRequest.user_id == user_id,
            SellLandOffer.status == OfferStatus.PENDING.value,
            SellLandOffer.buyer_id != user_id,
        )
        .scalar()
        or 0
    )
    buyer_countered = (
        db.query(func.count(SellLandOffer.id))
        .join(latest_offer_ids, SellLandOffer.id == latest_offer_ids.c.offer_id)
        .filter(
            SellLandOffer.buyer_id == user_id,
            SellLandOffer.status == OfferStatus.COUNTERED.value,
        )
        .scalar()
        or 0
    )
    return {
        "seller_pending": int(seller_pending),
        "buyer_countered": int(buyer_countered),
        "total": int(seller_pending) + int(buyer_countered),
    }


def get_offer_by_id_for_buyer(db: Session, offer_id: int, buyer_id: int) -> SellLandOffer | None:
    return (
        db.query(SellLandOffer)
        .filter(
            SellLandOffer.id == offer_id,
            SellLandOffer.buyer_id == buyer_id,
        )
        .first()
    )


def get_offer_by_id(db: Session, request_id: int, offer_id: int) -> SellLandOffer | None:
    return (
        db.query(SellLandOffer)
        .filter(SellLandOffer.id == offer_id, SellLandOffer.request_id == request_id)
        .first()
    )


def get_booking_for_listing_buyer(db: Session, request_id: int, buyer_id: int) -> SellLandBooking | None:
    return (
        db.query(SellLandBooking)
        .filter(
            SellLandBooking.request_id == request_id,
            SellLandBooking.buyer_id == buyer_id,
        )
        .order_by(SellLandBooking.created_at.desc(), SellLandBooking.id.desc())
        .first()
    )


def get_current_booking_for_listing_buyer(db: Session, request_id: int, buyer_id: int) -> SellLandBooking | None:
    """Return the buyer's current booking, leaving cancelled bookings as history."""
    return (
        db.query(SellLandBooking)
        .filter(
            SellLandBooking.request_id == request_id,
            SellLandBooking.buyer_id == buyer_id,
            SellLandBooking.booking_status != BookingStatus.CANCELLED.value,
        )
        .order_by(SellLandBooking.created_at.desc(), SellLandBooking.id.desc())
        .first()
    )


def get_booking_by_id_for_buyer(db: Session, booking_id: int, buyer_id: int) -> SellLandBooking | None:
    return (
        db.query(SellLandBooking)
        .filter(
            SellLandBooking.id == booking_id,
            SellLandBooking.buyer_id == buyer_id,
        )
        .first()
    )


def create_booking(
    db: Session,
    request_id: int,
    buyer_id: int,
    buyer_name: str,
    buyer_mobile: str,
    deal_amount: float,
    aadhaar_number: str = "",
    pan_number: str = "",
    bank_account: str = "",
    booking_fee_amount: float = 1000.0,
    *,
    commit: bool = True,
) -> SellLandBooking:
    entity = SellLandBooking(
        request_id=request_id,
        buyer_id=buyer_id,
        buyer_name=buyer_name,
        buyer_mobile=buyer_mobile,
        aadhaar_number=aadhaar_number,
        pan_number=pan_number,
        bank_account=bank_account,
        deal_amount=deal_amount,
        booking_fee_amount=booking_fee_amount,
        payment_status=PaymentStatus.INITIATED.value,
        booking_status=BookingStatus.BOOKED.value,
    )
    db.add(entity)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(entity)
    return entity


def mark_booking_paid(
    db: Session,
    booking: SellLandBooking,
    method: str | None = None,
    transaction_id: str | None = None,
    *,
    commit: bool = True,
) -> SellLandBooking:
    booking.payment_status = PaymentStatus.SUCCESS.value
    booking.paid_at = datetime.utcnow()
    if method:
        booking.payment_method = method.strip()
    if transaction_id:
        booking.payment_transaction_id = transaction_id.strip()
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(booking)
    return booking


def mark_booking_confirmed(
    db: Session,
    booking: SellLandBooking,
    method: str | None = None,
    transaction_id: str | None = None,
    *,
    commit: bool = True,
) -> SellLandBooking:
    booking.booking_status = BookingStatus.CONFIRMED.value
    return mark_booking_paid(db, booking, method=method, transaction_id=transaction_id, commit=commit)


def mark_booking_failed(
    db: Session,
    booking: SellLandBooking,
    transaction_id: str | None = None,
    *,
    commit: bool = True,
) -> SellLandBooking:
    booking.payment_status = PaymentStatus.FAILED.value
    if transaction_id:
        booking.payment_transaction_id = transaction_id.strip()
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(booking)
    return booking


def mark_listing_booked(db: Session, listing: SellLandRequest, *, commit: bool = True) -> SellLandRequest:
    now = datetime.utcnow()
    listing.status = SellLandStatus.BOOKED.value
    listing.offer_locked_by_buyer_id = None
    listing.offer_lock_expires_at = None
    (
        db.query(SellLandOffer)
        .filter(
            SellLandOffer.request_id == listing.id,
            SellLandOffer.status.in_([OfferStatus.PENDING.value, OfferStatus.COUNTERED.value]),
        )
        .update(
            {
                SellLandOffer.status: OfferStatus.REJECTED.value,
                SellLandOffer.seller_response_at: now,
            },
            synchronize_session=False,
        )
    )
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(listing)
    return listing


def mark_listing_pending_after_payment(
    db: Session,
    listing: SellLandRequest,
    *,
    commit: bool = True,
) -> bool:
    if listing.status not in {SellLandStatus.DRAFT.value, SellLandStatus.REJECTED.value}:
        return False
    if not listing.listing_code:
        listing.listing_code = f"MB-{secrets.randbelow(900000) + 100000}"
    listing.is_draft = False
    listing.draft_step = 8
    listing.reviewed_at = None
    listing.rejection_reason = None
    listing.status = SellLandStatus.PENDING.value
    if commit:
        db.commit()
    else:
        db.flush()
    return True


def update_booking_documents(
    db: Session,
    booking: SellLandBooking,
    aadhaar_doc_url: str,
    aadhaar_doc_name: str,
    pan_doc_url: str,
    pan_doc_name: str,
    bank_doc_url: str,
    bank_doc_name: str,
) -> SellLandBooking:
    booking.aadhaar_doc_url = aadhaar_doc_url
    booking.aadhaar_doc_name = aadhaar_doc_name
    booking.pan_doc_url = pan_doc_url
    booking.pan_doc_name = pan_doc_name
    booking.bank_doc_url = bank_doc_url
    booking.bank_doc_name = bank_doc_name
    db.commit()
    db.refresh(booking)
    return booking


def list_paid_bookings_for_buyer(
    db: Session,
    buyer_id: int,
) -> list[tuple[SellLandBooking, SellLandRequest]]:
    return (
        db.query(SellLandBooking, SellLandRequest)
        .join(SellLandRequest, SellLandRequest.id == SellLandBooking.request_id)
        .filter(
            SellLandBooking.buyer_id == buyer_id,
            SellLandBooking.payment_status == PaymentStatus.SUCCESS.value,
        )
        .order_by(SellLandBooking.created_at.desc(), SellLandBooking.id.desc())
        .all()
    )


def apply_seller_accept_offer(
    db: Session,
    listing: SellLandRequest,
    accepted_offer: SellLandOffer,
    lock_hours: int = 48,
    clear_counter_amount: bool = True,
) -> SellLandOffer:
    now = datetime.utcnow()

    (
        db.query(SellLandOffer)
        .filter(
            SellLandOffer.request_id == listing.id,
            SellLandOffer.id != accepted_offer.id,
            SellLandOffer.status.in_([OfferStatus.PENDING.value, OfferStatus.COUNTERED.value]),
        )
        .update(
            {
                SellLandOffer.status: OfferStatus.REJECTED.value,
                SellLandOffer.seller_response_at: now,
            },
            synchronize_session=False,
        )
    )

    accepted_offer.status = OfferStatus.ACCEPTED.value
    accepted_offer.seller_response_at = now
    if clear_counter_amount:
        accepted_offer.counter_amount = None

    listing.offer_locked_by_buyer_id = accepted_offer.buyer_id
    listing.offer_lock_expires_at = now + timedelta(hours=lock_hours)
    listing.accepted_offer_id = accepted_offer.id

    db.commit()
    db.refresh(accepted_offer)
    db.refresh(listing)
    return accepted_offer


def apply_seller_reject_offer(db: Session, offer: SellLandOffer) -> SellLandOffer:
    offer.status = OfferStatus.REJECTED.value
    offer.seller_response_at = datetime.utcnow()
    db.commit()
    db.refresh(offer)
    return offer


def apply_seller_counter_offer(db: Session, offer: SellLandOffer, counter_amount: float) -> SellLandOffer:
    offer.status = OfferStatus.COUNTERED.value
    offer.counter_amount = counter_amount
    offer.seller_response_at = datetime.utcnow()
    db.commit()
    db.refresh(offer)
    return offer


def apply_buyer_reject_counter_offer(db: Session, offer: SellLandOffer) -> SellLandOffer:
    offer.status = OfferStatus.REJECTED.value
    db.commit()
    db.refresh(offer)
    return offer


def apply_admin_review_decision(
    db: Session,
    entity: SellLandRequest,
    reviewed_by_id: int,
    target_status: str,
    rejection_reason: str | None,
) -> SellLandRequest:
    entity.status = target_status
    entity.reviewed_by_id = reviewed_by_id
    entity.reviewed_at = datetime.utcnow()
    entity.rejection_reason = rejection_reason
    if target_status == SellLandStatus.APPROVED.value:
        # Reset any previous field officer decision so the case re-appears in FO queue
        entity.field_officer_reviewed_by_id = None
        entity.field_officer_reviewed_at = None
        entity.field_officer_decision = None
        entity.field_officer_notes = None
        entity.field_officer_rejection_reason = None
        entity.field_officer_visit_photo_url = None
        entity.field_officer_visit_photo_name = None
        entity.assigned_field_officer_id = None
        entity.lock_started_at = None
        entity.lock_expires_at = None
    db.commit()
    db.refresh(entity)
    return entity


def list_available_cases_for_field_officer(
    db: Session,
    field_officer_id: int,
    skip: int,
    limit: int,
) -> tuple[list[SellLandRequest], int]:
    now = datetime.utcnow()
    release_expired_case_locks(db, now=now)
    query = (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.status == SellLandStatus.APPROVED.value,
            SellLandRequest.field_officer_reviewed_at.is_(None),
            (
                (SellLandRequest.assigned_field_officer_id.is_(None))
                | (SellLandRequest.assigned_field_officer_id == field_officer_id)
            ),
        )
    )
    total = query.count()
    items = (
        query.order_by(SellLandRequest.reviewed_at.desc(), SellLandRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def count_available_cases_for_field_officer(db: Session) -> int:
    now = datetime.utcnow()
    release_expired_case_locks(db, now=now)
    return (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.status == SellLandStatus.APPROVED.value,
            SellLandRequest.field_officer_reviewed_at.is_(None),
            SellLandRequest.assigned_field_officer_id.is_(None),
        )
        .count()
    )


def count_available_cases_for_field_officer_user(db: Session, field_officer_id: int) -> int:
    now = datetime.utcnow()
    release_expired_case_locks(db, now=now)
    return (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.status == SellLandStatus.APPROVED.value,
            SellLandRequest.field_officer_reviewed_at.is_(None),
            (
                (SellLandRequest.assigned_field_officer_id.is_(None))
                | (SellLandRequest.assigned_field_officer_id == field_officer_id)
            ),
        )
        .count()
    )


def count_completed_visits_for_field_officer_user(db: Session, field_officer_id: int) -> int:
    return (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.field_officer_reviewed_by_id == field_officer_id,
            SellLandRequest.field_officer_reviewed_at.is_not(None),
        )
        .count()
    )


def release_expired_case_locks(db: Session, now: datetime | None = None) -> int:
    current_time = now or datetime.utcnow()
    updated = (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.status == SellLandStatus.APPROVED.value,
            SellLandRequest.lock_expires_at.is_not(None),
            SellLandRequest.lock_expires_at <= current_time,
        )
        .update(
            {
                SellLandRequest.assigned_field_officer_id: None,
                SellLandRequest.lock_started_at: None,
                SellLandRequest.lock_expires_at: None,
            },
            synchronize_session=False,
        )
    )
    if updated:
        db.commit()
    return updated


def get_active_case_for_field_officer(db: Session, field_officer_id: int) -> SellLandRequest | None:
    now = datetime.utcnow()
    release_expired_case_locks(db, now=now)
    return (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.status == SellLandStatus.APPROVED.value,
            SellLandRequest.field_officer_reviewed_at.is_(None),
            SellLandRequest.assigned_field_officer_id == field_officer_id,
            SellLandRequest.lock_expires_at.is_not(None),
            SellLandRequest.lock_expires_at > now,
        )
        .order_by(SellLandRequest.lock_expires_at.desc())
        .first()
    )


def list_locked_cases_for_admin(
    db: Session,
    skip: int,
    limit: int,
    reviewed_by_id: int | None = None,
) -> tuple[list[SellLandRequest], int]:
    now = datetime.utcnow()
    release_expired_case_locks(db, now=now)
    query = (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.status == SellLandStatus.APPROVED.value,
            SellLandRequest.field_officer_reviewed_at.is_(None),
            SellLandRequest.assigned_field_officer_id.is_not(None),
            SellLandRequest.lock_expires_at.is_not(None),
            SellLandRequest.lock_expires_at > now,
        )
    )
    if reviewed_by_id is not None:
        query = query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
    total = query.count()
    items = (
        query.order_by(SellLandRequest.lock_started_at.asc(), SellLandRequest.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def list_available_cases_for_admin(
    db: Session,
    skip: int,
    limit: int,
    reviewed_by_id: int | None = None,
) -> tuple[list[SellLandRequest], int]:
    now = datetime.utcnow()
    release_expired_case_locks(db, now=now)
    query = (
        db.query(SellLandRequest)
        .filter(
            SellLandRequest.status == SellLandStatus.APPROVED.value,
            SellLandRequest.field_officer_reviewed_at.is_(None),
            SellLandRequest.assigned_field_officer_id.is_(None),
        )
    )
    if reviewed_by_id is not None:
        query = query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
    total = query.count()
    items = (
        query.order_by(SellLandRequest.reviewed_at.desc(), SellLandRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def claim_case_for_field_officer(
    db: Session,
    request_id: int,
    field_officer_id: int,
    lock_hours: int = 12,
) -> tuple[SellLandRequest | None, str | None]:
    now = datetime.utcnow()
    release_expired_case_locks(db, now=now)

    existing_active = get_active_case_for_field_officer(db, field_officer_id)
    if existing_active and existing_active.id != request_id:
        return None, "You already have an active locked case"

    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status != SellLandStatus.APPROVED.value:
        return None, "Only approved listings can be claimed"
    if entity.field_officer_reviewed_at is not None:
        return None, "This case has already been reviewed by field officer"
    if entity.assigned_field_officer_id and entity.assigned_field_officer_id != field_officer_id:
        return None, "Case is already locked by another field officer"

    entity.assigned_field_officer_id = field_officer_id
    entity.lock_started_at = now
    entity.lock_expires_at = now + timedelta(hours=lock_hours)
    db.commit()
    db.refresh(entity)
    return entity, None


def release_case_for_field_officer(
    db: Session,
    request_id: int,
    field_officer_id: int,
) -> tuple[SellLandRequest | None, str | None]:
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status != SellLandStatus.APPROVED.value:
        return None, "Only approved listings can be released"
    if entity.assigned_field_officer_id != field_officer_id:
        return None, "You can only release your own locked case"

    entity.assigned_field_officer_id = None
    entity.lock_started_at = None
    entity.lock_expires_at = None
    db.commit()
    db.refresh(entity)
    return entity, None


def force_release_case_by_admin(
    db: Session,
    request_id: int,
) -> tuple[SellLandRequest | None, str | None]:
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status != SellLandStatus.APPROVED.value:
        return None, "Only approved listings can be force released"
    if entity.field_officer_reviewed_at is not None:
        return None, "Case already reviewed by field officer"
    if entity.assigned_field_officer_id is None:
        return None, "Case is not locked"

    entity.assigned_field_officer_id = None
    entity.lock_started_at = None
    entity.lock_expires_at = None
    db.commit()
    db.refresh(entity)
    return entity, None


def assign_case_to_field_officer_by_admin(
    db: Session,
    request_id: int,
    field_officer_id: int,
    lock_hours: int = 12,
) -> tuple[SellLandRequest | None, str | None]:
    now = datetime.utcnow()
    release_expired_case_locks(db, now=now)

    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status != SellLandStatus.APPROVED.value:
        return None, "Only approved listings can be assigned"
    if entity.field_officer_reviewed_at is not None:
        return None, "Case already reviewed by field officer"
    if entity.assigned_field_officer_id and entity.assigned_field_officer_id != field_officer_id:
        return None, "Case is already locked by another field officer"

    entity.assigned_field_officer_id = field_officer_id
    entity.lock_started_at = now
    entity.lock_expires_at = now + timedelta(hours=lock_hours)
    db.commit()
    db.refresh(entity)
    return entity, None


def apply_field_officer_review_decision(
    db: Session,
    entity: SellLandRequest,
    reviewed_by_id: int,
    decision: str,
    notes: str | None,
    rejection_reason: str | None,
) -> SellLandRequest:
    entity.status = SellLandStatus.FIELD_VERIFIED.value if decision == SellLandStatus.APPROVED.value else decision
    entity.field_officer_reviewed_by_id = reviewed_by_id
    entity.field_officer_reviewed_at = datetime.utcnow()
    entity.field_officer_decision = decision
    entity.field_officer_notes = notes
    entity.field_officer_rejection_reason = rejection_reason
    entity.assigned_field_officer_id = None
    entity.lock_started_at = None
    entity.lock_expires_at = None
    db.commit()
    db.refresh(entity)
    return entity


def list_field_verified_cases_for_admin(
    db: Session,
    skip: int,
    limit: int,
    reviewed_by_id: int | None = None,
) -> tuple[list[SellLandRequest], int]:
    query = db.query(SellLandRequest).filter(
        SellLandRequest.status.in_([SellLandStatus.FIELD_VERIFIED.value, SellLandStatus.APPROVED.value]),
        SellLandRequest.field_officer_decision == SellLandStatus.APPROVED.value,
        SellLandRequest.field_officer_reviewed_at.is_not(None),
    )
    if reviewed_by_id is not None:
        query = query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
    total = query.count()
    items = (
        query.order_by(SellLandRequest.field_officer_reviewed_at.desc(), SellLandRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def apply_admin_final_approval_decision(
    db: Session,
    entity: SellLandRequest,
    decision: str,
    rejection_reason: str | None = None,
) -> SellLandRequest:
    if decision == "approve_go_live":
        entity.status = SellLandStatus.LIVE.value
        entity.rejection_reason = None
    elif decision == "reject":
        entity.status = SellLandStatus.REJECTED.value
        entity.rejection_reason = rejection_reason
    elif decision == "reassign_to_field_officer":
        entity.status = SellLandStatus.APPROVED.value
        entity.field_officer_reviewed_by_id = None
        entity.field_officer_reviewed_at = None
        entity.field_officer_decision = None
        entity.field_officer_notes = None
        entity.field_officer_rejection_reason = None
        entity.field_officer_visit_photo_url = None
        entity.field_officer_visit_photo_name = None
        entity.assigned_field_officer_id = None
        entity.lock_started_at = None
        entity.lock_expires_at = None
        entity.rejection_reason = None
    db.commit()
    db.refresh(entity)
    return entity


def get_admin_workflow_summary_counts(db: Session, reviewed_by_id: int | None = None) -> dict[str, int]:
    release_expired_offer_locks(db)
    pending_admin_review = (
        db.query(SellLandRequest)
        .filter(SellLandRequest.status == SellLandStatus.PENDING.value)
        .count()
    )
    assigned_query = db.query(SellLandRequest).filter(
        SellLandRequest.status == SellLandStatus.APPROVED.value,
        SellLandRequest.field_officer_reviewed_at.is_(None),
    )
    verified_query = db.query(SellLandRequest).filter(
        SellLandRequest.status.in_([SellLandStatus.FIELD_VERIFIED.value, SellLandStatus.APPROVED.value]),
        SellLandRequest.field_officer_decision == SellLandStatus.APPROVED.value,
        SellLandRequest.field_officer_reviewed_at.is_not(None),
    )
    live_query = db.query(SellLandRequest).filter(SellLandRequest.status == SellLandStatus.LIVE.value)
    booked_query = db.query(SellLandRequest).filter(SellLandRequest.status == SellLandStatus.BOOKED.value)
    sold_query = db.query(SellLandRequest).filter(SellLandRequest.status == SellLandStatus.SOLD.value)
    locked_listing_query = db.query(SellLandRequest).filter(
        SellLandRequest.status == SellLandStatus.LIVE.value,
        SellLandRequest.offer_lock_expires_at.is_not(None),
        SellLandRequest.offer_lock_expires_at > datetime.utcnow(),
        SellLandRequest.accepted_offer_id.is_not(None),
    )
    rejected_query = db.query(SellLandRequest).filter(SellLandRequest.status == SellLandStatus.REJECTED.value)
    cancel_refund_query = db.query(SellLandRequest).filter(
        SellLandRequest.status == SellLandStatus.PROCESSING_REFUND.value,
        SellLandRequest.cancellation_requires_admin_review.is_(True),
        SellLandRequest.refund_forwarded_to_accounting_at.is_(None),
    )
    registry_pending_query = (
        db.query(SellLandBooking)
        .join(SellLandRequest, SellLandRequest.id == SellLandBooking.request_id)
        .filter(SellLandBooking.booking_status == BookingStatus.REGISTRY_DONE.value)
    )

    if reviewed_by_id is not None:
        assigned_query = assigned_query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
        verified_query = verified_query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
        live_query = live_query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
        booked_query = booked_query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
        sold_query = sold_query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
        locked_listing_query = locked_listing_query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
        rejected_query = rejected_query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
        cancel_refund_query = cancel_refund_query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
        registry_pending_query = registry_pending_query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)

    assigned_to_field_officer = assigned_query.count()
    field_verified_final_approval = verified_query.count()
    live_listings = live_query.count()
    booked_listings = booked_query.count()
    sold_listings = sold_query.count()
    locked_listings = locked_listing_query.count()
    rejected_listings = rejected_query.count()
    cancel_refund_management = cancel_refund_query.count()
    pending_registry_verification = registry_pending_query.count()
    return {
        "pending_admin_review": pending_admin_review,
        "assigned_to_field_officer": assigned_to_field_officer,
        "field_verified_final_approval": field_verified_final_approval,
        "live_listings": live_listings,
        "booked_listings": booked_listings,
        "sold_listings": sold_listings,
        "locked_listings": locked_listings,
        "rejected_listings": rejected_listings,
        "cancel_refund_management": cancel_refund_management,
        "pending_registry_verification": pending_registry_verification,
    }


def list_registry_pending_bookings(
    db: Session,
    skip: int,
    limit: int,
    reviewed_by_id: int | None = None,
) -> tuple[list[SellLandBooking], int]:
    query = (
        db.query(SellLandBooking)
        .join(SellLandRequest, SellLandRequest.id == SellLandBooking.request_id)
        .filter(SellLandBooking.booking_status == BookingStatus.REGISTRY_DONE.value)
    )
    if reviewed_by_id is not None:
        query = query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
    total = query.count()
    items = (
        query.order_by(SellLandBooking.created_at.desc(), SellLandBooking.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def list_registry_proofs_for_booking(
    db: Session,
    booking_id: int,
) -> list[SellLandRegistryProof]:
    return (
        db.query(SellLandRegistryProof)
        .filter(SellLandRegistryProof.booking_id == booking_id)
        .order_by(SellLandRegistryProof.created_at.desc(), SellLandRegistryProof.id.desc())
        .all()
    )


def add_registry_proof(
    db: Session,
    booking_id: int,
    file_url: str,
    file_name: str,
) -> SellLandRegistryProof:
    entity = SellLandRegistryProof(
        booking_id=booking_id,
        file_url=file_url,
        file_name=file_name,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def list_pending_refund_cases_for_admin(
    db: Session,
    skip: int,
    limit: int,
    reviewed_by_id: int | None = None,
) -> tuple[list[SellLandRequest], int]:
    query = db.query(SellLandRequest).filter(
        SellLandRequest.status == SellLandStatus.PROCESSING_REFUND.value,
        SellLandRequest.cancellation_requires_admin_review.is_(True),
        SellLandRequest.refund_forwarded_to_accounting_at.is_(None),
    )
    if reviewed_by_id is not None:
        query = query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
    total = query.count()
    items = (
        query.order_by(SellLandRequest.cancelled_at.desc(), SellLandRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def list_pending_refund_cases_for_accounting(
    db: Session,
    skip: int,
    limit: int,
) -> tuple[list[SellLandRequest], int]:
    query = db.query(SellLandRequest).filter(
        SellLandRequest.status == SellLandStatus.PROCESSING_REFUND.value,
        (
            SellLandRequest.cancellation_requires_admin_review.is_(False)
            | SellLandRequest.refund_forwarded_to_accounting_at.is_not(None)
        ),
    )
    total = query.count()
    items = (
        query.order_by(SellLandRequest.cancelled_at.desc(), SellLandRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def list_refund_history_for_accounting(
    db: Session,
    skip: int,
    limit: int,
) -> tuple[list[SellLandRequest], int]:
    query = db.query(SellLandRequest).filter(
        SellLandRequest.status == SellLandStatus.REFUND_SUCCESSFUL.value,
    )
    total = query.count()
    items = (
        query.order_by(SellLandRequest.refund_completed_at.desc(), SellLandRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def list_success_refund_cases_for_admin(
    db: Session,
    skip: int,
    limit: int,
    reviewed_by_id: int | None = None,
) -> tuple[list[SellLandRequest], int]:
    query = db.query(SellLandRequest).filter(
        SellLandRequest.status == SellLandStatus.REFUND_SUCCESSFUL.value,
        SellLandRequest.cancellation_requires_admin_review.is_(True),
        SellLandRequest.refund_forwarded_to_accounting_at.is_not(None),
    )
    if reviewed_by_id is not None:
        query = query.filter(SellLandRequest.reviewed_by_id == reviewed_by_id)
    total = query.count()
    items = (
        query.order_by(SellLandRequest.refund_completed_at.desc(), SellLandRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total
