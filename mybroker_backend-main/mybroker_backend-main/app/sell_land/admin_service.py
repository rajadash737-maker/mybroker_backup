import json
import logging
from datetime import datetime, date, time, timedelta

from sqlalchemy.orm import Session

from app.sell_land.admin_schemas import (
    AccountingConfirmRefundRequest,
    AccountingConfirmRefundResponse,
    AccountingRefundHistoryItem,
    AccountingRefundHistoryListResponse,
    AccountingRefundPendingItem,
    AccountingRefundPendingListResponse,
    AccountingCompletedTransactionDetailResponse,
    AccountingCompletedTransactionItem,
    AccountingCompletedTransactionListResponse,
    AccountingDashboardSummaryResponse,
    RevenueRangeInfo,
    RevenueRangeType,
    RevenueBreakdown,
    RevenueTransactionItem,
    SuperAdminRevenueDashboardResponse,
    AccountingPaymentDetails,
    AccountingPaymentInfo,
    AdminForwardRefundToAccountingResponse,
    AdminBookedListingBuyerSummary,
    AdminBookedListingItem,
    AdminBookedListingListResponse,
    AdminBookedListingDetailResponse,
    AdminBookingDocument,
    AdminBookingFieldOfficerUpdateRequest,
    AdminBookingFieldOfficerUpdateResponse,
    AdminBookingPartyInfo,
    AdminBookedLandInfo,
    AdminBookedPaymentInfo,
    AdminRegistryInfo,
    AdminRegistryProofItem,
    AdminRegistryScheduleRequest,
    AdminRegistryScheduleResponse,
    AdminRegistryVerificationRequest,
    AdminRegistryVerificationResponse,
    AdminRegistryPendingItem,
    AdminRegistryPendingListResponse,
    AdminFieldVerifiedCaseItem,
    AdminFieldVerifiedCaseListResponse,
    AdminFinalApprovalActionRequest,
    AdminFinalApprovalActionResponse,
    AdminRefundMarkPaidResponse,
    AdminRefundQueueItem,
    AdminRefundQueueListResponse,
    AdminRefundQueueSellerSummary,
    AdminRefundSuccessItem,
    AdminRefundSuccessListResponse,
    AdminAssignCaseRequest,
    AdminAssignCaseResponse,
    AdminCaseAssignmentBoardItem,
    AdminCaseAssignmentBoardResponse,
    AdminCaseLockOfficerSummary,
    AdminDashboardViewer,
    AdminDashboardWorkflowSummary,
    AdminFieldOfficerOption,
    AdminForceReleaseCaseResponse,
    AdminForceReleaseOfferLockResponse,
    AdminLockedListingBuyerSummary,
    AdminLockedListingItem,
    AdminLockedListingListResponse,
    AdminReviewActionRequest,
    AdminInstagramUrlUpdateResponse,
    AdminSellLandReviewDetail,
    AdminSellLandReviewListItem,
    AdminSellLandReviewListResponse,
    AdminSellerSummary,
    BoundaryPoint,
    FinalApprovalDecision,
    ReviewDecision,
)
from app.sell_land.constants import BookingStatus, MediaType, PaymentStatus, SellLandStatus
from app.sell_land.models import SellLandBooking, SellLandMedia, SellLandRequest
from app.sell_land.repository import (
    apply_admin_review_decision,
    apply_admin_final_approval_decision,
    assign_case_to_field_officer_by_admin,
    force_release_case_by_admin,
    force_release_offer_lock_by_admin,
    get_admin_workflow_summary_counts,
    get_active_case_for_field_officer,
    get_sell_land_request_by_id,
    get_user_by_id,
    list_booked_listings_for_admin,
    list_sold_listings_for_admin,
    list_locked_offer_listings_for_admin,
    list_offers_by_ids,
    list_available_cases_for_admin,
    list_pending_refund_cases_for_accounting,
    list_pending_refund_cases_for_admin,
    list_field_officers,
    list_refund_history_for_accounting,
    list_success_refund_cases_for_admin,
    list_locked_cases_for_admin,
    list_registry_pending_bookings,
    list_registry_proofs_for_booking,
    list_media_for_requests,
    list_field_verified_cases_for_admin,
    list_sell_land_requests_for_admin_review,
    get_offer_by_id,
    list_users_by_ids,
    list_completed_transactions_for_accounting,
    get_completed_transaction_by_listing_id,
    get_latest_payment_by_request_id,
    get_accounting_dashboard_summary,
    get_super_admin_revenue_summary,
)
from app.notifications.service import notify_users

logger = logging.getLogger(__name__)
from app.users.model import User
from app.users.roles import UserRole


def _to_seller_summary(user: User) -> AdminSellerSummary:
    return AdminSellerSummary(
        id=user.id,
        fullname=user.fullname,
        mobile=user.mobile,
        email=user.email,
    )


def _to_refund_seller_summary(user: User) -> AdminRefundQueueSellerSummary:
    return AdminRefundQueueSellerSummary(
        id=user.id,
        fullname=user.fullname,
        mobile=user.mobile,
    )


def _parse_boundary_points(raw: str | None) -> list[BoundaryPoint]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    points: list[BoundaryPoint] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        lat = item.get("lat")
        lng = item.get("lng")
        if lat is None or lng is None:
            continue
        points.append(BoundaryPoint(lat=float(lat), lng=float(lng)))
    return points


def _to_lock_officer_summary(user: User) -> AdminCaseLockOfficerSummary:
    return AdminCaseLockOfficerSummary(
        id=user.id,
        fullname=user.fullname,
        mobile=user.mobile,
    )


def _to_locked_listing_buyer_summary(user: User) -> AdminLockedListingBuyerSummary:
    return AdminLockedListingBuyerSummary(
        id=user.id,
        fullname=user.fullname,
        mobile=user.mobile,
    )


def _to_booked_listing_buyer_summary(booking: SellLandBooking) -> AdminBookedListingBuyerSummary:
    return AdminBookedListingBuyerSummary(
        id=booking.buyer_id,
        fullname=booking.buyer_name,
        mobile=booking.buyer_mobile,
    )


def _to_registry_proof_item(entity) -> AdminRegistryProofItem:
    return AdminRegistryProofItem(
        id=entity.id,
        file_url=entity.file_url,
        file_name=entity.file_name,
        created_at=entity.created_at,
    )


def _humanize_admin_status_before_cancellation(status_before_cancellation: str | None) -> str:
    mapping = {
        SellLandStatus.PENDING.value: "Pending Admin Review",
        SellLandStatus.APPROVED.value: "Document Verified",
        SellLandStatus.FIELD_VERIFIED.value: "Field Visit Completed",
        SellLandStatus.LIVE.value: "Listing Live",
        SellLandStatus.REJECTED.value: "Rejected",
        SellLandStatus.BOOKED.value: "Booked",
        SellLandStatus.SOLD.value: "Sold",
        SellLandStatus.DRAFT.value: "Draft",
    }
    if not status_before_cancellation:
        return "Admin Reviewed"
    return mapping.get(status_before_cancellation, "Admin Reviewed")


def _format_listing_price(value) -> str | None:
    if value is None:
        return None
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return None
    return f"Rs {amount:,}"


def _discover_customers_for_live_listing(
    db: Session,
    listing: SellLandRequest,
) -> list[User]:
    return (
        db.query(User)
        .filter(User.is_active.is_(True))
        .filter(User.role == UserRole.CUSTOMER.value)
        .filter(User.id != listing.user_id)
        .filter(User.fcm_token.is_not(None))
        .all()
    )


def _map_payment_status(status: str | None) -> str | None:
    if not status:
        return None
    normalized = status.lower().strip()
    if normalized == PaymentStatus.SUCCESS.value:
        return "PAID"
    if normalized == PaymentStatus.FAILED.value:
        return "FAILED"
    return "PENDING"


def _map_payment_method(method: str | None) -> str | None:
    if not method:
        return None
    normalized = method.lower().strip()
    if normalized == "upi":
        return "UPI"
    if normalized == "debit_credit_card":
        return "CARD"
    if normalized == "net_banking":
        return "BANK"
    if normalized == "cash":
        return "CASH"
    return normalized.upper()


