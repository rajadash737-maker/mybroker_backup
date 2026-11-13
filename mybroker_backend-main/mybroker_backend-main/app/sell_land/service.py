import json
import logging
import os
from pathlib import Path
import secrets
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import quote_plus

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.media.url_utils import to_public_url
from app.core.config import settings
from app.sell_land.constants import (
    BookingStatus,
    DocumentType,
    MediaType,
    OfferStatus,
    OwnershipType,
    PaymentStatus,
    PriceType,
    SellLandStatus,
    get_allowed_documents_for_ownership,
    get_required_documents_for_ownership,
)
from app.sell_land.media_storage import (
    ALLOWED_DOC_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    save_booking_doc_file,
    save_listing_media_file,
)
from app.sell_land.schemas import SellLandMediaUploadResponse
from app.sell_land.models import SellLandBooking, SellLandMedia, SellLandOffer, SellLandPayment, SellLandRequest
from app.sell_land.repository import (
    add_media,
    apply_buyer_reject_counter_offer,
    apply_seller_accept_offer,
    apply_seller_counter_offer,
    apply_seller_reject_offer,
    create_favorite,
    create_or_update_offer_for_buyer,
    create_payment,
    create_payment_for_razorpay,
    create_sell_land_request,
    delete_favorite,
    delete_media,
    delete_sell_land_request,
    get_offer_by_id,
    get_favorite_for_user,
    get_favorite_counts_for_request_ids,
    get_offer_counts_for_request_ids,
    get_booking_by_id_for_buyer,
    get_booking_for_listing_buyer,
    get_live_sell_land_request_by_id,
    get_user_by_id,
    get_document_media_by_type,
    get_media_by_id,
    get_offer_by_id_for_buyer,
    get_payment_by_id,
    get_payment_by_provider_ref,
    get_sell_land_request_by_id,
    create_booking,
    list_registry_proofs_for_booking,
    list_favorite_request_ids_for_user,
    list_live_sell_land_requests,
    list_media_for_requests,
    list_media,
    list_offers_for_buyer,
    list_offers_for_request,
    list_paid_bookings_for_buyer,
    list_sell_land_requests_by_user,
    release_expired_offer_locks,
    mark_payment_success,
    mark_booking_paid,
    mark_listing_booked,
    mark_listing_pending_after_payment,
    update_booking_documents,
    update_boundary,
    update_sell_land_request,
    upsert_sell_land_draft,
)
import razorpay
from razorpay.errors import SignatureVerificationError
from app.notifications.service import notify_users
from app.settings.service import get_processing_fees
from app.services.notification_service import NotificationService
from app.sell_land.schemas import (
    BoundaryPoint,
    BuyerExploreLandCard,
    BuyerExploreLandDetailResponse,
    BuyerExploreLandListResponse,
    BuyerExploreLikeResponse,
    BuyerOfferActionResponse,
    BuyerOfferBookingStatus,
    BuyerOfferCreateRequest,
    BuyerOfferCreateResponse,
    BuyerOfferItem,
    BuyerOfferLandSummary,
    BuyerOfferListResponse,
    BuyerOfferTimelineEvent,
    BuyerBookingCreateRequest,
    BuyerBookingPreviewResponse,
    BuyerBookingPaymentRequest,
    ExploreSortType,
    RegistryProofItem,
    SellerOfferActionResponse,
    SellerOfferCounterRequest,
    SellerOfferItem,
    SellerOfferListResponse,
    SellLandCancelRequest,
    SellLandBoundaryRequest,
    SellLandCreateRequest,
    SellLandDraftUpsertRequest,
    SellLandPaymentInitRequest,
    SellLandPaymentMarkPaidRequest,
    SellLandDocumentRequirementsResponse,
    SellLandTrackingCardResponse,
    SellLandUpdateRequest,
    SellLandRazorpayOrderRequest,
    SellLandRazorpayOrderResponse,
    SellLandRazorpayVerifyRequest,
    SellLandRazorpayVerifyResponse,
)

MEDIA_ROOT = Path(__file__).resolve().parents[1] / "uploads" / "sell-land"
BOOKING_MEDIA_ROOT = settings.private_uploads_dir
DEFAULT_BOOKING_FEE_AMOUNT = 1000.0
logger = logging.getLogger(__name__)


_SELLER_PRICING_FIELDS = {
    "price_type",
    "expected_price",
}


def _prepare_seller_pricing_write(payload, existing: SellLandRequest | None = None):
    """Keep seller writes total-price-only without reinterpreting V1 records."""
    supplied = payload.model_fields_set
    has_pricing_fields = bool(supplied & _SELLER_PRICING_FIELDS)
    version_was_supplied = "pricing_version" in supplied
    current_version = int(getattr(existing, "pricing_version", 1) or 1) if existing else 1
    requested_version = payload.pricing_version

    if existing is None:
        if requested_version not in (None, 2):
            return None, "New seller drafts must use pricing_version=2"
        if payload.price_type is PriceType.PRICE_PER_UNIT:
            return None, "Seller pricing supports total land price only"
        return payload.model_copy(update={"pricing_version": 2}), None

    if current_version == 2:
        if payload.price_type is PriceType.PRICE_PER_UNIT and "price_type" in supplied:
            return None, "V2 seller pricing supports total land price only"
        if has_pricing_fields and requested_version != 2:
            return None, "V2 price updates require pricing_version=2"
        # Price fields omitted means preserve both stored price and version.
        if not has_pricing_fields:
            if version_was_supplied and requested_version != 2:
                payload = payload.model_copy(update={"pricing_version": 2})
            return payload, None
        return payload.model_copy(update={"pricing_version": 2}), None

    # Legacy V1 writes retain their original interpretation. An explicit V2
    # upgrade is only applied with an explicit total-price value.
    if requested_version == 2 and "expected_price" in supplied:
        existing_price_type = getattr(existing, "price_type", None)
        if isinstance(existing_price_type, str):
            try:
                existing_price_type = PriceType(existing_price_type)
            except ValueError:
                existing_price_type = None
        effective_price_type = payload.price_type or existing_price_type
        if effective_price_type is not PriceType.TOTAL_PRICE:
            return None, "V2 seller pricing supports total land price only"
        return payload.model_copy(update={"pricing_version": 2}), None
    if has_pricing_fields and getattr(existing, "price_type", None) in {
        PriceType.PRICE_PER_UNIT,
        PriceType.PRICE_PER_UNIT.value,
    }:
        return None, "Legacy per-unit listings require an explicit V2 total-price update"
    if requested_version == 2:
        # Supplying a version without a price is not an upgrade.
        return payload.model_copy(update={"pricing_version": 1}), None
    return payload, None


def _get_razorpay_client() -> razorpay.Client:
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise RuntimeError("Razorpay credentials are not configured")
    return razorpay.Client(auth=(key_id, key_secret))


def _to_paise(amount_inr: float) -> int:
    value = Decimal(str(amount_inr)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))
def _parse_boundary_points(raw_points: str | None) -> list[BoundaryPoint]:
    if not raw_points:
        return []
    try:
        payload = json.loads(raw_points)
        if not isinstance(payload, list):
            return []
        points: list[BoundaryPoint] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            points.append(BoundaryPoint.model_validate(entry))
    except (ValueError, TypeError):
        return []
    return points


def _amount_value(value: float | Decimal | None) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return int(value)
    return value


def _direct_booking_amount(
    expected_price: Decimal | int | float | None,
    pricing_version: int,
) -> Decimal | int | float | None:
    """Resolve a direct booking total, rounding V2 once to whole rupees."""
    if expected_price is None:
        return None
    if pricing_version != 2:
        return expected_price
    amount = Decimal(str(expected_price))
    return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _add_working_days(start_at: datetime, days: int) -> datetime:
    current = start_at
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _delete_media_file(media: SellLandMedia) -> None:
    if media.file_url.startswith("/media/private/listing/"):
        file_path = settings.private_uploads_dir / "listing" / f"request_{media.request_id}" / media.file_name
    else:
        file_path = MEDIA_ROOT / f"request_{media.request_id}" / media.file_name
    if file_path.exists():
        file_path.unlink()


