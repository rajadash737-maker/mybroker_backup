from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.sell_land.constants import PaymentStatus, SellLandStatus
from app.sell_land.models import SellLandRequest
from app.settings.models import ProcessingFeeSettings
from app.settings.repository import get_processing_fee_settings
from app.settings.service import get_or_create_processing_fees
from app.site_visits.constants import SiteVisitStatus, site_visit_today
from app.site_visits.constants import AssignmentAction, AssignmentActorType
from app.site_visits.models import SiteVisitAssignment, SiteVisitRequest, SiteVisitWorkflowHistory, SiteVisitRefund
from app.notifications.models import Notification
from app.payments.models import RazorpayWebhookLog
from app.site_visits.refund_service import open_site_visit_refund
from app.notifications.service import notify_users
from app.users.roles import UserRole
from app.site_visits.schemas import (
    SiteVisitBookingResponse,
    SiteVisitCancelRequest,
    SiteVisitCancelResponse,
    SiteVisitFeeResponse,
    SiteVisitRequestCreate,
    SiteVisitAdminActionRequest,
    SiteVisitCorrectionResponseRequest,
    SiteVisitBoundaryPoint,
)
from app.site_visits.completion_code import (
    CompletionCodeConfigurationError,
    decrypt_completion_code,
    encrypt_completion_code,
    generate_completion_code,
    hash_completion_code,
    verify_completion_code_hash,
)
from app.users.model import User


ACTIVE_DUPLICATE_STATUSES = (
    SiteVisitStatus.PENDING_PAYMENT.value,
    SiteVisitStatus.PENDING.value,
    SiteVisitStatus.ASSIGNED.value,
    SiteVisitStatus.SCHEDULED.value,
    SiteVisitStatus.IN_PROGRESS.value,
    SiteVisitStatus.CORRECTION_REQUIRED.value,
)
BUYER_CANCELLABLE_STATUSES = (
    SiteVisitStatus.PENDING_PAYMENT.value,
    SiteVisitStatus.PENDING.value,
    SiteVisitStatus.ASSIGNED.value,
    SiteVisitStatus.SCHEDULED.value,
    SiteVisitStatus.CORRECTION_REQUIRED.value,
)
MAX_SITE_VISIT_FEE_PAISE = 10_000_000
logger = logging.getLogger(__name__)
COMPLETION_CODE_TTL = timedelta(minutes=10)
COMPLETION_CODE_MAX_ATTEMPTS = 5


PAID_ADMIN_STATUSES = tuple(
    status.value for status in SiteVisitStatus if status != SiteVisitStatus.PENDING_PAYMENT
)


def _admin_site_visit_item(entity: SiteVisitRequest) -> dict:
    officer = entity.assigned_field_officer
    return {
        "id": entity.id,
        "listing_id": entity.listing_id,
        "listing_code": entity.listing_code_snapshot,
        "property_name": entity.property_name_snapshot,
        "buyer_name": entity.buyer_name_snapshot,
        "buyer_mobile": entity.buyer_mobile_snapshot,
        "preferred_visit_date": entity.preferred_visit_date,
        "preferred_visit_time": entity.preferred_visit_time,
        "visitor_count": entity.visitor_count,
        "status": entity.status,
        "payment_status": entity.payment_status,
        "site_visit_fee_rupees": (Decimal(entity.site_visit_fee_paise) / Decimal(100)).quantize(Decimal("0.01")),
        "paid_at": entity.paid_at,
        "assigned_field_officer": (
            {"id": officer.id, "fullname": officer.fullname} if officer else None
        ),
        "created_at": entity.created_at,
    }


def _invalidate_site_visit_completion_code(request: SiteVisitRequest) -> None:
    """Erase pending completion credentials when the visit can no longer use them."""
    request.completion_code_hash = None
    request.completion_code_encrypted = None
    request.completion_code_expires_at = None


def _workflow_history_item(item: SiteVisitWorkflowHistory) -> dict:
    return {
        "id": item.id,
        "event_type": item.event_type,
        "actor_id": item.actor_id,
        "actor_role": item.actor_role,
        "reason": item.reason,
        "previous_values": item.previous_values,
        "updated_values": item.updated_values,
        "created_at": item.created_at,
    }


def _admin_owns_site_visit_listing(db: Session, request: SiteVisitRequest, actor: User) -> bool:
    """Admin ownership follows the listing's current Admin reviewer/approver."""
    if actor.role == UserRole.SUPER_ADMIN.value:
        return True
    if actor.role != UserRole.ADMIN.value:
        return False
    return db.query(SellLandRequest.id).filter(
        SellLandRequest.id == request.listing_id,
        SellLandRequest.reviewed_by_id == actor.id,
    ).first() is not None