def _to_assignment_item(
    entity: SellLandRequest,
    officer_map: dict[int, User],
    now: datetime,
) -> AdminCaseAssignmentBoardItem:
    assigned_officer = officer_map.get(entity.assigned_field_officer_id) if entity.assigned_field_officer_id else None
    locked_for_seconds = None
    if entity.lock_started_at:
        locked_for_seconds = max(0, int((now - entity.lock_started_at).total_seconds()))
    return AdminCaseAssignmentBoardItem(
        id=entity.id,
        listing_code=entity.listing_code,
        owner_name=entity.owner_name,
        owner_mobile=entity.owner_mobile,
        location=entity.location,
        assigned_field_officer=_to_lock_officer_summary(assigned_officer) if assigned_officer else None,
        lock_started_at=entity.lock_started_at,
        lock_expires_at=entity.lock_expires_at,
        locked_for_seconds=locked_for_seconds,
    )


def _to_field_verified_item(
    entity: SellLandRequest,
    officer_map: dict[int, User],
) -> AdminFieldVerifiedCaseItem:
    officer = officer_map.get(entity.field_officer_reviewed_by_id) if entity.field_officer_reviewed_by_id else None
    return AdminFieldVerifiedCaseItem(
        id=entity.id,
        listing_code=entity.listing_code,
        owner_name=entity.owner_name,
        owner_mobile=entity.owner_mobile,
        location=entity.location,
        field_officer=_to_lock_officer_summary(officer) if officer else None,
        field_officer_notes=entity.field_officer_notes,
        field_officer_reviewed_at=entity.field_officer_reviewed_at,
        visit_photo_url=entity.field_officer_visit_photo_url,
    )


def list_requests_for_review(
    db: Session,
    current_user: User,
    status_filter: SellLandStatus | None,
    search: str | None,
    state_filter: str | None,
    city_filter: str | None,
    skip: int,
    limit: int,
    listing_id: int | None = None,
) -> AdminSellLandReviewListResponse:
    status_value = status_filter.value if status_filter else None
    reviewed_by_id = None
    if current_user.role == UserRole.ADMIN.value and status_filter != SellLandStatus.PENDING:
        reviewed_by_id = current_user.id
    items, total = list_sell_land_requests_for_admin_review(
        db=db,
        status_filter=status_value,
        search=search,
        state_filter=state_filter,
        city_filter=city_filter,
        skip=skip,
        limit=limit,
        reviewed_by_id=reviewed_by_id,
        listing_id=listing_id,
    )
    users = list_users_by_ids(db, [item.user_id for item in items])
    user_map = {user.id: user for user in users}

    response_items: list[AdminSellLandReviewListItem] = []
    for item in items:
        seller = user_map.get(item.user_id)
        if not seller:
            continue
        response_items.append(
            AdminSellLandReviewListItem(
                id=item.id,
                listing_code=item.listing_code,
                title=item.title,
                owner_name=item.owner_name,
                owner_mobile=item.owner_mobile,
                land_type=item.land_type,
                ownership_type=item.ownership_type,
                city=item.city,
                state=item.state,
                expected_price=item.expected_price,
                status=item.status,
                payment_status=item.payment_status,
                created_at=item.created_at,
                updated_at=item.updated_at,
                seller=_to_seller_summary(seller),
            )
        )

    return AdminSellLandReviewListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=response_items,
    )


def get_request_for_review(
    db: Session,
    request_id: int,
) -> tuple[AdminSellLandReviewDetail | None, str | None]:
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"

    user_ids = [entity.user_id]
    if entity.reviewed_by_id:
        user_ids.append(entity.reviewed_by_id)
    if entity.assigned_field_officer_id:
        user_ids.append(entity.assigned_field_officer_id)
    if entity.field_officer_reviewed_by_id:
        user_ids.append(entity.field_officer_reviewed_by_id)

    users = list_users_by_ids(db, list({uid for uid in user_ids if uid is not None}))
    if not users:
        return None, "Seller not found"
    user_map = {user.id: user for user in users}
    seller = user_map.get(entity.user_id)
    if not seller:
        return None, "Seller not found"
    media_items = list_media_for_requests(db, [entity.id])
    latest_payment = get_latest_payment_by_request_id(db, entity.id)

    admin_user = user_map.get(entity.reviewed_by_id) if entity.reviewed_by_id else None
    field_officer_user = None
    if entity.assigned_field_officer_id:
        field_officer_user = user_map.get(entity.assigned_field_officer_id)
    elif entity.field_officer_reviewed_by_id:
        field_officer_user = user_map.get(entity.field_officer_reviewed_by_id)

    detail = AdminSellLandReviewDetail(
        id=entity.id,
        user_id=entity.user_id,
        listing_code=entity.listing_code,
        title=entity.title,
        instagram_url=entity.instagram_url,
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
        is_draft=entity.is_draft,
        draft_step=entity.draft_step,
        payment_required_amount=entity.payment_required_amount,
        payment_status=entity.payment_status,
        payment_paid_at=latest_payment.paid_at if latest_payment else None,
        payment_amount=latest_payment.amount if latest_payment else None,
        status=entity.status,
        reviewed_by_id=entity.reviewed_by_id,
        reviewed_at=entity.reviewed_at,
        rejection_reason=entity.rejection_reason,
        cancellation_reason=entity.cancellation_reason,
        refund_upi_id=entity.refund_upi_id,
        cancelled_at=entity.cancelled_at,
        refund_due_at=entity.refund_due_at,
        refund_completed_at=entity.refund_completed_at,
        refund_amount=entity.refund_amount,
        refund_transaction_id=entity.refund_transaction_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        seller=_to_seller_summary(seller),
        admin_handler=_to_lock_officer_summary(admin_user) if admin_user else None,
        field_officer=_to_lock_officer_summary(field_officer_user) if field_officer_user else None,
        media=media_items,
    )
    return detail, None


def update_listing_instagram_url(db: Session, request_id: int, instagram_url: str | None):
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None
    entity.instagram_url = instagram_url
    db.commit()
    db.refresh(entity)
    return AdminInstagramUrlUpdateResponse(request_id=entity.id, instagram_url=entity.instagram_url)


def review_request(
    db: Session,
    request_id: int,
    current_user: User,
    payload: AdminReviewActionRequest,
) -> tuple[SellLandRequest | None, str | None]:
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"

    if entity.status not in {SellLandStatus.PENDING.value, SellLandStatus.REJECTED.value}:
        return None, "Only submitted listings can be reviewed"

    if entity.status == SellLandStatus.REJECTED.value and payload.decision == ReviewDecision.REJECTED:
        return None, "Listing already rejected"

    rejection_reason = None
    target_status = payload.decision.value
    if payload.decision == ReviewDecision.REJECTED:
        if not payload.rejection_reason:
            return None, "rejection_reason is required when decision is rejected"
        rejection_reason = payload.rejection_reason

    updated = apply_admin_review_decision(
        db=db,
        entity=entity,
        reviewed_by_id=current_user.id,
        target_status=target_status,
        rejection_reason=rejection_reason,
    )
    try:
        seller = get_user_by_id(db, updated.user_id)
        if seller:
            if payload.decision == ReviewDecision.REJECTED:
                notify_users(
                    db=db,
                    users=[seller],
                    title="Land Rejected",
                    body="Your land was rejected",
                    notif_type="LAND_REJECTED",
                    role_target=seller.role,
                    reference_id=str(updated.id),
                )
            elif payload.decision == ReviewDecision.APPROVED:
                notify_users(
                    db=db,
                    users=[seller],
                    title="Documents Verified",
                    body="Your documents are verified",
                    notif_type="LAND_VERIFIED",
                    role_target=seller.role,
                    reference_id=str(updated.id),
                )
    except Exception:
        logger.exception("Failed to send review notifications")
    return updated, None


