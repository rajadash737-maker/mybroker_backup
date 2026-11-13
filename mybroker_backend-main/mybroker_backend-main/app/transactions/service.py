from decimal import Decimal

from app.sell_land.constants import BookingStatus, PaymentStatus, SellLandStatus
from app.transactions.repository import (
    get_booking_by_id_for_user,
    get_booking_by_transaction_id,
    get_offer_by_id,
    list_user_offer_transactions,
    list_user_transactions,
)
from app.transactions.schemas import TransactionItemResponse, TransactionsResponse


def _normalize_payment_status(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if value == PaymentStatus.SUCCESS.value:
        return "paid"
    if value == PaymentStatus.FAILED.value:
        return "failed"
    return "pending"


def _derive_deal_status(listing_status: str | None, booking_status: str | None) -> str:
    ls = (listing_status or "").strip().lower()
    bs = (booking_status or "").strip().lower()

    if ls == SellLandStatus.REFUND_SUCCESSFUL.value:
        return "refunded"
    if ls == SellLandStatus.PROCESSING_REFUND.value:
        return "cancelled"
    if ls == SellLandStatus.SOLD.value or bs in {
        BookingStatus.REGISTRY_DONE.value,
        BookingStatus.SOLD.value,
    }:
        return "completed"
    if bs == BookingStatus.REGISTRY_SCHEDULED.value:
        return "registry_scheduled"
    if bs in {BookingStatus.BOOKED.value, BookingStatus.CONFIRMED.value, BookingStatus.IN_PROCESS.value}:
        return "booked"
    return "pending"


def _amount_value(value) -> float | int:
    if isinstance(value, Decimal):
        return int(value)
    if value is None:
        return 0
    return float(value)


def list_my_transactions(
    db,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
) -> TransactionsResponse:
    window = skip + limit
    booking_rows = list_user_transactions(db=db, user_id=user_id, skip=0, limit=window)
    offer_rows = list_user_offer_transactions(db=db, user_id=user_id, skip=0, limit=window)

    items_with_time: list[tuple[str | None, TransactionItemResponse]] = []
    for booking, listing, seller in booking_rows:
        seller_name = (listing.owner_name or seller.fullname or "").strip()
        buyer_name = (booking.buyer_name or "").strip()
        status = _derive_deal_status(listing.status, booking.booking_status)
        location = (listing.location or "").strip()
        if not location:
            city = (listing.city or "").strip()
            state = (listing.state or "").strip()
            if city and state:
                location = f"{city}, {state}"
            else:
                location = city or state or "Location not available"
        booking_tx_id = (booking.payment_transaction_id or "").strip()
        if not booking_tx_id:
            booking_tx_id = f"booking-{booking.id}"
        item = TransactionItemResponse(
            transaction_id=booking_tx_id,
            property_title=(listing.title or "").strip(),
            buyer_name=buyer_name,
            seller_name=seller_name,
            location=location,
            deal_amount=_amount_value(booking.deal_amount),
            payment_status=_normalize_payment_status(booking.payment_status),
            deal_status=status,
            offer_status=None,
            offer_status_at=None,
            registry_date=booking.registry_date.isoformat() if booking.registry_date else None,
            created_at=booking.created_at.isoformat() if booking.created_at else None,
        )
        items_with_time.append((item.created_at, item))

    for offer, listing, seller_user, buyer_user in offer_rows:
        seller_name = (listing.owner_name or seller_user.fullname or "").strip()
        buyer_name = (buyer_user.fullname or "").strip()
        location = (listing.location or "").strip()
        if not location:
            city = (listing.city or "").strip()
            state = (listing.state or "").strip()
            if city and state:
                location = f"{city}, {state}"
            else:
                location = city or state or "Location not available"

        deal_amount = offer.counter_amount or offer.offered_amount or 0
        item = TransactionItemResponse(
            transaction_id=f"offer-{offer.id}",
            property_title=(listing.title or "").strip(),
            buyer_name=buyer_name,
            seller_name=seller_name,
            location=location,
            deal_amount=_amount_value(deal_amount),
            payment_status="pending",
            deal_status=(offer.status or "pending").lower(),
            offer_status=(offer.status or "").lower() or None,
            offer_status_at=(
                offer.seller_response_at.isoformat()
                if offer.seller_response_at
                else (offer.updated_at.isoformat() if offer.updated_at else None)
            ),
            registry_date=None,
            created_at=offer.created_at.isoformat() if offer.created_at else None,
        )
        items_with_time.append((item.created_at, item))

    items_with_time.sort(key=lambda x: x[0] or "", reverse=True)
    items = [item for _, item in items_with_time][skip: skip + limit]
    return TransactionsResponse(data=items)


def get_transaction_detail(
    db,
    user_id: int,
    transaction_id: str,
) -> TransactionItemResponse | None:
    if transaction_id.startswith("offer-"):
        try:
            offer_id = int(transaction_id.split("-", 1)[1])
        except (IndexError, ValueError):
            return None
        row = get_offer_by_id(db=db, user_id=user_id, offer_id=offer_id)
        if not row:
            return None
        offer, listing, seller_user, buyer_user = row
        seller_name = (listing.owner_name or seller_user.fullname or "").strip()
        buyer_name = (buyer_user.fullname or "").strip()
        location = (listing.location or "").strip()
        if not location:
            city = (listing.city or "").strip()
            state = (listing.state or "").strip()
            if city and state:
                location = f"{city}, {state}"
            else:
                location = city or state or "Location not available"
        deal_amount = offer.counter_amount or offer.offered_amount or 0
        return TransactionItemResponse(
            transaction_id=f"offer-{offer.id}",
            property_title=(listing.title or "").strip(),
            buyer_name=buyer_name,
            seller_name=seller_name,
            location=location,
        deal_amount=_amount_value(deal_amount),
            payment_status="pending",
            deal_status=(offer.status or "pending").lower(),
            offer_status=(offer.status or "").lower() or None,
            offer_status_at=(
                offer.seller_response_at.isoformat()
                if offer.seller_response_at
                else (offer.updated_at.isoformat() if offer.updated_at else None)
            ),
            registry_date=None,
            created_at=offer.created_at.isoformat() if offer.created_at else None,
        )

    if transaction_id.startswith("booking-"):
        try:
            booking_id = int(transaction_id.split("-", 1)[1])
        except (IndexError, ValueError):
            return None
        row = get_booking_by_id_for_user(db=db, user_id=user_id, booking_id=booking_id)
    else:
        row = get_booking_by_transaction_id(db=db, user_id=user_id, transaction_id=transaction_id)
    if not row:
        return None
    booking, listing, seller = row
    seller_name = (listing.owner_name or seller.fullname or "").strip()
    buyer_name = (booking.buyer_name or "").strip()
    status = _derive_deal_status(listing.status, booking.booking_status)
    location = (listing.location or "").strip()
    if not location:
        city = (listing.city or "").strip()
        state = (listing.state or "").strip()
        if city and state:
            location = f"{city}, {state}"
        else:
            location = city or state or "Location not available"
    return TransactionItemResponse(
        transaction_id=(booking.payment_transaction_id or "").strip() or None,
        property_title=(listing.title or "").strip(),
        buyer_name=buyer_name,
        seller_name=seller_name,
        location=location,
        deal_amount=_amount_value(booking.deal_amount),
        payment_status=_normalize_payment_status(booking.payment_status),
        deal_status=status,
        offer_status=None,
        offer_status_at=None,
        registry_date=booking.registry_date.isoformat() if booking.registry_date else None,
        created_at=booking.created_at.isoformat() if booking.created_at else None,
    )