def list_admin_site_visits(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 20,
    request_status: str | None = None,
    assigned_field_officer_id: int | None = None,
    preferred_date_from=None,
    preferred_date_to=None,
    search: str | None = None,
    actor: User,
) -> dict:
    query = db.query(SiteVisitRequest).join(
        SellLandRequest, SellLandRequest.id == SiteVisitRequest.listing_id,
    ).filter(
        SiteVisitRequest.payment_status == PaymentStatus.SUCCESS.value
    )
    if actor.role == UserRole.ADMIN.value:
        query = query.filter(SellLandRequest.reviewed_by_id == actor.id)
    if request_status:
        query = query.filter(SiteVisitRequest.status == request_status)
    if assigned_field_officer_id is not None:
        query = query.filter(SiteVisitRequest.assigned_field_officer_id == assigned_field_officer_id)
    if preferred_date_from:
        query = query.filter(SiteVisitRequest.preferred_visit_date >= preferred_date_from)
    if preferred_date_to:
        query = query.filter(SiteVisitRequest.preferred_visit_date <= preferred_date_to)
    if search:
        term = f"%{search.strip()}%"
        predicates = [
            SiteVisitRequest.property_name_snapshot.ilike(term),
            SiteVisitRequest.listing_code_snapshot.ilike(term),
            SiteVisitRequest.buyer_name_snapshot.ilike(term),
            SiteVisitRequest.buyer_mobile_snapshot.ilike(term),
        ]
        if search.strip().isdigit():
            predicates.append(SiteVisitRequest.id == int(search.strip()))
        query = query.filter(or_(*predicates))

    total = query.order_by(None).count()
    entities = (
        query.options(joinedload(SiteVisitRequest.assigned_field_officer))
        .order_by(SiteVisitRequest.created_at.desc(), SiteVisitRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"total": total, "skip": skip, "limit": limit, "items": [_admin_site_visit_item(row) for row in entities]}


def get_admin_site_visit(db: Session, *, request_id: int, actor: User) -> dict | None:
    entity = (
        db.query(SiteVisitRequest)
        .join(SellLandRequest, SellLandRequest.id == SiteVisitRequest.listing_id)
        .options(
            joinedload(SiteVisitRequest.assigned_field_officer),
            joinedload(SiteVisitRequest.listing),
            selectinload(SiteVisitRequest.assignment_history).joinedload(SiteVisitAssignment.actor),
            selectinload(SiteVisitRequest.assignment_history).joinedload(SiteVisitAssignment.field_officer),
            selectinload(SiteVisitRequest.assignment_history).joinedload(SiteVisitAssignment.previous_field_officer),
            selectinload(SiteVisitRequest.workflow_history),
        )
        .filter(
            SiteVisitRequest.id == request_id,
            SiteVisitRequest.payment_status == PaymentStatus.SUCCESS.value,
        )
    )
    if actor.role == UserRole.ADMIN.value:
        entity = entity.filter(SellLandRequest.reviewed_by_id == actor.id)
    entity = entity.first()
    if entity is None:
        return None
    result = _admin_site_visit_item(entity)
    listing = entity.listing
    verifier = db.get(User, listing.field_officer_reviewed_by_id) if listing and listing.field_officer_reviewed_by_id else None
    result.update({
        "pickup_address": entity.pickup_address,
        "message": entity.message,
        "started_at": entity.started_at,
        "scheduled_at": entity.scheduled_at,
        "completed_at": entity.completed_at,
        "cancelled_at": entity.cancelled_at,
        "cancellation_reason": entity.cancellation_reason,
        "cancelled_by_id": entity.cancelled_by_id,
        "cancellation_actor_role": entity.cancellation_actor_role,
        "correction_reason": entity.correction_reason,
        "workflow_history": [_workflow_history_item(item) for item in entity.workflow_history],
        "cancelled_by_id": entity.cancelled_by_id,
        "cancellation_actor_role": entity.cancellation_actor_role,
        "correction_reason": entity.correction_reason,
        "workflow_history": [_workflow_history_item(item) for item in entity.workflow_history],
        "property": ({
            "id": listing.id,
            "listing_code": listing.listing_code,
            "title": listing.title,
            "status": listing.status,
            "city": listing.city,
            "state": listing.state,
            "location": listing.location,
            "field_officer_decision": listing.field_officer_decision,
            "field_officer_reviewed_at": listing.field_officer_reviewed_at,
            "verified_by": {"id": verifier.id, "fullname": verifier.fullname} if verifier else None,
        } if listing else None),
        "assignment_history": [{
            "id": item.id,
            "action": item.action,
            "actor_type": item.actor_type,
            "actor": {"id": item.actor.id, "fullname": item.actor.fullname} if item.actor else None,
            "previous_field_officer": ({"id": item.previous_field_officer.id, "fullname": item.previous_field_officer.fullname}
                                        if item.previous_field_officer else None),
            "field_officer": {"id": item.field_officer.id, "fullname": item.field_officer.fullname}
                              if item.field_officer else None,
            "note": item.note,
            "created_at": item.created_at,
        } for item in entity.assignment_history],
    })
    return result


def list_eligible_site_visit_field_officers(db: Session) -> list[dict]:
    officers = (
        db.query(User)
        .filter(User.role == UserRole.FIELD_OFFICER.value, User.is_active.is_(True))
        .order_by(User.fullname.asc(), User.id.asc())
        .all()
    )
    return [{"id": officer.id, "fullname": officer.fullname} for officer in officers]


def list_field_officer_site_visits(db: Session, *, officer_id: int) -> list[dict]:
    """Return only paid bookings currently assigned to this officer, without OTP secrets."""
    requests = (
        db.query(SiteVisitRequest)
        .options(
            selectinload(SiteVisitRequest.assignment_history),
            joinedload(SiteVisitRequest.listing),
        )
        .filter(
            SiteVisitRequest.assigned_field_officer_id == officer_id,
            SiteVisitRequest.payment_status == PaymentStatus.SUCCESS.value,
        )
        .order_by(SiteVisitRequest.preferred_visit_date.asc(),
                  SiteVisitRequest.preferred_visit_time.asc(), SiteVisitRequest.id.asc())
        .all()
    )
    results = []
    for request in requests:
        assignment = next(
            (row for row in reversed(request.assignment_history)
             if row.field_officer_id == officer_id and row.action in {
                 AssignmentAction.ASSIGNED.value, AssignmentAction.REASSIGNED.value
             }),
            None,
        )
        results.append({
            "id": request.id,
            "listing_id": request.listing_id,
            "listing_code": request.listing_code_snapshot,
            "land_boundary_points": _site_visit_boundary_points(
                request.listing.boundary_points if request.listing else None
            ),
            "property_name": request.property_name_snapshot,
            "buyer_name": request.buyer_name_snapshot,
            "buyer_mobile": request.buyer_mobile_snapshot,
            "preferred_visit_date": request.preferred_visit_date,
            "preferred_visit_time": request.preferred_visit_time,
            "visitor_count": request.visitor_count,
            "pickup_address": request.pickup_address,
            "message": request.message,
            "status": request.status,
            "payment_status": request.payment_status,
            "site_visit_fee_rupees": (Decimal(request.site_visit_fee_paise) / Decimal(100)).quantize(Decimal("0.01")),
            "started_at": request.started_at,
            "completed_at": request.completed_at,
            "assigned_at": assignment.created_at if assignment else None,
            "assignment_note": assignment.note if assignment else None,
        })
    return results


def _site_visit_boundary_points(raw: str | None) -> list[SiteVisitBoundaryPoint]:
    """Return only valid registered boundary coordinates for assigned visits."""
    if not raw:
        return []
    try:
        values = json.loads(raw)
        if not isinstance(values, list):
            return []
        points = []
        for value in values:
            try:
                points.append(SiteVisitBoundaryPoint.model_validate(value))
            except Exception:
                continue
        return points
    except (TypeError, ValueError):
        return []


def get_admin_site_visit_summary(db: Session, *, actor: User) -> dict:
    query = db.query(SiteVisitRequest.status, func.count(SiteVisitRequest.id)).join(
        SellLandRequest, SellLandRequest.id == SiteVisitRequest.listing_id,
    ).filter(SiteVisitRequest.payment_status == PaymentStatus.SUCCESS.value)
    if actor.role == UserRole.ADMIN.value:
        query = query.filter(SellLandRequest.reviewed_by_id == actor.id)
    rows = (
        query
        .group_by(SiteVisitRequest.status)
        .all()
    )
    counts = {status: count for status, count in rows}
    return {"total_paid": sum(counts.values()), **{status: counts.get(status, 0) for status in PAID_ADMIN_STATUSES}}


def get_super_admin_site_visit_audit_summary(db: Session) -> dict:
    booking = SiteVisitRequest
    total = db.query(func.count(booking.id)).scalar() or 0
    paid = db.query(func.count(booking.id)).filter(booking.payment_status == PaymentStatus.SUCCESS.value).scalar() or 0
    unpaid = db.query(func.count(booking.id)).filter(booking.payment_status != PaymentStatus.SUCCESS.value).scalar() or 0
    count_status = lambda value: db.query(func.count(booking.id)).filter(booking.status == value).scalar() or 0
    refund_pending = db.query(func.count(SiteVisitRefund.id)).filter(SiteVisitRefund.status.in_(("pending_details", "pending"))).scalar() or 0
    refunded_amount = db.query(func.coalesce(func.sum(SiteVisitRefund.actual_refunded_amount_paise), 0)).filter(SiteVisitRefund.status == "refunded").scalar() or 0
    failed_refunds = db.query(func.count(SiteVisitRefund.id)).filter(SiteVisitRefund.status == "failed").scalar() or 0
    notification_events = db.query(func.count(Notification.id)).filter(Notification.type.like("SITE_VISIT%") ).scalar() or 0
    return {"total_bookings": total, "paid_bookings": paid, "unpaid_bookings": unpaid,
        "pending_admin_review": count_status(SiteVisitStatus.PENDING.value),
        "assigned": count_status(SiteVisitStatus.ASSIGNED.value) + count_status(SiteVisitStatus.SCHEDULED.value),
        "in_progress": count_status(SiteVisitStatus.IN_PROGRESS.value), "completed": count_status(SiteVisitStatus.COMPLETED.value),
        "cancelled": count_status(SiteVisitStatus.CANCELLED.value), "correction_requests": count_status(SiteVisitStatus.CORRECTION_REQUIRED.value),
        "refund_pending": refund_pending, "refunded_amount_paise": int(refunded_amount), "failed_refunds": failed_refunds,
        "notification_events": notification_events}


def list_super_admin_site_visit_audit(db: Session, *, skip: int = 0, limit: int = 25, date_from=None, date_to=None,
    booking_id: int | None = None, listing_id: int | None = None, listing_code: str | None = None,
    buyer_search: str | None = None, officer_id: int | None = None, officer_search: str | None = None, admin_id: int | None = None,
    accounting_id: int | None = None, reference_search: str | None = None) -> dict:
    query = db.query(SiteVisitRequest)
    if date_from:
        query = query.filter(SiteVisitRequest.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(SiteVisitRequest.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    if booking_id:
        query = query.filter(SiteVisitRequest.id == booking_id)
    if listing_id:
        query = query.filter(SiteVisitRequest.listing_id == listing_id)
    if listing_code:
        query = query.filter(SiteVisitRequest.listing_code_snapshot.ilike(f"%{listing_code.strip()}%"))
    if buyer_search:
        term = f"%{buyer_search.strip()}%"
        query = query.filter(or_(SiteVisitRequest.buyer_name_snapshot.ilike(term), SiteVisitRequest.buyer_mobile_snapshot.ilike(term)))
    if officer_id:
        query = query.filter(or_(SiteVisitRequest.assigned_field_officer_id == officer_id, SiteVisitRequest.id.in_(
            db.query(SiteVisitAssignment.site_visit_request_id).filter(or_(SiteVisitAssignment.field_officer_id == officer_id, SiteVisitAssignment.previous_field_officer_id == officer_id)))))
    if officer_search:
        term = f"%{officer_search.strip()}%"
        officer_ids = db.query(User.id).filter(User.role == UserRole.FIELD_OFFICER.value,
            or_(User.fullname.ilike(term), User.mobile.ilike(term)))
        query = query.filter(or_(SiteVisitRequest.assigned_field_officer_id.in_(officer_ids), SiteVisitRequest.id.in_(
            db.query(SiteVisitAssignment.site_visit_request_id).filter(or_(SiteVisitAssignment.field_officer_id.in_(officer_ids),
                SiteVisitAssignment.previous_field_officer_id.in_(officer_ids))))))
    if admin_id:
        query = query.filter(or_(SiteVisitRequest.id.in_(db.query(SiteVisitAssignment.site_visit_request_id).filter(SiteVisitAssignment.actor_id == admin_id)),
            SiteVisitRequest.id.in_(db.query(SiteVisitWorkflowHistory.site_visit_request_id).filter(SiteVisitWorkflowHistory.actor_id == admin_id))))
    if accounting_id:
        query = query.filter(SiteVisitRequest.id.in_(db.query(SiteVisitRefund.site_visit_request_id).filter(SiteVisitRefund.accounting_user_id == accounting_id)))
    if reference_search:
        term = f"%{reference_search.strip()}%"
        query = query.filter(or_(SiteVisitRequest.payment_id.ilike(term), SiteVisitRequest.payment_order_id.ilike(term),
            SiteVisitRequest.payment_order_id.in_(db.query(RazorpayWebhookLog.order_id).filter(
                RazorpayWebhookLog.payment_context == "site_visit", RazorpayWebhookLog.payment_id.ilike(term))),
            SiteVisitRequest.id.in_(db.query(SiteVisitRefund.site_visit_request_id).filter(or_(
                SiteVisitRefund.original_payment_reference.ilike(term), SiteVisitRefund.upi_transaction_reference.ilike(term))))))
    total = query.order_by(None).count()
    rows = query.options(joinedload(SiteVisitRequest.assigned_field_officer)).order_by(SiteVisitRequest.created_at.desc(), SiteVisitRequest.id.desc()).offset(skip).limit(limit).all()
    items = []
    for row in rows:
        item = _admin_site_visit_item(row)
        item.update({"seller_name": row.seller_name_snapshot, "payment_order_id": row.payment_order_id, "payment_id": row.payment_id})
        items.append(item)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


def get_super_admin_site_visit_audit_detail(db: Session, *, request_id: int) -> dict | None:
    entity = db.query(SiteVisitRequest).options(joinedload(SiteVisitRequest.assigned_field_officer),
        selectinload(SiteVisitRequest.assignment_history).joinedload(SiteVisitAssignment.actor),
        selectinload(SiteVisitRequest.assignment_history).joinedload(SiteVisitAssignment.field_officer),
        selectinload(SiteVisitRequest.assignment_history).joinedload(SiteVisitAssignment.previous_field_officer),
        selectinload(SiteVisitRequest.workflow_history), selectinload(SiteVisitRequest.refund_record).selectinload(SiteVisitRefund.history)
    ).filter(SiteVisitRequest.id == request_id).first()
    if entity is None:
        return None
    result = _admin_site_visit_item(entity)
    result.update({"seller_name": entity.seller_name_snapshot, "payment_order_id": entity.payment_order_id, "payment_id": entity.payment_id,
        "pickup_address": entity.pickup_address, "message": entity.message, "started_at": entity.started_at,
        "completed_at": entity.completed_at, "cancelled_at": entity.cancelled_at, "cancellation_reason": entity.cancellation_reason,
        "cancellation_actor_role": entity.cancellation_actor_role,
        "assignment_history": [{"id": a.id, "action": a.action, "actor_type": a.actor_type,
            "actor": ({"id": a.actor.id, "fullname": a.actor.fullname} if a.actor else None),
            "previous_field_officer": ({"id": a.previous_field_officer.id, "fullname": a.previous_field_officer.fullname}
                                        if a.previous_field_officer else None),
            "field_officer": ({"id": a.field_officer.id, "fullname": a.field_officer.fullname}
                              if a.field_officer else None),
            "note": a.note, "created_at": a.created_at} for a in entity.assignment_history],
        "workflow_history": [_workflow_history_item(h) for h in entity.workflow_history],
        "payment_history": [{"event": "booking_payment_state", "payment_status": entity.payment_status,
            "order_id": entity.payment_order_id, "payment_id": entity.payment_id, "paid_at": entity.paid_at, "created_at": entity.created_at}] + [
            {"event": log.event, "status": log.status, "order_id": log.order_id, "payment_id": log.payment_id,
             "attempt_count": log.attempt_count, "created_at": log.created_at}
            for log in db.query(RazorpayWebhookLog).filter(RazorpayWebhookLog.payment_context == "site_visit",
                RazorpayWebhookLog.order_id == entity.payment_order_id).order_by(RazorpayWebhookLog.created_at.asc()).all()
        ],
        "refund_history": ([{"refund_id": h.id, "actor_id": h.actor_id, "actor_role": h.actor_role, "action": h.action,
            "previous_status": h.previous_status, "new_status": h.new_status, "actual_amount_paise": h.actual_amount_paise,
            "transaction_reference": h.transaction_reference, "note": h.note, "created_at": h.created_at}
            for h in entity.refund_record.history] if entity.refund_record else []),
        "notification_history": [{"id": n.id, "user_id": n.user_id, "recipient_role": n.role_target, "title": n.title,
            "body": n.body, "type": n.type, "reference_id": n.reference_id, "is_read": n.is_read, "created_at": n.created_at}
            for n in db.query(Notification).filter(Notification.type.like("SITE_VISIT%"), Notification.reference_id == str(entity.id)).order_by(Notification.created_at.asc()).all()]})
    return result


def mutate_admin_site_visit_assignment(
    db: Session,
    *,
    request_id: int,
    actor: User,
    field_officer_id: int | None,
    note: str | None = None,
) -> tuple[dict | None, str | None]:
    """Assign, reassign, or unassign a paid request and append its audit row atomically."""
    request = (
        db.query(SiteVisitRequest)
        .filter(SiteVisitRequest.id == request_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if request is None:
        db.rollback()
        return None, "Site Visit request not found"
    if not _admin_owns_site_visit_listing(db, request, actor):
        db.rollback()
        return None, "Site Visit request not found"
    if request.payment_status != PaymentStatus.SUCCESS.value:
        db.rollback()
        return None, "Only successfully paid Site Visit requests can be assigned"

    previous_id = request.assigned_field_officer_id
    previous_officer = db.get(User, previous_id) if previous_id is not None else None
    has_progress_timestamp = any((request.scheduled_at, request.started_at, request.completed_at, request.cancelled_at))
    in_progress = request.status == SiteVisitStatus.IN_PROGRESS.value
    if field_officer_id is None:
        if in_progress:
            if previous_id is None:
                db.rollback()
                return None, "Site Visit request has no assigned Field Officer"
            if not note or len(note.strip()) < 3:
                db.rollback()
                return None, "An override reason of at least 3 characters is required during an active visit"
            action = AssignmentAction.UNASSIGNED
            target_officer = None
            request.assigned_field_officer_id = None
        elif request.status != SiteVisitStatus.ASSIGNED.value or previous_id is None or has_progress_timestamp:
            db.rollback()
            return None, "Site Visit request cannot be unassigned in its current state"
        else:
            action = AssignmentAction.UNASSIGNED
            target_officer = None
            request.assigned_field_officer_id = None
            request.status = SiteVisitStatus.PENDING.value
    else:
        target_officer = (
            db.query(User)
            .filter(
                User.id == field_officer_id,
                User.role == UserRole.FIELD_OFFICER.value,
                User.is_active.is_(True),
            )
            .with_for_update()
            .first()
        )
        if target_officer is None:
            db.rollback()
            return None, "Field Officer is not eligible for assignment"
        if in_progress:
            if not note or len(note.strip()) < 3:
                db.rollback()
                return None, "An override reason of at least 3 characters is required during an active visit"
            if previous_id == target_officer.id:
                db.rollback()
                return None, "Site Visit request is already assigned to this Field Officer"
            action = AssignmentAction.REASSIGNED if previous_id is not None else AssignmentAction.ASSIGNED
            request.assigned_field_officer_id = target_officer.id
        elif request.status == SiteVisitStatus.PENDING.value and previous_id is None and not has_progress_timestamp:
            action = AssignmentAction.ASSIGNED
        elif request.status == SiteVisitStatus.ASSIGNED.value and previous_id is not None and not has_progress_timestamp:
            if previous_id == target_officer.id:
                db.rollback()
                return None, "Site Visit request is already assigned to this Field Officer"
            action = AssignmentAction.REASSIGNED
        else:
            db.rollback()
            return None, "Site Visit request cannot be assigned in its current state"
        request.assigned_field_officer_id = target_officer.id
        # Active visit overrides change staffing while preserving the visit lifecycle.
        if not in_progress:
            request.status = SiteVisitStatus.ASSIGNED.value

    if in_progress and previous_id != (target_officer.id if target_officer else None):
        _invalidate_site_visit_completion_code(request)

    actor_type = (
        AssignmentActorType.SUPER_ADMIN
        if actor.role == UserRole.SUPER_ADMIN.value
        else AssignmentActorType.ADMIN
    )
    audit_time = datetime.utcnow()
    history = SiteVisitAssignment(
        site_visit_request_id=request.id,
        previous_field_officer_id=previous_id,
        field_officer_id=target_officer.id if target_officer else None,
        actor_id=actor.id,
        action=action.value,
        actor_type=actor_type.value,
        note=note,
        created_at=audit_time,
    )
    db.add(history)
    if in_progress:
        override_action = "in_progress_unassigned" if field_officer_id is None else "in_progress_reassigned"
        db.add(SiteVisitWorkflowHistory(
            site_visit_request_id=request.id,
            event_type=override_action,
            actor_id=actor.id,
            actor_role=actor.role,
            reason=note.strip(),
            previous_values={"status": SiteVisitStatus.IN_PROGRESS.value, "field_officer_id": previous_id},
            updated_values={"status": SiteVisitStatus.IN_PROGRESS.value, "field_officer_id": target_officer.id if target_officer else None},
            created_at=audit_time,
        ))
    try:
        db.commit()
        db.refresh(history)
    except Exception:
        db.rollback()
        raise

    # Notification failures must not undo an already committed assignment/history pair.
    if target_officer is not None:
        _send_assignment_notification(
            db,
            target_officer,
            request_id=request.id,
            notif_type="SITE_VISIT_ASSIGNED",
            title="Site Visit Assigned",
            action=action.value,
        )
    if previous_officer is not None and action in {AssignmentAction.REASSIGNED, AssignmentAction.UNASSIGNED}:
        _send_assignment_notification(
            db,
            previous_officer,
            request_id=request.id,
            notif_type="SITE_VISIT_ASSIGNMENT_REMOVED",
            title="Site Visit Assignment Updated",
            action=action.value,
        )
    if in_progress:
        _notify_site_visit_admins(
            db, request,
            title="In-progress Site Visit assignment overridden",
            body=f"An Admin changed Field Officer assignment for Site Visit booking #{request.id}.",
            event="IN_PROGRESS_ASSIGNMENT_OVERRIDE",
        )

    return {
        "request_id": request.id,
        "status": request.status,
        "action": history.action,
        "previous_field_officer_id": history.previous_field_officer_id,
        "field_officer_id": history.field_officer_id,
        "actor_id": history.actor_id,
        "actor_type": history.actor_type,
        "note": history.note,
        "created_at": history.created_at,
    }, None


def _send_assignment_notification(
    db: Session,
    officer: User,
    *,
    request_id: int,
    notif_type: str,
    title: str,
    action: str,
) -> None:
    try:
        booking = db.get(SiteVisitRequest, request_id)
        property_name = booking.property_name_snapshot if booking else "Site Visit"
        listing_id = booking.listing_id if booking else None
        listing_context = f"{property_name} (Listing #{listing_id})" if listing_id is not None else property_name
        if notif_type == "SITE_VISIT_ASSIGNED":
            body = f"Site Visit booking #{request_id} for {listing_context} has been assigned to you."
        elif action == AssignmentAction.REASSIGNED.value:
            body = f"Site Visit booking #{request_id} for {listing_context} was reassigned to another Field Officer."
        else:
            body = f"You are no longer assigned to Site Visit booking #{request_id} for {listing_context}."
        deep_link = (
            f"field_site_visit_booking/{request_id}"
            if notif_type == "SITE_VISIT_ASSIGNED"
            else "field_site_visits"
        )
        notify_users(
            db=db,
            users=[officer],
            title=title,
            body=body,
            notif_type=notif_type,
            role_target=UserRole.FIELD_OFFICER.value,
            reference_id=str(request_id),
            extra_data={
                "site_visit_request_id": str(request_id),
                "assignment_action": action,
                "listing_id": str(listing_id or ""),
                "property_name": property_name,
                "deep_link": deep_link,
            },
        )
    except Exception:
        db.rollback()
        logger.exception("Site Visit assignment notification failed for request_id=%s user_id=%s", request_id, officer.id)


def notify_site_visit_auto_assignment(db: Session, *, request_id: int, field_officer_id: int) -> None:
    """Send the standard assignment notification after the payment transaction commits."""
    try:
        officer = db.get(User, field_officer_id)
        if officer is None:
            logger.warning(
                "Auto-assigned Site Visit officer disappeared before notification request_id=%s user_id=%s",
                request_id,
                field_officer_id,
            )
            return
        _send_assignment_notification(
            db,
            officer,
            request_id=request_id,
            notif_type="SITE_VISIT_ASSIGNED",
            title="Site Visit Assigned",
            action=AssignmentAction.ASSIGNED.value,
        )
    except Exception:
        db.rollback()
        logger.exception(
            "Automatic Site Visit assignment notification failed for request_id=%s user_id=%s",
            request_id,
            field_officer_id,
        )


def _fee_paise(fee_rupees: Decimal) -> int:
    normalized = Decimal(str(fee_rupees)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    paise = int(normalized * 100)
    if paise < 0 or paise > MAX_SITE_VISIT_FEE_PAISE:
        raise ValueError("Configured Site Visit fee is outside the supported range")
    return paise


def _fee_record_for_update(db: Session) -> ProcessingFeeSettings:
    record = get_processing_fee_settings(db)
    if record is None:
        # Match the existing settings endpoint's default-row behavior before
        # beginning the booking transaction that locks listing and fee rows.
        get_or_create_processing_fees(db)
    record = (
        db.query(ProcessingFeeSettings)
        .with_for_update()
        .first()
    )
    if record is None:
        raise RuntimeError("Processing fee settings could not be loaded")
    return record


def _to_booking_response(entity: SiteVisitRequest, *, include_active_completion_code: bool = False) -> SiteVisitBookingResponse:
    fee_paise = entity.site_visit_fee_paise
    code = None
    expires_at = None
    now = datetime.utcnow()
    if (
        include_active_completion_code
        and entity.buyer_id != entity.seller_id
        and entity.status == SiteVisitStatus.IN_PROGRESS.value
        and entity.completion_code_encrypted
        and entity.completion_code_hash
        and entity.completion_code_used_at is None
        and entity.completion_code_failed_attempts < COMPLETION_CODE_MAX_ATTEMPTS
        and entity.completion_code_expires_at is not None
        and entity.completion_code_expires_at > now
    ):
        try:
            code = decrypt_completion_code(entity.id, entity.completion_code_encrypted)
            expires_at = entity.completion_code_expires_at
        except Exception:
            logger.error("Site Visit completion-code retrieval failed request_id=%s", entity.id)
    return SiteVisitBookingResponse(
        id=entity.id,
        listing_id=entity.listing_id,
        listing_code=entity.listing_code_snapshot,
        property_name=entity.property_name_snapshot,
        buyer_name=entity.buyer_name_snapshot,
        buyer_mobile=entity.buyer_mobile_snapshot,
        preferred_visit_date=entity.preferred_visit_date,
        preferred_visit_time=entity.preferred_visit_time,
        visitor_count=entity.visitor_count,
        pickup_address=entity.pickup_address,
        message=entity.message,
        booking_status=entity.status,
        payment_status=entity.payment_status,
        site_visit_fee_rupees=(Decimal(fee_paise) / Decimal(100)).quantize(Decimal("0.01")),
        site_visit_fee_paise=fee_paise,
        cancellation_reason=entity.cancellation_reason,
        cancelled_at=entity.cancelled_at,
        cancelled_by_role=entity.cancellation_actor_role,
        correction_reason=entity.correction_reason,
        correction_requested_at=entity.correction_requested_at,
        workflow_history=[_workflow_history_item(item) for item in entity.workflow_history],
        refund=(
            {
                "eligible": True,
                "eligible_amount_paise": entity.refund_record.eligible_amount_paise,
                "status": entity.refund_record.status,
                "actual_refunded_amount_paise": entity.refund_record.actual_refunded_amount_paise,
                "transaction_reference": entity.refund_record.upi_transaction_reference,
                "refunded_at": entity.refund_record.refunded_at,
            }
            if entity.refund_record is not None
            else ({"eligible": False, "eligible_amount_paise": 0, "status": None, "actual_refunded_amount_paise": None, "transaction_reference": None, "refunded_at": None} if entity.cancelled_at and entity.payment_status == PaymentStatus.SUCCESS.value else None)
        ),
        created_at=entity.created_at,
        completion_code=code,
        completion_code_expires_at=expires_at,
    )


def get_site_visit_fee(db: Session) -> SiteVisitFeeResponse:
    record = get_or_create_processing_fees(db)
    fee_paise = _fee_paise(Decimal(str(record.site_visit_fee)))
    return SiteVisitFeeResponse(
        site_visit_fee_rupees=(Decimal(fee_paise) / Decimal(100)).quantize(Decimal("0.01")),
        site_visit_fee_paise=fee_paise,
    )


def create_site_visit_request(
    db: Session,
    *,
    buyer: User,
    payload: SiteVisitRequestCreate,
) -> tuple[SiteVisitBookingResponse | None, str | None]:
    if payload.preferred_visit_date < site_visit_today():
        return None, "Preferred visit date cannot be in the past"

    try:
        fee_record = _fee_record_for_update(db)
        listing = (
            db.query(SellLandRequest)
            .filter(SellLandRequest.id == payload.listing_id)
            .with_for_update()
            .first()
        )
        if listing is None:
            db.rollback()
            return None, "Listing not found"
        if listing.status != SellLandStatus.LIVE.value:
            db.rollback()
            return None, "Only live listings can receive Site Visit requests"
        if listing.user_id == buyer.id:
            db.rollback()
            return None, "You cannot request a Site Visit for your own listing"

        duplicate_query = db.query(SiteVisitRequest).filter(
            SiteVisitRequest.buyer_id == buyer.id,
            SiteVisitRequest.listing_id == listing.id,
        )
        if payload.submission_key:
            existing_key = db.query(SiteVisitRequest).filter(
                SiteVisitRequest.buyer_id == buyer.id,
                SiteVisitRequest.submission_key == payload.submission_key,
            ).first()
            if existing_key:
                same_request = (
                    existing_key.listing_id == listing.id
                    and existing_key.preferred_visit_date == payload.preferred_visit_date
                    and existing_key.preferred_visit_time == payload.preferred_visit_time
                    and existing_key.visitor_count == payload.visitor_count
                    and existing_key.pickup_address == payload.pickup_address
                    and existing_key.message == payload.message
                )
                db.rollback()
                if same_request:
                    return _to_booking_response(existing_key), None
                return None, "Submission key was already used for a different Site Visit request"

        active_duplicate = duplicate_query.filter(
            SiteVisitRequest.status.in_(ACTIVE_DUPLICATE_STATUSES)
        ).first()
        if active_duplicate:
            db.rollback()
            return None, "An active Site Visit request already exists for this listing"

        seller = db.query(User).filter(User.id == listing.user_id).first()
        if seller is None:
            db.rollback()
            return None, "Listing seller not found"

        buyer_mobile = (buyer.mobile or "").strip()
        if not buyer_mobile:
            db.rollback()
            return None, "A registered mobile number is required to request a Site Visit"

        fee_paise = _fee_paise(Decimal(str(fee_record.site_visit_fee)))
        buyer_name = (buyer.fullname or "").strip() or (buyer.username or "").strip() or "Buyer"
        seller_name = (listing.owner_name or seller.fullname or "").strip() or "Seller"
        seller_mobile = (listing.owner_mobile or seller.mobile or "").strip()
        property_name = (listing.title or "").strip() or f"Land listing {listing.id}"

        entity = SiteVisitRequest(
            listing_id=listing.id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            property_name_snapshot=property_name,
            listing_code_snapshot=listing.listing_code,
            buyer_name_snapshot=buyer_name,
            buyer_mobile_snapshot=buyer_mobile,
            seller_name_snapshot=seller_name,
            seller_mobile_snapshot=seller_mobile,
            preferred_visit_date=payload.preferred_visit_date,
            preferred_visit_time=payload.preferred_visit_time,
            visitor_count=payload.visitor_count,
            pickup_address=payload.pickup_address,
            message=payload.message,
            submission_key=payload.submission_key,
            site_visit_fee_paise=fee_paise,
            status=SiteVisitStatus.PENDING_PAYMENT.value,
            payment_status=PaymentStatus.INITIATED.value,
        )
        db.add(entity)
        db.commit()
        db.refresh(entity)
        _notify_site_visit_buyer(db, entity, title="Site Visit booking received", body="Your Site Visit request is ready for payment. Open the booking to continue.", event="BOOKING_CREATED")
        _notify_site_visit_admins(db, entity, title="New Site Visit request", body="A buyer created a Site Visit request. Review it in the admin queue.", event="BOOKING_CREATED")
        return _to_booking_response(entity), None
    except IntegrityError:
        db.rollback()
        if payload.submission_key:
            existing = (
                db.query(SiteVisitRequest)
                .filter(
                    SiteVisitRequest.buyer_id == buyer.id,
                    SiteVisitRequest.submission_key == payload.submission_key,
                )
                .first()
            )
            if existing:
                same_request = (
                    existing.listing_id == payload.listing_id
                    and existing.preferred_visit_date == payload.preferred_visit_date
                    and existing.preferred_visit_time == payload.preferred_visit_time
                    and existing.visitor_count == payload.visitor_count
                    and existing.pickup_address == payload.pickup_address
                    and existing.message == payload.message
                )
                if same_request:
                    return _to_booking_response(existing), None
                return None, "Submission key was already used for a different Site Visit request"
        active_duplicate = (
            db.query(SiteVisitRequest.id)
            .filter(
                SiteVisitRequest.buyer_id == buyer.id,
                SiteVisitRequest.listing_id == payload.listing_id,
                SiteVisitRequest.status.in_(ACTIVE_DUPLICATE_STATUSES),
            )
            .first()
        )
        if active_duplicate:
            return None, "An active Site Visit request already exists for this listing"
        raise
    except Exception:
        db.rollback()
        raise


def list_my_site_visits(db: Session, *, buyer_id: int) -> list[SiteVisitBookingResponse]:
    items = (
        db.query(SiteVisitRequest)
        .options(
            selectinload(SiteVisitRequest.workflow_history),
            selectinload(SiteVisitRequest.refund_record),
        )
        .filter(SiteVisitRequest.buyer_id == buyer_id, SiteVisitRequest.seller_id != buyer_id)
        .order_by(SiteVisitRequest.created_at.desc(), SiteVisitRequest.id.desc())
        .all()
    )
    return [_to_booking_response(item, include_active_completion_code=True) for item in items]


def _assigned_active_field_officer(db: Session, request: SiteVisitRequest, actor_id: int) -> bool:
    officer = db.query(User).filter(
        User.id == actor_id,
        User.role == UserRole.FIELD_OFFICER.value,
        User.is_active.is_(True),
    ).first()
    return officer is not None and request.assigned_field_officer_id == actor_id


def start_site_visit(db: Session, *, request_id: int, officer_id: int) -> tuple[dict | None, str | None]:
    request = db.query(SiteVisitRequest).filter(SiteVisitRequest.id == request_id).with_for_update().populate_existing().first()
    if request is None:
        db.rollback()
        return None, "Site Visit request not found"
    if not _assigned_active_field_officer(db, request, officer_id):
        db.rollback()
        return None, "Only the assigned active Field Officer can perform this action"
    if request.payment_status != PaymentStatus.SUCCESS.value or request.status != SiteVisitStatus.ASSIGNED.value:
        db.rollback()
        return None, "Site Visit request cannot be started in its current state"
    request.status = SiteVisitStatus.IN_PROGRESS.value
    request.started_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(request)
    except Exception:
        db.rollback()
        raise
    buyer = db.get(User, request.buyer_id)
    if buyer:
        try:
            notify_users(db, [buyer], "Site Visit started", f"The Field Officer started Site Visit booking #{request.id}.",
                "SITE_VISIT_STARTED", reference_id=str(request.id), extra_data={"site_visit_request_id": str(request.id)})
        except Exception:
            db.rollback()
            logger.exception("Site Visit started notification failed request_id=%s", request.id)
    _notify_site_visit_admins(db, request, title="Site Visit started", body=f"The Field Officer started Site Visit booking #{request.id}.", event="STARTED")
    return {"booking_id": request.id, "booking_status": request.status, "started_at": request.started_at}, None


def initiate_site_visit_completion(db: Session, *, request_id: int, officer_id: int) -> tuple[dict | None, str | None]:
    request = db.query(SiteVisitRequest).filter(SiteVisitRequest.id == request_id).with_for_update().populate_existing().first()
    if request is None:
        db.rollback()
        return None, "Site Visit request not found"
    if not _assigned_active_field_officer(db, request, officer_id):
        db.rollback()
        return None, "Only the assigned active Field Officer can perform this action"
    if request.payment_status != PaymentStatus.SUCCESS.value:
        db.rollback()
        return None, "Site Visit payment must be successful before completion can be initiated"
    if request.status != SiteVisitStatus.IN_PROGRESS.value:
        db.rollback()
        return None, "Site Visit must be In Progress before completion can be initiated"
    if request.started_at is None:
        db.rollback()
        return None, "Site Visit request cannot initiate completion before it has started"
    now = datetime.utcnow()
    if request.completion_code_used_at is not None:
        db.rollback()
        return None, "Site Visit completion code has already been used"
    if request.completion_code_failed_attempts >= COMPLETION_CODE_MAX_ATTEMPTS:
        db.rollback()
        return None, "Site Visit completion code attempts are locked"
    if request.completion_code_hash and request.completion_code_encrypted and request.completion_code_expires_at and request.completion_code_expires_at > now:
        expires_at = request.completion_code_expires_at
        db.rollback()
        return {"booking_id": request.id, "booking_status": request.status, "completion_code_expires_at": expires_at}, None
    try:
        code = generate_completion_code()
        expiry = now + COMPLETION_CODE_TTL
        request.completion_code_hash = hash_completion_code(request.id, code)
        request.completion_code_encrypted = encrypt_completion_code(request.id, code)
        request.completion_code_expires_at = expiry
        db.commit()
    except CompletionCodeConfigurationError:
        db.rollback()
        logger.error("Site Visit completion-code configuration unavailable")
        return None, "Site Visit completion-code service is unavailable"
    except Exception:
        db.rollback()
        logger.error("Site Visit completion-code initiation failed request_id=%s", request_id)
        return None, "Site Visit completion could not be initiated"
    _notify_completion_parties(db, request, completed=False)
    return {"booking_id": request.id, "booking_status": request.status, "completion_code_expires_at": expiry}, None


def verify_site_visit_completion(db: Session, *, request_id: int, officer_id: int, code: str) -> tuple[dict | None, str | None]:
    request = db.query(SiteVisitRequest).filter(SiteVisitRequest.id == request_id).with_for_update().populate_existing().first()
    if request is None:
        db.rollback()
        return None, "Site Visit request not found"
    if not _assigned_active_field_officer(db, request, officer_id):
        db.rollback()
        return None, "Only the assigned active Field Officer can perform this action"
    if request.payment_status != PaymentStatus.SUCCESS.value:
        db.rollback()
        return None, "Site Visit payment must be successful before completion can be verified"
    if request.status != SiteVisitStatus.IN_PROGRESS.value:
        db.rollback()
        return None, "Site Visit must be In Progress before completion can be verified"
    if request.started_at is None:
        db.rollback()
        return None, "Site Visit request cannot be completed before it has started"
    now = datetime.utcnow()
    if request.completion_code_used_at is not None:
        db.rollback()
        return None, "Site Visit completion code has already been used"
    if request.completion_code_failed_attempts >= COMPLETION_CODE_MAX_ATTEMPTS:
        db.rollback()
        return None, "Site Visit completion code attempts are locked"
    if not request.completion_code_hash or not request.completion_code_encrypted:
        db.rollback()
        return None, "No active Site Visit completion code"
    if request.completion_code_expires_at is None or request.completion_code_expires_at <= now:
        request.completion_code_hash = None
        request.completion_code_encrypted = None
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.error("Site Visit expired completion-code update failed request_id=%s", request_id)
            return None, "Site Visit completion could not be verified"
        return None, "Site Visit completion code has expired; Field Officer may initiate a new code"
    try:
        valid = verify_completion_code_hash(request.id, code, request.completion_code_hash)
    except CompletionCodeConfigurationError:
        db.rollback()
        logger.error("Site Visit completion-code configuration unavailable")
        return None, "Site Visit completion-code service is unavailable"
    if not valid:
        request.completion_code_failed_attempts += 1
        if request.completion_code_failed_attempts >= COMPLETION_CODE_MAX_ATTEMPTS:
            request.completion_code_hash = None
            request.completion_code_encrypted = None
            request.completion_code_expires_at = None
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.error("Site Visit failed-attempt update failed request_id=%s", request_id)
            return None, "Site Visit completion could not be verified"
        if request.completion_code_failed_attempts >= COMPLETION_CODE_MAX_ATTEMPTS:
            return None, "Site Visit completion code attempts are locked"
        return None, "Site Visit completion code is invalid"
    request.completion_code_used_at = now
    request.completion_code_hash = None
    request.completion_code_encrypted = None
    request.status = SiteVisitStatus.COMPLETED.value
    request.completed_at = now
    db.add(SiteVisitWorkflowHistory(
        site_visit_request_id=request.id,
        event_type="field_officer_completed",
        actor_id=officer_id,
        actor_role=UserRole.FIELD_OFFICER.value,
        reason="Buyer completion code verified",
        previous_values={"status": SiteVisitStatus.IN_PROGRESS.value, "started_at": request.started_at.isoformat()},
        updated_values={"status": SiteVisitStatus.COMPLETED.value, "completed_at": now.isoformat()},
        created_at=now,
    ))
    try:
        db.commit()
        db.refresh(request)
    except Exception:
        db.rollback()
        logger.error("Site Visit completion commit failed request_id=%s", request_id)
        return None, "Site Visit completion could not be saved"
    _notify_completion_parties(db, request, completed=True)
    return {"booking_id": request.id, "booking_status": request.status, "started_at": request.started_at}, None


def _notify_completion_parties(db: Session, request: SiteVisitRequest, *, completed: bool) -> None:
    buyer = db.get(User, request.buyer_id)
    admins = _site_visit_admin_recipients(db, request)
    recipients = ([buyer] if buyer is not None else []) + admins
    if not recipients:
        return
    event = "completed" if completed else "code_ready"
    title = "Site Visit Completed" if completed else "Site Visit completion verification required"
    body = (f"Site Visit request #{request.id} has been completed." if completed else
            f"A completion code is ready for Site Visit request #{request.id}.")
    try:
        notify_users(
            db=db,
            users=recipients,
            title=title,
            body=body,
            notif_type="SITE_VISIT_" + ("COMPLETED" if completed else "COMPLETION_CODE_READY"),
            reference_id=str(request.id),
            extra_data={"site_visit_request_id": str(request.id), "event": event},
        )
    except Exception:
        db.rollback()
        logger.error("Site Visit completion notification failed request_id=%s", request.id)


def cancel_my_site_visit(
    db: Session,
    *,
    buyer_id: int,
    booking_id: int,
    payload: SiteVisitCancelRequest,
) -> tuple[SiteVisitCancelResponse | None, str | None]:
    entity = (
        db.query(SiteVisitRequest)
        .filter(
            SiteVisitRequest.id == booking_id,
            SiteVisitRequest.buyer_id == buyer_id,
        )
        .with_for_update()
        .first()
    )
    if entity is None:
        db.rollback()
        return None, "Site Visit request not found"
    if entity.status not in BUYER_CANCELLABLE_STATUSES:
        db.rollback()
        return None, "This Site Visit request can no longer be cancelled by the buyer"

    previous_status = entity.status
    entity.status = SiteVisitStatus.CANCELLED.value
    _invalidate_site_visit_completion_code(entity)
    entity.cancellation_reason = payload.reason
    entity.cancelled_at = datetime.utcnow()
    entity.cancelled_by_id = buyer_id
    entity.cancellation_actor_role = UserRole.CUSTOMER.value
    db.add(SiteVisitWorkflowHistory(
        site_visit_request_id=entity.id,
        event_type="buyer_cancelled",
        actor_id=buyer_id,
        actor_role=UserRole.CUSTOMER.value,
        reason=payload.reason,
        previous_values={"status": previous_status},
        updated_values={"status": SiteVisitStatus.CANCELLED.value},
    ))
    open_site_visit_refund(db, booking=entity, actor_id=buyer_id, actor_role=UserRole.CUSTOMER.value)
    try:
        db.commit()
        db.refresh(entity)
    except Exception:
        db.rollback()
        raise

    _notify_site_visit_admins(db, entity, title="Buyer cancelled Site Visit", body=f"Buyer cancelled Site Visit booking #{entity.id}. Review its refund case.", event="BUYER_CANCELLED")

    return (
        SiteVisitCancelResponse(
            status="Site Visit request cancelled",
            booking_id=entity.id,
            booking_status=entity.status,
            cancellation_reason=entity.cancellation_reason,
            cancelled_at=entity.cancelled_at,
            cancelled_by_role=entity.cancellation_actor_role,
        ),
        None,
    )


def _notify_site_visit_buyer(db: Session, entity: SiteVisitRequest, *, title: str, body: str, event: str) -> None:
    buyer = db.get(User, entity.buyer_id)
    if buyer is None:
        return
    try:
        notify_users(
            db=db,
            users=[buyer],
            title=title,
            body=body,
            notif_type=f"SITE_VISIT_{event.upper()}",
            reference_id=str(entity.id),
            extra_data={"site_visit_request_id": str(entity.id), "event": event},
        )
    except Exception:
        db.rollback()
        logger.exception("Site Visit workflow notification failed request_id=%s event=%s", entity.id, event)


def _notify_site_visit_admins(db: Session, entity: SiteVisitRequest, *, title: str, body: str, event: str) -> None:
    recipients = _site_visit_admin_recipients(db, entity)
    if not recipients:
        return
    try:
        notify_users(
            db=db,
            users=recipients,
            title=title,
            body=body,
            notif_type=f"SITE_VISIT_{event.upper()}",
            reference_id=str(entity.id),
            extra_data={"site_visit_request_id": str(entity.id), "event": event},
        )
    except Exception:
        db.rollback()
        logger.exception("Site Visit workflow notification failed request_id=%s event=%s", entity.id, event)


def _site_visit_admin_recipients(db: Session, entity: SiteVisitRequest) -> list[User]:
    listing = db.get(SellLandRequest, entity.listing_id)
    responsible_admin = None
    if listing is not None and listing.reviewed_by_id is not None:
        responsible_admin = db.query(User).filter(
            User.id == listing.reviewed_by_id,
            User.role == UserRole.ADMIN.value,
            User.is_active.is_(True),
        ).first()
    super_admins = db.query(User).filter(
        User.role == UserRole.SUPER_ADMIN.value,
        User.is_active.is_(True),
    ).all()
    recipients = ([responsible_admin] if responsible_admin is not None else []) + super_admins
    return list({user.id: user for user in recipients}.values())


def notify_site_visit_payment_event(db: Session, *, booking_id: int, event: str) -> None:
    entity = db.get(SiteVisitRequest, booking_id)
    if entity is None:
        return
    if event == "PAYMENT_SUCCESS":
        _notify_site_visit_buyer(db, entity, title="Site Visit payment successful", body=f"Payment for Site Visit booking #{entity.id} was received.", event=event)
        _notify_site_visit_admins(db, entity, title="Site Visit payment received", body=f"Site Visit booking #{entity.id} is ready for review.", event=event)
    elif event == "PAYMENT_FAILED":
        _notify_site_visit_buyer(db, entity, title="Site Visit payment failed", body=f"Payment for Site Visit booking #{entity.id} did not complete. You can retry from the booking.", event=event)


def request_site_visit_correction(
    db: Session, *, request_id: int, actor: User, payload: SiteVisitAdminActionRequest
) -> tuple[dict | None, str | None]:
    entity = db.query(SiteVisitRequest).filter(
        SiteVisitRequest.id == request_id,
        SiteVisitRequest.payment_status == PaymentStatus.SUCCESS.value,
    ).with_for_update().first()
    if entity is None:
        db.rollback()
        return None, "Paid Site Visit request not found"
    if not _admin_owns_site_visit_listing(db, entity, actor):
        db.rollback()
        return None, "Paid Site Visit request not found"
    if entity.status != SiteVisitStatus.PENDING.value:
        db.rollback()
        return None, "Correction can only be requested while a paid Site Visit is pending admin review"

    now = datetime.utcnow()
    prior = {
        "preferred_visit_date": entity.preferred_visit_date.isoformat(),
        "preferred_visit_time": entity.preferred_visit_time.isoformat(),
        "visitor_count": entity.visitor_count,
        "pickup_address": entity.pickup_address,
        "message": entity.message,
        "status": entity.status,
    }
    entity.status = SiteVisitStatus.CORRECTION_REQUIRED.value
    entity.correction_reason = payload.reason
    entity.correction_requested_at = now
    entity.correction_requested_by_id = actor.id
    db.add(SiteVisitWorkflowHistory(
        site_visit_request_id=entity.id,
        event_type="correction_requested",
        actor_id=actor.id,
        actor_role=actor.role,
        reason=payload.reason,
        previous_values=prior,
        updated_values={"status": SiteVisitStatus.CORRECTION_REQUIRED.value},
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    _notify_site_visit_buyer(db, entity, title="Site Visit correction required", body="Please review the correction request and resubmit your Site Visit details.", event="CORRECTION_REQUESTED")
    return {"booking_id": entity.id, "booking_status": entity.status, "reason": payload.reason, "actor_id": actor.id, "actor_role": actor.role, "occurred_at": now}, None


def resubmit_site_visit_correction(
    db: Session, *, request_id: int, actor: User, payload: SiteVisitCorrectionResponseRequest
) -> tuple[SiteVisitBookingResponse | None, str | None]:
    entity = db.query(SiteVisitRequest).filter(
        SiteVisitRequest.id == request_id,
        SiteVisitRequest.buyer_id == actor.id,
    ).with_for_update().first()
    if entity is None:
        db.rollback()
        return None, "Site Visit request not found"
    if entity.status != SiteVisitStatus.CORRECTION_REQUIRED.value or not entity.correction_reason:
        db.rollback()
        return None, "This Site Visit request is not awaiting a buyer correction"
    now = datetime.utcnow()
    previous = {
        "preferred_visit_date": entity.preferred_visit_date.isoformat(),
        "preferred_visit_time": entity.preferred_visit_time.isoformat(),
        "visitor_count": entity.visitor_count,
        "pickup_address": entity.pickup_address,
        "message": entity.message,
        "status": entity.status,
    }
    entity.preferred_visit_date = payload.preferred_visit_date
    entity.preferred_visit_time = payload.preferred_visit_time
    entity.visitor_count = payload.visitor_count
    entity.pickup_address = payload.pickup_address
    entity.message = payload.message
    entity.status = SiteVisitStatus.PENDING.value
    updated = {
        "preferred_visit_date": payload.preferred_visit_date.isoformat(),
        "preferred_visit_time": payload.preferred_visit_time.isoformat(),
        "visitor_count": payload.visitor_count,
        "pickup_address": payload.pickup_address,
        "message": payload.message,
        "status": SiteVisitStatus.PENDING.value,
    }
    history = SiteVisitWorkflowHistory(
        site_visit_request_id=entity.id,
        event_type="buyer_resubmitted",
        actor_id=actor.id,
        actor_role=actor.role,
        reason=entity.correction_reason,
        previous_values=previous,
        updated_values=updated,
        created_at=now,
    )
    db.add(history)
    try:
        db.commit()
        db.refresh(entity)
    except Exception:
        db.rollback()
        raise
    _notify_site_visit_admins(db, entity, title="Site Visit details resubmitted", body="A buyer resubmitted corrected Site Visit details for review.", event="CORRECTION_SUBMITTED")
    return _to_booking_response(entity), None


def cancel_site_visit_by_admin(
    db: Session, *, request_id: int, actor: User, payload: SiteVisitAdminActionRequest
) -> tuple[dict | None, str | None]:
    entity = db.query(SiteVisitRequest).filter(
        SiteVisitRequest.id == request_id,
        SiteVisitRequest.payment_status == PaymentStatus.SUCCESS.value,
    ).with_for_update().first()
    if entity is None:
        db.rollback()
        return None, "Paid Site Visit request not found"
    if not _admin_owns_site_visit_listing(db, entity, actor):
        db.rollback()
        return None, "Paid Site Visit request not found"
    eligible = {
        SiteVisitStatus.PENDING.value,
        SiteVisitStatus.CORRECTION_REQUIRED.value,
        SiteVisitStatus.ASSIGNED.value,
        SiteVisitStatus.SCHEDULED.value,
        SiteVisitStatus.IN_PROGRESS.value,
    }
    if entity.status not in eligible:
        db.rollback()
        return None, "This Site Visit request cannot be cancelled by admin in its current state"
    now = datetime.utcnow()
    previous_status = entity.status
    assigned_officer = db.get(User, entity.assigned_field_officer_id) if entity.assigned_field_officer_id else None
    entity.status = SiteVisitStatus.CANCELLED.value
    _invalidate_site_visit_completion_code(entity)
    entity.cancellation_reason = payload.reason
    entity.cancelled_at = now
    entity.cancelled_by_id = actor.id
    entity.cancellation_actor_role = actor.role
    event_type = "in_progress_cancelled" if previous_status == SiteVisitStatus.IN_PROGRESS.value else "admin_cancelled"
    db.add(SiteVisitWorkflowHistory(
        site_visit_request_id=entity.id,
        event_type=event_type,
        actor_id=actor.id,
        actor_role=actor.role,
        reason=payload.reason,
        previous_values={"status": previous_status, "field_officer_id": entity.assigned_field_officer_id},
        updated_values={"status": SiteVisitStatus.CANCELLED.value, "field_officer_id": entity.assigned_field_officer_id, "cancellation_reason": payload.reason},
        created_at=now,
    ))
    open_site_visit_refund(db, booking=entity, actor_id=actor.id, actor_role=actor.role)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    _notify_site_visit_buyer(db, entity, title="Site Visit cancelled", body="An admin cancelled your Site Visit. Open your booking to view the reason.", event="ADMIN_CANCELLED")
    if previous_status == SiteVisitStatus.IN_PROGRESS.value:
        if assigned_officer is not None:
            _send_assignment_notification(
                db, assigned_officer, request_id=entity.id,
                notif_type="SITE_VISIT_ASSIGNMENT_REMOVED",
                title="Site Visit Cancelled",
                action=AssignmentAction.UNASSIGNED.value,
            )
        _notify_site_visit_admins(
            db, entity, title="In-progress Site Visit cancelled",
            body=f"An Admin cancelled in-progress Site Visit booking #{entity.id}.",
            event="IN_PROGRESS_CANCELLED",
        )
    return {"booking_id": entity.id, "booking_status": entity.status, "reason": payload.reason, "actor_id": actor.id, "actor_role": actor.role, "occurred_at": now}, None