def list_field_verified_cases_for_final_approval(
    db: Session,
    current_user: User,
    skip: int,
    limit: int,
) -> AdminFieldVerifiedCaseListResponse:
    reviewed_by_id = None
    if current_user.role == UserRole.ADMIN.value:
        reviewed_by_id = current_user.id
    items, total = list_field_verified_cases_for_admin(
        db=db,
        skip=skip,
        limit=limit,
        reviewed_by_id=reviewed_by_id,
    )
    officer_ids = list({
        item.field_officer_reviewed_by_id
        for item in items
        if item.field_officer_reviewed_by_id is not None
    })
    officers = list_users_by_ids(db, officer_ids)
    officer_map = {officer.id: officer for officer in officers}
    return AdminFieldVerifiedCaseListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[_to_field_verified_item(item, officer_map) for item in items],
    )


def take_final_approval_action(
    db: Session,
    current_user: User,
    request_id: int,
    payload: AdminFinalApprovalActionRequest,
) -> tuple[AdminFinalApprovalActionResponse | None, str | None]:
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status not in {SellLandStatus.FIELD_VERIFIED.value, SellLandStatus.APPROVED.value}:
        return None, "Only field verified listings can be processed in final approval"
    if entity.field_officer_decision != SellLandStatus.APPROVED.value:
        return None, "Only field officer approved listings can be processed in final approval"
    if current_user.role == UserRole.ADMIN.value and entity.reviewed_by_id != current_user.id:
        return None, "You can only process your own verified listings"
    if payload.decision == FinalApprovalDecision.REJECT and not payload.rejection_reason:
        return None, "rejection_reason is required when decision is reject"

    updated = apply_admin_final_approval_decision(
        db=db,
        entity=entity,
        decision=payload.decision.value,
        rejection_reason=payload.rejection_reason,
    )
    status_message = "Final approval decision applied successfully"
    if payload.decision == FinalApprovalDecision.APPROVE_GO_LIVE:
        status_message = "Listing approved and moved to live"
    elif payload.decision == FinalApprovalDecision.REASSIGN_TO_FIELD_OFFICER:
        status_message = "Listing reassigned to field officer queue"
    elif payload.decision == FinalApprovalDecision.REJECT:
        status_message = "Listing rejected successfully"

    try:
        seller = get_user_by_id(db, updated.user_id)
        if seller:
            if payload.decision == FinalApprovalDecision.APPROVE_GO_LIVE:
                listing_title = (updated.title or "Your land listing").strip()
                location_label = ", ".join(
                    part for part in [updated.city, updated.state] if part and part.strip()
                )
                seller_body = f"{listing_title} is approved and now live"
                if location_label:
                    seller_body += f" in {location_label}"
                notify_users(
                    db=db,
                    users=[seller],
                    title="Listing Approved",
                    body=seller_body,
                    notif_type="FINAL_APPROVAL_APPROVED",
                    role_target=seller.role,
                    reference_id=str(updated.id),
                )
                customers = _discover_customers_for_live_listing(db, updated)
                if customers:
                    buyer_title = (updated.title or "New live land listing").strip()
                    location_text = ", ".join(
                        part for part in [updated.city, updated.state] if part and part.strip()
                    )
                    price_text = _format_listing_price(updated.expected_price)
                    buyer_body_parts = ["A new verified land listing is now available"]
                    if location_text:
                        buyer_body_parts.append(location_text)
                    if price_text:
                        buyer_body_parts.append(price_text)
                    notify_users(
                        db=db,
                        users=customers,
                        title=buyer_title,
                        body=" | ".join(buyer_body_parts),
                        notif_type="LIVE_LISTING_NEARBY",
                        role_target=UserRole.CUSTOMER.value,
                        reference_id=str(updated.id),
                    )
            elif payload.decision == FinalApprovalDecision.REJECT:
                notify_users(
                    db=db,
                    users=[seller],
                    title="Land Rejected",
                    body="Your land was rejected",
                    notif_type="FINAL_APPROVAL_REJECTED",
                    role_target=seller.role,
                    reference_id=str(updated.id),
                )
    except Exception:
        logger.exception("Failed to send final approval notifications")

    return (
        AdminFinalApprovalActionResponse(
            status=status_message,
            request_id=updated.id,
            listing_status=updated.status,
            rejection_reason=updated.rejection_reason,
        ),
        None,
    )


def get_admin_dashboard_workflow_summary(db: Session, current_user: User) -> AdminDashboardWorkflowSummary:
    reviewed_by_id = None
    if current_user.role == UserRole.ADMIN.value:
        reviewed_by_id = current_user.id
    counts = get_admin_workflow_summary_counts(db, reviewed_by_id=reviewed_by_id)
    return AdminDashboardWorkflowSummary(
        **counts,
        viewer=AdminDashboardViewer(
            id=current_user.id,
            fullname=current_user.fullname,
            role=current_user.role,
            profile_image_url=current_user.profile_image_url,
        ),
    )


def list_assignable_field_officers(db: Session) -> list[AdminFieldOfficerOption]:
    officers = list_field_officers(db, only_active=True)
    return [
        AdminFieldOfficerOption(
            id=officer.id,
            fullname=officer.fullname,
            mobile=officer.mobile,
            is_active=officer.is_active,
        )
        for officer in officers
    ]


def get_case_assignment_board(
    db: Session,
    current_user: User,
    skip: int,
    limit: int,
) -> AdminCaseAssignmentBoardResponse:
    now = datetime.utcnow()
    reviewed_by_id = None
    if current_user.role == UserRole.ADMIN.value:
        reviewed_by_id = current_user.id
    locked_cases, locked_total = list_locked_cases_for_admin(
        db=db,
        skip=skip,
        limit=limit,
        reviewed_by_id=reviewed_by_id,
    )
    available_cases, available_total = list_available_cases_for_admin(
        db=db,
        skip=skip,
        limit=limit,
        reviewed_by_id=reviewed_by_id,
    )

    officer_ids = list({
        case.assigned_field_officer_id
        for case in locked_cases
        if case.assigned_field_officer_id is not None
    })
    officers = list_users_by_ids(db, officer_ids)
    officer_map = {officer.id: officer for officer in officers}

    return AdminCaseAssignmentBoardResponse(
        locked_total=locked_total,
        available_total=available_total,
        locked_cases=[_to_assignment_item(case, officer_map, now) for case in locked_cases],
        available_cases=[_to_assignment_item(case, officer_map, now) for case in available_cases],
    )


def force_release_case_lock(
    db: Session,
    request_id: int,
) -> tuple[AdminForceReleaseCaseResponse | None, str | None]:
    entity, error = force_release_case_by_admin(db=db, request_id=request_id)
    if error:
        return None, error
    return (
        AdminForceReleaseCaseResponse(
            status="Case force released successfully",
            request_id=entity.id,
        ),
        None,
    )


def list_locked_offer_listings(
    db: Session,
    current_user: User,
    skip: int,
    limit: int,
) -> AdminLockedListingListResponse:
    now = datetime.utcnow()
    reviewed_by_id = None
    if current_user.role == UserRole.ADMIN.value:
        reviewed_by_id = current_user.id

    items, total = list_locked_offer_listings_for_admin(
        db=db,
        skip=skip,
        limit=limit,
        reviewed_by_id=reviewed_by_id,
    )
    seller_ids = [item.user_id for item in items]
    offer_ids = [item.accepted_offer_id for item in items if item.accepted_offer_id is not None]
    offers = list_offers_by_ids(db, offer_ids)
    offer_map = {offer.id: offer for offer in offers}

    buyer_ids = [
        offer.buyer_id
        for offer in offers
        if offer.buyer_id is not None
    ]
    users = list_users_by_ids(db, list({*seller_ids, *buyer_ids}))
    user_map = {user.id: user for user in users}

    response_items: list[AdminLockedListingItem] = []
    for item in items:
        seller = user_map.get(item.user_id)
        if not seller:
            continue
        offer = offer_map.get(item.accepted_offer_id) if item.accepted_offer_id else None
        buyer = user_map.get(offer.buyer_id) if offer else None
        lock_started_at = offer.seller_response_at if offer else None
        locked_for_seconds = None
        if lock_started_at:
            locked_for_seconds = max(0, int((now - lock_started_at).total_seconds()))
        deal_price = None
        offer_status = None
        offer_id = None
        if offer:
            offer_id = offer.id
            offer_status = offer.status
            deal_price = offer.counter_amount if offer.counter_amount is not None else offer.offered_amount

        response_items.append(
            AdminLockedListingItem(
                id=item.id,
                listing_code=item.listing_code,
                owner_name=item.owner_name,
                owner_mobile=item.owner_mobile,
                expected_price=item.expected_price,
                lock_started_at=lock_started_at,
                lock_expires_at=item.offer_lock_expires_at,
                locked_for_seconds=locked_for_seconds,
                seller=_to_seller_summary(seller),
                buyer=_to_locked_listing_buyer_summary(buyer) if buyer else None,
                offer_id=offer_id,
                offer_status=offer_status,
                deal_price=deal_price,
            )
        )

    return AdminLockedListingListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=response_items,
    )