def _is_offer_lock_active(entity: SellLandRequest) -> bool:
    if not entity.offer_lock_expires_at:
        return False
    return entity.offer_lock_expires_at > datetime.utcnow()


def _resolve_ownership_type(raw_value: str | None) -> OwnershipType:
    if not raw_value:
        return OwnershipType.SINGLE_OWNER
    try:
        return OwnershipType(raw_value)
    except ValueError:
        return OwnershipType.SINGLE_OWNER


def _build_buyer_offer_timeline(offer: SellLandOffer) -> list[BuyerOfferTimelineEvent]:
    timeline = [
        BuyerOfferTimelineEvent(
            key="offer_placed",
            label="Offer placed",
            at=offer.created_at,
        )
    ]
    if offer.seller_response_at:
        if offer.status == OfferStatus.COUNTERED.value:
            timeline.append(
                BuyerOfferTimelineEvent(
                    key="counter_received",
                    label="Seller sent counter offer",
                    at=offer.seller_response_at,
                )
            )
        elif offer.status == OfferStatus.ACCEPTED.value:
            timeline.append(
                BuyerOfferTimelineEvent(
                    key="seller_accepted",
                    label="Offer accepted by seller",
                    at=offer.seller_response_at,
                )
            )
        elif offer.status == OfferStatus.REJECTED.value:
            timeline.append(
                BuyerOfferTimelineEvent(
                    key="seller_rejected",
                    label="Offer rejected",
                    at=offer.seller_response_at,
                )
            )
        elif offer.status == OfferStatus.EXPIRED.value:
            timeline.append(
                BuyerOfferTimelineEvent(
                    key="window_expired",
                    label="Booking window expired",
                    at=offer.seller_response_at,
                )
            )
    elif offer.status == OfferStatus.REJECTED.value:
        timeline.append(
            BuyerOfferTimelineEvent(
                key="counter_rejected",
                label="Counter offer rejected by buyer",
                at=offer.updated_at,
            )
        )
    return timeline


def _derive_buyer_booking_state(
    listing: SellLandRequest,
    offer: SellLandOffer,
    buyer_id: int,
) -> tuple[BuyerOfferBookingStatus, str, bool, datetime | None]:
    is_active_lock = (
        listing.offer_locked_by_buyer_id == buyer_id
        and listing.accepted_offer_id == offer.id
        and _is_offer_lock_active(listing)
    )
    if offer.status == OfferStatus.COUNTERED.value:
        return BuyerOfferBookingStatus.COUNTER_RECEIVED, "Counter offer received", False, None
    if offer.status == OfferStatus.REJECTED.value:
        return BuyerOfferBookingStatus.REJECTED, "Rejected", False, None
    if offer.status == OfferStatus.ACCEPTED.value:
        if is_active_lock:
            return (
                BuyerOfferBookingStatus.ACCEPTED_BOOK_NOW,
                "Accepted - book within 48 hours",
                True,
                listing.offer_lock_expires_at,
            )
        return BuyerOfferBookingStatus.EXPIRED, "Booking window expired", False, listing.offer_lock_expires_at
    if offer.status == OfferStatus.EXPIRED.value:
        return BuyerOfferBookingStatus.EXPIRED, "Booking window expired", False, listing.offer_lock_expires_at
    return BuyerOfferBookingStatus.OFFER_SENT, "Waiting for seller response", False, None


def _normalize_booking_status(value: str | None) -> BuyerOfferBookingStatus | None:
    if not value:
        return None
    if value == BookingStatus.CONFIRMED.value:
        return BuyerOfferBookingStatus.BOOKED
    try:
        return BuyerOfferBookingStatus(value)
    except ValueError:
        return None


def _booking_status_label(status: BuyerOfferBookingStatus | None) -> str | None:
    if status is None:
        return None
    return {
        BuyerOfferBookingStatus.BOOKED: "Booked",
        BuyerOfferBookingStatus.IN_PROCESS: "In process",
        BuyerOfferBookingStatus.REGISTRY_SCHEDULED: "Registry scheduled",
        BuyerOfferBookingStatus.REGISTRY_DONE: "Registry done",
        BuyerOfferBookingStatus.SOLD: "Sold",
    }.get(status)


def _mark_listing_booked(db: Session, listing: SellLandRequest) -> None:
    mark_listing_booked(db, listing)


def create_request(db: Session, user_id: int, payload: SellLandCreateRequest) -> SellLandRequest:
    payload, error = _prepare_seller_pricing_write(payload)
    if error:
        raise ValueError(error)
    seller_fee, _ = get_processing_fees(db)
    return create_sell_land_request(db, user_id, payload, payment_required_amount=seller_fee)


def _sync_seller_processing_fee(db: Session, entity: SellLandRequest) -> SellLandRequest:
    if entity.payment_status == PaymentStatus.SUCCESS.value:
        return entity
    seller_fee, _ = get_processing_fees(db)
    if float(entity.payment_required_amount or 0.0) != float(seller_fee):
        entity.payment_required_amount = seller_fee
        db.commit()
        db.refresh(entity)
    return entity


def upsert_my_draft(
    db: Session,
    user_id: int,
    payload: SellLandDraftUpsertRequest,
    request_id: int | None = None,
) -> tuple[SellLandRequest | None, str | None]:
    was_rejected = False
    if request_id is not None:
        existing = get_sell_land_request_by_id(db, request_id)
        if not existing or existing.user_id != user_id:
            return None, "Sell land request not found"
        was_rejected = existing.status == SellLandStatus.REJECTED.value
        if not existing.is_draft:
            # Allow rejected listings to enter correction flow without creating
            # a new request or redoing payment.
            if existing.status == SellLandStatus.REJECTED.value:
                was_rejected = True
                existing.is_draft = True
            else:
                return None, "Only draft requests can use draft endpoint"

    payload, pricing_error = _prepare_seller_pricing_write(payload, existing=existing if request_id is not None else None)
    if pricing_error:
        return None, pricing_error
    entity = upsert_sell_land_draft(db, user_id, payload, request_id=request_id)
    entity = _sync_seller_processing_fee(db, entity)
    return entity, None


def list_my_requests(db: Session, user_id: int) -> list[SellLandRequest]:
    return list_sell_land_requests_by_user(db, user_id)


def list_my_request_tracking(db: Session, user_id: int) -> list[SellLandTrackingCardResponse]:
    items = list_sell_land_requests_by_user(db, user_id)
    request_ids = [item.id for item in items]
    likes_count_by_request_id = get_favorite_counts_for_request_ids(db, request_ids)
    offer_count_by_request_id = get_offer_counts_for_request_ids(db, request_ids)
    cards: list[SellLandTrackingCardResponse] = []

    for item in items:
        card = SellLandTrackingCardResponse.model_validate(item)
        card.likes_count = likes_count_by_request_id.get(item.id, 0)
        card.offer_count = offer_count_by_request_id.get(item.id, 0)
        booking = (
            db.query(SellLandBooking)
            .filter(SellLandBooking.request_id == item.id)
            .order_by(SellLandBooking.created_at.desc(), SellLandBooking.id.desc())
            .first()
        )
        if booking:
            card.deal_amount = _amount_value(booking.deal_amount)
            try:
                card.booking_status = BookingStatus(booking.booking_status)
            except ValueError:
                card.booking_status = None
            if item.status == SellLandStatus.SOLD.value:
                card.booking_status = BookingStatus.SOLD
            card.registry_date = booking.registry_date
            card.registry_time = booking.registry_time
            card.registry_location = booking.registry_location
            card.registry_proofs = [
                RegistryProofItem.model_validate(proof)
                for proof in list_registry_proofs_for_booking(db, booking.id)
            ]
        cards.append(card)

    return cards


