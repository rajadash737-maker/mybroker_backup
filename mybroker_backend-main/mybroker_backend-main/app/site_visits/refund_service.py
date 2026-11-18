"""Site Visit refund ledger operations. Money transfer remains external to MyBrokerr."""

from datetime import datetime
import logging

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.notifications.service import notify_users
from app.site_visits.models import SiteVisitRefund, SiteVisitRefundHistory, SiteVisitRequest
from app.site_visits.refund_crypto import RefundEncryptionConfigurationError, decrypt_buyer_upi, encrypt_buyer_upi
from app.site_visits.schemas import BuyerSiteVisitRefundDetailsRequest, SiteVisitRefundConfirmRequest, SiteVisitRefundFailureRequest
from app.sell_land.constants import PaymentStatus
from app.users.model import User
from app.users.roles import UserRole

logger = logging.getLogger(__name__)


class RefundUPIDecryptionError(RuntimeError):
    pass


def open_site_visit_refund(db: Session, *, booking: SiteVisitRequest, actor_id: int, actor_role: str) -> SiteVisitRefund | None:
    """Open one full-fee refund case after a paid booking is cancelled."""
    if booking.payment_status != PaymentStatus.SUCCESS.value or booking.site_visit_fee_paise <= 0:
        return None
    existing = db.query(SiteVisitRefund).filter_by(site_visit_request_id=booking.id).first()
    if existing is not None:
        return existing
    refund = SiteVisitRefund(
        site_visit_request_id=booking.id,
        original_payment_reference=booking.payment_id or booking.payment_order_id,
        eligible_amount_paise=booking.site_visit_fee_paise,
        status="pending_details",
    )
    db.add(refund)
    db.flush()
    db.add(SiteVisitRefundHistory(
        refund_id=refund.id,
        actor_id=actor_id,
        actor_role=actor_role,
        action="opened",
        previous_status=None,
        new_status="pending_details",
    ))
    return refund