def list_booked_listings(
    db: Session,
    current_user: User,
    skip: int,
    limit: int,
) -> AdminBookedListingListResponse:
    reviewed_by_id = None
    if current_user.role == UserRole.ADMIN.value:
        reviewed_by_id = current_user.id

    items, total = list_booked_listings_for_admin(
        db=db,
        skip=skip,
        limit=limit,
        reviewed_by_id=reviewed_by_id,
    )
    seller_ids = [item.user_id for item in items]
    users = list_users_by_ids(db, seller_ids)
    user_map = {user.id: user for user in users}

    offer_ids = [item.accepted_offer_id for item in items if item.accepted_offer_id is not None]
    offers = list_offers_by_ids(db, offer_ids) if offer_ids else []
    offer_map = {offer.id: offer for offer in offers}

    request_ids = [item.id for item in items]
    bookings: list[SellLandBooking] = []
    if request_ids:
        bookings = (
            db.query(SellLandBooking)
            .filter(
                SellLandBooking.request_id.in_(request_ids),
                SellLandBooking.payment_status == PaymentStatus.SUCCESS.value,
            )
            .order_by(SellLandBooking.created_at.desc(), SellLandBooking.id.desc())
            .all()
        )
    booking_map: dict[int, SellLandBooking] = {}
    for booking in bookings:
        if booking.request_id not in booking_map:
            booking_map[booking.request_id] = booking

    officer_ids = list({
        *[
            booking.assigned_field_officer_id
            for booking in bookings
            if booking.assigned_field_officer_id is not None
        ],
        *[
            item.field_officer_reviewed_by_id
            for item in items
            if item.field_officer_reviewed_by_id is not None
        ],
    })
    officers = list_users_by_ids(db, officer_ids)
    officer_map = {officer.id: officer for officer in officers}

    response_items: list[AdminBookedListingItem] = []
    for item in items:
        seller = user_map.get(item.user_id)
        if not seller:
            continue
        booking = booking_map.get(item.id)
        booked_at = None
        buyer = None
        deal_price = None
        booking_fee_amount = None
        payment_status = None
        booking_status = None
        booking_id = None
        assigned_officer = None
        if booking:
            booked_at = booking.paid_at or booking.created_at
            buyer = _to_booked_listing_buyer_summary(booking)
            accepted_offer = offer_map.get(item.accepted_offer_id) if item.accepted_offer_id else None
            if accepted_offer:
                deal_price = accepted_offer.counter_amount if accepted_offer.counter_amount is not None else accepted_offer.offered_amount
            else:
                deal_price = booking.deal_amount
            booking_fee_amount = booking.booking_fee_amount
            payment_status = booking.payment_status
            booking_status = booking.booking_status
            booking_id = booking.id
            assigned_officer = (
                officer_map.get(booking.assigned_field_officer_id)
                if booking.assigned_field_officer_id
                else officer_map.get(item.field_officer_reviewed_by_id)
            )

        response_items.append(
            AdminBookedListingItem(
                id=item.id,
                listing_code=item.listing_code,
                owner_name=item.owner_name,
                owner_mobile=item.owner_mobile,
                expected_price=item.expected_price,
                booked_at=booked_at,
                deal_price=deal_price,
                booking_fee_amount=booking_fee_amount,
                payment_status=payment_status,
                booking_status=BookingStatus(booking_status) if booking_status else None,
                field_officer=_to_lock_officer_summary(assigned_officer) if assigned_officer else None,
                seller=_to_seller_summary(seller),
                buyer=buyer,
                booking_id=booking_id,
            )
        )

    return AdminBookedListingListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=response_items,
    )


def list_sold_listings(
    db: Session,
    current_user: User,
    skip: int,
    limit: int,
) -> AdminBookedListingListResponse:
    reviewed_by_id = None
    if current_user.role == UserRole.ADMIN.value:
        reviewed_by_id = current_user.id

    items, total = list_sold_listings_for_admin(
        db=db,
        skip=skip,
        limit=limit,
        reviewed_by_id=reviewed_by_id,
    )
    seller_ids = [item.user_id for item in items]
    users = list_users_by_ids(db, seller_ids)
    user_map = {user.id: user for user in users}

    offer_ids = [item.accepted_offer_id for item in items if item.accepted_offer_id is not None]
    offers = list_offers_by_ids(db, offer_ids) if offer_ids else []
    offer_map = {offer.id: offer for offer in offers}

    request_ids = [item.id for item in items]
    bookings: list[SellLandBooking] = []
    if request_ids:
        bookings = (
            db.query(SellLandBooking)
            .filter(
                SellLandBooking.request_id.in_(request_ids),
                SellLandBooking.payment_status == PaymentStatus.SUCCESS.value,
            )
            .order_by(SellLandBooking.created_at.desc(), SellLandBooking.id.desc())
            .all()
        )
    booking_map: dict[int, SellLandBooking] = {}
    for booking in bookings:
        if booking.request_id not in booking_map:
            booking_map[booking.request_id] = booking

    officer_ids = list({
        booking.assigned_field_officer_id
        for booking in bookings
        if booking.assigned_field_officer_id is not None
    })
    officers = list_users_by_ids(db, officer_ids)
    officer_map = {officer.id: officer for officer in officers}

    response_items: list[AdminBookedListingItem] = []
    for item in items:
        seller = user_map.get(item.user_id)
        if not seller:
            continue
        booking = booking_map.get(item.id)
        booked_at = None
        buyer = None
        deal_price = None
        booking_fee_amount = None
        payment_status = None
        booking_status = None
        booking_id = None
        assigned_officer = None
        if booking:
            booked_at = booking.paid_at or booking.created_at
            buyer = _to_booked_listing_buyer_summary(booking)
            accepted_offer = offer_map.get(item.accepted_offer_id) if item.accepted_offer_id else None
            if accepted_offer:
                deal_price = accepted_offer.counter_amount if accepted_offer.counter_amount is not None else accepted_offer.offered_amount
            else:
                deal_price = booking.deal_amount
            booking_fee_amount = booking.booking_fee_amount
            payment_status = booking.payment_status
            booking_status = booking.booking_status
            booking_id = booking.id
            assigned_officer = officer_map.get(booking.assigned_field_officer_id) if booking.assigned_field_officer_id else None

        response_items.append(
            AdminBookedListingItem(
                id=item.id,
                listing_code=item.listing_code,
                owner_name=item.owner_name,
                owner_mobile=item.owner_mobile,
                expected_price=item.expected_price,
                booked_at=booked_at,
                deal_price=deal_price,
                booking_fee_amount=booking_fee_amount,
                payment_status=payment_status,
                booking_status=BookingStatus(booking_status) if booking_status else None,
                field_officer=_to_lock_officer_summary(assigned_officer) if assigned_officer else None,
                seller=_to_seller_summary(seller),
                buyer=buyer,
                booking_id=booking_id,
            )
        )

    return AdminBookedListingListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=response_items,
    )


