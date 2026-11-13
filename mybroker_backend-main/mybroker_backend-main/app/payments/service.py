from decimal import Decimal, ROUND_HALF_UP
import logging
import os

import razorpay
from razorpay.errors import SignatureVerificationError
from sqlalchemy.orm import Session

from app.payments.repository import (
    create_payment_order,
    create_webhook_log,
    get_payment_order_by_order_id,
    get_payment_order_detail,
    get_webhook_log_by_event_id,
    list_payment_orders,
    list_webhook_logs,
    mark_payment_failed,
    mark_payment_success,
    update_webhook_log_attempt,
)
from app.payments.schemas import CreateOrderRequest, CreateOrderResponse, VerifyPaymentRequest, VerifyPaymentResponse
from app.sell_land.constants import PaymentStatus, SellLandStatus
from app.notifications.service import notify_users
from app.sell_land.repository import (
    get_booking_for_listing_buyer,
    get_payment_by_provider_ref,
    mark_booking_confirmed,
    mark_booking_failed,
    mark_listing_booked,
    mark_payment_failed as mark_seller_payment_failed,
    mark_payment_success as mark_seller_payment_success,
    mark_listing_pending_after_payment,
)
from app.sell_land.models import SellLandRequest
from app.users.model import User
from app.users.roles import UserRole

logger = logging.getLogger(__name__)


def _notify_buyer_booking_paid(
    db: Session,
    listing: SellLandRequest | None,
    buyer_name: str | None = None,
) -> None:
    if listing is None:
        return

    recipients: list[User] = []
    seen_user_ids: set[int] = set()

    def add_user(user_id: int | None) -> None:
        if not user_id or user_id in seen_user_ids:
            return
        user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
        if user is None:
            return
        recipients.append(user)
        seen_user_ids.add(user.id)

    add_user(listing.user_id)
    add_user(listing.reviewed_by_id)

    if not recipients:
        return

    resolved_buyer_name = (buyer_name or "").strip() or "the user"
    seller_id = listing.user_id
    for user in recipients:
        if user.id == seller_id:
            title = "Land Booked"
            body = f"Your listing has been booked successfully by {resolved_buyer_name}."
        elif user.role in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}:
            title = "Booking Payment Successful"
            body = f"Listing LST-{listing.id} has been booked successfully."
        else:
            title = "Booking Payment Successful"
            body = f"Listing LST-{listing.id} payment completed successfully."

        notify_users(
            db=db,
            users=[user],
            title=title,
            body=body,
            notif_type="BOOKING_PAYMENT_SUCCESS",
            role_target=user.role,
            reference_id=str(listing.id),
        )


def _get_client() -> razorpay.Client:
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise RuntimeError("Razorpay credentials are not configured")
    return razorpay.Client(auth=(key_id, key_secret))


def _to_paise(amount_inr: float) -> int:
    value = Decimal(str(amount_inr)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    paise = int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return paise


def create_order(
    db: Session, payload: CreateOrderRequest, *, user_id: int
) -> tuple[CreateOrderResponse | None, str | None]:
    if payload.user_id != user_id:
        return None, "User mismatch"
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        return None, "User not found"

    listing = db.query(SellLandRequest).filter(SellLandRequest.id == payload.property_id).first()
    if not listing:
        return None, "Property not found"

    booking = get_booking_for_listing_buyer(db, listing.id, user_id)
    if not booking:
        return None, "Booking not found"
    if booking.payment_status == PaymentStatus.SUCCESS.value:
        return None, "Booking already paid"

    # The client amount remains accepted for compatibility but is not trusted.
    amount_inr = float(booking.booking_fee_amount)
    amount_paise = _to_paise(amount_inr)
    if amount_paise <= 0:
        return None, "Amount must be greater than 0"

    try:
        client = _get_client()
    except RuntimeError as exc:
        logger.error("Razorpay client init failed: %s", exc)
        return None, "Payment gateway is not configured"
    try:
        order = client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {"user_id": str(user_id), "property_id": str(listing.id)},
            }
        )
    except Exception as exc:
        logger.exception("Razorpay order creation failed")
        return None, f"Payment gateway error: {exc}"

    order_id = order.get("id")
    currency = order.get("currency", "INR")
    try:
        amount = int(order.get("amount", amount_paise))
    except (TypeError, ValueError):
        return None, "Payment gateway returned invalid order terms"
    if not order_id:
        logger.error("Razorpay order response missing id: %s", order)
        return None, "Payment gateway returned an invalid order"
    if amount != amount_paise or currency != "INR":
        logger.error("Razorpay returned order terms that differ from requested amount/currency")
        return None, "Payment gateway returned invalid order terms"

    create_payment_order(
        db,
        user_id=user_id,
        property_id=listing.id,
        amount_inr=amount_inr,
        amount_paise=amount,
        currency=currency,
        order_id=order_id,
    )

    logger.info(
        "payment_order_created order_id=%s user_id=%s property_id=%s amount_paise=%s",
        order_id,
        user_id,
        listing.id,
        amount,
    )

    return CreateOrderResponse(order_id=order_id, amount=amount, currency=currency), None