def submit_site_visit_refund_details(
    db: Session, *, booking_id: int, buyer_id: int, payload: BuyerSiteVisitRefundDetailsRequest
) -> tuple[dict | None, str | None]:
    booking = db.query(SiteVisitRequest).filter_by(id=booking_id, buyer_id=buyer_id).with_for_update().first()
    if booking is None:
        db.rollback()
        return None, "Site Visit request not found"
    if booking.cancelled_at is None or booking.payment_status != PaymentStatus.SUCCESS.value:
        db.rollback()
        return None, "Refund details can only be submitted for a cancelled paid Site Visit"
    refund = db.query(SiteVisitRefund).filter_by(site_visit_request_id=booking.id).with_for_update().first()
    if refund is None:
        db.rollback()
        return None, "Refund case is not available"
    if refund.status == "pending":
        db.rollback()
        return {"refund_id": refund.id, "booking_id": booking.id, "status": refund.status}, None
    if refund.status != "pending_details":
        db.rollback()
        return None, "Refund details cannot be changed after accounting processing has started"
    old_status = refund.status
    try:
        refund.buyer_upi_ciphertext = encrypt_buyer_upi(refund.id, payload.upi_id)
    except RefundEncryptionConfigurationError:
        db.rollback()
        raise
    refund.status = "pending"
    db.add(SiteVisitRefundHistory(
        refund_id=refund.id,
        actor_id=buyer_id,
        actor_role=UserRole.CUSTOMER.value,
        action="details_submitted",
        previous_status=old_status,
        new_status=refund.status,
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    _notify_accounting_refund_ready(db, booking.id)
    return {"refund_id": refund.id, "booking_id": booking.id, "status": refund.status}, None


def _refund_history(refund: SiteVisitRefund) -> list[dict]:
    return [{
        "id": entry.id,
        "actor_id": entry.actor_id,
        "actor_role": entry.actor_role,
        "action": entry.action,
        "previous_status": entry.previous_status,
        "new_status": entry.new_status,
        "actual_amount_paise": entry.actual_amount_paise,
        "transaction_reference": entry.transaction_reference,
        "note": entry.note,
        "created_at": entry.created_at,
    } for entry in refund.history]


def _accounting_refund_item(refund: SiteVisitRefund) -> dict:
    booking = refund.site_visit
    try:
        upi = decrypt_buyer_upi(refund.id, refund.buyer_upi_ciphertext) if refund.buyer_upi_ciphertext else None
    except RefundEncryptionConfigurationError:
        raise
    except ValueError:
        raise RefundUPIDecryptionError from None
    return {
        "refund_id": refund.id,
        "booking_id": booking.id,
        "listing_id": booking.listing_id,
        "listing_code": booking.listing_code_snapshot,
        "property_name": booking.property_name_snapshot,
        "buyer_name": booking.buyer_name_snapshot,
        "buyer_mobile": booking.buyer_mobile_snapshot,
        "preferred_visit_date": booking.preferred_visit_date,
        "preferred_visit_time": booking.preferred_visit_time,
        "fee_paise": booking.site_visit_fee_paise,
        "payment_status": booking.payment_status,
        "original_payment_reference": refund.original_payment_reference,
        "cancellation_reason": booking.cancellation_reason,
        "eligible_amount_paise": refund.eligible_amount_paise,
        "actual_refunded_amount_paise": refund.actual_refunded_amount_paise,
        "buyer_upi_id": upi,
        "transaction_reference": refund.upi_transaction_reference,
        "status": refund.status,
        "refunded_at": refund.refunded_at,
        "accounting_user_id": refund.accounting_user_id,
        "internal_note": refund.internal_note,
        "failure_reason": refund.failure_reason,
        "created_at": refund.created_at,
        "history": _refund_history(refund),
    }


def _notify_refund_buyer(db: Session, booking_id: int, buyer_id: int, *, title: str, body: str, event: str) -> None:
    buyer = db.get(User, buyer_id)
    if not buyer:
        return
    try:
        notify_users(
            db=db,
            users=[buyer],
            title=title,
            body=body,
            notif_type=f"SITE_VISIT_REFUND_{event}",
            reference_id=str(booking_id),
            extra_data={"site_visit_request_id": str(booking_id), "event": f"REFUND_{event}"},
        )
    except Exception:
        db.rollback()
        logger.warning("Site Visit refund notification failed booking_id=%s event=%s", booking_id, event)


def _notify_accounting_refund_ready(db: Session, booking_id: int) -> None:
    accountants = db.query(User).filter(User.role == UserRole.ACCOUNTING.value, User.is_active.is_(True)).all()
    try:
        notify_users(
            db=db,
            users=accountants,
            title="Site Visit refund details received",
            body="A cancelled Site Visit has buyer refund details ready for Accounting review.",
            notif_type="SITE_VISIT_REFUND_REQUESTED",
            reference_id=str(booking_id),
            extra_data={"site_visit_request_id": str(booking_id), "event": "REFUND_REQUESTED"},
        )
    except Exception:
        db.rollback()
        logger.warning("Site Visit refund notification failed booking_id=%s event=requested", booking_id)


def get_site_visit_accounting_summary(db: Session) -> dict:
    booking_counts = dict(db.query(SiteVisitRequest.status, func.count(SiteVisitRequest.id)).group_by(SiteVisitRequest.status).all())
    payment_counts = dict(db.query(SiteVisitRequest.payment_status, func.count(SiteVisitRequest.id)).group_by(SiteVisitRequest.payment_status).all())
    refund_counts = dict(db.query(SiteVisitRefund.status, func.count(SiteVisitRefund.id)).group_by(SiteVisitRefund.status).all())
    revenue = db.query(func.coalesce(func.sum(SiteVisitRequest.site_visit_fee_paise), 0)).filter(SiteVisitRequest.payment_status == PaymentStatus.SUCCESS.value).scalar() or 0
    refunded_amount = db.query(func.coalesce(func.sum(SiteVisitRefund.actual_refunded_amount_paise), 0)).filter(SiteVisitRefund.status == "refunded").scalar() or 0
    cancelled = db.query(func.count(SiteVisitRequest.id)).filter(SiteVisitRequest.cancelled_at.is_not(None)).scalar() or 0
    return {
        "total_site_visit_bookings": sum(booking_counts.values()),
        "paid_site_visits": payment_counts.get(PaymentStatus.SUCCESS.value, 0),
        "pending_payments": payment_counts.get(PaymentStatus.INITIATED.value, 0),
        "cancelled_bookings": cancelled,
        "refund_requests": sum(refund_counts.values()),
        "refund_pending": refund_counts.get("pending_details", 0) + refund_counts.get("pending", 0),
        "refunded": refund_counts.get("refunded", 0),
        "refund_failed": refund_counts.get("failed", 0),
        "site_visit_revenue_paise": int(revenue),
        "refund_amount_paise": int(refunded_amount),
    }


def list_site_visit_accounting_refunds(
    db: Session, *, skip: int = 0, limit: int = 50, status_filter: str | None = None, search: str | None = None
) -> dict:
    query = db.query(SiteVisitRefund).join(SiteVisitRequest).options(
        joinedload(SiteVisitRefund.site_visit),
        joinedload(SiteVisitRefund.history),
    )
    if status_filter:
        query = query.filter(SiteVisitRefund.status == status_filter)
    if search:
        term = f"%{search.strip()}%"
        filters = [
            SiteVisitRequest.buyer_name_snapshot.ilike(term),
            SiteVisitRequest.buyer_mobile_snapshot.ilike(term),
            SiteVisitRequest.listing_code_snapshot.ilike(term),
            SiteVisitRefund.original_payment_reference.ilike(term),
            SiteVisitRefund.upi_transaction_reference.ilike(term),
        ]
        if search.strip().isdigit():
            numeric = int(search.strip())
            filters.extend([SiteVisitRefund.id == numeric, SiteVisitRequest.id == numeric, SiteVisitRequest.listing_id == numeric])
        query = query.filter(or_(*filters))
    total = query.order_by(None).count()
    rows = query.order_by(SiteVisitRefund.created_at.desc(), SiteVisitRefund.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "skip": skip, "limit": limit, "items": [_accounting_refund_item(row) for row in rows]}


def confirm_site_visit_refund(
    db: Session, *, refund_id: int, actor: User, payload: SiteVisitRefundConfirmRequest
) -> tuple[dict | None, str | None]:
    refund = db.query(SiteVisitRefund).filter_by(id=refund_id).with_for_update().first()
    if refund is None:
        db.rollback()
        return None, "Site Visit refund not found"
    if refund.status == "refunded":
        if refund.actual_refunded_amount_paise == payload.actual_refunded_amount_paise and refund.upi_transaction_reference == payload.transaction_reference:
            return {"refund_id": refund.id, "booking_id": refund.site_visit_request_id, "status": refund.status, "actual_refunded_amount_paise": refund.actual_refunded_amount_paise, "transaction_reference": refund.upi_transaction_reference, "accounting_user_id": refund.accounting_user_id or actor.id, "occurred_at": refund.refunded_at, "idempotent": True}, None
        db.rollback()
        return None, "Refund was already confirmed with different transaction details"
    if refund.status != "pending":
        db.rollback()
        return None, "Refund cannot be confirmed before buyer UPI details are submitted"
    if not refund.buyer_upi_ciphertext:
        db.rollback()
        return None, "Buyer refund details are missing"
    if payload.actual_refunded_amount_paise > refund.eligible_amount_paise:
        db.rollback()
        return None, "Refund amount exceeds the eligible amount"
    duplicate_reference = db.query(SiteVisitRefund.id).filter(
        SiteVisitRefund.upi_transaction_reference == payload.transaction_reference,
        SiteVisitRefund.id != refund.id,
    ).first()
    if duplicate_reference:
        db.rollback()
        return None, "UPI transaction reference has already been recorded"
    now = datetime.utcnow()
    old_status = refund.status
    refund.status = "refunded"
    refund.actual_refunded_amount_paise = payload.actual_refunded_amount_paise
    refund.upi_transaction_reference = payload.transaction_reference
    refund.refunded_at = now
    refund.accounting_user_id = actor.id
    refund.internal_note = payload.internal_note
    db.add(SiteVisitRefundHistory(
        refund_id=refund.id,
        actor_id=actor.id,
        actor_role=UserRole.ACCOUNTING.value,
        action="confirmed",
        previous_status=old_status,
        new_status=refund.status,
        actual_amount_paise=refund.actual_refunded_amount_paise,
        transaction_reference=refund.upi_transaction_reference,
        note=payload.internal_note,
        created_at=now,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(SiteVisitRefund).filter_by(upi_transaction_reference=payload.transaction_reference).first()
        if existing and existing.id == refund_id and existing.status == "refunded" and existing.actual_refunded_amount_paise == payload.actual_refunded_amount_paise:
            return {"refund_id": existing.id, "booking_id": existing.site_visit_request_id, "status": existing.status, "actual_refunded_amount_paise": existing.actual_refunded_amount_paise, "transaction_reference": existing.upi_transaction_reference, "accounting_user_id": existing.accounting_user_id or actor.id, "occurred_at": existing.refunded_at, "idempotent": True}, None
        return None, "UPI transaction reference has already been recorded"
    except Exception:
        db.rollback()
        raise
    _notify_refund_buyer(db, refund.site_visit_request_id, refund.site_visit.buyer_id, title="Site Visit refund recorded", body="Accounting recorded your Site Visit refund. Open your booking for the transaction reference.", event="CONFIRMED")
    return {"refund_id": refund.id, "booking_id": refund.site_visit_request_id, "status": refund.status, "actual_refunded_amount_paise": refund.actual_refunded_amount_paise, "transaction_reference": refund.upi_transaction_reference, "accounting_user_id": actor.id, "occurred_at": now, "idempotent": False}, None


def fail_site_visit_refund(
    db: Session, *, refund_id: int, actor: User, payload: SiteVisitRefundFailureRequest
) -> tuple[dict | None, str | None]:
    refund = db.query(SiteVisitRefund).filter_by(id=refund_id).with_for_update().first()
    if refund is None:
        db.rollback()
        return None, "Site Visit refund not found"
    if refund.status == "failed" and refund.failure_reason == payload.reason:
        return {"refund_id": refund.id, "booking_id": refund.site_visit_request_id, "status": refund.status, "actual_refunded_amount_paise": None, "transaction_reference": None, "accounting_user_id": refund.accounting_user_id or actor.id, "occurred_at": refund.updated_at, "idempotent": True}, None
    if refund.status != "pending":
        db.rollback()
        return None, "Only a pending Site Visit refund can be marked failed"
    now = datetime.utcnow()
    old_status = refund.status
    refund.status = "failed"
    refund.failure_reason = payload.reason
    refund.accounting_user_id = actor.id
    db.add(SiteVisitRefundHistory(refund_id=refund.id, actor_id=actor.id, actor_role=UserRole.ACCOUNTING.value, action="failed", previous_status=old_status, new_status=refund.status, note=payload.reason, created_at=now))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    _notify_refund_buyer(db, refund.site_visit_request_id, refund.site_visit.buyer_id, title="Site Visit refund needs attention", body="Accounting could not complete your Site Visit refund. Contact support for assistance.", event="FAILED")
    return {"refund_id": refund.id, "booking_id": refund.site_visit_request_id, "status": refund.status, "actual_refunded_amount_paise": None, "transaction_reference": None, "accounting_user_id": actor.id, "occurred_at": now, "idempotent": False}, None