def _to_completed_transaction_item(
    listing: SellLandRequest,
    booking: SellLandBooking | None,
    seller_name: str,
) -> AccountingCompletedTransactionItem:
    seller_fee_amount = listing.payment_required_amount or 0.0
    buyer_fee_amount = booking.booking_fee_amount if booking else None
    buyer_fee_status = "PAID" if booking and booking.payment_status == PaymentStatus.SUCCESS.value else "PENDING"
    seller_fee_status = "PAID" if listing.payment_status == PaymentStatus.SUCCESS.value else "PENDING"
    status = "COMPLETED" if booking else "WAITING_BUYER"
    buyer_name = booking.buyer_name if booking else None
    date = (booking.paid_at or booking.created_at) if booking else listing.updated_at or listing.created_at

    return AccountingCompletedTransactionItem(
        listing_id=listing.id,
        listing_code=listing.listing_code,
        seller_name=seller_name,
        seller_fee=seller_fee_amount,
        seller_fee_status=seller_fee_status,
        buyer_name=buyer_name,
        buyer_fee=buyer_fee_amount,
        buyer_fee_status=buyer_fee_status,
        status=status,
        date=date,
    )


def list_completed_transactions_for_accounting_panel(
    db: Session,
    skip: int,
    limit: int,
) -> AccountingCompletedTransactionListResponse:
    rows, total = list_completed_transactions_for_accounting(db=db, skip=skip, limit=limit)
    seller_ids = list({listing.user_id for listing, _ in rows})
    sellers = list_users_by_ids(db, seller_ids)
    seller_map = {seller.id: seller for seller in sellers}

    items: list[AccountingCompletedTransactionItem] = []
    for listing, booking in rows:
        seller_user = seller_map.get(listing.user_id)
        seller_name = listing.owner_name or (seller_user.fullname if seller_user else "Seller")
        items.append(_to_completed_transaction_item(listing, booking, seller_name))

    return AccountingCompletedTransactionListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items,
    )


def get_completed_transaction_detail(
    db: Session,
    listing_id: int,
) -> tuple[AccountingCompletedTransactionDetailResponse | None, str | None]:
    row = get_completed_transaction_by_listing_id(db=db, listing_id=listing_id)
    if not row:
        return None, "Completed transaction not found"

    listing, booking = row
    seller_user = get_user_by_id(db, listing.user_id)
    seller_name = listing.owner_name or (seller_user.fullname if seller_user else "Seller")
    transaction = _to_completed_transaction_item(listing, booking, seller_name)
    final_status = "COMPLETED" if transaction.status == "COMPLETED" else "WAITING_BUYER"
    seller_payment = get_latest_payment_by_request_id(db, listing.id)
    seller_payment_info = None
    if seller_payment:
        seller_payment_info = AccountingPaymentInfo(
            method=_map_payment_method(seller_payment.method),
            transaction_id=seller_payment.provider_ref,
            paid_at=seller_payment.paid_at or seller_payment.created_at,
            status=_map_payment_status(seller_payment.status),
        )

    buyer_payment_info = None
    if booking:
        buyer_payment_info = AccountingPaymentInfo(
            method=_map_payment_method(booking.payment_method),
            transaction_id=booking.payment_transaction_id,
            paid_at=booking.paid_at or booking.created_at,
            status=_map_payment_status(booking.payment_status),
        )

    return (
        AccountingCompletedTransactionDetailResponse(
            transaction=transaction,
            payment_details=AccountingPaymentDetails(
                seller=seller_payment_info,
                buyer=buyer_payment_info,
            ),
            land_price_note="Paid outside app",
            final_status=final_status,
        ),
        None,
    )


def get_accounting_dashboard_summary_service(
    db: Session,
    range_type: RevenueRangeType,
    start_date: date | None,
    end_date: date | None,
) -> AccountingDashboardSummaryResponse:
    start_at, end_at = _resolve_revenue_range(range_type, start_date, end_date)
    total_revenue, pending_payments, completed_transactions, pending_refunds = get_accounting_dashboard_summary(
        db,
        start_at,
        end_at,
    )
    return AccountingDashboardSummaryResponse(
        total_revenue=total_revenue,
        pending_payments=pending_payments,
        completed_transactions=completed_transactions,
        pending_refunds=pending_refunds,
    )


def _resolve_revenue_range(
    range_type: RevenueRangeType,
    start_date: date | None,
    end_date: date | None,
) -> tuple[datetime, datetime]:
    today = datetime.utcnow().date()
    if range_type == RevenueRangeType.ALL:
        start = datetime(1970, 1, 1)
        end = datetime.combine(today, time.max)
        return start, end
    if range_type == RevenueRangeType.TODAY:
        start = datetime.combine(today, time.min)
        end = datetime.combine(today, time.max)
        return start, end
    if range_type == RevenueRangeType.WEEK:
        start = datetime.combine(today - timedelta(days=6), time.min)
        end = datetime.combine(today, time.max)
        return start, end
    if range_type == RevenueRangeType.MONTH:
        start = datetime.combine(today.replace(day=1), time.min)
        end = datetime.combine(today, time.max)
        return start, end
    if range_type == RevenueRangeType.CUSTOM:
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required for custom range")
        start = datetime.combine(start_date, time.min)
        end = datetime.combine(end_date, time.max)
        return start, end
    raise ValueError("Invalid range type")


def get_super_admin_revenue_dashboard(
    db: Session,
    range_type: RevenueRangeType,
    start_date: date | None,
    end_date: date | None,
) -> SuperAdminRevenueDashboardResponse:
    start_at, end_at = _resolve_revenue_range(range_type, start_date, end_date)
    total, seller, buyer, transactions = get_super_admin_revenue_summary(db, start_at, end_at)
    return SuperAdminRevenueDashboardResponse(
        range=RevenueRangeInfo(type=range_type, start=start_at, end=end_at),
        revenue=RevenueBreakdown(total=total, seller=seller, buyer=buyer),
        transactions=[RevenueTransactionItem(**item) for item in transactions],
    )


def get_booked_listing_detail(
    db: Session,
    current_user: User,
    request_id: int,
) -> tuple[AdminBookedListingDetailResponse | None, str | None]:
    listing = get_sell_land_request_by_id(db, request_id)
    if not listing:
        return None, "Sell land request not found"
    if listing.status not in {SellLandStatus.BOOKED.value, SellLandStatus.SOLD.value}:
        return None, "Listing is not booked"
    if current_user.role == UserRole.ADMIN.value and listing.reviewed_by_id != current_user.id:
        return None, "You can only view booked listings verified by you"

    booking = (
        db.query(SellLandBooking)
        .filter(
            SellLandBooking.request_id == request_id,
            SellLandBooking.payment_status == PaymentStatus.SUCCESS.value,
        )
        .order_by(
            SellLandBooking.paid_at.is_(None),
            SellLandBooking.paid_at.desc(),
            SellLandBooking.created_at.desc(),
        )
        .first()
    )
    if not booking:
        return None, "Booking not found"

    accepted_offer = None
    if listing.accepted_offer_id is not None:
        accepted_offer = get_offer_by_id(db, request_id=listing.id, offer_id=listing.accepted_offer_id)

    seller_user = list_users_by_ids(db, [listing.user_id])
    seller_name = listing.owner_name or (seller_user[0].fullname if seller_user else "Seller")
    seller_mobile = listing.owner_mobile or (seller_user[0].mobile if seller_user else None)

    media_items = list_media_for_requests(db, [listing.id])
    seller_docs: list[AdminBookingDocument] = []
    for media in media_items:
        if media.media_type != MediaType.DOCUMENT.value:
            continue
        label = media.document_type or media.file_name or "Document"
        seller_docs.append(
            AdminBookingDocument(
                name=label,
                file_url=media.file_url,
            )
        )

    buyer_docs: list[AdminBookingDocument] = []
    if booking.aadhaar_doc_url:
        buyer_docs.append(AdminBookingDocument(name="Aadhar Card", file_url=booking.aadhaar_doc_url))
    if booking.pan_doc_url:
        buyer_docs.append(AdminBookingDocument(name="PAN Card", file_url=booking.pan_doc_url))
    if booking.bank_doc_url:
        buyer_docs.append(AdminBookingDocument(name="Bank Account", file_url=booking.bank_doc_url))

    location = listing.location
    if not location:
        location = ", ".join([value for value in [listing.city, listing.state] if value])
        location = location or None

    deal_price = (
        accepted_offer.counter_amount
        if accepted_offer and accepted_offer.counter_amount is not None
        else accepted_offer.offered_amount if accepted_offer else booking.deal_amount
    )

    remaining_amount = None
    if deal_price is not None and booking.booking_fee_amount is not None:
        remaining_amount = max(0.0, float(deal_price) - float(booking.booking_fee_amount))

    officer = None
    officer_id = booking.assigned_field_officer_id or listing.field_officer_reviewed_by_id
    if officer_id:
        officers = list_users_by_ids(db, [officer_id])
        officer = officers[0] if officers else None

    response = AdminBookedListingDetailResponse(
        booking_id=booking.id,
        listing_id=listing.id,
        status=SellLandStatus(listing.status),
        booked_at=booking.paid_at or booking.created_at,
        booking_status=BookingStatus(booking.booking_status),
        buyer=AdminBookingPartyInfo(
            name=booking.buyer_name,
            mobile=booking.buyer_mobile,
            documents=buyer_docs,
        ),
        seller=AdminBookingPartyInfo(
            name=seller_name,
            mobile=seller_mobile,
            documents=seller_docs,
        ),
        land=AdminBookedLandInfo(
            expected_price=listing.expected_price,
            deal_price=deal_price,
            location=location,
        ),
        payment=AdminBookedPaymentInfo(
            token_amount=booking.booking_fee_amount,
            remaining_amount=remaining_amount,
            payment_status=booking.payment_status,
        ),
        field_officer=_to_lock_officer_summary(officer) if officer else None,
        registry=AdminRegistryInfo(
            registry_date=booking.registry_date,
            registry_time=booking.registry_time,
            registry_location=booking.registry_location,
            proof_url=booking.registry_proof_url,
            proofs=[_to_registry_proof_item(p) for p in list_registry_proofs_for_booking(db, booking.id)],
            proof_notes=booking.registry_notes,
            status=BookingStatus(booking.booking_status) if booking.booking_status else None,
        ),
    )
    return response, None


