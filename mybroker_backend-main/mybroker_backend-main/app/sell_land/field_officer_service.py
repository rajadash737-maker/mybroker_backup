import json
from datetime import datetime
from pathlib import Path
import logging

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.notifications.service import notify_users
from app.sell_land.constants import BookingStatus, SellLandStatus
from app.sell_land.field_officer_schemas import FieldOfficerDecision
from app.sell_land.field_officer_schemas import (
    FieldOfficerAvailableCaseItem,
    FieldOfficerAvailableCaseListResponse,
    FieldOfficerCaseActionResponse,
    FieldOfficerCaseDetailResponse,
    FieldOfficerBoundaryPoint,
    FieldOfficerDashboardResponse,
    FieldOfficerDashboardViewer,
    FieldOfficerListingMedia,
    FieldOfficerReviewActionRequest,
    FieldOfficerReviewActionResponse,
    FieldOfficerSellerSummary,
    FieldOfficerVisitPhotoUploadResponse,
    FieldOfficerRegistryCompleteResponse,
    FieldOfficerRegistryProofItem,
    FieldOfficerRegistryProofUploadResponse,
    FieldOfficerRegistryAssignmentItem,
    FieldOfficerRegistryAssignmentListResponse,
    FieldOfficerRegistryAssignmentDetail,
    FieldOfficerRegistryAssignmentDetailResponse,
)
from app.sell_land.media_storage import ALLOWED_DOC_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS, save_listing_media_file, save_registry_proof_file
from app.sell_land.models import SellLandBooking, SellLandRequest, SellLandRegistryProof
from app.sell_land.repository import (
    apply_field_officer_review_decision,
    claim_case_for_field_officer,
    count_available_cases_for_field_officer_user,
    count_completed_visits_for_field_officer_user,
    get_active_case_for_field_officer,
    get_sell_land_request_by_id,
    get_user_by_id,
    list_available_cases_for_field_officer,
    list_media_for_requests,
    list_users_by_ids,
    release_case_for_field_officer,
    list_registry_proofs_for_booking,
)
from app.users.model import User
from app.users.roles import UserRole

MEDIA_ROOT = Path(__file__).resolve().parents[1] / "uploads" / "sell-land"
REGISTRY_PROOF_ROOT = settings.private_uploads_dir
logger = logging.getLogger(__name__)


def _to_case_item(entity: SellLandRequest) -> FieldOfficerAvailableCaseItem:
    return FieldOfficerAvailableCaseItem(
        id=entity.id,
        listing_code=entity.listing_code,
        title=entity.title,
        owner_name=entity.owner_name,
        owner_mobile=entity.owner_mobile,
        land_type=entity.land_type,
        location=entity.location,
        city=entity.city,
        state=entity.state,
        pincode=entity.pincode,
        expected_price=entity.expected_price,
        reviewed_at=entity.reviewed_at,
        created_at=entity.created_at,
    )


def _to_seller_summary(user: User) -> FieldOfficerSellerSummary:
    return FieldOfficerSellerSummary(
        id=user.id,
        fullname=user.fullname,
        mobile=user.mobile,
        email=user.email,
        profile_image_url=user.profile_image_url,
    )


def _parse_boundary_points(raw: str | None) -> list[FieldOfficerBoundaryPoint]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    points: list[FieldOfficerBoundaryPoint] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        lat = item.get("lat")
        lng = item.get("lng")
        if lat is None or lng is None:
            continue
        points.append(FieldOfficerBoundaryPoint(lat=float(lat), lng=float(lng)))
    return points


def _delete_visit_photo_file(request_id: int, file_name: str | None) -> None:
    if not file_name:
        return
    for file_path in (
        settings.private_uploads_dir / "listing" / f"request_{request_id}" / file_name,
        MEDIA_ROOT / f"request_{request_id}" / file_name,
    ):
        if file_path.exists():
            file_path.unlink()


def _get_claimed_case_for_field_officer(
    db: Session,
    current_user: User,
    request_id: int,
) -> tuple[SellLandRequest | None, str | None]:
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status != SellLandStatus.APPROVED.value:
        return None, "Only approved listings can be reviewed by field officer"
    if entity.assigned_field_officer_id != current_user.id:
        return None, "You can only review your own locked case"
    if entity.lock_expires_at and entity.lock_expires_at <= datetime.utcnow():
        return None, "Case lock has expired"
    return entity, None