def verify_payment(
    db: Session, payload: VerifyPaymentRequest, *, user_id: int
) -> tuple[VerifyPaymentResponse | None, str | None]:
    order = get_payment_order_by_order_id(db, payload.razorpay_order_id, for_update=True)
    if not order:
        return None, "Order not found"
    if order.user_id != user_id:
        return None, "Not authorized"

    if order.status == "SUCCESS":
        if order.payment_id != payload.razorpay_payment_id:
            return None, "Order was already verified with a different payment"
        return (
            VerifyPaymentResponse(
                status="success",
                order_id=order.order_id,
                payment_id=order.payment_id or payload.razorpay_payment_id,
            ),
            None,
        )

    if order.status != "CREATED":
        return None, "Order is not payable"

    booking = get_booking_for_listing_buyer(db, order.property_id, order.user_id)
    if not booking:
        return None, "Booking not found"
    if order.amount_paise != _to_paise(float(booking.booking_fee_amount)) or order.currency != "INR":
        return None, "Order amount or currency does not match the booking"

    try:
        client = _get_client()
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": payload.razorpay_order_id,
                "razorpay_payment_id": payload.razorpay_payment_id,
                "razorpay_signature": payload.razorpay_signature,
            }
        )
        provider_payment = client.payment.fetch(payload.razorpay_payment_id)
    except SignatureVerificationError:
        logger.warning("Invalid Razorpay signature for order_id=%s", payload.razorpay_order_id)
        return None, "Invalid payment signature"
    except RuntimeError:
        return None, "Payment gateway is not configured"
    except Exception:
        logger.exception("Razorpay payment verification failed")
        return None, "Payment verification failed"

    try:
        provider_amount = int(provider_payment.get("amount", -1)) if isinstance(provider_payment, dict) else -1
    except (TypeError, ValueError):
        provider_amount = -1
    if (
        not isinstance(provider_payment, dict)
        or provider_payment.get("order_id") != order.order_id
        or provider_amount != order.amount_paise
        or provider_payment.get("currency") != order.currency
        or provider_payment.get("status") != "captured"
    ):
        return None, "Payment details do not match the order"

    mark_payment_success(
        db,
        order,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
        commit=False,
    )
    logger.info(
        "payment_verified order_id=%s payment_id=%s user_id=%s property_id=%s",
        order.order_id,
        payload.razorpay_payment_id,
        order.user_id,
        order.property_id,
    )

    buyer = db.query(User).filter(User.id == order.user_id).first()
    buyer_name = (
        (booking.buyer_name if booking and booking.buyer_name else None)
        or (buyer.fullname if buyer and buyer.fullname else None)
        or "the user"
    )
    listing = None
    if booking:
        if booking.payment_status != PaymentStatus.SUCCESS.value:
            mark_booking_confirmed(
                db,
                booking,
                method="razorpay",
                transaction_id=payload.razorpay_payment_id,
                commit=False,
            )
        else:
            logger.info("Booking already marked paid: booking_id=%s", booking.id)
        listing = db.query(SellLandRequest).filter(SellLandRequest.id == booking.request_id).first()
        if listing and listing.status != SellLandStatus.BOOKED.value:
            mark_listing_booked(db, listing, commit=False)
    else:
        logger.warning(
            "No booking found for payment order: order_id=%s user_id=%s property_id=%s",
            order.order_id,
            order.user_id,
            order.property_id,
        )
    try:
        # Order, booking, and listing state transition together. Notifications
        # run only after this transaction has committed.
        db.commit()
    except Exception:
        db.rollback()
        raise
    try:
        _notify_buyer_booking_paid(db, listing, buyer_name=buyer_name)
    except Exception:
        logger.exception("Failed to send booking payment success notifications")

    return (
        VerifyPaymentResponse(
            status="success",
            order_id=payload.razorpay_order_id,
            payment_id=payload.razorpay_payment_id,
        ),
        None,
    )