def update_booking_field_officer(
    db: Session,
    current_user: User,
    booking_id: int,
    payload: AdminBookingFieldOfficerUpdateRequest,
) -> tuple[AdminBookingFieldOfficerUpdateResponse | None, str | None]:
    booking = db.query(SellLandBooking).filter(SellLandBooking.id == booking_id).first()
    if not booking:
        return None, "Booking not found"

    listing = get_sell_land_request_by_id(db, booking.request_id)
    if not listing:
        return None, "Sell land request not found"
    if listing.status != SellLandStatus.BOOKED.value:
        return None, "Listing is not booked"
    if current_user.role == UserRole.ADMIN.value and listing.reviewed_by_id != current_user.id:
        return None, "You can only update bookings verified by you"

    field_officer = get_user_by_id(db, payload.field_officer_id)
    if not field_officer:
        return None, "Field officer not found"
    if field_officer.role != UserRole.FIELD_OFFICER.value:
        return None, "Selected user is not a field officer"
    if not field_officer.is_active:
        return None, "Field officer is inactive"

    booking.assigned_field_officer_id = field_officer.id
    db.commit()
    db.refresh(booking)

    return (
        AdminBookingFieldOfficerUpdateResponse(
            status="Field officer updated",
            booking_id=booking.id,
            field_officer=_to_lock_officer_summary(field_officer),
        ),
        None,
    )


def schedule_registry(
    db: Session,
    current_user: User,
    booking_id: int,
    payload: AdminRegistryScheduleRequest,
) -> tuple[AdminRegistryScheduleResponse | None, str | None]:
    booking = db.query(SellLandBooking).filter(SellLandBooking.id == booking_id).first()
    if not booking:
        return None, "Booking not found"
    listing = get_sell_land_request_by_id(db, booking.request_id)
    if not listing:
        return None, "Sell land request not found"
    if listing.status != SellLandStatus.BOOKED.value:
        return None, "Listing is not booked"
    if current_user.role == UserRole.ADMIN.value and listing.reviewed_by_id != current_user.id:
        return None, "You can only update bookings verified by you"

    # Ensure a field officer is assigned for registry follow-up.
    if booking.assigned_field_officer_id is None and listing.field_officer_reviewed_by_id is not None:
        booking.assigned_field_officer_id = listing.field_officer_reviewed_by_id

    booking.registry_date = payload.registry_date
    booking.registry_time = payload.registry_time
    booking.registry_location = payload.registry_location.strip()
    booking.booking_status = BookingStatus.REGISTRY_SCHEDULED.value
    db.commit()
    db.refresh(booking)

    try:
        seller = get_user_by_id(db, listing.user_id)
        buyer = get_user_by_id(db, booking.buyer_id)
        field_officer = (
            get_user_by_id(db, booking.assigned_field_officer_id)
            if booking.assigned_field_officer_id is not None
            else None
        )
        registry_date_text = (
            booking.registry_date.isoformat()
            if booking.registry_date is not None
            else "TBD"
        )
        registry_time_text = (
            booking.registry_time.isoformat()
            if booking.registry_time is not None
            else "TBD"
        )
        registry_location_text = (booking.registry_location or "").strip() or "TBD"
        listing_title = (listing.title or "Land").strip()

        if seller:
            notify_users(
                db=db,
                users=[seller],
                title="Registry Scheduled",
                body=(
                    f"Registry scheduled for {listing_title} on "
                    f"{registry_date_text} at {registry_time_text} in {registry_location_text}"
                ),
                notif_type="REGISTRY_SCHEDULED",
                role_target=seller.role,
                reference_id=str(listing.id),
            )
        if buyer:
            notify_users(
                db=db,
                users=[buyer],
                title="Registry Scheduled",
                body=(
                    f"Your registry for {listing_title} is scheduled on "
                    f"{registry_date_text} at {registry_time_text} in {registry_location_text}"
                ),
                notif_type="REGISTRY_SCHEDULED",
                role_target=buyer.role,
                reference_id=str(listing.id),
            )
        if field_officer:
            notify_users(
                db=db,
                users=[field_officer],
                title="Registry Visit Assigned",
                body=(
                    f"Registry visit for {listing_title} is scheduled on "
                    f"{registry_date_text} at {registry_time_text} in {registry_location_text}"
                ),
                notif_type="REGISTRY_SCHEDULED",
                role_target=field_officer.role,
                reference_id=str(booking.id),
            )
    except Exception:
        logger.exception("Failed to send registry scheduled notifications")

    return (
        AdminRegistryScheduleResponse(
            status="Registry scheduled",
            booking_id=booking.id,
            booking_status=BookingStatus(booking.booking_status),
        registry=AdminRegistryInfo(
            registry_date=booking.registry_date,
            registry_time=booking.registry_time,
            registry_location=booking.registry_location,
            proof_url=booking.registry_proof_url,
            proofs=[_to_registry_proof_item(p) for p in list_registry_proofs_for_booking(db, booking.id)],
            proof_notes=booking.registry_notes,
            status=BookingStatus(booking.booking_status),
        ),
        ),
        None,
    )


