"""Property booking cancellation and external refund ledger operations."""

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.notifications.service import notify_users
from app.payments.models import RazorpayPaymentOrder
from app.sell_land.booking_refund_crypto import (
    BookingRefundEncryptionConfigurationError,
    decrypt_buyer_upi,
    encrypt_buyer_upi,
)
from app.sell_land.constants import BookingStatus, OfferStatus, PaymentStatus, SellLandStatus
from app.sell_land.models import (
    PropertyBookingRefund,
    PropertyBookingRefundEvent,
    SellLandBooking,
    SellLandOffer,
    SellLandRequest,
)
from app.sell_land.admin_schemas import (
    AccountingPropertyBookingRefundConfirmRequest,
    AccountingPropertyBookingRefundDetail,
    AccountingPropertyBookingRefundFailRequest,
    PropertyBookingCancellationRequest,
    PropertyBookingCancellationPreview,
    PropertyBookingCancellationResponse,
    PropertyBookingRefundHistoryItem,
    PropertyBookingRefundQueueItem,
    PropertyBookingRefundQueueResponse,
)
from app.sell_land.schemas import (
    BuyerPropertyBookingRefundResponse,
    BuyerPropertyBookingRefundUpiRequest,
)
from app.users.model import User
from app.users.roles import UserRole

CENT = Decimal("0.01")
ACTIVE_BOOKING_STATUSES = (
    BookingStatus.BOOKED.value,
    BookingStatus.CONFIRMED.value,
    BookingStatus.IN_PROCESS.value,
    BookingStatus.REGISTRY_SCHEDULED.value,
)


def _money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENT)


def _add_event(db: Session, refund: PropertyBookingRefund, event_type: str,
               from_status: str | None, to_status: str, actor: User, note: str | None = None) -> None:
    db.add(PropertyBookingRefundEvent(
        refund_id=refund.id,
        booking_id=refund.booking_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        actor_id=actor.id,
        actor_role=actor.role,
        note=note,
    ))


def _payment_for_booking(db: Session, booking: SellLandBooking) -> RazorpayPaymentOrder | None:
    if not booking.payment_transaction_id:
        return None
    return (
        db.query(RazorpayPaymentOrder)
        .filter(
            RazorpayPaymentOrder.user_id == booking.buyer_id,
            RazorpayPaymentOrder.property_id == booking.request_id,
            RazorpayPaymentOrder.site_visit_request_id.is_(None),
            RazorpayPaymentOrder.payment_context == "buyer",
            RazorpayPaymentOrder.status == "SUCCESS",
            RazorpayPaymentOrder.currency == "INR",
            RazorpayPaymentOrder.payment_id == booking.payment_transaction_id,
            RazorpayPaymentOrder.amount_paise > 0,
        )
        .order_by(RazorpayPaymentOrder.paid_at.desc(), RazorpayPaymentOrder.id.desc())
        .first()
    )