def _to_registry_proof_item(entity: SellLandRegistryProof) -> FieldOfficerRegistryProofItem:
    return FieldOfficerRegistryProofItem(
        id=entity.id,
        file_url=entity.file_url,
        file_name=entity.file_name,
        created_at=entity.created_at,
    )


def _format_property_area(entity: SellLandRequest) -> str | None:
    if entity.area is None:
        return None
    unit = (entity.area_unit or "").strip()
    unit_text = f" {unit}" if unit else ""
    return f"{entity.area}{unit_text}"


def _format_property_address(entity: SellLandRequest) -> str | None:
    parts = [
        (entity.location or "").strip(),
        (entity.city or "").strip(),
        (entity.state or "").strip(),
        (entity.pincode or "").strip(),
    ]
    cleaned = [part for part in parts if part]
    return ", ".join(cleaned) if cleaned else None


def list_registry_assignments(
    db: Session,
    current_user: User,
    skip: int,
    limit: int,
) -> FieldOfficerRegistryAssignmentListResponse:
    query = (
        db.query(SellLandBooking, SellLandRequest)
        .join(SellLandRequest, SellLandRequest.id == SellLandBooking.request_id)
        .filter(SellLandBooking.assigned_field_officer_id == current_user.id)
        .filter(
            SellLandBooking.booking_status.in_(
                {
                    BookingStatus.REGISTRY_SCHEDULED.value,
                    BookingStatus.IN_PROCESS.value,
                    BookingStatus.REGISTRY_DONE.value,
                }
            )
        )
    )
    total = query.count()
    rows = (
        query.order_by(
            SellLandBooking.registry_date.asc(),
            SellLandBooking.registry_time.asc(),
            SellLandBooking.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    items: list[FieldOfficerRegistryAssignmentItem] = []
    for booking, listing in rows:
        items.append(
            FieldOfficerRegistryAssignmentItem(
                booking_id=booking.id,
                listing_id=booking.request_id,
                deal_amount=booking.deal_amount,
                property_name=listing.title,
                property_type=listing.land_type,
                property_area=_format_property_area(listing),
                property_address=_format_property_address(listing),
                buyer_name=booking.buyer_name,
                buyer_mobile=booking.buyer_mobile,
                seller_name=listing.owner_name,
                seller_mobile=listing.owner_mobile,
                registry_date=booking.registry_date,
                registry_time=booking.registry_time,
                registry_location=booking.registry_location,
                status=BookingStatus(booking.booking_status),
                assigned_officer_name=current_user.fullname,
                assigned_officer_mobile=current_user.mobile,
            )
        )

    return FieldOfficerRegistryAssignmentListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items,
    )


def get_registry_assignment_detail(
    db: Session,
    current_user: User,
    booking_id: int,
) -> tuple[FieldOfficerRegistryAssignmentDetailResponse | None, str | None]:
    row = (
        db.query(SellLandBooking, SellLandRequest)
        .join(SellLandRequest, SellLandRequest.id == SellLandBooking.request_id)
        .filter(SellLandBooking.id == booking_id)
        .first()
    )
    if not row:
        return None, "Booking not found"
    booking, listing = row
    officer_id = booking.assigned_field_officer_id or listing.field_officer_reviewed_by_id
    if officer_id != current_user.id:
        return None, "You can only view registry assigned to you"

    proofs = list_registry_proofs_for_booking(db, booking.id)
    detail = FieldOfficerRegistryAssignmentDetail(
        booking_id=booking.id,
        listing_id=booking.request_id,
        deal_amount=booking.deal_amount,
        property_name=listing.title,
        property_type=listing.land_type,
        property_area=_format_property_area(listing),
        property_address=_format_property_address(listing),
        buyer_name=booking.buyer_name,
        buyer_mobile=booking.buyer_mobile,
        seller_name=listing.owner_name,
        seller_mobile=listing.owner_mobile,
        registry_date=booking.registry_date,
        registry_time=booking.registry_time,
        registry_location=booking.registry_location,
        status=BookingStatus(booking.booking_status),
        assigned_officer_name=current_user.fullname,
        assigned_officer_mobile=current_user.mobile,
        proofs=[_to_registry_proof_item(item) for item in proofs],
    )
    return (
        FieldOfficerRegistryAssignmentDetailResponse(
            status="Registry assignment fetched",
            assignment=detail,
        ),
        None,
    )


def start_registry_visit(
    db: Session,
    current_user: User,
    booking_id: int,
) -> tuple[FieldOfficerRegistryAssignmentDetailResponse | None, str | None]:
    booking = db.query(SellLandBooking).filter(SellLandBooking.id == booking_id).first()
    if not booking:
        return None, "Booking not found"
    listing = get_sell_land_request_by_id(db, booking.request_id)
    if not listing:
        return None, "Sell land request not found"
    officer_id = booking.assigned_field_officer_id or listing.field_officer_reviewed_by_id
    if officer_id != current_user.id:
        return None, "You can only start registry for your assigned booking"
    if booking.booking_status != BookingStatus.REGISTRY_SCHEDULED.value:
        return None, "Registry is not scheduled"

    booking.booking_status = BookingStatus.IN_PROCESS.value
    db.commit()
    db.refresh(booking)

    try:
        seller = get_user_by_id(db, listing.user_id)
        buyer = get_user_by_id(db, booking.buyer_id)
        admin_user = get_user_by_id(db, listing.reviewed_by_id) if listing.reviewed_by_id else None
        listing_title = (listing.title or "Land").strip()
        registry_date_text = booking.registry_date.isoformat() if booking.registry_date else "TBD"
        registry_time_text = booking.registry_time.isoformat() if booking.registry_time else "TBD"
        registry_location_text = (booking.registry_location or "").strip() or "TBD"

        if buyer:
            notify_users(
                db=db,
                users=[buyer],
                title="Registry In Progress",
                body=(
                    f"Registry visit for {listing_title} has started on "
                    f"{registry_date_text} at {registry_time_text} in {registry_location_text}"
                ),
                notif_type="REGISTRY_IN_PROCESS",
                role_target=buyer.role,
                reference_id=str(listing.id),
            )
        if seller:
            notify_users(
                db=db,
                users=[seller],
                title="Registry In Progress",
                body=(
                    f"Registry visit for {listing_title} has started on "
                    f"{registry_date_text} at {registry_time_text} in {registry_location_text}"
                ),
                notif_type="REGISTRY_IN_PROCESS",
                role_target=seller.role,
                reference_id=str(listing.id),
            )
        if admin_user and admin_user.role in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}:
            notify_users(
                db=db,
                users=[admin_user],
                title="Registry Visit Started",
                body=f"Field officer started registry visit for {listing_title}",
                notif_type="REGISTRY_IN_PROCESS",
                role_target=admin_user.role,
                reference_id=str(listing.id),
            )
    except Exception:
        logger.exception("Failed to send registry in-progress notifications")

    return get_registry_assignment_detail(db, current_user, booking_id)