def get_my_request(db: Session, user_id: int, request_id: int) -> SellLandRequest | None:
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity or entity.user_id != user_id:
        return None
    return _sync_seller_processing_fee(db, entity)


def update_my_request(
    db: Session,
    user_id: int,
    request_id: int,
    payload: SellLandUpdateRequest,
) -> tuple[SellLandRequest | None, str | None]:
    entity = get_my_request(db, user_id, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status in {SellLandStatus.SOLD.value, SellLandStatus.BOOKED.value}:
        return None, "Booked request cannot be updated"
    if entity.status in {
        SellLandStatus.PROCESSING_REFUND.value,
        SellLandStatus.REFUND_SUCCESSFUL.value,
    }:
        return None, "Cancelled request cannot be updated"

    payload, pricing_error = _prepare_seller_pricing_write(payload, existing=entity)
    if pricing_error:
        return None, pricing_error
    updated = update_sell_land_request(db, entity, payload)
    return updated, None


def update_my_boundary(
    db: Session,
    user_id: int,
    request_id: int,
    payload: SellLandBoundaryRequest,
) -> tuple[SellLandRequest | None, str | None]:
    entity = get_my_request(db, user_id, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status in {
        SellLandStatus.PROCESSING_REFUND.value,
        SellLandStatus.REFUND_SUCCESSFUL.value,
    }:
        return None, "Cancelled request cannot be updated"

    updated = update_boundary(db, entity, payload)
    return updated, None


def upload_photo(
    db: Session,
    user_id: int,
    request_id: int,
    file: UploadFile,
) -> tuple[SellLandMedia | None, str | None]:
    entity = get_my_request(db, user_id, request_id)
    if not entity:
        return None, "Sell land request not found"

    try:
        file_name, file_url = save_listing_media_file(
            file=file,
            request_id=request_id,
            media_root=MEDIA_ROOT,
            allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
        )
    except ValueError as exc:
        return None, str(exc)

    media = add_media(
        db=db,
        request_id=request_id,
        media_type=MediaType.PHOTO,
        file_url=file_url,
        file_name=file_name,
        document_type=None,
        is_required=False,
    )
    return media, None


def upload_document(
    db: Session,
    user_id: int,
    request_id: int,
    document_type: DocumentType,
    file: UploadFile,
) -> tuple[SellLandMedia | None, str | None]:
    entity = get_my_request(db, user_id, request_id)
    if not entity:
        return None, "Sell land request not found"
    ownership_type = _resolve_ownership_type(entity.ownership_type)
    allowed_docs = get_allowed_documents_for_ownership(ownership_type)
    if document_type not in allowed_docs:
        allowed_labels = ", ".join(doc.value for doc in allowed_docs)
        return None, f"Invalid document for seller type '{ownership_type.value}'. Allowed: {allowed_labels}"

    try:
        file_name, file_url = save_listing_media_file(
            file=file,
            request_id=request_id,
            media_root=settings.private_uploads_dir,
            allowed_extensions=ALLOWED_DOC_EXTENSIONS,
            private=True,
        )
    except ValueError as exc:
        return None, str(exc)

    existing = get_document_media_by_type(db, request_id, document_type.value)
    if existing:
        _delete_media_file(existing)
        delete_media(db, existing)

    media = add_media(
        db=db,
        request_id=request_id,
        media_type=MediaType.DOCUMENT,
        file_url=file_url,
        file_name=file_name,
        document_type=document_type.value,
        is_required=document_type in get_required_documents_for_ownership(ownership_type),
    )
    return media, None


def list_my_media(
    db: Session,
    user_id: int,
    request_id: int,
) -> tuple[list[SellLandMedia] | None, str | None]:
    entity = get_my_request(db, user_id, request_id)
    if not entity:
        return None, "Sell land request not found"
    return list_media(db, request_id), None


def delete_my_media(
    db: Session,
    user_id: int,
    request_id: int,
    media_id: int,
) -> str | None:
    entity = get_my_request(db, user_id, request_id)
    if not entity:
        return "Sell land request not found"

    media = get_media_by_id(db, media_id)
    if not media or media.request_id != request_id:
        return "Media not found"

    _delete_media_file(media.request_id, media.file_name)
    delete_media(db, media)
    return None


def initiate_payment(
    db: Session,
    user_id: int,
    payload: SellLandPaymentInitRequest,
) -> tuple[SellLandPayment | None, str | None]:
    entity = get_my_request(db, user_id, payload.request_id)
    if not entity:
        return None, "Sell land request not found"

    payment = create_payment(db, payload, amount=entity.payment_required_amount)
    return payment, None


def mark_payment_paid(
    db: Session,
    user_id: int,
    payload: SellLandPaymentMarkPaidRequest,
) -> tuple[SellLandPayment | None, str | None]:
    payment = get_payment_by_id(db, payload.payment_id)
    if not payment:
        return None, "Payment not found"

    request = get_my_request(db, user_id, payment.request_id)
    if not request:
        return None, "Sell land request not found"

    marked = mark_payment_success(db, payment, provider_ref=payload.provider_ref)
    return marked, None


def create_seller_razorpay_order(
    db: Session,
    user_id: int,
    payload: SellLandRazorpayOrderRequest,
) -> tuple[SellLandRazorpayOrderResponse | None, str | None]:
    entity = get_my_request(db, user_id, payload.request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.payment_status == PaymentStatus.SUCCESS.value:
        return None, "Payment already completed"

    amount_inr = float(entity.payment_required_amount or 0.0)
    amount_paise = _to_paise(amount_inr)
    if amount_paise <= 0:
        return None, "Invalid payment amount"

    try:
        client = _get_razorpay_client()
    except RuntimeError:
        return None, "Payment gateway is not configured"

    try:
        order = client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {"seller_id": str(user_id), "request_id": str(entity.id), "purpose": "listing_fee"},
            }
        )
    except Exception:
        return None, "Payment gateway error"

    order_id = order.get("id")
    if not order_id:
        return None, "Payment gateway returned invalid order"
    try:
        order_amount = int(order.get("amount", -1))
    except (TypeError, ValueError):
        order_amount = -1
    if order_amount != amount_paise or order.get("currency", "INR") != "INR":
        return None, "Payment gateway returned invalid order terms"

    create_payment_for_razorpay(
        db=db,
        request_id=entity.id,
        amount=amount_inr,
        order_id=order_id,
    )

    return SellLandRazorpayOrderResponse(
        order_id=order_id,
        amount=int(order.get("amount", amount_paise)),
        currency=order.get("currency", "INR"),
    ), None


def verify_seller_razorpay_payment(
    db: Session,
    user_id: int,
    payload: SellLandRazorpayVerifyRequest,
) -> tuple[SellLandRazorpayVerifyResponse | None, str | None]:
    payment = get_payment_by_provider_ref(db, payload.razorpay_order_id, for_update=True)
    if not payment:
        return None, "Payment not found"

    request = get_my_request(db, user_id, payment.request_id)
    if not request:
        return None, "Sell land request not found"

    def _notify_admins(request_id: int) -> None:
        try:
            notify_result = NotificationService(db=db).notify_property_uploaded(request_id)
            skipped = sum(1 for item in notify_result.get("results", []) if item.get("skipped"))
            logger.info(
                "Property upload notifications: request_id=%s requested=%s sent=%s skipped=%s",
                request_id,
                notify_result.get("requested"),
                notify_result.get("sent"),
                skipped,
            )
        except Exception as exc:  # noqa: BLE001 - avoid blocking payment verification
            logger.warning("FCM notification failed for listing %s: %s", request_id, exc)

    if payment.status == PaymentStatus.SUCCESS.value:
        if payment.gateway_payment_id != payload.razorpay_payment_id:
            return None, "Payment was already verified with a different payment"
        status_updated = mark_listing_pending_after_payment(db, request, commit=False)
        db.commit()
        logger.info(
            "Payment already marked success; listing_status_updated=%s request_id=%s",
            status_updated,
            request.id,
        )
        _notify_admins(request.id)
        return (
            SellLandRazorpayVerifyResponse(
                status="success",
                order_id=payload.razorpay_order_id,
                payment_id=payload.razorpay_payment_id,
            ),
            None,
        )

    try:
        client = _get_razorpay_client()
    except RuntimeError:
        return None, "Payment gateway is not configured"

    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": payload.razorpay_order_id,
                "razorpay_payment_id": payload.razorpay_payment_id,
                "razorpay_signature": payload.razorpay_signature,
            }
        )
        provider_payment = client.payment.fetch(payload.razorpay_payment_id)
    except SignatureVerificationError:
        return None, "Invalid payment signature"
    except Exception:
        return None, "Payment verification error"

    try:
        provider_amount = int(provider_payment.get("amount", -1)) if isinstance(provider_payment, dict) else -1
    except (TypeError, ValueError):
        provider_amount = -1
    if (
        not isinstance(provider_payment, dict)
        or provider_payment.get("order_id") != payment.provider_ref
        or provider_amount != _to_paise(float(payment.amount))
        or provider_payment.get("currency") != "INR"
        or provider_payment.get("status") != "captured"
    ):
        return None, "Payment details do not match the order"

    mark_payment_success(
        db,
        payment,
        provider_ref=payment.provider_ref,
        gateway_payment_id=payload.razorpay_payment_id,
        commit=False,
    )
    status_updated = mark_listing_pending_after_payment(db, request, commit=False)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info(
        "Payment verified and marked success; listing_status_updated=%s request_id=%s",
        status_updated,
        request.id,
    )
    _notify_admins(request.id)
    return (
        SellLandRazorpayVerifyResponse(
            status="success",
            order_id=payload.razorpay_order_id,
            payment_id=payload.razorpay_payment_id,
        ),
        None,
    )