def handle_webhook_event(
    db: Session,
    *,
    event: str,
    event_id: str | None,
    payload_json: str,
    signature: str | None,
    order_id: str | None,
    payment_id: str | None,
    payment_status: str | None,
    amount_paise: int | None = None,
    currency: str | None = None,
) -> tuple[bool, str | None]:
    existing = None
    if event_id:
        existing = get_webhook_log_by_event_id(db, event_id)
        if existing and existing.status in {"processed", "duplicate"}:
            logger.info("webhook_idempotent event_id=%s status=%s", event_id, existing.status)
            update_webhook_log_attempt(
                db,
                existing,
                status=existing.status,
                payment_context=existing.payment_context,
                error=existing.error,
                payload=payload_json,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
            )
            return True, None

    if event not in {"payment.captured", "payment.failed"}:
        if existing:
            update_webhook_log_attempt(
                db,
                existing,
                status="ignored",
                payment_context="unknown",
                payload=payload_json,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
            )
        else:
            create_webhook_log(
                db,
                event_id=event_id,
                event=event,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
                payload=payload_json,
                status="ignored",
                payment_context="unknown",
            )
        logger.info("webhook_ignored event=%s event_id=%s order_id=%s", event, event_id, order_id)
        return True, None

    expected_status = "captured" if event == "payment.captured" else "failed"
    if payment_status != expected_status:
        return False, "Payment status does not match webhook event"
    if event == "payment.captured" and (not payment_id or amount_paise is None or not currency):
        return False, "Captured payment is missing verification fields"

    if not order_id:
        if existing:
            update_webhook_log_attempt(
                db,
                existing,
                status="failed",
                payment_context="unknown",
                error="Missing order_id in webhook payload",
                payload=payload_json,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
            )
        else:
            create_webhook_log(
                db,
                event_id=event_id,
                event=event,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
                payload=payload_json,
                status="failed",
                payment_context="unknown",
                error="Missing order_id in webhook payload",
            )
        logger.warning("webhook_missing_order_id event=%s event_id=%s", event, event_id)
        return False, "Missing order_id"

    seller_payment = get_payment_by_provider_ref(db, order_id, for_update=True)
    if seller_payment:
        if event == "payment.captured" and (
            amount_paise != _to_paise(float(seller_payment.amount)) or currency != "INR"
        ):
            return False, "Payment amount or currency does not match seller order"
        if seller_payment.status == PaymentStatus.SUCCESS.value:
            if seller_payment.gateway_payment_id != payment_id:
                return False, "Payment ID does not match the successful seller payment"
            if existing:
                update_webhook_log_attempt(
                    db,
                    existing,
                    status="duplicate",
                    payment_context="seller",
                    payload=payload_json,
                    order_id=order_id,
                    payment_id=payment_id,
                    signature=signature,
                )
            else:
                create_webhook_log(
                    db,
                    event_id=event_id,
                    event=event,
                    order_id=order_id,
                    payment_id=payment_id,
                    signature=signature,
                    payload=payload_json,
                    status="duplicate",
                    payment_context="seller",
                )
            logger.info("webhook_duplicate_seller event=%s order_id=%s", event, order_id)
            return True, None

        if event == "payment.captured":
            mark_seller_payment_success(
                db,
                seller_payment,
                provider_ref=seller_payment.provider_ref,
                gateway_payment_id=payment_id,
                commit=False,
            )
            listing = db.query(SellLandRequest).filter(
                SellLandRequest.id == seller_payment.request_id
            ).with_for_update().first()
            if listing is None:
                db.rollback()
                return False, "Listing not found"
            mark_listing_pending_after_payment(db, listing, commit=False)
            db.commit()
            if existing:
                update_webhook_log_attempt(
                    db,
                    existing,
                    status="processed",
                    payment_context="seller",
                    payload=payload_json,
                    order_id=order_id,
                    payment_id=payment_id,
                    signature=signature,
                )
            else:
                create_webhook_log(
                    db,
                    event_id=event_id,
                    event=event,
                    order_id=order_id,
                    payment_id=payment_id,
                    signature=signature,
                    payload=payload_json,
                    status="processed",
                    payment_context="seller",
                )
            logger.info("webhook_seller_payment_captured order_id=%s payment_id=%s", order_id, payment_id)
            return True, None

        if event == "payment.failed":
            mark_seller_payment_failed(db, seller_payment, commit=False)
            db.commit()
            if existing:
                update_webhook_log_attempt(
                    db,
                    existing,
                    status="processed",
                    payment_context="seller",
                    payload=payload_json,
                    order_id=order_id,
                    payment_id=payment_id,
                    signature=signature,
                )
            else:
                create_webhook_log(
                    db,
                    event_id=event_id,
                    event=event,
                    order_id=order_id,
                    payment_id=payment_id,
                    signature=signature,
                    payload=payload_json,
                    status="processed",
                    payment_context="seller",
                )
            logger.info("webhook_seller_payment_failed order_id=%s payment_id=%s", order_id, payment_id)
            return True, None

    order = get_payment_order_by_order_id(db, order_id, for_update=True)
    if not order:
        if existing:
            update_webhook_log_attempt(
                db,
                existing,
                status="failed",
                payment_context="buyer",
                error="Order not found",
                payload=payload_json,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
            )
        else:
            create_webhook_log(
                db,
                event_id=event_id,
                event=event,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
                payload=payload_json,
                status="failed",
                payment_context="buyer",
                error="Order not found",
            )
        logger.warning("webhook_order_not_found event=%s order_id=%s", event, order_id)
        return False, "Order not found"

    if event == "payment.captured" and (
        amount_paise != order.amount_paise or currency != order.currency
    ):
        return False, "Payment amount or currency does not match order"

    if order.status == "SUCCESS":
        if existing:
            update_webhook_log_attempt(
                db,
                existing,
                status="duplicate",
                payment_context="buyer",
                payload=payload_json,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
            )
        else:
            create_webhook_log(
                db,
                event_id=event_id,
                event=event,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
                payload=payload_json,
                status="duplicate",
                payment_context="buyer",
            )
        logger.info("webhook_duplicate event=%s order_id=%s", event, order_id)
        return True, None

    if event == "payment.captured":
        resolved_payment_id = payment_id or order.payment_id or "unknown"
        mark_payment_success(
            db,
            order,
            payment_id=resolved_payment_id,
            signature=order.signature or "",
            commit=False,
        )
        booking = get_booking_for_listing_buyer(db, order.property_id, order.user_id)
        buyer = db.query(User).filter(User.id == order.user_id).first()
        buyer_name = (
            (booking.buyer_name if booking and booking.buyer_name else None)
            or (buyer.fullname if buyer and buyer.fullname else None)
            or "the user"
        )
        if booking and booking.payment_status != PaymentStatus.SUCCESS.value:
            mark_booking_confirmed(
                db,
                booking,
                method="razorpay",
                transaction_id=resolved_payment_id,
                commit=False,
            )
        listing = None
        if booking:
            listing = db.query(SellLandRequest).filter(SellLandRequest.id == booking.request_id).first()
            if listing and listing.status != SellLandStatus.BOOKED.value:
                mark_listing_booked(db, listing, commit=False)
        db.commit()
        try:
            _notify_buyer_booking_paid(db, listing, buyer_name=buyer_name)
        except Exception:
            logger.exception("Failed to send booking payment success notifications from webhook")
        if existing:
            update_webhook_log_attempt(
                db,
                existing,
                status="processed",
                payment_context="buyer",
                payload=payload_json,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
            )
        else:
            create_webhook_log(
                db,
                event_id=event_id,
                event=event,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
                payload=payload_json,
                status="processed",
                payment_context="buyer",
            )
        logger.info("webhook_payment_captured order_id=%s payment_id=%s", order_id, payment_id)
        return True, None

    if event == "payment.failed":
        mark_payment_failed(db, order, payment_id=payment_id, commit=False)
        booking = get_booking_for_listing_buyer(db, order.property_id, order.user_id)
        if booking and booking.payment_status != PaymentStatus.FAILED.value:
            mark_booking_failed(db, booking, transaction_id=payment_id, commit=False)
        db.commit()
        if existing:
            update_webhook_log_attempt(
                db,
                existing,
                status="processed",
                payment_context="buyer",
                payload=payload_json,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
            )
        else:
            create_webhook_log(
                db,
                event_id=event_id,
                event=event,
                order_id=order_id,
                payment_id=payment_id,
                signature=signature,
                payload=payload_json,
                status="processed",
                payment_context="buyer",
            )
        logger.info("webhook_payment_failed order_id=%s payment_id=%s", order_id, payment_id)
        return True, None

    if existing:
        update_webhook_log_attempt(
            db,
            existing,
            status="ignored",
            payment_context="buyer",
            payload=payload_json,
            order_id=order_id,
            payment_id=payment_id,
            signature=signature,
        )
    else:
        create_webhook_log(
            db,
            event_id=event_id,
            event=event,
            order_id=order_id,
            payment_id=payment_id,
            signature=signature,
            payload=payload_json,
            status="ignored",
            payment_context="buyer",
        )
    return True, None