def upload_registry_proofs(
    db: Session,
    current_user: User,
    booking_id: int,
    files: list[UploadFile],
    notes: str | None = None,
) -> tuple[FieldOfficerRegistryProofUploadResponse | None, str | None]:
    booking = db.query(SellLandBooking).filter(SellLandBooking.id == booking_id).first()
    if not booking:
        return None, "Booking not found"
    listing = get_sell_land_request_by_id(db, booking.request_id)
    if not listing:
        return None, "Sell land request not found"
    officer_id = booking.assigned_field_officer_id or listing.field_officer_reviewed_by_id
    if officer_id != current_user.id:
        return None, "You can only upload proof for your assigned booking"
    if booking.booking_status not in {
        BookingStatus.REGISTRY_SCHEDULED.value,
        BookingStatus.IN_PROCESS.value,
    }:
        return None, "Registry is not in progress"
    if not files:
        return None, "No files uploaded"

    proofs: list[SellLandRegistryProof] = []
    last_file_name = None
    last_file_url = None
    for file in files:
        try:
            file_name, file_url = save_registry_proof_file(
                file=file,
                booking_id=booking.id,
                media_root=REGISTRY_PROOF_ROOT,
                allowed_extensions=ALLOWED_DOC_EXTENSIONS,
            )
        except ValueError as exc:
            return None, str(exc)
        proofs.append(
            SellLandRegistryProof(
                booking_id=booking.id,
                file_url=file_url,
                file_name=file_name,
            )
        )
        last_file_name = file_name
        last_file_url = file_url

    if last_file_url and last_file_name:
        booking.registry_proof_name = last_file_name
        booking.registry_proof_url = last_file_url
    if notes:
        booking.registry_notes = notes.strip()

    db.add_all(proofs)
    db.commit()
    db.refresh(booking)

    stored = list_registry_proofs_for_booking(db, booking.id)
    return (
        FieldOfficerRegistryProofUploadResponse(
            status="Registry proofs uploaded",
            booking_id=booking.id,
            proofs=[_to_registry_proof_item(item) for item in stored],
        ),
        None,
    )