def _required_fields_missing(entity: SellLandRequest) -> list[str]:
    if not entity.location:
        location_parts = [part for part in [entity.city, entity.state] if part]
        if location_parts:
            entity.location = ", ".join(location_parts)

    required_fields = (
        "title",
        "owner_name",
        "owner_mobile",
        "city",
        "state",
        "pincode",
        "area",
        "expected_price",
    )
    missing = []
    for field in required_fields:
        if getattr(entity, field) in (None, ""):
            missing.append(field)
    return missing


def _has_required_documents(media_items: list[SellLandMedia], ownership_type: OwnershipType) -> bool:
    required_documents = {doc.value for doc in get_required_documents_for_ownership(ownership_type)}
    uploaded = {
        item.document_type
        for item in media_items
        if item.media_type == MediaType.DOCUMENT.value and item.document_type
    }
    return required_documents.issubset(uploaded)


def get_document_requirements(
    ownership_type: OwnershipType | None = None,
) -> list[SellLandDocumentRequirementsResponse]:
    types = [ownership_type] if ownership_type else [
        OwnershipType.SINGLE_OWNER,
        OwnershipType.MULTI_OWNER,
        OwnershipType.INHERITED_LAND,
    ]
    return [
        SellLandDocumentRequirementsResponse(
            ownership_type=entry,
            required_document_types=list(get_required_documents_for_ownership(entry)),
        )
        for entry in types
    ]