def verify_registry(
    db: Session,
    current_user: User,
    booking_id: int,
    payload: AdminRegistryVerificationRequest,
) -> tuple[AdminRegistryVerificationResponse | None, str | None]:
    booking = db.query(SellLandBooking).filter(SellLandBooking.id == booking_id).first()
    if not booking:
        return None, "Booking not found"
    listing = get_sell_land_request_by_id(db, booking.request_id)
    if not listing:
        return None, "Sell land request not found"
    if listing.status != SellLandStatus.BOOKED.value:
        return None, "Listing is not booked"
    if current_user.role == UserRole.ADMIN.value and listing.reviewed_by_id != current_user.id:
        return None, "You can only update bookings verified by you"
    if booking.booking_status != BookingStatus.REGISTRY_DONE.value:
        return None, "Registry is not marked completed"

    if payload.decision == "approve":
        booking.booking_status = BookingStatus.SOLD.value
        listing.status = SellLandStatus.SOLD.value
        status_message = "Registry verified and listing marked as sold"
    else:
        booking.booking_status = BookingStatus.REGISTRY_SCHEDULED.value
        status_message = "Registry verification rejected"
    db.commit()
    db.refresh(booking)
    db.refresh(listing)

    try:
        seller = get_user_by_id(db, listing.user_id)
        buyer = get_user_by_id(db, booking.buyer_id)
        field_officer = (
            get_user_by_id(db, booking.assigned_field_officer_id)
            if booking.assigned_field_officer_id is not None
            else None
        )
        listing_title = (listing.title or "Land").strip()
        registry_date_text = booking.registry_date.isoformat() if booking.registry_date else "TBD"
        registry_time_text = booking.registry_time.isoformat() if booking.registry_time else "TBD"
        registry_location_text = (booking.registry_location or "").strip() or "TBD"

        if payload.decision == "approve":
            if seller:
                notify_users(
                    db=db,
                    users=[seller],
                    title="Land Sold",
                    body=(
                        f"Your registry for {listing_title} is verified and land is marked sold. "
                        f"{registry_date_text} {registry_time_text} {registry_location_text}"
                    ),
                    notif_type="REGISTRY_SOLD",
                    role_target=seller.role,
                    reference_id=str(listing.id),
                )
            if buyer:
                notify_users(
                    db=db,
                    users=[buyer],
                    title="Land Sold",
                    body=(
                        f"Your registry for {listing_title} is verified and land is marked sold. "
                        f"{registry_date_text} {registry_time_text} {registry_location_text}"
                    ),
                    notif_type="REGISTRY_SOLD",
                    role_target=buyer.role,
                    reference_id=str(listing.id),
                )
        else:
            if seller:
                notify_users(
                    db=db,
                    users=[seller],
                    title="Registry Rescheduled",
                    body=f"Registry verification for {listing_title} was rejected and sent back for scheduling",
                    notif_type="REGISTRY_SCHEDULED",
                    role_target=seller.role,
                    reference_id=str(listing.id),
                )
            if buyer:
                notify_users(
                    db=db,
                    users=[buyer],
                    title="Registry Rescheduled",
                    body=f"Registry verification for {listing_title} was rejected and sent back for scheduling",
                    notif_type="REGISTRY_SCHEDULED",
                    role_target=buyer.role,
                    reference_id=str(listing.id),
                )
            if field_officer:
                notify_users(
                    db=db,
                    users=[field_officer],
                    title="Registry Rescheduled",
                    body=f"Registry verification for {listing_title} was rejected and sent back for scheduling",
                    notif_type="REGISTRY_SCHEDULED",
                    role_target=field_officer.role,
                    reference_id=str(booking.id),
                )
    except Exception:
        logger.exception("Failed to send registry verification notifications")

    return (
        AdminRegistryVerificationResponse(
            status=status_message,
            booking_id=booking.id,
            booking_status=BookingStatus(booking.booking_status),
        ),
        None,
    )


def list_pending_registry_verification(
    db: Session,
    current_user: User,
    skip: int,
    limit: int,
) -> AdminRegistryPendingListResponse:
    reviewed_by_id = None
    if current_user.role == UserRole.ADMIN.value:
        reviewed_by_id = current_user.id

    items, total = list_registry_pending_bookings(
        db=db,
        skip=skip,
        limit=limit,
        reviewed_by_id=reviewed_by_id,
    )
    request_ids = [item.request_id for item in items]
    listings = db.query(SellLandRequest).filter(SellLandRequest.id.in_(request_ids)).all() if request_ids else []
    listing_map = {listing.id: listing for listing in listings}

    response_items: list[AdminRegistryPendingItem] = []
    for booking in items:
        listing = listing_map.get(booking.request_id)
        proofs = list_registry_proofs_for_booking(db, booking.id)
        response_items.append(
            AdminRegistryPendingItem(
                booking_id=booking.id,
                listing_id=booking.request_id,
                seller_name=listing.owner_name if listing else None,
                seller_mobile=listing.owner_mobile if listing else None,
                buyer_name=booking.buyer_name,
                buyer_mobile=booking.buyer_mobile,
                registry_date=booking.registry_date,
                registry_time=booking.registry_time,
                registry_location=booking.registry_location,
                proof_url=booking.registry_proof_url,
                proofs=[_to_registry_proof_item(p) for p in proofs],
            )
        )

    return AdminRegistryPendingListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=response_items,
    )


def force_release_offer_lock(
    db: Session,
    current_user: User,
    request_id: int,
) -> tuple[AdminForceReleaseOfferLockResponse | None, str | None]:
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"
    if current_user.role == UserRole.ADMIN.value and entity.reviewed_by_id != current_user.id:
        return None, "You can only release locks for your own verified listings"

    released, error = force_release_offer_lock_by_admin(db=db, request_id=request_id)
    if error:
        return None, error
    return (
        AdminForceReleaseOfferLockResponse(
            status="Offer lock released successfully",
            request_id=released.id,
        ),
        None,
    )


def assign_case_to_field_officer(
    db: Session,
    request_id: int,
    payload: AdminAssignCaseRequest,
) -> tuple[AdminAssignCaseResponse | None, str | None]:
    field_officer = get_user_by_id(db, payload.field_officer_id)
    if not field_officer:
        return None, "Field officer not found"
    if field_officer.role != UserRole.FIELD_OFFICER.value:
        return None, "Selected user is not a field officer"
    if not field_officer.is_active:
        return None, "Field officer is inactive"

    active_case = get_active_case_for_field_officer(db, payload.field_officer_id)
    if active_case and active_case.id != request_id:
        return None, "Selected field officer already has an active locked case"

    entity, error = assign_case_to_field_officer_by_admin(
        db=db,
        request_id=request_id,
        field_officer_id=payload.field_officer_id,
        lock_hours=payload.lock_hours,
    )
    if error:
        return None, error
    if not entity.lock_started_at or not entity.lock_expires_at:
        return None, "Failed to lock case"

    try:
        notify_users(
            db=db,
            users=[field_officer],
            title="New Case Assigned",
            body="A new land case has been assigned to you",
            notif_type="CASE_ASSIGNED",
            role_target=field_officer.role,
            reference_id=str(entity.id),
        )
    except Exception:
        logger.exception("Failed to send field officer assignment notification")

    return (
        AdminAssignCaseResponse(
            status=f"Case assigned and locked for {payload.lock_hours} hours",
            request_id=entity.id,
            assigned_field_officer=_to_lock_officer_summary(field_officer),
            lock_started_at=entity.lock_started_at,
            lock_expires_at=entity.lock_expires_at,
        ),
        None,
    )


def mark_refund_paid_by_admin(
    db: Session,
    request_id: int,
) -> tuple[AdminRefundMarkPaidResponse | None, str | None]:
    response, error = confirm_refund_by_accounting(db=db, request_id=request_id)
    if error:
        return None, error
    return (
        AdminRefundMarkPaidResponse(
            status=response.status,
            request_id=response.request_id,
            listing_status=response.listing_status,
            refund_completed_at=response.refund_completed_at,
        ),
        None,
    )


def list_pending_refunds_for_admin(
    db: Session,
    current_user: User,
    skip: int,
    limit: int,
) -> AdminRefundQueueListResponse:
    reviewed_by_id = None
    if current_user.role == UserRole.ADMIN.value:
        reviewed_by_id = current_user.id
    items, total = list_pending_refund_cases_for_admin(
        db=db,
        skip=skip,
        limit=limit,
        reviewed_by_id=reviewed_by_id,
    )
    seller_ids = [item.user_id for item in items]
    sellers = list_users_by_ids(db, seller_ids)
    seller_map = {seller.id: seller for seller in sellers}
    response_items: list[AdminRefundQueueItem] = []
    for item in items:
        seller = seller_map.get(item.user_id)
        if not seller:
            continue
        response_items.append(
            AdminRefundQueueItem(
                request_id=item.id,
                listing_code=item.listing_code,
                seller_uid=seller.id,
                seller=_to_refund_seller_summary(seller),
                cancellation_reason=item.cancellation_reason or "",
                cancelled_at=item.cancelled_at,
                refund_due_at=item.refund_due_at,
                refund_upi_id=item.refund_upi_id,
                total_paid=item.payment_required_amount,
            )
        )
    return AdminRefundQueueListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=response_items,
    )