def get_field_officer_dashboard(db: Session, current_user: User) -> FieldOfficerDashboardResponse:
    active_case = get_active_case_for_field_officer(db, current_user.id)
    available_cases = count_available_cases_for_field_officer_user(db, current_user.id)
    completed_visits = count_completed_visits_for_field_officer_user(db, current_user.id)
    total_cases = available_cases + completed_visits
    lock_remaining_seconds = None
    active_case_id = None
    active_case_item = None
    if active_case and active_case.lock_expires_at:
        lock_remaining_seconds = max(0, int((active_case.lock_expires_at - datetime.utcnow()).total_seconds()))
        active_case_id = active_case.id
        active_case_item = _to_case_item(active_case)
    return FieldOfficerDashboardResponse(
        status="Dashboard fetched successfully",
        viewer=FieldOfficerDashboardViewer(
            id=current_user.id,
            fullname=current_user.fullname,
            role=current_user.role,
            profile_image_url=current_user.profile_image_url,
        ),
        active_case_id=active_case_id,
        active_case=active_case_item,
        lock_remaining_seconds=lock_remaining_seconds,
        total_cases=total_cases,
        available_cases=available_cases,
        completed_visits=completed_visits,
    )


def list_available_cases(
    db: Session,
    current_user: User,
    skip: int,
    limit: int,
) -> FieldOfficerAvailableCaseListResponse:
    items, total = list_available_cases_for_field_officer(
        db=db,
        field_officer_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return FieldOfficerAvailableCaseListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[_to_case_item(item) for item in items],
    )


def claim_case(
    db: Session,
    current_user: User,
    request_id: int,
) -> tuple[FieldOfficerCaseActionResponse | None, str | None]:
    entity, error = claim_case_for_field_officer(
        db=db,
        request_id=request_id,
        field_officer_id=current_user.id,
        lock_hours=12,
    )
    if error:
        return None, error
    return (
        FieldOfficerCaseActionResponse(
            status="Case locked successfully for 12 hours",
            request_id=entity.id,
            lock_expires_at=entity.lock_expires_at,
        ),
        None,
    )


def release_case(
    db: Session,
    current_user: User,
    request_id: int,
) -> tuple[FieldOfficerCaseActionResponse | None, str | None]:
    entity, error = release_case_for_field_officer(
        db=db,
        request_id=request_id,
        field_officer_id=current_user.id,
    )
    if error:
        return None, error
    return (
        FieldOfficerCaseActionResponse(
            status="Case released successfully",
            request_id=entity.id,
            lock_expires_at=None,
        ),
        None,
    )


def get_case_review_detail(
    db: Session,
    current_user: User,
    request_id: int,
) -> tuple[FieldOfficerCaseDetailResponse | None, str | None]:
    entity, error = _get_claimed_case_for_field_officer(db, current_user, request_id)
    if error:
        return None, error
    users = list_users_by_ids(db, [entity.user_id])
    if not users:
        return None, "Seller not found"
    media_items = list_media_for_requests(db, [entity.id])
    return (
        FieldOfficerCaseDetailResponse(
            id=entity.id,
            user_id=entity.user_id,
            listing_code=entity.listing_code,
            title=entity.title,
            owner_name=entity.owner_name,
            owner_mobile=entity.owner_mobile,
            owner_category=entity.owner_category,
            land_type=entity.land_type,
            ownership_type=entity.ownership_type,
            location=entity.location,
            city=entity.city,
            state=entity.state,
            pincode=entity.pincode,
            area=entity.area,
            area_unit=entity.area_unit,
            price_type=entity.price_type,
            expected_price=entity.expected_price,
            negotiable=entity.negotiable,
            availability=entity.availability,
            description=entity.description,
            boundary_points=_parse_boundary_points(entity.boundary_points),
            payment_status=entity.payment_status,
            status=entity.status,
            lock_expires_at=entity.lock_expires_at,
            field_officer_decision=entity.field_officer_decision,
            field_officer_reviewed_at=entity.field_officer_reviewed_at,
            field_officer_notes=entity.field_officer_notes,
            field_officer_rejection_reason=entity.field_officer_rejection_reason,
            field_officer_visit_photo_url=entity.field_officer_visit_photo_url,
            seller=_to_seller_summary(users[0]),
            media=[FieldOfficerListingMedia.model_validate(item) for item in media_items],
        ),
        None,
    )