def submit_my_request(
    db: Session,
    user_id: int,
    request_id: int,
) -> tuple[SellLandRequest | None, str | None]:
    entity = get_my_request(db, user_id, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status in {
        SellLandStatus.PROCESSING_REFUND.value,
        SellLandStatus.REFUND_SUCCESSFUL.value,
    }:
        return None, "Cancelled request cannot be submitted"

    missing_fields = _required_fields_missing(entity)
    if missing_fields:
        return None, f"Missing required fields: {', '.join(missing_fields)}"

    if not entity.boundary_points:
        return None, "Boundary points are required before submit"

    media_items = list_media(db, request_id)
    has_photo = any(item.media_type == MediaType.PHOTO.value for item in media_items)
    if not has_photo:
        return None, "At least one land photo is required before submit"
    ownership_type = _resolve_ownership_type(entity.ownership_type)
    if not _has_required_documents(media_items, ownership_type):
        required_docs = ", ".join(doc.value for doc in get_required_documents_for_ownership(ownership_type))
        return None, f"Missing required documents for seller type '{ownership_type.value}'. Required: {required_docs}"

    if entity.payment_status != PaymentStatus.SUCCESS.value:
        return None, "Payment must be successful before final submit"

    if not entity.listing_code:
        entity.listing_code = f"MB-{secrets.randbelow(900000) + 100000}"

    entity.is_draft = False
    entity.draft_step = 8
    if entity.status == SellLandStatus.REJECTED.value:
        entity.reviewed_at = None
        entity.rejection_reason = None
        entity.status = SellLandStatus.PENDING.value
    else:
        entity.status = SellLandStatus.PENDING.value
    db.commit()
    db.refresh(entity)
    return entity, None


def delete_my_request(db: Session, user_id: int, request_id: int) -> str | None:
    entity = get_my_request(db, user_id, request_id)
    if not entity:
        return "Sell land request not found"
    if entity.status in {SellLandStatus.SOLD.value, SellLandStatus.BOOKED.value}:
        return "Booked request cannot be deleted"
    if entity.status in {
        SellLandStatus.PROCESSING_REFUND.value,
        SellLandStatus.REFUND_SUCCESSFUL.value,
    }:
        return "Cancelled request cannot be deleted"

    delete_sell_land_request(db, entity)
    return None


def cancel_my_request(
    db: Session,
    user_id: int,
    request_id: int,
    payload: SellLandCancelRequest,
) -> tuple[SellLandRequest | None, str | None]:
    entity = get_my_request(db, user_id, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.is_draft:
        return None, "Draft listing cannot be cancelled"
    if entity.payment_status != PaymentStatus.SUCCESS.value:
        return None, "Payment not completed for this listing"
    if entity.status in {SellLandStatus.SOLD.value, SellLandStatus.BOOKED.value}:
        return None, "Booked request cannot be cancelled"
    if entity.status in {
        SellLandStatus.PROCESSING_REFUND.value,
        SellLandStatus.REFUND_SUCCESSFUL.value,
    }:
        return None, "Listing is already cancelled"

    now = datetime.utcnow()
    cancellation_reason = payload.reason.value
    if payload.notes:
        cancellation_reason = f"{cancellation_reason}: {payload.notes}"

    entity.status_before_cancellation = entity.status
    entity.status = SellLandStatus.PROCESSING_REFUND.value
    entity.is_draft = False
    entity.cancellation_reason = cancellation_reason
    entity.refund_upi_id = payload.upi_id
    entity.cancelled_at = now
    entity.refund_due_at = _add_working_days(now, 3)
    entity.refund_completed_at = None
    entity.cancellation_requires_admin_review = entity.reviewed_by_id is not None
    if entity.cancellation_requires_admin_review:
        entity.refund_forwarded_to_accounting_by_id = None
        entity.refund_forwarded_to_accounting_at = None
    else:
        # Direct cancellation path: never reviewed by admin, so send straight to accounting queue.
        entity.refund_forwarded_to_accounting_by_id = None
        entity.refund_forwarded_to_accounting_at = now
    entity.assigned_field_officer_id = None
    entity.lock_started_at = None
    entity.lock_expires_at = None
    entity.offer_locked_by_buyer_id = None
    entity.offer_lock_expires_at = None
    entity.accepted_offer_id = None

    db.commit()
    db.refresh(entity)
    return entity, None


def _build_buyer_explore_card(
    request: SellLandRequest,
    media_by_request_id: dict[int, list[SellLandMedia]],
    liked_request_ids: set[int],
    likes_count: int = 0,
) -> BuyerExploreLandCard:
    photos = []
    for media in media_by_request_id.get(request.id, []):
        if media.media_type == MediaType.PHOTO.value:
            photo_url = to_public_url(media.file_url) or media.file_url
            photos.append(photo_url)

    from app.sell_land.instagram_urls import normalize_instagram_url

    return BuyerExploreLandCard(
        id=request.id,
        title=request.title,
        instagram_url=normalize_instagram_url(getattr(request, "instagram_url", None)),
        land_type=request.land_type,
        listing_status=request.status,
        price_type=request.price_type,
        expected_price=request.expected_price,
        area=request.area,
        area_unit=request.area_unit,
        location=request.location,
        city=request.city,
        state=request.state,
        pincode=request.pincode,
        boundary_points=_parse_boundary_points(request.boundary_points),
        images=photos,
        is_liked=request.id in liked_request_ids,
        likes_count=likes_count,
        is_offer_locked=_is_offer_lock_active(request),
        offer_lock_expires_at=request.offer_lock_expires_at,
        created_at=request.created_at,
    )


def get_explore_land_detail(
    db: Session,
    request_id: int,
) -> BuyerExploreLandDetailResponse | None:
    request = get_live_sell_land_request_by_id(db, request_id)
    if not request:
        return None

    media_items = list_media(db, request_id)
    photos = [
        to_public_url(media.file_url) or media.file_url
        for media in media_items
        if media.media_type == MediaType.PHOTO.value
    ]
    documents = [
        SellLandMediaUploadResponse.model_validate(media)
        for media in media_items
        if media.media_type == MediaType.DOCUMENT.value
    ]
    map_query = ", ".join(part for part in [request.location, request.city, request.state, request.pincode] if part)
    map_url = (
        f"https://www.google.com/maps/search/?api=1&query={quote_plus(map_query)}" if map_query else None
    )

    return BuyerExploreLandDetailResponse(
        id=request.id,
        user_id=request.user_id,
        title=request.title,
        owner_category=request.owner_category,
        land_type=request.land_type,
        listing_status=request.status,
        status_label="available",
        price_type=request.price_type,
        expected_price=request.expected_price,
        area=request.area,
        area_unit=request.area_unit,
        location=request.location,
        city=request.city,
        state=request.state,
        pincode=request.pincode,
        boundary_points=_parse_boundary_points(request.boundary_points),
        images=photos,
        is_offer_locked=_is_offer_lock_active(request),
        offer_lock_expires_at=request.offer_lock_expires_at,
        map_query=map_query or None,
        map_url=map_url,
        documents=documents,
    )


def get_buyer_land_detail_for_buyer(
    db: Session,
    request_id: int,
    buyer_id: int,
) -> tuple[BuyerExploreLandDetailResponse | None, str | None]:
    request = get_sell_land_request_by_id(db, request_id)
    if not request:
        return None, "Sell land request not found"

    has_offer = (
        db.query(SellLandOffer)
        .filter(
            SellLandOffer.request_id == request_id,
            SellLandOffer.buyer_id == buyer_id,
        )
        .first()
    )
    booking = get_booking_for_listing_buyer(db, request_id, buyer_id)

    if not has_offer and not booking:
        return None, "Not authorized"

    media_items = list_media(db, request_id)
    photos = [
        to_public_url(media.file_url) or media.file_url
        for media in media_items
        if media.media_type == MediaType.PHOTO.value
    ]
    documents = [
        SellLandMediaUploadResponse.model_validate(media)
        for media in media_items
        if media.media_type == MediaType.DOCUMENT.value
    ]
    map_query = ", ".join(part for part in [request.location, request.city, request.state, request.pincode] if part)
    map_url = (
        f"https://www.google.com/maps/search/?api=1&query={quote_plus(map_query)}" if map_query else None
    )

    deal_amount = booking.deal_amount if booking else None
    booking_status: BookingStatus | None = None
    registry_date = None
    registry_time = None
    registry_location = None
    registry_proofs: list[RegistryProofItem] = []
    if booking:
        try:
            booking_status = BookingStatus(booking.booking_status)
        except ValueError:
            booking_status = None
        if request.status == SellLandStatus.SOLD.value:
            booking_status = BookingStatus.SOLD
        registry_date = booking.registry_date
        registry_time = booking.registry_time
        registry_location = booking.registry_location
        registry_proofs = [
            RegistryProofItem.model_validate(item)
            for item in list_registry_proofs_for_booking(db, booking.id)
        ]

    return (
        BuyerExploreLandDetailResponse(
            id=request.id,
            user_id=request.user_id,
            title=request.title,
            owner_category=request.owner_category,
            land_type=request.land_type,
            listing_status=request.status,
            status_label=request.status,
            price_type=request.price_type,
            expected_price=request.expected_price,
            area=request.area,
            area_unit=request.area_unit,
            location=request.location,
            city=request.city,
            state=request.state,
            pincode=request.pincode,
            boundary_points=_parse_boundary_points(request.boundary_points),
            images=photos,
            is_offer_locked=_is_offer_lock_active(request),
            offer_lock_expires_at=request.offer_lock_expires_at,
            map_query=map_query or None,
            map_url=map_url,
            documents=documents,
            deal_amount=_amount_value(deal_amount),
            booking_status=booking_status,
            registry_date=registry_date,
            registry_time=registry_time,
            registry_location=registry_location,
            registry_proofs=registry_proofs,
        ),
        None,
    )


def list_explore_lands(
    db: Session,
    user_id: int,
    search: str | None,
    min_price: float | None,
    max_price: float | None,
    min_area: float | None,
    max_area: float | None,
    sort_by: ExploreSortType,
    skip: int,
    limit: int,
) -> BuyerExploreLandListResponse:
    items, total = list_live_sell_land_requests(
        db=db,
        search=search,
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        max_area=max_area,
        sort_by=sort_by.value,
        skip=skip,
        limit=limit,
    )
    request_ids = [item.id for item in items]
    media = list_media_for_requests(db, request_ids)
    liked_request_ids = list_favorite_request_ids_for_user(db, user_id, request_ids)
    favorite_counts = get_favorite_counts_for_request_ids(db, request_ids)

    media_by_request_id: dict[int, list[SellLandMedia]] = {}
    for entry in media:
        media_by_request_id.setdefault(entry.request_id, []).append(entry)

    cards = [
        _build_buyer_explore_card(
            request=item,
            media_by_request_id=media_by_request_id,
            liked_request_ids=liked_request_ids,
            likes_count=favorite_counts.get(item.id, 0),
        )
        for item in items
    ]
    return BuyerExploreLandListResponse(total=total, skip=skip, limit=limit, items=cards)


def like_explore_land(db: Session, user_id: int, request_id: int) -> tuple[BuyerExploreLikeResponse | None, str | None]:
    listing = get_live_sell_land_request_by_id(db, request_id)
    if not listing:
        return None, "Sell land request not found"

    existing = get_favorite_for_user(db, user_id, request_id)
    if existing:
        count = get_favorite_counts_for_request_ids(db, [request_id]).get(request_id, 0)
        return BuyerExploreLikeResponse(status="Liked", request_id=request_id, liked=True, likes_count=count), None

    try:
        create_favorite(db, user_id, request_id)
    except IntegrityError:
        db.rollback()
    count = get_favorite_counts_for_request_ids(db, [request_id]).get(request_id, 0)
    return BuyerExploreLikeResponse(status="Liked", request_id=request_id, liked=True, likes_count=count), None


def unlike_explore_land(
    db: Session,
    user_id: int,
    request_id: int,
) -> tuple[BuyerExploreLikeResponse | None, str | None]:
    listing = get_live_sell_land_request_by_id(db, request_id)
    if not listing:
        return None, "Sell land request not found"

    existing = get_favorite_for_user(db, user_id, request_id)
    if existing:
        delete_favorite(db, existing)
    count = get_favorite_counts_for_request_ids(db, [request_id]).get(request_id, 0)
    return BuyerExploreLikeResponse(status="Unliked", request_id=request_id, liked=False, likes_count=count), None


def make_offer_on_explore_land(
    db: Session,
    user_id: int,
    request_id: int,
    payload: BuyerOfferCreateRequest,
) -> tuple[BuyerOfferCreateResponse | None, str | None]:
    release_expired_offer_locks(db)
    listing = get_live_sell_land_request_by_id(db, request_id)
    if not listing:
        return None, "Sell land request not found"
    if listing.user_id == user_id:
        return None, "You cannot make an offer on your own listing"
    if _is_offer_lock_active(listing) and listing.offer_locked_by_buyer_id != user_id:
        return None, "Listing is temporarily locked for another buyer"

    offer = create_or_update_offer_for_buyer(
        db=db,
        request_id=request_id,
        buyer_id=user_id,
        offered_amount=payload.amount,
    )
    try:
        seller = get_user_by_id(db, listing.user_id)
        buyer = get_user_by_id(db, user_id)
        if seller and buyer:
            buyer_name = (buyer.fullname or "A buyer").strip()
            notify_users(
                db=db,
                users=[seller],
                title="New Offer Received",
                body=f"{buyer_name} sent an offer on your listing",
                notif_type="OFFER_RECEIVED",
                role_target=seller.role,
                reference_id=str(listing.id),
            )
    except Exception:
        logger.exception("Failed to send seller offer notification")
    return (
        BuyerOfferCreateResponse(
            status="Offer sent",
            offer_id=offer.id,
            request_id=request_id,
            offered_amount=_amount_value(offer.offered_amount),
            offer_status=OfferStatus.PENDING,
        ),
        None,
    )


def list_my_buyer_offers(
    db: Session,
    user_id: int,
) -> BuyerOfferListResponse:
    release_expired_offer_locks(db)
    rows = list_offers_for_buyer(db, buyer_id=user_id)
    items: list[BuyerOfferItem] = []
    offer_request_ids: set[int] = set()
    for offer, listing in rows:
        offer_request_ids.add(listing.id)
        booking_status, status_label, is_active_window, lock_expires_at = _derive_buyer_booking_state(
            listing=listing,
            offer=offer,
            buyer_id=user_id,
        )
        booking = get_booking_for_listing_buyer(db, listing.id, user_id)
        registry_date = None
        registry_time = None
        registry_location = None
        if booking and booking.payment_status == PaymentStatus.SUCCESS.value:
            normalized_status = _normalize_booking_status(booking.booking_status)
            if listing.status == SellLandStatus.SOLD.value:
                booking_status = BuyerOfferBookingStatus.SOLD
                status_label = _booking_status_label(booking_status) or "Sold"
            else:
                booking_status = normalized_status or BuyerOfferBookingStatus.BOOKED
                status_label = _booking_status_label(booking_status) or "Booked"
            is_active_window = False
            lock_expires_at = None
            registry_date = booking.registry_date
            registry_time = booking.registry_time
            registry_location = booking.registry_location
        final_amount = (
            offer.counter_amount
            if offer.status in {OfferStatus.COUNTERED.value, OfferStatus.ACCEPTED.value} and offer.counter_amount
            else offer.offered_amount
        )
        items.append(
            BuyerOfferItem(
                offer_id=offer.id,
                request_id=offer.request_id,
                offered_amount=_amount_value(offer.offered_amount),
                counter_amount=_amount_value(offer.counter_amount),
                final_amount=_amount_value(final_amount),
                offer_status=offer.status,
                booking_status=booking_status,
                status_label=status_label,
                is_book_window_active=is_active_window,
                offer_lock_expires_at=lock_expires_at,
                created_at=offer.created_at,
                updated_at=offer.updated_at,
                seller_response_at=offer.seller_response_at,
                can_accept_counter=offer.status == OfferStatus.COUNTERED.value,
                can_reject_counter=offer.status == OfferStatus.COUNTERED.value,
                timeline=_build_buyer_offer_timeline(offer),
                registry_date=registry_date,
                registry_time=registry_time,
                registry_location=registry_location,
                land=BuyerOfferLandSummary(
                    id=listing.id,
                    title=listing.title,
                    land_type=listing.land_type,
                    location=listing.location,
                    city=listing.city,
                    state=listing.state,
                    expected_price=listing.expected_price,
                ),
            )
        )
    booking_rows = list_paid_bookings_for_buyer(db, buyer_id=user_id)
    for booking, listing in booking_rows:
        if listing.id in offer_request_ids:
            continue
        items.append(
            BuyerOfferItem(
                offer_id=booking.id,
                request_id=listing.id,
                offered_amount=_amount_value(booking.deal_amount),
                counter_amount=None,
                final_amount=_amount_value(booking.deal_amount),
                offer_status=OfferStatus.ACCEPTED.value,
                booking_status=BuyerOfferBookingStatus.BOOKED,
                status_label="Booked",
                is_book_window_active=False,
                offer_lock_expires_at=None,
                created_at=booking.created_at,
                updated_at=booking.created_at,
                seller_response_at=None,
                can_accept_counter=False,
                can_reject_counter=False,
                timeline=[],
                registry_date=booking.registry_date,
                registry_time=booking.registry_time,
                registry_location=booking.registry_location,
                land=BuyerOfferLandSummary(
                    id=listing.id,
                    title=listing.title,
                    land_type=listing.land_type,
                    location=listing.location,
                    city=listing.city,
                    state=listing.state,
                    expected_price=listing.expected_price,
                ),
            )
        )
    return BuyerOfferListResponse(total=len(items), items=items)


def get_booking_preview_for_buyer(
    db: Session,
    user_id: int,
    request_id: int,
) -> tuple[BuyerBookingPreviewResponse | None, str | None]:
    release_expired_offer_locks(db)
    listing = get_live_sell_land_request_by_id(db, request_id)
    if not listing:
        return None, "Sell land request not found"

    total_amount = listing.expected_price
    deal_amount = total_amount
    booking_status: BuyerOfferBookingStatus | None = None
    status_label: str | None = None
    is_book_window_active = False
    offer_lock_expires_at = listing.offer_lock_expires_at
    offer_id: int | None = None
    offer_status: OfferStatus | None = None
    can_book = True

    if listing.accepted_offer_id is not None:
        offer = get_offer_by_id(db, request_id=listing.id, offer_id=listing.accepted_offer_id)
        if not offer:
            return None, "Accepted offer not found"
        offer_id = offer.id
        offer_status = OfferStatus(offer.status)
        deal_amount = offer.counter_amount if offer.counter_amount is not None else offer.offered_amount
        (
            booking_status,
            status_label,
            is_book_window_active,
            offer_lock_expires_at,
        ) = _derive_buyer_booking_state(
            listing=listing,
            offer=offer,
            buyer_id=user_id,
        )
        can_book = booking_status == BuyerOfferBookingStatus.ACCEPTED_BOOK_NOW and is_book_window_active
    else:
        if int(getattr(listing, "pricing_version", 1) or 1) == 2:
            deal_amount = _direct_booking_amount(total_amount, 2)
            total_amount = deal_amount
        if _is_offer_lock_active(listing) and listing.offer_locked_by_buyer_id != user_id:
            can_book = False
            status_label = "Listing is temporarily locked for another buyer"

    if deal_amount is None:
        return None, "Expected price not available for direct booking"

    existing_booking = get_booking_for_listing_buyer(db, listing.id, user_id)
    if existing_booking and existing_booking.booking_fee_amount is not None:
        buyer_fee = float(existing_booking.booking_fee_amount)
    else:
        _, buyer_fee = get_processing_fees(db)
    return (
        BuyerBookingPreviewResponse(
            request_id=request_id,
            total_amount=total_amount,
            deal_amount=_amount_value(deal_amount),
            booking_fee_amount=buyer_fee,
            can_book=can_book,
            booking_status=booking_status,
            status_label=status_label,
            offer_id=offer_id,
            offer_status=offer_status,
            offer_lock_expires_at=offer_lock_expires_at,
            is_book_window_active=is_book_window_active,
        ),
        None,
    )


def accept_counter_offer_for_buyer(
    db: Session,
    user_id: int,
    offer_id: int,
) -> tuple[BuyerOfferActionResponse | None, str | None]:
    release_expired_offer_locks(db)
    offer = get_offer_by_id_for_buyer(db, offer_id=offer_id, buyer_id=user_id)
    if not offer:
        return None, "Offer not found"
    if offer.status != OfferStatus.COUNTERED.value:
        return None, "Only counter offers can be accepted"

    listing = get_live_sell_land_request_by_id(db, offer.request_id)
    if not listing:
        return None, "Sell land request not found"
    if _is_offer_lock_active(listing) and listing.offer_locked_by_buyer_id != user_id:
        return None, "Listing is temporarily locked for another buyer"

    accepted = apply_seller_accept_offer(
        db=db,
        listing=listing,
        accepted_offer=offer,
        lock_hours=48,
        clear_counter_amount=False,
    )
    try:
        seller = get_user_by_id(db, listing.user_id)
        admin_user = get_user_by_id(db, listing.reviewed_by_id) if listing.reviewed_by_id else None
        if seller:
            notify_users(
                db=db,
                users=[seller],
                title="Counter Offer Accepted",
                body="A buyer accepted your counter offer. Listing is now locked for 48 hours",
                notif_type="SELLER_COUNTER_ACCEPTED",
                role_target=seller.role,
                reference_id=str(listing.id),
            )
        if admin_user:
            notify_users(
                db=db,
                users=[admin_user],
                title="Listing Locked",
                body=f"Listing LST-{listing.id} is locked after buyer accepted the counter offer",
                notif_type="LISTING_LOCKED_FOR_ADMIN",
                role_target=admin_user.role,
                reference_id=str(listing.id),
            )
    except Exception:
        logger.exception("Failed to send counter accepted lock notifications")
    return (
        BuyerOfferActionResponse(
            status="Counter offer accepted. Book within 48 hours",
            request_id=accepted.request_id,
            offer_id=accepted.id,
            offer_status=accepted.status,
            booking_status=BuyerOfferBookingStatus.ACCEPTED_BOOK_NOW,
            offer_lock_expires_at=listing.offer_lock_expires_at,
        ),
        None,
    )


def reject_counter_offer_for_buyer(
    db: Session,
    user_id: int,
    offer_id: int,
) -> tuple[BuyerOfferActionResponse | None, str | None]:
    offer = get_offer_by_id_for_buyer(db, offer_id=offer_id, buyer_id=user_id)
    if not offer:
        return None, "Offer not found"
    if offer.status != OfferStatus.COUNTERED.value:
        return None, "Only counter offers can be rejected"

    updated = apply_buyer_reject_counter_offer(db, offer)
    try:
        listing = get_sell_land_request_by_id(db, updated.request_id)
        seller = get_user_by_id(db, listing.user_id) if listing else None
        if seller:
            notify_users(
                db=db,
                users=[seller],
                title="Counter Offer Rejected",
                body="The buyer rejected your counter offer",
                notif_type="BUYER_COUNTER_REJECTED",
                role_target=seller.role,
                reference_id=str(updated.request_id),
            )
    except Exception:
        logger.exception("Failed to send counter reject notification to seller")
    return (
        BuyerOfferActionResponse(
            status="Counter offer rejected",
            request_id=updated.request_id,
            offer_id=updated.id,
            offer_status=updated.status,
            booking_status=BuyerOfferBookingStatus.REJECTED,
            offer_lock_expires_at=None,
        ),
        None,
    )


def list_my_listing_offers(
    db: Session,
    user_id: int,
    request_id: int,
) -> tuple[SellerOfferListResponse | None, str | None]:
    release_expired_offer_locks(db)
    listing = get_sell_land_request_by_id(db, request_id)
    if not listing or listing.user_id != user_id:
        return None, "Sell land request not found"

    rows = list_offers_for_request(db, request_id)
    items = [
        SellerOfferItem(
            id=offer.id,
            request_id=offer.request_id,
            buyer_id=offer.buyer_id,
            offered_amount=_amount_value(offer.offered_amount),
            counter_amount=_amount_value(offer.counter_amount),
            offer_status=offer.status,
            created_at=offer.created_at,
            seller_response_at=offer.seller_response_at,
            buyer={
                "id": buyer.id,
                "fullname": buyer.fullname,
                "mobile": buyer.mobile,
            },
        )
        for offer, buyer in rows
    ]
    return (
        SellerOfferListResponse(
            request_id=request_id,
            total=len(items),
            is_offer_locked=_is_offer_lock_active(listing),
            offer_lock_expires_at=listing.offer_lock_expires_at,
            items=items,
        ),
        None,
    )


def _get_offer_for_seller_action(
    db: Session,
    user_id: int,
    request_id: int,
    offer_id: int,
) -> tuple[SellLandRequest | None, SellLandOffer | None, str | None]:
    listing = get_sell_land_request_by_id(db, request_id)
    if not listing or listing.user_id != user_id:
        return None, None, "Sell land request not found"

    offer = get_offer_by_id(db, request_id=request_id, offer_id=offer_id)
    if not offer:
        return None, None, "Offer not found"
    if offer.status not in {OfferStatus.PENDING.value, OfferStatus.COUNTERED.value}:
        return None, None, "Offer is already finalized"
    return listing, offer, None


def accept_offer_for_my_listing(
    db: Session,
    user_id: int,
    request_id: int,
    offer_id: int,
) -> tuple[SellerOfferActionResponse | None, str | None]:
    release_expired_offer_locks(db)
    listing, offer, error = _get_offer_for_seller_action(db, user_id, request_id, offer_id)
    if error:
        return None, error
    if _is_offer_lock_active(listing):
        return None, "Listing is already locked by an accepted offer"

    accepted = apply_seller_accept_offer(db=db, listing=listing, accepted_offer=offer, lock_hours=48)
    try:
        buyer = get_user_by_id(db, accepted.buyer_id)
        admin_user = get_user_by_id(db, listing.reviewed_by_id) if listing.reviewed_by_id else None
        if buyer:
            notify_users(
                db=db,
                users=[buyer],
                title="Offer Accepted",
                body="Your offer was accepted. Book within 48 hours",
                notif_type="BUYER_OFFER_ACCEPTED",
                role_target=buyer.role,
                reference_id=str(request_id),
            )
        if admin_user:
            notify_users(
                db=db,
                users=[admin_user],
                title="Listing Locked",
                body=f"Listing LST-{request_id} is locked after seller accepted an offer",
                notif_type="LISTING_LOCKED_FOR_ADMIN",
                role_target=admin_user.role,
                reference_id=str(request_id),
            )
    except Exception:
        logger.exception("Failed to send offer accepted notifications")
    return (
        SellerOfferActionResponse(
            status="Offer accepted and listing locked for 48 hours",
            request_id=request_id,
            offer_id=accepted.id,
            offer_status=accepted.status,
            offer_lock_expires_at=listing.offer_lock_expires_at,
        ),
        None,
    )


def reject_offer_for_my_listing(
    db: Session,
    user_id: int,
    request_id: int,
    offer_id: int,
) -> tuple[SellerOfferActionResponse | None, str | None]:
    release_expired_offer_locks(db)
    _, offer, error = _get_offer_for_seller_action(db, user_id, request_id, offer_id)
    if error:
        return None, error

    updated = apply_seller_reject_offer(db, offer)
    try:
        buyer = get_user_by_id(db, updated.buyer_id)
        if buyer:
            notify_users(
                db=db,
                users=[buyer],
                title="Offer Rejected",
                body="Your offer was rejected by the seller",
                notif_type="BUYER_OFFER_REJECTED",
                role_target=buyer.role,
                reference_id=str(request_id),
            )
    except Exception:
        logger.exception("Failed to send buyer reject notification")
    return (
        SellerOfferActionResponse(
            status="Offer rejected",
            request_id=request_id,
            offer_id=updated.id,
            offer_status=updated.status,
            offer_lock_expires_at=None,
        ),
        None,
    )


def counter_offer_for_my_listing(
    db: Session,
    user_id: int,
    request_id: int,
    offer_id: int,
    payload: SellerOfferCounterRequest,
) -> tuple[SellerOfferActionResponse | None, str | None]:
    release_expired_offer_locks(db)
    _, offer, error = _get_offer_for_seller_action(db, user_id, request_id, offer_id)
    if error:
        return None, error
    if payload.counter_amount <= 0:
        return None, "Counter amount must be greater than zero"

    updated = apply_seller_counter_offer(db, offer, payload.counter_amount)
    try:
        buyer = get_user_by_id(db, updated.buyer_id)
        if buyer:
            notify_users(
                db=db,
                users=[buyer],
                title="Counter Offer Received",
                body=f"The seller sent a counter offer of Rs {int(payload.counter_amount):,}",
                notif_type="BUYER_COUNTER_RECEIVED",
                role_target=buyer.role,
                reference_id=str(request_id),
            )
    except Exception:
        logger.exception("Failed to send buyer counter notification")
    return (
        SellerOfferActionResponse(
            status="Counter offer sent",
            request_id=request_id,
            offer_id=updated.id,
            offer_status=updated.status,
            offer_lock_expires_at=None,
        ),
        None,
    )


def create_booking_for_buyer(
    db: Session,
    user_id: int,
    payload: BuyerBookingCreateRequest,
    aadhaar_doc: UploadFile,
    pan_doc: UploadFile,
    bank_doc: UploadFile,
) -> tuple[SellLandBooking | None, str | None]:
    release_expired_offer_locks(db)
    listing = (
        db.query(SellLandRequest)
        .filter(SellLandRequest.id == payload.request_id)
        .with_for_update()
        .first()
    )
    if not listing:
        return None, "Sell land request not found"
    if listing.status != SellLandStatus.LIVE.value:
        return None, "Only live listings can be booked"
    deal_amount: Decimal | int | float | None = None
    if listing.accepted_offer_id is not None:
        if listing.offer_locked_by_buyer_id != user_id or not _is_offer_lock_active(listing):
            return None, "Listing is not locked for this buyer"
        offer = get_offer_by_id(db, request_id=listing.id, offer_id=listing.accepted_offer_id)
        if not offer or offer.buyer_id != user_id or offer.status != OfferStatus.ACCEPTED.value:
            return None, "Accepted offer not found"
        deal_amount = offer.counter_amount if offer.counter_amount is not None else offer.offered_amount
    else:
        if _is_offer_lock_active(listing) and listing.offer_locked_by_buyer_id != user_id:
            return None, "Listing is temporarily locked for another buyer"
        deal_amount = _direct_booking_amount(
            listing.expected_price,
            int(getattr(listing, "pricing_version", 1) or 1),
        )

    existing = get_booking_for_listing_buyer(db, listing.id, user_id)
    if existing:
        if existing.payment_status == PaymentStatus.SUCCESS.value:
            return None, "Booking already completed"
        if (
            existing.aadhaar_doc_url
            and existing.pan_doc_url
            and existing.bank_doc_url
        ):
            return existing, None

    _, buyer_fee = get_processing_fees(db)
    booking = existing or create_booking(
        db=db,
        request_id=listing.id,
        buyer_id=user_id,
        buyer_name=payload.buyer_name,
        buyer_mobile=payload.buyer_mobile,
        aadhaar_number="",
        pan_number="",
        bank_account="",
        deal_amount=deal_amount,
        booking_fee_amount=buyer_fee,
        commit=False,
    )
    saved_names: list[str] = []
    try:
        aadhaar_name, aadhaar_url = save_booking_doc_file(
            file=aadhaar_doc,
            booking_id=booking.id,
            media_root=BOOKING_MEDIA_ROOT,
            allowed_extensions=ALLOWED_DOC_EXTENSIONS,
            doc_label="aadhaar",
        )
        saved_names.append(aadhaar_name)
        pan_name, pan_url = save_booking_doc_file(
            file=pan_doc,
            booking_id=booking.id,
            media_root=BOOKING_MEDIA_ROOT,
            allowed_extensions=ALLOWED_DOC_EXTENSIONS,
            doc_label="pan",
        )
        saved_names.append(pan_name)
        bank_name, bank_url = save_booking_doc_file(
            file=bank_doc,
            booking_id=booking.id,
            media_root=BOOKING_MEDIA_ROOT,
            allowed_extensions=ALLOWED_DOC_EXTENSIONS,
            doc_label="bank",
        )
        saved_names.append(bank_name)
    except ValueError as exc:
        db.rollback()
        booking_dir = settings.private_uploads_dir / "booking" / f"booking_{booking.id}"
        for saved_name in saved_names:
            saved_file = booking_dir / saved_name
            if saved_file.is_file():
                saved_file.unlink()
        return None, str(exc)
    booking = update_booking_documents(
        db=db,
        booking=booking,
        aadhaar_doc_url=aadhaar_url,
        aadhaar_doc_name=aadhaar_name,
        pan_doc_url=pan_url,
        pan_doc_name=pan_name,
        bank_doc_url=bank_url,
        bank_doc_name=bank_name,
    )
    return booking, None


def mark_booking_paid_for_buyer(
    db: Session,
    user_id: int,
    booking_id: int,
    payload: BuyerBookingPaymentRequest,
) -> tuple[SellLandBooking | None, str | None]:
    booking = get_booking_by_id_for_buyer(db, booking_id=booking_id, buyer_id=user_id)
    if not booking:
        return None, "Booking not found"
    if booking.payment_status == PaymentStatus.SUCCESS.value:
        return None, "Booking already paid"
    updated = mark_booking_paid(
        db,
        booking,
        method=payload.method.value if hasattr(payload.method, "value") else str(payload.method),
        transaction_id=payload.transaction_id,
    )
    listing = get_sell_land_request_by_id(db, booking.request_id)
    if listing and listing.status != SellLandStatus.BOOKED.value:
        _mark_listing_booked(db, listing)
    try:
        if listing:
            seller = get_user_by_id(db, listing.user_id)
            admin_user = get_user_by_id(db, listing.reviewed_by_id) if listing.reviewed_by_id else None
            buyer = get_user_by_id(db, user_id)
            buyer_name = (
                (booking.buyer_name if booking.buyer_name else None)
                or (buyer.fullname if buyer and buyer.fullname else None)
                or "the user"
            )
            if seller:
                notify_users(
                    db=db,
                    users=[seller],
                    title="Land Booked",
                    body=f"Your listing has been booked successfully by {buyer_name}.",
                    notif_type="BOOKING_PAYMENT_SUCCESS",
                    role_target=seller.role,
                    reference_id=str(listing.id),
                )
            if admin_user:
                notify_users(
                    db=db,
                    users=[admin_user],
                    title="Booking Payment Successful",
                    body=f"Listing LST-{listing.id} has been booked successfully.",
                    notif_type="BOOKING_PAYMENT_SUCCESS",
                    role_target=admin_user.role,
                    reference_id=str(listing.id),
                )
    except Exception:
        logger.exception("Failed to send booking payment success notifications")
    return updated, None