def list_success_refunds_for_admin(
    db: Session,
    current_user: User,
    skip: int,
    limit: int,
) -> AdminRefundSuccessListResponse:
    reviewed_by_id = None
    if current_user.role == UserRole.ADMIN.value:
        reviewed_by_id = current_user.id
    items, total = list_success_refund_cases_for_admin(
        db=db,
        skip=skip,
        limit=limit,
        reviewed_by_id=reviewed_by_id,
    )
    seller_ids = [item.user_id for item in items]
    sellers = list_users_by_ids(db, seller_ids)
    seller_map = {seller.id: seller for seller in sellers}
    response_items: list[AdminRefundSuccessItem] = []
    for item in items:
        seller = seller_map.get(item.user_id)
        if not seller:
            continue
        status_before_label = _humanize_admin_status_before_cancellation(item.status_before_cancellation)
        response_items.append(
            AdminRefundSuccessItem(
                request_id=item.id,
                listing_code=item.listing_code,
                seller_uid=seller.id,
                seller=_to_refund_seller_summary(seller),
                cancellation_reason=item.cancellation_reason or "",
                status_before_cancellation=item.status_before_cancellation,
                status_before_cancellation_label=status_before_label,
                cancellation_stage=status_before_label,
                cancelled_at=item.cancelled_at,
                refund_completed_at=item.refund_completed_at,
                refund_amount=item.refund_amount,
                refund_transaction_id=item.refund_transaction_id,
                status=item.status,
            )
        )
    return AdminRefundSuccessListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=response_items,
    )


def forward_refund_to_accounting(
    db: Session,
    current_user: User,
    request_id: int,
) -> tuple[AdminForwardRefundToAccountingResponse | None, str | None]:
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status != SellLandStatus.PROCESSING_REFUND.value:
        return None, "Only processing refund listings can be forwarded"
    if not entity.cancellation_requires_admin_review:
        return None, "This cancellation is direct to accounting and does not need admin forwarding"
    if current_user.role == UserRole.ADMIN.value and entity.reviewed_by_id != current_user.id:
        return None, "You can only forward refunds for your own verified listings"
    if entity.refund_forwarded_to_accounting_at is not None:
        return None, "Refund is already forwarded to accounting"

    entity.refund_forwarded_to_accounting_by_id = current_user.id
    entity.refund_forwarded_to_accounting_at = datetime.utcnow()
    db.commit()
    db.refresh(entity)
    return (
        AdminForwardRefundToAccountingResponse(
            status="Refund case forwarded to accounting",
            request_id=entity.id,
            forwarded_to_accounting_at=entity.refund_forwarded_to_accounting_at,
        ),
        None,
    )


def list_pending_refunds_for_accounting(
    db: Session,
    skip: int,
    limit: int,
) -> AccountingRefundPendingListResponse:
    items, total = list_pending_refund_cases_for_accounting(
        db=db,
        skip=skip,
        limit=limit,
    )
    seller_ids = [item.user_id for item in items]
    admin_ids = [
        item.refund_forwarded_to_accounting_by_id
        for item in items
        if item.refund_forwarded_to_accounting_by_id is not None
    ]
    users = list_users_by_ids(db, list({*seller_ids, *admin_ids}))
    user_map = {user.id: user for user in users}
    response_items: list[AccountingRefundPendingItem] = []
    for item in items:
        seller = user_map.get(item.user_id)
        if not seller:
            continue
        forwarding_admin = (
            user_map.get(item.refund_forwarded_to_accounting_by_id)
            if item.refund_forwarded_to_accounting_by_id is not None
            else None
        )
        admin_involved = bool(item.cancellation_requires_admin_review)
        admin_status = None
        if admin_involved:
            base_status = _humanize_admin_status_before_cancellation(item.status_before_cancellation)
            if forwarding_admin:
                admin_status = f"{base_status} (Forwarded to Accounting)"
            else:
                admin_status = base_status
        response_items.append(
            AccountingRefundPendingItem(
                request_id=item.id,
                listing_code=item.listing_code,
                seller_uid=seller.id,
                seller_fullname=seller.fullname,
                seller_mobile=seller.mobile,
                cancellation_reason=item.cancellation_reason or "",
                cancelled_at=item.cancelled_at,
                refund_due_at=item.refund_due_at,
                refund_upi_id=item.refund_upi_id,
                total_paid=item.payment_required_amount,
                admin_involved=admin_involved,
                admin_name=forwarding_admin.fullname if forwarding_admin else None,
                admin_mobile=forwarding_admin.mobile if forwarding_admin else None,
                admin_status=admin_status,
            )
        )
    return AccountingRefundPendingListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=response_items,
    )


def list_refund_history_for_accounting_panel(
    db: Session,
    skip: int,
    limit: int,
) -> AccountingRefundHistoryListResponse:
    items, total = list_refund_history_for_accounting(
        db=db,
        skip=skip,
        limit=limit,
    )
    seller_ids = [item.user_id for item in items]
    admin_ids = [
        item.refund_forwarded_to_accounting_by_id
        for item in items
        if item.refund_forwarded_to_accounting_by_id is not None
    ]
    users = list_users_by_ids(db, list({*seller_ids, *admin_ids}))
    user_map = {user.id: user for user in users}
    response_items: list[AccountingRefundHistoryItem] = []
    for item in items:
        seller = user_map.get(item.user_id)
        if not seller:
            continue
        forwarding_admin = (
            user_map.get(item.refund_forwarded_to_accounting_by_id)
            if item.refund_forwarded_to_accounting_by_id is not None
            else None
        )
        admin_status = None
        if item.cancellation_requires_admin_review:
            base_status = _humanize_admin_status_before_cancellation(item.status_before_cancellation)
            if forwarding_admin:
                admin_status = f"{base_status} (Forwarded to Accounting)"
            else:
                admin_status = base_status
        response_items.append(
            AccountingRefundHistoryItem(
                request_id=item.id,
                listing_code=item.listing_code,
                seller_uid=seller.id,
                seller_fullname=seller.fullname,
                seller_mobile=seller.mobile,
                cancellation_reason=item.cancellation_reason or "",
                cancelled_at=item.cancelled_at,
                refund_upi_id=item.refund_upi_id,
                refund_completed_at=item.refund_completed_at,
                total_paid=item.payment_required_amount,
                admin_involved=bool(item.cancellation_requires_admin_review),
                admin_name=forwarding_admin.fullname if forwarding_admin else None,
                admin_mobile=forwarding_admin.mobile if forwarding_admin else None,
                admin_status=admin_status,
                refund_amount=item.refund_amount,
                refund_transaction_id=item.refund_transaction_id,
                status=item.status,
            )
        )
    return AccountingRefundHistoryListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=response_items,
    )


def confirm_refund_by_accounting(
    db: Session,
    request_id: int,
    payload: AccountingConfirmRefundRequest | None = None,
    confirmed_by_id: int | None = None,
) -> tuple[AccountingConfirmRefundResponse | None, str | None]:
    entity = get_sell_land_request_by_id(db, request_id)
    if not entity:
        return None, "Sell land request not found"
    if entity.status != SellLandStatus.PROCESSING_REFUND.value:
        return None, "Only processing refund listings can be marked as refunded"
    if entity.cancellation_requires_admin_review and entity.refund_forwarded_to_accounting_at is None:
        return None, "Admin forwarding is required before accounting can confirm this refund"

    entity.status = SellLandStatus.REFUND_SUCCESSFUL.value
    entity.refund_completed_at = datetime.utcnow()
    entity.refund_amount = payload.refund_amount if payload and payload.refund_amount is not None else entity.payment_required_amount
    entity.refund_transaction_id = payload.transaction_id if payload else None
    entity.refund_confirmed_by_id = confirmed_by_id
    db.commit()
    db.refresh(entity)
    return (
        AccountingConfirmRefundResponse(
            status="Refund marked successful",
            request_id=entity.id,
            listing_status=entity.status,
            refund_completed_at=entity.refund_completed_at,
            refund_amount=entity.refund_amount,
            refund_transaction_id=entity.refund_transaction_id,
        ),
        None,
    )