def upload_visit_photo(
    db: Session,
    current_user: User,
    request_id: int,
    file: UploadFile,
) -> tuple[FieldOfficerVisitPhotoUploadResponse | None, str | None]:
    entity, error = _get_claimed_case_for_field_officer(db, current_user, request_id)
    if error:
        return None, error
    try:
        file_name, file_url = save_listing_media_file(
            file=file,
            request_id=request_id,
            media_root=settings.private_uploads_dir,
            allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
            private=True,
        )
    except ValueError as exc:
        return None, str(exc)

    _delete_visit_photo_file(request_id, entity.field_officer_visit_photo_name)
    entity.field_officer_visit_photo_name = file_name
    entity.field_officer_visit_photo_url = file_url
    db.commit()
    db.refresh(entity)

    return (
        FieldOfficerVisitPhotoUploadResponse(
            status="Visit photo uploaded successfully",
            request_id=entity.id,
            visit_photo_url=entity.field_officer_visit_photo_url,
        ),
        None,
    )


def review_case(
    db: Session,
    current_user: User,
    request_id: int,
    payload: FieldOfficerReviewActionRequest,
) -> tuple[FieldOfficerReviewActionResponse | None, str | None]:
    entity, error = _get_claimed_case_for_field_officer(db, current_user, request_id)
    if error:
        return None, error
    # Photo is mandatory for both approve and reject actions.
    if not entity.field_officer_visit_photo_url:
        return None, "Visit photo is required before review decision"
    if payload.decision == FieldOfficerDecision.REJECTED and not payload.rejection_reason:
        return None, "rejection_reason is required when decision is rejected"

    rejection_reason = payload.rejection_reason if payload.decision == FieldOfficerDecision.REJECTED else None
    updated = apply_field_officer_review_decision(
        db=db,
        entity=entity,
        reviewed_by_id=current_user.id,
        decision=payload.decision.value,
        notes=payload.inspection_notes,
        rejection_reason=rejection_reason,
    )

    try:
        seller = get_user_by_id(db, updated.user_id)
        admin_user = get_user_by_id(db, updated.reviewed_by_id) if updated.reviewed_by_id else None
        reviewer_can_receive = admin_user is not None and admin_user.role in {
            UserRole.ADMIN.value,
            UserRole.SUPER_ADMIN.value,
        }

        if payload.decision == FieldOfficerDecision.REJECTED:
            if seller:
                notify_users(
                    db=db,
                    users=[seller],
                    title="Land Needs Correction",
                    body="Your land was rejected after field visit review",
                    notif_type="FIELD_VISIT_REJECTED",
                    role_target=seller.role,
                    reference_id=str(updated.id),
                )
            if reviewer_can_receive:
                notify_users(
                    db=db,
                    users=[admin_user],
                    title="Field Visit Rejected",
                    body="A field officer rejected listing LST-%s" % updated.id,
                    notif_type="FIELD_VISIT_REJECTED",
                    role_target=admin_user.role,
                    reference_id=str(updated.id),
                )
        else:
            if seller:
                notify_users(
                    db=db,
                    users=[seller],
                    title="Field Visit Verified",
                    body="Your land passed field visit and moved to final admin approval",
                    notif_type="FIELD_VISIT_APPROVED",
                    role_target=seller.role,
                    reference_id=str(updated.id),
                )
            if reviewer_can_receive:
                notify_users(
                    db=db,
                    users=[admin_user],
                    title="Field Visit Approved",
                    body="A listing is ready for final approval: LST-%s" % updated.id,
                    notif_type="FIELD_VISIT_APPROVED",
                    role_target=admin_user.role,
                    reference_id=str(updated.id),
                )
    except Exception:
        logger.exception("Failed to send field officer review notifications")

    status_message = "Listing approved by field officer"
    if payload.decision == FieldOfficerDecision.REJECTED:
        status_message = "Listing rejected by field officer"
    return (
        FieldOfficerReviewActionResponse(
            status=status_message,
            request_id=updated.id,
            listing_status=updated.status,
            field_officer_decision=updated.field_officer_decision,
            field_officer_reviewed_at=updated.field_officer_reviewed_at,
            field_officer_rejection_reason=updated.field_officer_rejection_reason,
        ),
        None,
    )