def list_payments(
    db: Session,
    *,
    user_id: int | None,
    skip: int,
    limit: int,
) -> tuple[int, list[dict]]:
    total, items = list_payment_orders(db, user_id=user_id, skip=skip, limit=limit)
    payload = [
        {
            "id": item.id,
            "user_id": item.user_id,
            "property_id": item.property_id,
            "order_id": item.order_id,
            "payment_id": item.payment_id,
            "amount": item.amount,
            "status": item.status,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in items
    ]
    return total, payload


def get_payment_detail(
    db: Session,
    *,
    order_id: str,
) -> dict | None:
    item = get_payment_order_detail(db, order_id)
    if not item:
        return None
    return {
        "id": item.id,
        "user_id": item.user_id,
        "property_id": item.property_id,
        "order_id": item.order_id,
        "payment_id": item.payment_id,
        "amount": item.amount,
        "status": item.status,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def list_webhook_logs_service(
    db: Session,
    *,
    skip: int,
    limit: int,
    payment_context: str | None,
    status: str | None,
    event: str | None,
    order_id: str | None,
    payment_id: str | None,
) -> tuple[int, list[dict]]:
    total, items = list_webhook_logs(
        db,
        skip=skip,
        limit=limit,
        payment_context=payment_context,
        status=status,
        event=event,
        order_id=order_id,
        payment_id=payment_id,
    )
    payload = [
        {
            "id": item.id,
            "event_id": item.event_id,
            "event": item.event,
            "order_id": item.order_id,
            "payment_id": item.payment_id,
            "status": item.status,
            "payment_context": item.payment_context,
            "error": item.error,
            "payload": item.payload,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]
    return total, payload