def get_booking_cancellation_preview(db: Session, *, booking_id: int, actor: User) -> PropertyBookingCancellationPreview:
    if actor.role != UserRole.SUPER_ADMIN.value or not actor.is_active:
        raise HTTPException(status_code=403, detail="Only an active Super Admin can view cancellation details")
    booking = db.query(SellLandBooking).filter(SellLandBooking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    listing = db.query(SellLandRequest).filter(SellLandRequest.id == booking.request_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    payment = _payment_for_booking(db, booking)
    has_refund = db.query(PropertyBookingRefund.id).filter(PropertyBookingRefund.booking_id == booking.id).first()
    reason = None
    if listing.status != SellLandStatus.BOOKED.value or booking.booking_status not in ACTIVE_BOOKING_STATUSES:
        reason = "Booking is not in an eligible active state"
    elif payment is None:
        reason = "No verified captured property booking payment is linked to this booking"
    elif has_refund:
        reason = "Booking cancellation has already been requested"
    return PropertyBookingCancellationPreview(
        booking_id=booking.id, listing_id=listing.id, listing_code=listing.listing_code,
        property_name=listing.title, buyer_name=booking.buyer_name, buyer_mobile=booking.buyer_mobile,
        booking_status=booking.booking_status, listing_status=listing.status,
        captured_payment_amount=(Decimal(payment.amount_paise) / Decimal(100)) if payment else None,
        captured_at=payment.paid_at if payment else None,
        can_cancel=reason is None, blocking_reason=reason,
    )


def cancel_property_booking(
    db: Session,
    *,
    booking_id: int,
    actor: User,
    payload: PropertyBookingCancellationRequest,
) -> PropertyBookingCancellationResponse:
    if actor.role != UserRole.SUPER_ADMIN.value or not actor.is_active:
        raise HTTPException(status_code=403, detail="Only an active Super Admin can cancel a property booking")

    booking = db.query(SellLandBooking).filter(SellLandBooking.id == booking_id).with_for_update().first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    listing = db.query(SellLandRequest).filter(SellLandRequest.id == booking.request_id).with_for_update().first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if db.query(PropertyBookingRefund.id).filter(PropertyBookingRefund.booking_id == booking.id).first():
        raise HTTPException(status_code=409, detail="Booking cancellation has already been requested")
    if listing.status != SellLandStatus.BOOKED.value or booking.booking_status not in ACTIVE_BOOKING_STATUSES:
        raise HTTPException(status_code=409, detail="Only an active booked or registry-pending booking can be cancelled")

    payment = _payment_for_booking(db, booking)
    if payment is None:
        raise HTTPException(status_code=409, detail="No verified captured property booking payment is linked to this booking")
    captured = _money(Decimal(payment.amount_paise) / Decimal(100))
    approved = (payload.refund_amount if payload.refund_amount is not None else captured) if payload.refund_decision == "REFUND" else Decimal("0.00")
    if payload.refund_decision == "REFUND" and (approved <= 0 or approved > captured):
        raise HTTPException(status_code=422, detail="Refund must be greater than zero and no more than the captured payment")
    if payload.refund_decision == "NO_REFUND" and payload.refund_amount not in (None, Decimal("0")):
        raise HTTPException(status_code=422, detail="No Refund requires a zero refund amount")

    previous_listing_status = listing.status
    initial_refund_status = "AWAITING_BUYER_DETAILS" if payload.refund_decision == "REFUND" else "NOT_REQUIRED"
    refund = PropertyBookingRefund(
        booking_id=booking.id,
        listing_id=listing.id,
        buyer_id=booking.buyer_id,
        cancellation_actor_id=actor.id,
        cancellation_actor_role=actor.role,
        cancellation_reason=payload.cancellation_reason,
        previous_listing_status=previous_listing_status,
        refund_decision=payload.refund_decision,
        approved_refund_amount=_money(approved),
        original_captured_amount=captured,
        payment_order_id=payment.id,
        refund_status=initial_refund_status,
    )
    prior_booking_status = booking.booking_status
    booking.booking_status = BookingStatus.CANCELLED.value
    db.add(refund)
    try:
        db.flush()

        # The listing may remain blocked by another booking or deal lock, but
        # this booking's accepted offer is terminal as soon as it is cancelled.
        cancelled_offer = None
        if listing.accepted_offer_id is not None:
            cancelled_offer = db.query(SellLandOffer).filter(
                SellLandOffer.id == listing.accepted_offer_id,
                SellLandOffer.request_id == listing.id,
                SellLandOffer.buyer_id == booking.buyer_id,
                SellLandOffer.status == OfferStatus.ACCEPTED.value,
            ).first()
        if cancelled_offer:
            cancelled_offer.status = OfferStatus.EXPIRED.value
            listing.accepted_offer_id = None

        active_other = (
            db.query(SellLandBooking.id)
            .filter(
                SellLandBooking.request_id == listing.id,
                SellLandBooking.id != booking.id,
                SellLandBooking.payment_status == PaymentStatus.SUCCESS.value,
                SellLandBooking.booking_status.in_(ACTIVE_BOOKING_STATUSES),
            )
            .first()
        )
        completed_other = (
            db.query(SellLandBooking.id)
            .filter(
                SellLandBooking.request_id == listing.id,
                SellLandBooking.id != booking.id,
                SellLandBooking.booking_status.in_((BookingStatus.REGISTRY_DONE.value, BookingStatus.SOLD.value)),
            )
            .first()
        )
        active_lock = (
            listing.offer_lock_expires_at is not None
            and listing.offer_lock_expires_at > datetime.utcnow()
            and listing.offer_locked_by_buyer_id != booking.buyer_id
        )
        unrelated_lock_owner = (
            listing.offer_locked_by_buyer_id is not None
            and listing.offer_locked_by_buyer_id != booking.buyer_id
        )
        unrelated_accepted_offer = False
        if listing.accepted_offer_id is not None:
            accepted = db.query(SellLandOffer).filter(
                SellLandOffer.id == listing.accepted_offer_id,
                SellLandOffer.request_id == listing.id,
            ).first()
            unrelated_accepted_offer = accepted is None or accepted.buyer_id != booking.buyer_id
        if (
            listing.status == SellLandStatus.BOOKED.value
            and not active_other
            and not completed_other
            and not active_lock
            and not unrelated_lock_owner
            and not unrelated_accepted_offer
            and booking.booking_status == BookingStatus.CANCELLED.value
        ):
            # Clear only the cancelled booking's own accepted offer lock.
            if listing.offer_locked_by_buyer_id == booking.buyer_id:
                listing.offer_locked_by_buyer_id = None
                listing.offer_lock_expires_at = None
                listing.lock_started_at = None
                listing.lock_expires_at = None
            listing.status = SellLandStatus.LIVE.value

        db.add(PropertyBookingRefundEvent(
            refund_id=refund.id,
            booking_id=booking.id,
            event_type="BOOKING_CANCELLED",
            from_status=prior_booking_status,
            to_status=BookingStatus.CANCELLED.value,
            actor_id=actor.id,
            actor_role=actor.role,
            note=f"{payload.refund_decision}: {payload.cancellation_reason}",
        ))
        db.add(PropertyBookingRefundEvent(
            refund_id=refund.id,
            booking_id=booking.id,
            event_type="REFUND_DECISION_RECORDED",
            from_status=None,
            to_status=initial_refund_status,
            actor_id=actor.id,
            actor_role=actor.role,
            note=f"approved_amount={_money(approved)}",
        ))
        if listing.status == SellLandStatus.LIVE.value:
            db.add(PropertyBookingRefundEvent(
                refund_id=refund.id,
                booking_id=booking.id,
                event_type="LISTING_RESTORED_LIVE",
                from_status=previous_listing_status,
                to_status=listing.status,
                actor_id=actor.id,
                actor_role=actor.role,
                note="Cancelled blocking booking; no other active booking or unrelated deal lock remains",
            ))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Booking cancellation conflicts with another request") from None
    except Exception:
        db.rollback()
        raise

    _notify_cancellation(db, booking, listing, refund)
    return PropertyBookingCancellationResponse(
        booking_id=booking.id,
        listing_id=listing.id,
        refund_id=refund.id,
        booking_status=booking.booking_status,
        listing_status=listing.status,
        refund_decision=refund.refund_decision,
        refund_status=refund.refund_status,
        original_captured_amount=refund.original_captured_amount,
        approved_refund_amount=refund.approved_refund_amount,
    )


def _notify_cancellation(db: Session, booking: SellLandBooking, listing: SellLandRequest,
                         refund: PropertyBookingRefund) -> None:
    try:
        buyer = db.query(User).filter(User.id == booking.buyer_id).first()
        if buyer:
            notify_users(
                db=db, users=[buyer], title="Property booking cancelled",
                body=f"Booking for {listing.title or 'property'} was cancelled. Decision: {refund.refund_decision}. Reason: {refund.cancellation_reason}",
                notif_type="PROPERTY_BOOKING_CANCELLED", role_target=buyer.role,
                reference_id=str(booking.id),
            )
        if refund.refund_decision == "REFUND":
            accounting_users = db.query(User).filter(
                User.role == UserRole.ACCOUNTING.value, User.is_active.is_(True)
            ).all()
            if accounting_users:
                notify_users(
                    db=db, users=accounting_users, title="Property booking refund awaiting buyer details",
                    body=f"Booking {booking.id} on listing {listing.id} was cancelled and requires buyer UPI details before processing.",
                    notif_type="PROPERTY_BOOKING_REFUND_CREATED", role_target=UserRole.ACCOUNTING.value,
                    reference_id=str(refund.id),
                )
    except Exception:
        # Notification delivery must never undo committed cancellation/refund state.
        db.rollback()


def get_buyer_booking_refund(db: Session, *, booking_id: int, buyer: User) -> BuyerPropertyBookingRefundResponse:
    booking = db.query(SellLandBooking).filter(
        SellLandBooking.id == booking_id, SellLandBooking.buyer_id == buyer.id
    ).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    refund = db.query(PropertyBookingRefund).filter(PropertyBookingRefund.booking_id == booking.id).first()
    if refund is None:
        raise HTTPException(status_code=404, detail="No cancellation refund record exists for this booking")
    return BuyerPropertyBookingRefundResponse(
        booking_id=booking.id, listing_id=refund.listing_id, booking_status=booking.booking_status,
        refund_decision=refund.refund_decision, refund_status=refund.refund_status,
        cancellation_reason=refund.cancellation_reason, approved_refund_amount=refund.approved_refund_amount,
        actual_refunded_amount=refund.actual_refunded_amount,
        transaction_reference=refund.transaction_reference,
        accounting_confirmed_at=refund.accounting_confirmed_at,
    )


def submit_buyer_refund_upi(db: Session, *, booking_id: int, buyer: User,
                            payload: BuyerPropertyBookingRefundUpiRequest) -> BuyerPropertyBookingRefundResponse:
    refund = db.query(PropertyBookingRefund).join(SellLandBooking).filter(
        SellLandBooking.id == booking_id,
        SellLandBooking.buyer_id == buyer.id,
        PropertyBookingRefund.booking_id == SellLandBooking.id,
    ).with_for_update().first()
    if refund is None:
        raise HTTPException(status_code=404, detail="Refund record not found")
    if refund.refund_decision != "REFUND" or refund.refund_status != "AWAITING_BUYER_DETAILS":
        raise HTTPException(status_code=409, detail="UPI details are not eligible for submission")
    try:
        encrypted = encrypt_buyer_upi(refund.id, payload.upi_id)
    except BookingRefundEncryptionConfigurationError:
        raise HTTPException(status_code=503, detail="Refund detail encryption is not configured") from None
    from_status = refund.refund_status
    refund.buyer_upi_ciphertext = encrypted
    refund.buyer_upi_submitted_at = datetime.utcnow()
    refund.refund_status = "PENDING_ACCOUNTING"
    _add_event(db, refund, "BUYER_UPI_SUBMITTED", from_status, refund.refund_status, buyer)
    db.commit()
    _notify_accounting_upi_received(db, refund)
    return get_buyer_booking_refund(db, booking_id=booking_id, buyer=buyer)


def _notify_accounting_upi_received(db: Session, refund: PropertyBookingRefund) -> None:
    _notify_roles_safely(
        db, refund, roles=(UserRole.ACCOUNTING.value,),
        title="Property refund ready for accounting",
        body=f"Buyer details are ready for property booking refund {refund.id}.",
        notif_type="PROPERTY_BOOKING_REFUND_UPI_RECEIVED",
    )
    _notify_roles_safely(
        db, refund, roles=(UserRole.CUSTOMER.value,),
        title="UPI details received",
        body=f"Your UPI details were received for booking {refund.booking_id}. The refund is awaiting Accounting.",
        notif_type="PROPERTY_BOOKING_REFUND_UPI_RECEIVED",
        user_ids=(refund.buyer_id,),
    )
    _notify_roles_safely(
        db, refund, roles=(UserRole.SUPER_ADMIN.value,),
        title="Property refund processing started",
        body=f"Buyer details were received for property booking refund {refund.id}.",
        notif_type="PROPERTY_BOOKING_REFUND_UPI_RECEIVED",
    )


def _queue_item(refund: PropertyBookingRefund, booking: SellLandBooking,
                listing: SellLandRequest, buyer_upi_id: str | None = None) -> PropertyBookingRefundQueueItem:
    return PropertyBookingRefundQueueItem(
        refund_id=refund.id, booking_id=booking.id, listing_id=listing.id,
        listing_code=listing.listing_code, property_name=listing.title,
        buyer_name=booking.buyer_name, buyer_mobile=booking.buyer_mobile,
        original_captured_amount=refund.original_captured_amount,
        approved_refund_amount=refund.approved_refund_amount,
        cancellation_reason=refund.cancellation_reason, refund_status=refund.refund_status,
        cancelled_at=refund.cancelled_at, buyer_upi_id=buyer_upi_id,
    )


def list_property_booking_refunds(db: Session, *, skip: int, limit: int,
                                  include_history: bool = False) -> PropertyBookingRefundQueueResponse:
    query = db.query(PropertyBookingRefund, SellLandBooking, SellLandRequest).join(
        SellLandBooking, SellLandBooking.id == PropertyBookingRefund.booking_id
    ).join(SellLandRequest, SellLandRequest.id == PropertyBookingRefund.listing_id)
    if not include_history:
        # Failed transfers remain in the Accounting work queue until resolved.
        query = query.filter(PropertyBookingRefund.refund_status.in_(
            ("AWAITING_BUYER_DETAILS", "PENDING_ACCOUNTING", "FAILED")
        ))
    total = query.count()
    rows = query.order_by(PropertyBookingRefund.cancelled_at.asc(), PropertyBookingRefund.id.asc()).offset(skip).limit(limit).all()
    items = []
    for refund, booking, listing in rows:
        upi = None
        if refund.buyer_upi_ciphertext:
            try:
                upi = decrypt_buyer_upi(refund.id, refund.buyer_upi_ciphertext)
            except BookingRefundEncryptionConfigurationError:
                raise HTTPException(status_code=503, detail="Refund detail encryption is not configured") from None
            except ValueError:
                raise HTTPException(status_code=500, detail="Refund detail could not be decrypted") from None
        items.append(_queue_item(refund, booking, listing, buyer_upi_id=upi))
    return PropertyBookingRefundQueueResponse(
        total=total, skip=skip, limit=limit,
        items=items,
    )


def get_accounting_property_booking_refund(db: Session, refund_id: int) -> AccountingPropertyBookingRefundDetail:
    row = db.query(PropertyBookingRefund, SellLandBooking, SellLandRequest).join(
        SellLandBooking, SellLandBooking.id == PropertyBookingRefund.booking_id
    ).join(SellLandRequest, SellLandRequest.id == PropertyBookingRefund.listing_id).filter(
        PropertyBookingRefund.id == refund_id
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Property booking refund not found")
    refund, booking, listing = row
    upi = None
    if refund.buyer_upi_ciphertext:
        try:
            upi = decrypt_buyer_upi(refund.id, refund.buyer_upi_ciphertext)
        except BookingRefundEncryptionConfigurationError:
            raise HTTPException(status_code=503, detail="Refund detail encryption is not configured") from None
        except ValueError:
            raise HTTPException(status_code=500, detail="Refund detail could not be decrypted") from None
    history = db.query(PropertyBookingRefundEvent).filter(
        PropertyBookingRefundEvent.refund_id == refund.id
    ).order_by(PropertyBookingRefundEvent.created_at.asc(), PropertyBookingRefundEvent.id.asc()).all()
    return AccountingPropertyBookingRefundDetail(
        **_queue_item(refund, booking, listing, buyer_upi_id=upi).model_dump(), buyer_id=booking.buyer_id,
        transaction_reference=refund.transaction_reference,
        actual_refunded_amount=refund.actual_refunded_amount,
        confirmation_note=refund.confirmation_note,
        accounting_confirmed_at=refund.accounting_confirmed_at,
        payment_order_id=refund.payment_order_id,
        history=[PropertyBookingRefundHistoryItem(
            event_type=e.event_type, from_status=e.from_status, to_status=e.to_status,
            actor_role=e.actor_role, note=e.note, created_at=e.created_at,
        ) for e in history],
    )


def confirm_property_booking_refund(db: Session, *, refund_id: int, actor: User,
                                    payload: AccountingPropertyBookingRefundConfirmRequest) -> AccountingPropertyBookingRefundDetail:
    if actor.role != UserRole.ACCOUNTING.value or not actor.is_active:
        raise HTTPException(status_code=403, detail="Only active Accounting users can confirm property refunds")
    refund = db.query(PropertyBookingRefund).filter(PropertyBookingRefund.id == refund_id).with_for_update().first()
    if refund is None:
        raise HTTPException(status_code=404, detail="Property booking refund not found")
    amount = _money(payload.actual_refunded_amount)
    if refund.refund_status == "CONFIRMED":
        if refund.transaction_reference == payload.transaction_reference and refund.actual_refunded_amount == amount:
            return get_accounting_property_booking_refund(db, refund_id)
        raise HTTPException(status_code=409, detail="Refund has already been confirmed")
    if refund.refund_status not in {"PENDING_ACCOUNTING", "FAILED"} or not refund.buyer_upi_ciphertext:
        raise HTTPException(status_code=409, detail="Refund is not eligible for confirmation")
    if amount != _money(refund.approved_refund_amount):
        raise HTTPException(status_code=422, detail="Actual refund amount must equal the approved amount")
    previous = refund.refund_status
    refund.refund_status = "CONFIRMED"
    refund.actual_refunded_amount = amount
    refund.transaction_reference = payload.transaction_reference
    refund.confirmation_note = (payload.confirmation_note or "").strip() or None
    refund.accounting_actor_id = actor.id
    refund.accounting_confirmed_at = datetime.utcnow()
    _add_event(db, refund, "EXTERNAL_REFUND_CONFIRMED", previous, refund.refund_status, actor, refund.confirmation_note)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Transaction reference has already been used") from None
    _notify_buyer_refund_status(db, refund, "Property booking refund confirmed", "Your property booking refund was recorded as completed.", "PROPERTY_BOOKING_REFUND_CONFIRMED")
    return get_accounting_property_booking_refund(db, refund_id)


def fail_property_booking_refund(db: Session, *, refund_id: int, actor: User,
                                 payload: AccountingPropertyBookingRefundFailRequest) -> AccountingPropertyBookingRefundDetail:
    if actor.role != UserRole.ACCOUNTING.value or not actor.is_active:
        raise HTTPException(status_code=403, detail="Only active Accounting users can update property refunds")
    refund = db.query(PropertyBookingRefund).filter(PropertyBookingRefund.id == refund_id).with_for_update().first()
    if refund is None:
        raise HTTPException(status_code=404, detail="Property booking refund not found")
    if refund.refund_status != "PENDING_ACCOUNTING":
        raise HTTPException(status_code=409, detail="Refund is not eligible to be marked failed")
    from_status = refund.refund_status
    refund.refund_status = "FAILED"
    refund.failure_reason = payload.reason.strip()
    refund.accounting_actor_id = actor.id
    refund.accounting_failed_at = datetime.utcnow()
    _add_event(db, refund, "EXTERNAL_REFUND_FAILED", from_status, refund.refund_status, actor, refund.failure_reason)
    db.commit()
    _notify_buyer_refund_status(db, refund, "Property booking refund update", "Accounting could not complete your property booking refund. Contact support for assistance.", "PROPERTY_BOOKING_REFUND_FAILED")
    return get_accounting_property_booking_refund(db, refund_id)


def _notify_buyer_refund_status(db: Session, refund: PropertyBookingRefund, title: str,
                                body: str, notif_type: str) -> None:
    _notify_roles_safely(db, refund, roles=(UserRole.CUSTOMER.value,), title=title, body=body,
                         notif_type=notif_type, user_ids=(refund.buyer_id,))
    _notify_roles_safely(db, refund, roles=(UserRole.SUPER_ADMIN.value,), title=title, body=body,
                         notif_type=notif_type)


def _notify_roles_safely(db: Session, refund: PropertyBookingRefund, *, roles: tuple[str, ...],
                         title: str, body: str, notif_type: str,
                         user_ids: tuple[int, ...] | None = None) -> None:
    try:
        query = db.query(User).filter(User.role.in_(roles), User.is_active.is_(True))
        if user_ids:
            query = query.filter(User.id.in_(user_ids))
        users = query.all()
        if users:
            notify_users(db=db, users=users, title=title, body=body,
                         notif_type=notif_type, role_target=roles[0], reference_id=str(refund.booking_id))
    except Exception:
        # The corresponding financial transaction is already committed.
        pass