def complete_registry(
    db: Session,
    current_user: User,
    booking_id: int,
    files: list[UploadFile] | None = None,
    notes: str | None = None,
) -> tuple[FieldOfficerRegistryCompleteResponse | None, str | None]:
    booking = db.query(SellLandBooking).filter(SellLandBooking.id == booking_id).first()
    if not booking:
        return None, "Booking not found"
    listing = get_sell_land_request_by_id(db, booking.request_id)
    if not listing:
        return None, "Sell land request not found"
    officer_id = booking.assigned_field_officer_id or listing.field_officer_reviewed_by_id
    if officer_id != current_user.id:
        return None, "You can only complete registry for your assigned booking"
    if booking.booking_status not in {
        BookingStatus.REGISTRY_SCHEDULED.value,
        BookingStatus.IN_PROCESS.value,
    }:
        return None, "Registry is not scheduled"

    uploaded: list[SellLandRegistryProof] = []
    if files:
        for file in files:
            try:
                file_name, file_url = save_registry_proof_file(
                    file=file,
                    booking_id=booking.id,
                    media_root=REGISTRY_PROOF_ROOT,
                    allowed_extensions=ALLOWED_DOC_EXTENSIONS,
                )
            except ValueError as exc:
                return None, str(exc)
            uploaded.append(
                SellLandRegistryProof(
                    booking_id=booking.id,
                    file_url=file_url,
                    file_name=file_name,
                )
            )
        last_file = uploaded[-1]
        booking.registry_proof_name = last_file.file_name
        booking.registry_proof_url = last_file.file_url

    if notes:
        booking.registry_notes = notes.strip()

    if uploaded:
        db.add_all(uploaded)

    proofs = list_registry_proofs_for_booking(db, booking.id)
    if not proofs and not uploaded:
        return None, "Registry proof is required before completion"

    booking.booking_status = BookingStatus.REGISTRY_DONE.value
    db.commit()
    db.refresh(booking)

    try:
        seller = get_user_by_id(db, listing.user_id)
        buyer = get_user_by_id(db, booking.buyer_id)
        admin_user = get_user_by_id(db, listing.reviewed_by_id) if listing.reviewed_by_id else None
        registry_date_text = booking.registry_date.isoformat() if booking.registry_date else "TBD"
        registry_time_text = booking.registry_time.isoformat() if booking.registry_time else "TBD"
        registry_location_text = (booking.registry_location or "").strip() or "TBD"
        listing_title = (listing.title or "Land").strip()

        if buyer:
            notify_users(
                db=db,
                users=[buyer],
                title="Registry Done",
                body=(
                    f"Registry for {listing_title} is completed on "
                    f"{registry_date_text} at {registry_time_text} in {registry_location_text}"
                ),
                notif_type="REGISTRY_DONE",
                role_target=buyer.role,
                reference_id=str(listing.id),
            )
        if seller:
            notify_users(
                db=db,
                users=[seller],
                title="Registry Done",
                body=(
                    f"Registry for {listing_title} is completed on "
                    f"{registry_date_text} at {registry_time_text} in {registry_location_text}"
                ),
                notif_type="REGISTRY_DONE",
                role_target=seller.role,
                reference_id=str(listing.id),
            )
        if admin_user and admin_user.role in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}:
            notify_users(
                db=db,
                users=[admin_user],
                title="Registry Completed",
                body=f"Registry proofs uploaded and booking is ready for approval: {listing_title}",
                notif_type="REGISTRY_DONE",
                role_target=admin_user.role,
                reference_id=str(listing.id),
            )
    except Exception:
        logger.exception("Failed to send registry completion notifications")

    return (
        FieldOfficerRegistryCompleteResponse(
            status="Registry marked completed",
            booking_id=booking.id,
            proofs=[_to_registry_proof_item(item) for item in list_registry_proofs_for_booking(db, booking.id)],
        ),
        None,
    )
