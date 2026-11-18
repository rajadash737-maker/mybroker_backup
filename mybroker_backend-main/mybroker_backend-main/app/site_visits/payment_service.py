from decimal import Decimal
import json
import logging

from razorpay.errors import SignatureVerificationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.payments.models import RazorpayPaymentOrder, RazorpayWebhookLog
from app.payments.repository import create_payment_order, mark_payment_success
from app.payments.schemas import VerifyPaymentResponse
from app.payments.service import _get_client
from app.sell_land.models import SellLandRequest
from app.site_visits.constants import AssignmentAction, AssignmentActorType, SiteVisitStatus
from app.site_visits.models import SiteVisitAssignment, SiteVisitRequest
from app.site_visits.schemas import SiteVisitVerifyPaymentRequest
from app.users.model import User
from app.users.roles import UserRole

logger = logging.getLogger(__name__)

PAYMENT_CONTEXT = "site_visit"
ACTIVE_ORDER_STATUSES = {"CREATED", "ATTEMPTED", "CANCEL_REPORTED"}


def _as_int(value, default=-1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fetch_order_and_payments(client, order_id: str) -> tuple[dict | None, list[dict] | None, str | None]:
    try:
        remote_order = client.order.fetch(order_id)
        collection = client.order.payments(order_id, {"count": 100})
    except Exception:
        logger.exception("Could not reconcile Razorpay Site Visit order_id=%s", order_id)
        return None, None, "Could not confirm previous Site Visit payment state with Razorpay"
    items = collection.get("items") if isinstance(collection, dict) else None
    if (
        not isinstance(remote_order, dict)
        or remote_order.get("id") != order_id
        or not isinstance(items, list)
        or any(not isinstance(item, dict) for item in items)
        or _as_int(collection.get("count"), len(items)) > len(items)
    ):
        return None, None, "Razorpay returned incomplete previous-order details"
    return remote_order, items, None


def _provider_captured_payments(remote_order: dict, payments: list[dict]) -> list[dict]:
    return [
        payment for payment in payments
        if payment.get("status") in {"captured", "refunded"} or payment.get("captured") is True
    ]


def _confirmed_non_capture(remote_order: dict, payments: list[dict]) -> str | None:
    if _as_int(remote_order.get("amount_paid"), 0) != 0:
        return None
    if _provider_captured_payments(remote_order, payments):
        return None
    remote_status = remote_order.get("status")
    if remote_status == "expired" and all(item.get("status") == "failed" for item in payments):
        return "EXPIRED"
    if remote_status == "attempted" and payments and all(item.get("status") == "failed" for item in payments):
        return "FAILED"
    return None


def _record_reconciliation_event(
    db: Session,
    *,
    order: RazorpayPaymentOrder,
    payment_id: str,
    amount_paise: int,
    source: str,
) -> None:
    existing = (
        db.query(RazorpayWebhookLog)
        .filter(
            RazorpayWebhookLog.event == "site_visit.duplicate_capture",
            RazorpayWebhookLog.order_id == order.order_id,
            RazorpayWebhookLog.payment_id == payment_id,
            RazorpayWebhookLog.status == "reconciliation_required",
        )
        .first()
    )
    if existing is not None:
        return
    db.add(
        RazorpayWebhookLog(
            event_id=None,
            event="site_visit.duplicate_capture",
            order_id=order.order_id,
            payment_id=payment_id,
            signature=None,
            status="reconciliation_required",
            payment_context=PAYMENT_CONTEXT,
            error="Additional captured payment requires reconciliation",
            payload=json.dumps(
                {
                    "source": source,
                    "site_visit_request_id": order.site_visit_request_id,
                    "order_id": order.order_id,
                    "payment_id": payment_id,
                    "amount_paise": amount_paise,
                }
            ),
        )
    )


def _record_failed_attempt(
    db: Session,
    *,
    order: RazorpayPaymentOrder,
    payment_id: str,
    source: str,
) -> None:
    existing = (
        db.query(RazorpayWebhookLog)
        .filter(
            RazorpayWebhookLog.event == "site_visit.payment_attempt_failed",
            RazorpayWebhookLog.order_id == order.order_id,
            RazorpayWebhookLog.payment_id == payment_id,
        )
        .first()
    )
    if existing is not None:
        return
    db.add(
        RazorpayWebhookLog(
            event_id=None,
            event="site_visit.payment_attempt_failed",
            order_id=order.order_id,
            payment_id=payment_id,
            signature=None,
            status="processed",
            payment_context=PAYMENT_CONTEXT,
            error=None,
            payload=json.dumps(
                {
                    "source": source,
                    "site_visit_request_id": order.site_visit_request_id,
                    "order_id": order.order_id,
                    "payment_id": payment_id,
                }
            ),
        )
    )


def _record_site_visit_capture(
    db: Session,
    *,
    booking: SiteVisitRequest,
    order: RazorpayPaymentOrder,
    provider_payment: dict,
    signature: str | None,
) -> tuple[bool, bool, str | None, int | None]:
    payment_id = provider_payment.get("id") if isinstance(provider_payment, dict) else None
    if (
        order.payment_context != PAYMENT_CONTEXT
        or order.site_visit_request_id != booking.id
        or order.user_id != booking.buyer_id
        or order.property_id != booking.listing_id
        or order.amount_paise != booking.site_visit_fee_paise
        or order.currency != "INR"
        or not payment_id
        or provider_payment.get("order_id") != order.order_id
        or _as_int(provider_payment.get("amount")) != booking.site_visit_fee_paise
        or provider_payment.get("currency") != "INR"
        or provider_payment.get("status") not in {"captured", "refunded"}
    ):
        return False, False, "Razorpay payment ID, order ID, amount, or currency does not match the Site Visit booking", None

    if order.status == "SUCCESS":
        return (True, False, None, None) if order.payment_id == payment_id else (True, True, None, None)
    if order.status == "DUPLICATE_SUCCESS":
        return True, True, None, None

    duplicate = booking.payment_status == "success" and booking.payment_id != payment_id
    if duplicate:
        # Preserve this second captured payment on its own shared ledger row;
        # leave the already-paid booking untouched for reconciliation/refund.
        order.payment_id = payment_id
        order.signature = signature or order.signature
        order.status = "DUPLICATE_SUCCESS"
        order.paid_at = func.now()
        db.flush()
        return True, True, None, None

    mark_payment_success(db, order, payment_id=payment_id, signature=signature or "", commit=False)
    booking.payment_id = payment_id
    booking.payment_status = "success"
    booking.paid_at = order.paid_at
    if booking.status == SiteVisitStatus.PENDING_PAYMENT.value:
        booking.status = SiteVisitStatus.PENDING.value
    assigned_officer_id = _auto_assign_site_visit_to_verifier(db, booking)
    return True, False, None, assigned_officer_id


def _auto_assign_site_visit_to_verifier(db: Session, booking: SiteVisitRequest) -> int | None:
    """Assign only a newly paid, pending, unassigned request to its valid property verifier."""
    if (
        booking.status != SiteVisitStatus.PENDING.value
        or booking.assigned_field_officer_id is not None
    ):
        return None

    listing = (
        db.query(SellLandRequest)
        .filter(SellLandRequest.id == booking.listing_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    verifier_id = listing.field_officer_reviewed_by_id if listing is not None else None
    if verifier_id is None:
        return None
    officer = (
        db.query(User)
        .filter(
            User.id == verifier_id,
            User.role == UserRole.FIELD_OFFICER.value,
            User.is_active.is_(True),
        )
        .with_for_update()
        .first()
    )
    if officer is None:
        return None

    booking.assigned_field_officer_id = officer.id
    booking.status = SiteVisitStatus.ASSIGNED.value
    db.add(
        SiteVisitAssignment(
            site_visit_request_id=booking.id,
            previous_field_officer_id=None,
            field_officer_id=officer.id,
            actor_id=None,
            action=AssignmentAction.ASSIGNED.value,
            actor_type=AssignmentActorType.SYSTEM.value,
            note="Automatically assigned to the property's verifying Field Officer after successful Site Visit payment.",
        )
    )
    db.flush()
    return officer.id


def _order_response(order: RazorpayPaymentOrder, booking_id: int) -> dict:
    return {
        "booking_id": booking_id,
        "order_id": order.order_id,
        "amount_paise": order.amount_paise,
        "currency": order.currency,
        "payment_status": order.status.lower(),
    }


def create_site_visit_order(db: Session, *, booking_id: int, buyer_id: int) -> tuple[dict | None, str | None]:
    booking = (
        db.query(SiteVisitRequest)
        .filter(SiteVisitRequest.id == booking_id, SiteVisitRequest.buyer_id == buyer_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if booking is None:
        db.rollback()
        return None, "Site Visit request not found"
    if booking.status != SiteVisitStatus.PENDING_PAYMENT.value:
        db.rollback()
        return None, "Site Visit request is not awaiting payment"
    if booking.payment_status == "success":
        db.rollback()
        return None, "Site Visit request is already paid"
    if booking.payment_order_id:
        order = (
            db.query(RazorpayPaymentOrder)
            .filter(RazorpayPaymentOrder.order_id == booking.payment_order_id)
            .with_for_update()
            .populate_existing()
            .first()
        )
        if (
            order is None
            or order.user_id != buyer_id
            or order.site_visit_request_id != booking.id
            or order.payment_context != PAYMENT_CONTEXT
            or order.property_id != booking.listing_id
            or order.amount_paise != booking.site_visit_fee_paise
            or order.currency != "INR"
        ):
            db.rollback()
            return None, "Stored Site Visit payment order is inconsistent"
        if order.status in {"SUCCESS", "DUPLICATE_SUCCESS"}:
            db.rollback()
            return None, "Site Visit request is already paid or requires reconciliation"
        try:
            client = _get_client()
        except RuntimeError:
            db.rollback()
            return None, "Payment gateway is not configured"
        remote_order, payments, error = _fetch_order_and_payments(client, order.order_id)
        if error:
            db.rollback()
            return None, error
        if (
            _as_int(remote_order.get("amount")) != booking.site_visit_fee_paise
            or remote_order.get("currency") != "INR"
            or not isinstance(remote_order.get("notes"), dict)
            or remote_order["notes"].get("context") != PAYMENT_CONTEXT
            or remote_order["notes"].get("site_visit_request_id") != str(booking.id)
            or remote_order["notes"].get("buyer_id") != str(buyer_id)
        ):
            db.rollback()
            return None, "Razorpay order amount or currency differs from the Site Visit snapshot"
        captured = _provider_captured_payments(remote_order, payments)
        if captured or _as_int(remote_order.get("amount_paid"), 0) > 0 or remote_order.get("status") == "paid":
            reconciliation_needed = False
            auto_assigned_officer_ids: set[int] = set()
            for payment_summary in captured:
                payment_id = payment_summary.get("id")
                if not payment_id:
                    db.rollback()
                    return None, "Captured Razorpay payment is missing its payment reference"
                try:
                    provider_payment = client.payment.fetch(payment_id)
                except Exception:
                    logger.exception("Could not verify late captured Site Visit payment_id=%s", payment_id)
                    db.rollback()
                    return None, "Could not verify captured Site Visit payment with Razorpay"
                ok, reconciliation, capture_error, auto_assigned_officer_id = _record_site_visit_capture(
                    db,
                    booking=booking,
                    order=order,
                    provider_payment=provider_payment,
                    signature=order.signature,
                )
                if not ok:
                    db.rollback()
                    return None, capture_error
                if auto_assigned_officer_id is not None:
                    auto_assigned_officer_ids.add(auto_assigned_officer_id)
                reconciliation_needed = reconciliation_needed or reconciliation
                if reconciliation:
                    _record_reconciliation_event(
                        db,
                        order=order,
                        payment_id=payment_id,
                        amount_paise=booking.site_visit_fee_paise,
                        source="order_reconciliation",
                    )
            if _as_int(remote_order.get("amount_paid"), 0) > 0 and not captured:
                db.rollback()
                return None, "Razorpay reports a paid order without a verifiable captured payment"
            db.commit()
            for officer_id in auto_assigned_officer_ids:
                _notify_auto_assigned_officer(db, booking_id=booking.id, officer_id=officer_id)
            if reconciliation_needed:
                return None, "Duplicate Site Visit capture recorded for reconciliation"
            return None, "Site Visit request is already paid"

        terminal_status = _confirmed_non_capture(remote_order, payments)
        if terminal_status:
            if booking.payment_status == "success":
                db.rollback()
                return None, "Site Visit request already has a successful payment"
            for failed_payment in payments:
                if failed_payment.get("status") == "failed" and failed_payment.get("id"):
                    _record_failed_attempt(
                        db,
                        order=order,
                        payment_id=failed_payment["id"],
                        source="order_reconciliation",
                    )
            if terminal_status == "FAILED":
                # Razorpay Orders remain payable in `attempted` state after a
                # failed payment. Reuse that one active provider order only for
                # a fresh payment attempt; never reuse the failed payment ID.
                order.status = "ATTEMPTED"
                order.payment_id = payments[-1].get("id")
                booking.payment_status = "initiated"
                db.commit()
                from app.site_visits.service import notify_site_visit_payment_event
                notify_site_visit_payment_event(db, booking_id=booking.id, event="PAYMENT_FAILED")
                return _order_response(order, booking.id), None
            order.status = "EXPIRED"
        elif remote_order.get("status") == "created" and not payments and order.status in ACTIVE_ORDER_STATUSES:
            # A local cancellation report does not cancel a Razorpay order. Keep
            # returning the single provider order while it remains payable.
            db.rollback()
            return _order_response(order, booking.id), None
        else:
            db.rollback()
            return None, "Previous payment attempt is still active or not conclusively uncaptured"

        if booking.payment_status not in {"initiated", "failed"}:
            db.rollback()
            return None, "Site Visit payment is not available for retry"
        prior_attempt_count = (
            db.query(RazorpayPaymentOrder)
            .filter(
                RazorpayPaymentOrder.site_visit_request_id == booking.id,
                RazorpayPaymentOrder.payment_context == PAYMENT_CONTEXT,
            )
            .count()
        )
    else:
        if booking.payment_status != "initiated" or booking.site_visit_fee_paise <= 0:
            db.rollback()
            return None, "Site Visit payment is not available"
        prior_attempt_count = 0

    try:
        client = client if booking.payment_order_id else _get_client()
        provider_order = client.order.create(
            {
                "amount": booking.site_visit_fee_paise,
                "currency": "INR",
                "payment_capture": 1,
                "receipt": f"sv-{booking.id}-{prior_attempt_count + 1}",
                "notes": {
                    "context": PAYMENT_CONTEXT,
                    "site_visit_request_id": str(booking.id),
                    "buyer_id": str(buyer_id),
                    "attempt_number": str(prior_attempt_count + 1),
                },
            }
        )
    except RuntimeError:
        db.rollback()
        return None, "Payment gateway is not configured"
    except Exception:
        db.rollback()
        logger.exception("Razorpay Site Visit order creation failed for booking_id=%s", booking.id)
        return None, "Payment gateway order creation failed"

    try:
        order_id = provider_order.get("id") if isinstance(provider_order, dict) else None
        amount = int(provider_order.get("amount", -1)) if isinstance(provider_order, dict) else -1
        currency = provider_order.get("currency") if isinstance(provider_order, dict) else None
    except (TypeError, ValueError):
        order_id, amount, currency = None, -1, None
    if not order_id or amount != booking.site_visit_fee_paise or currency != "INR":
        db.rollback()
        logger.error("Razorpay returned invalid Site Visit order terms for booking_id=%s", booking.id)
        return None, "Payment gateway returned invalid order terms"

    order = create_payment_order(
        db,
        user_id=buyer_id,
        property_id=booking.listing_id,
        amount_inr=float(Decimal(booking.site_visit_fee_paise) / Decimal(100)),
        amount_paise=booking.site_visit_fee_paise,
        currency="INR",
        order_id=order_id,
        payment_context=PAYMENT_CONTEXT,
        site_visit_request_id=booking.id,
        commit=False,
    )
    booking.payment_order_id = order_id
    booking.payment_status = "initiated"
    try:
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise
    return _order_response(order, booking.id), None


def cancel_site_visit_payment_attempt(
    db: Session, *, booking_id: int, buyer_id: int
) -> tuple[dict | None, str | None]:
    booking = (
        db.query(SiteVisitRequest)
        .filter(SiteVisitRequest.id == booking_id, SiteVisitRequest.buyer_id == buyer_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if booking is None:
        db.rollback()
        return None, "Site Visit request not found"
    if booking.status != SiteVisitStatus.PENDING_PAYMENT.value or not booking.payment_order_id:
        db.rollback()
        return None, "There is no active Site Visit payment attempt to cancel"
    order = (
        db.query(RazorpayPaymentOrder)
        .filter(RazorpayPaymentOrder.order_id == booking.payment_order_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if order is None or order.user_id != buyer_id:
        db.rollback()
        return None, "Site Visit payment order not found"
    if order.status == "SUCCESS":
        db.rollback()
        return None, "A successful payment cannot be cancelled"
    if order.status not in {"CREATED", "CANCEL_REPORTED"}:
        db.rollback()
        return None, "Site Visit payment attempt is no longer cancellable"
    # This records only the buyer's report. It does not represent a gateway
    # cancellation and must never be used as evidence that payment was absent.
    order.status = "CANCEL_REPORTED"
    order.buyer_cancel_reported_at = func.now()
    db.commit()
    return {"booking_id": booking.id, "order_id": order.order_id, "payment_status": "cancelled"}, None


def _site_visit_for_order(db: Session, order_id: str, *, for_update: bool = False) -> SiteVisitRequest | None:
    order = db.query(RazorpayPaymentOrder).filter(RazorpayPaymentOrder.order_id == order_id).first()
    if (
        order is None
        or order.payment_context != PAYMENT_CONTEXT
        or order.site_visit_request_id is None
    ):
        return None
    query = db.query(SiteVisitRequest).filter(SiteVisitRequest.id == order.site_visit_request_id)
    if for_update:
        query = query.with_for_update().populate_existing()
    return query.first()


def verify_site_visit_payment(
    db: Session,
    payload: SiteVisitVerifyPaymentRequest,
    *,
    booking_id: int,
    buyer_id: int,
) -> tuple[VerifyPaymentResponse | None, str | None]:
    order_reference = (
        db.query(RazorpayPaymentOrder)
        .filter(RazorpayPaymentOrder.order_id == payload.razorpay_order_id)
        .first()
    )
    if (
        order_reference is None
        or order_reference.payment_context != PAYMENT_CONTEXT
        or order_reference.site_visit_request_id != booking_id
    ):
        db.rollback()
        return None, "Site Visit payment order not found"
    booking = (
        db.query(SiteVisitRequest)
        .filter(SiteVisitRequest.id == booking_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if booking is None:
        db.rollback()
        return None, "Site Visit payment order not found"
    if booking.buyer_id != buyer_id:
        db.rollback()
        return None, "Not authorized"
    order = (
        db.query(RazorpayPaymentOrder)
        .filter(RazorpayPaymentOrder.order_id == payload.razorpay_order_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if order is None or order.user_id != buyer_id:
        db.rollback()
        return None, "Site Visit payment order not found"
    if (
        order.site_visit_request_id != booking.id
        or order.payment_context != PAYMENT_CONTEXT
        or order.property_id != booking.listing_id
        or order.amount_paise != booking.site_visit_fee_paise
        or order.currency != "INR"
    ):
        db.rollback()
        return None, "Order amount or currency does not match Site Visit fee snapshot"
    if order.status == "SUCCESS" and order.payment_id == payload.razorpay_payment_id:
        db.rollback()
        return VerifyPaymentResponse(status="success", order_id=order.order_id, payment_id=order.payment_id), None
    if booking.status not in {SiteVisitStatus.PENDING_PAYMENT.value, SiteVisitStatus.CANCELLED.value}:
        db.rollback()
        return None, "Site Visit request is not eligible for payment verification"

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
        db.rollback()
        return None, "Invalid payment signature"
    except RuntimeError:
        db.rollback()
        return None, "Payment gateway is not configured"
    except Exception:
        db.rollback()
        logger.exception("Razorpay Site Visit payment verification failed for order_id=%s", order.order_id)
        return None, "Payment verification failed"

    try:
        provider_amount = int(provider_payment.get("amount", -1)) if isinstance(provider_payment, dict) else -1
    except (TypeError, ValueError):
        provider_amount = -1
    if (
        not isinstance(provider_payment, dict)
        or provider_payment.get("id") != payload.razorpay_payment_id
        or provider_payment.get("order_id") != order.order_id
        or provider_amount != booking.site_visit_fee_paise
        or provider_payment.get("currency") != "INR"
    ):
        db.rollback()
        return None, "Payment details do not match the Site Visit order"

    provider_status = provider_payment.get("status")
    if provider_status in {"created", "authorized", "pending"}:
        db.rollback()
        return VerifyPaymentResponse(status="pending", order_id=order.order_id, payment_id=payload.razorpay_payment_id), None
    if provider_status == "failed":
        if order.status not in {"SUCCESS", "DUPLICATE_SUCCESS"} and booking.payment_status != "success":
            order.status = "ATTEMPTED"
            order.payment_id = payload.razorpay_payment_id
            booking.payment_status = "failed"
            _record_failed_attempt(
                db,
                order=order,
                payment_id=payload.razorpay_payment_id,
                source="payment_verification",
            )
        db.commit()
        from app.site_visits.service import notify_site_visit_payment_event
        notify_site_visit_payment_event(db, booking_id=booking.id, event="PAYMENT_FAILED")
        return VerifyPaymentResponse(status="failed", order_id=order.order_id, payment_id=payload.razorpay_payment_id), None
    if provider_status not in {"captured", "refunded"}:
        db.rollback()
        return None, "Payment is not in a verifiable state"

    ok, reconciliation, capture_error, auto_assigned_officer_id = _record_site_visit_capture(
        db,
        booking=booking,
        order=order,
        provider_payment=provider_payment,
        signature=payload.razorpay_signature,
    )
    if not ok:
        db.rollback()
        return None, capture_error
    if reconciliation:
        _record_reconciliation_event(
            db,
            order=order,
            payment_id=payload.razorpay_payment_id,
            amount_paise=booking.site_visit_fee_paise,
            source="payment_verification",
        )
    db.commit()
    from app.site_visits.service import notify_site_visit_payment_event
    notify_site_visit_payment_event(db, booking_id=booking.id, event="PAYMENT_SUCCESS")
    if auto_assigned_officer_id is not None:
        _notify_auto_assigned_officer(db, booking_id=booking.id, officer_id=auto_assigned_officer_id)
    response_status = "reconciliation_required" if reconciliation else "success"
    return VerifyPaymentResponse(
        status=response_status,
        order_id=order.order_id,
        payment_id=payload.razorpay_payment_id,
    ), None


def handle_site_visit_webhook(
    db: Session,
    *,
    order: RazorpayPaymentOrder,
    event: str,
    payment_id: str | None,
    signature: str | None,
    amount_paise: int | None,
    currency: str | None,
) -> tuple[bool, bool, str | None, int | None]:
    booking = _site_visit_for_order(db, order.order_id, for_update=True)
    if booking is None:
        return False, False, "Site Visit request not found for payment order", None
    locked_order = (
        db.query(RazorpayPaymentOrder)
        .filter(RazorpayPaymentOrder.order_id == order.order_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if locked_order is None:
        db.rollback()
        return False, False, "Razorpay order not found", None
    order = locked_order
    if (
        order.site_visit_request_id != booking.id
        or order.payment_context != PAYMENT_CONTEXT
        or order.user_id != booking.buyer_id
        or order.property_id != booking.listing_id
        or order.amount_paise != booking.site_visit_fee_paise
        or order.currency != "INR"
    ):
        db.rollback()
        return False, False, "Stored Site Visit order differs from booking or fee snapshot", None
    if event not in {"payment.captured", "payment.failed"} or not payment_id:
        db.rollback()
        return False, False, "Webhook payment reference is missing or event is unsupported", None
    if event == "payment.captured" and (
        amount_paise != booking.site_visit_fee_paise or currency != "INR"
    ):
        db.rollback()
        return False, False, "Webhook amount or currency does not match Site Visit fee snapshot", None

    try:
        client = _get_client()
        provider_payment = client.payment.fetch(payment_id)
    except Exception:
        logger.exception("Could not fetch Razorpay Site Visit webhook payment_id=%s", payment_id)
        db.rollback()
        return False, False, "Could not verify Site Visit payment with Razorpay", None
    if (
        not isinstance(provider_payment, dict)
        or provider_payment.get("id") != payment_id
        or provider_payment.get("order_id") != order.order_id
        or _as_int(provider_payment.get("amount")) != booking.site_visit_fee_paise
        or provider_payment.get("currency") != "INR"
    ):
        db.rollback()
        return False, False, "Razorpay payment ID, order ID, amount, or currency does not match Site Visit order", None

    provider_status = provider_payment.get("status")
    if provider_status in {"captured", "refunded"}:
        ok, reconciliation, error, auto_assigned_officer_id = _record_site_visit_capture(
            db,
            booking=booking,
            order=order,
            provider_payment=provider_payment,
            signature=signature,
        )
        if not ok:
            db.rollback()
            return False, False, error, None
        if reconciliation:
            _record_reconciliation_event(
                db,
                order=order,
                payment_id=payment_id,
                amount_paise=booking.site_visit_fee_paise,
                source="webhook",
            )
        return True, reconciliation, None, auto_assigned_officer_id
    if event == "payment.failed" and provider_status == "failed":
        if order.status not in {"SUCCESS", "DUPLICATE_SUCCESS"} and booking.payment_status != "success":
            order.status = "ATTEMPTED"
            order.payment_id = payment_id
            booking.payment_status = "failed"
            _record_failed_attempt(db, order=order, payment_id=payment_id, source="webhook")
        return True, False, None, None
    if provider_status in {"created", "authorized", "pending"}:
        db.rollback()
        return False, False, "Razorpay payment is not in a terminal state", None
    db.rollback()
    return False, False, "Razorpay payment status does not match webhook event", None


def is_site_visit_order(db: Session, order_id: str) -> bool:
    order = db.query(RazorpayPaymentOrder).filter(RazorpayPaymentOrder.order_id == order_id).first()
    return bool(order and order.payment_context == "site_visit")


def _notify_auto_assigned_officer(db: Session, *, booking_id: int, officer_id: int) -> None:
    # Imported lazily to keep the payment and Site Visit service modules decoupled.
    from app.site_visits.service import notify_site_visit_auto_assignment

    notify_site_visit_auto_assignment(db, request_id=booking_id, field_officer_id=officer_id)
