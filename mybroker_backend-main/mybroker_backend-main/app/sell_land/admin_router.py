from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.sell_land.admin_schemas import (
    AccountingConfirmRefundRequest,
    AccountingConfirmRefundResponse,
    AccountingRefundHistoryListResponse,
    AccountingRefundPendingListResponse,
    AccountingCompletedTransactionListResponse,
    AccountingCompletedTransactionDetailResponse,
    AccountingDashboardSummaryResponse,
    RevenueRangeType,
    SuperAdminRevenueDashboardResponse,
    AdminAssignCaseRequest,
    AdminAssignCaseResponse,
    AdminCaseAssignmentBoardResponse,
    AdminDashboardWorkflowSummary,
    AdminBookedListingListResponse,
    AdminBookedListingDetailResponse,
    AdminBookingFieldOfficerUpdateRequest,
    AdminBookingFieldOfficerUpdateResponse,
    AdminRegistryScheduleRequest,
    AdminRegistryScheduleResponse,
    AdminRegistryVerificationRequest,
    AdminRegistryVerificationResponse,
    AdminRegistryPendingListResponse,
    AdminForwardRefundToAccountingResponse,
    AdminFieldOfficerOption,
    AdminFieldVerifiedCaseListResponse,
    AdminFinalApprovalActionRequest,
    AdminFinalApprovalActionResponse,
    AdminForceReleaseCaseResponse,
    AdminForceReleaseOfferLockResponse,
    AdminLockedListingListResponse,
    AdminRefundMarkPaidResponse,
    AdminRefundQueueListResponse,
    AdminRefundSuccessListResponse,
    AdminReviewActionRequest,
    AdminReviewActionResponse,
    AdminInstagramUrlUpdateRequest,
    AdminInstagramUrlUpdateResponse,
    AdminSellLandReviewDetail,
    AdminSellLandReviewListResponse,
)
from app.sell_land.admin_service import (
    assign_case_to_field_officer,
    confirm_refund_by_accounting,
    forward_refund_to_accounting,
    force_release_case_lock,
    force_release_offer_lock,
    get_case_assignment_board,
    get_admin_dashboard_workflow_summary,
    get_request_for_review,
    get_booked_listing_detail,
    update_booking_field_officer,
    schedule_registry,
    verify_registry,
    list_pending_registry_verification,
    list_booked_listings,
    list_sold_listings,
    list_locked_offer_listings,
    list_pending_refunds_for_accounting,
    list_pending_refunds_for_admin,
    list_success_refunds_for_admin,
    list_refund_history_for_accounting_panel,
    list_completed_transactions_for_accounting_panel,
    get_completed_transaction_detail,
    get_accounting_dashboard_summary_service,
    get_super_admin_revenue_dashboard,
    list_field_verified_cases_for_final_approval,
    list_assignable_field_officers,
    list_requests_for_review,
    mark_refund_paid_by_admin,
    take_final_approval_action,
    review_request,
    update_listing_instagram_url,
)
from app.sell_land.constants import SellLandStatus
from app.users.model import User
from app.users.roles import UserRole

router = APIRouter(prefix="/admin/sell-land", tags=["Admin Sell Land Review"])


@router.get("/dashboard/workflow-summary", response_model=AdminDashboardWorkflowSummary)
def get_dashboard_workflow_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return get_admin_dashboard_workflow_summary(db, current_user)


@router.get("/field-officers", response_model=list[AdminFieldOfficerOption])
def get_available_field_officers(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_assignable_field_officers(db)


@router.get("/cases/assignment-board", response_model=AdminCaseAssignmentBoardResponse)
def get_assignment_board(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return get_case_assignment_board(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.post("/cases/{request_id}/force-release", response_model=AdminForceReleaseCaseResponse)
def force_release_case(
    request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    response, error = force_release_case_lock(db=db, request_id=request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only approved listings can be force released",
        "Case already reviewed by field officer",
        "Case is not locked",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/locked-listings", response_model=AdminLockedListingListResponse)
def list_locked_listings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_locked_offer_listings(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get("/booked-listings", response_model=AdminBookedListingListResponse)
def list_booked_listings_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_booked_listings(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get("/sold-listings", response_model=AdminBookedListingListResponse)
def list_sold_listings_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_sold_listings(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get("/booked-listings/{request_id}", response_model=AdminBookedListingDetailResponse)
def get_booked_listing_detail_endpoint(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    response, error = get_booked_listing_detail(
        db=db,
        current_user=current_user,
        request_id=request_id,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Listing is not booked",
        "You can only view booked listings verified by you",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.patch("/bookings/{booking_id}/field-officer", response_model=AdminBookingFieldOfficerUpdateResponse)
def update_booking_field_officer_endpoint(
    booking_id: int,
    payload: AdminBookingFieldOfficerUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    response, error = update_booking_field_officer(
        db=db,
        current_user=current_user,
        booking_id=booking_id,
        payload=payload,
    )
    if error in {"Booking not found", "Sell land request not found", "Field officer not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Listing is not booked",
        "You can only update bookings verified by you",
        "Selected user is not a field officer",
        "Field officer is inactive",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.patch("/bookings/{booking_id}/registry-schedule", response_model=AdminRegistryScheduleResponse)
def schedule_registry_endpoint(
    booking_id: int,
    payload: AdminRegistryScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    response, error = schedule_registry(
        db=db,
        current_user=current_user,
        booking_id=booking_id,
        payload=payload,
    )
    if error in {"Booking not found", "Sell land request not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {"Listing is not booked", "You can only update bookings verified by you"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.patch("/bookings/{booking_id}/registry-verify", response_model=AdminRegistryVerificationResponse)
def verify_registry_endpoint(
    booking_id: int,
    payload: AdminRegistryVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    response, error = verify_registry(
        db=db,
        current_user=current_user,
        booking_id=booking_id,
        payload=payload,
    )
    if error in {"Booking not found", "Sell land request not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Listing is not booked",
        "You can only update bookings verified by you",
        "Registry is not marked completed",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/bookings/registry-pending", response_model=AdminRegistryPendingListResponse)
def list_registry_pending_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_pending_registry_verification(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.post("/locked-listings/{request_id}/force-release", response_model=AdminForceReleaseOfferLockResponse)
def force_release_locked_listing(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    response, error = force_release_offer_lock(db=db, current_user=current_user, request_id=request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only live listings can be force released",
        "Listing is not locked",
        "You can only release locks for your own verified listings",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/cases/{request_id}/assign", response_model=AdminAssignCaseResponse)
def assign_case(
    request_id: int,
    payload: AdminAssignCaseRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    response, error = assign_case_to_field_officer(
        db=db,
        request_id=request_id,
        payload=payload,
    )
    if error == "Sell land request not found" or error == "Field officer not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Selected user is not a field officer",
        "Field officer is inactive",
        "Selected field officer already has an active locked case",
        "Only approved listings can be assigned",
        "Case already reviewed by field officer",
        "Case is already locked by another field officer",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/final-approval", response_model=AdminFieldVerifiedCaseListResponse)
def list_final_approval_cases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_field_verified_cases_for_final_approval(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.patch("/final-approval/{request_id}/action", response_model=AdminFinalApprovalActionResponse)
def final_approval_action(
    request_id: int,
    payload: AdminFinalApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    response, error = take_final_approval_action(
        db=db,
        current_user=current_user,
        request_id=request_id,
        payload=payload,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only field verified listings can be processed in final approval",
        "Only field officer approved listings can be processed in final approval",
        "You can only process your own verified listings",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error == "rejection_reason is required when decision is reject":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.patch("/requests/{request_id}/refund/mark-paid", response_model=AdminRefundMarkPaidResponse)
def mark_refund_paid(
    request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    response, error = mark_refund_paid_by_admin(
        db=db,
        request_id=request_id,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Only processing refund listings can be marked as refunded":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/refunds/pending-admin", response_model=AdminRefundQueueListResponse)
def list_pending_admin_refunds(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_pending_refunds_for_admin(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.patch("/refunds/{request_id}/forward-accounting", response_model=AdminForwardRefundToAccountingResponse)
def forward_case_to_accounting(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    response, error = forward_refund_to_accounting(
        db=db,
        current_user=current_user,
        request_id=request_id,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only processing refund listings can be forwarded",
        "This cancellation is direct to accounting and does not need admin forwarding",
        "Refund is already forwarded to accounting",
        "You can only forward refunds for your own verified listings",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/refunds/success", response_model=AdminRefundSuccessListResponse)
def list_success_admin_refunds(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_success_refunds_for_admin(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get("/accounting/refunds/pending", response_model=AccountingRefundPendingListResponse)
def list_accounting_pending_refunds(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTING)),
):
    return list_pending_refunds_for_accounting(
        db=db,
        skip=skip,
        limit=limit,
    )


@router.get("/accounting/refunds/history", response_model=AccountingRefundHistoryListResponse)
def list_accounting_refund_history(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTING)),
):
    return list_refund_history_for_accounting_panel(
        db=db,
        skip=skip,
        limit=limit,
    )


@router.get("/accounting/transactions/completed", response_model=AccountingCompletedTransactionListResponse)
def list_accounting_completed_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTING)),
):
    return list_completed_transactions_for_accounting_panel(
        db=db,
        skip=skip,
        limit=limit,
    )


@router.get("/accounting/transactions/{listing_id}", response_model=AccountingCompletedTransactionDetailResponse)
def get_accounting_completed_transaction(
    listing_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTING)),
):
    response, error = get_completed_transaction_detail(db=db, listing_id=listing_id)
    if error == "Completed transaction not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/accounting/dashboard/summary", response_model=AccountingDashboardSummaryResponse)
def get_accounting_dashboard_summary(
    range_type: RevenueRangeType = Query(default=RevenueRangeType.MONTH, alias="range"),
    start_date: date | None = Query(default=None, alias="start"),
    end_date: date | None = Query(default=None, alias="end"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTING)),
):
    return get_accounting_dashboard_summary_service(
        db=db,
        range_type=range_type,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/super-admin/dashboard/revenue", response_model=SuperAdminRevenueDashboardResponse)
def get_super_admin_revenue(
    range_type: RevenueRangeType = Query(default=RevenueRangeType.MONTH, alias="range"),
    start_date: date | None = Query(default=None, alias="start"),
    end_date: date | None = Query(default=None, alias="end"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    return get_super_admin_revenue_dashboard(
        db=db,
        range_type=range_type,
        start_date=start_date,
        end_date=end_date,
    )


@router.patch("/accounting/refunds/{request_id}/confirm", response_model=AccountingConfirmRefundResponse)
def confirm_refund(
    request_id: int,
    payload: AccountingConfirmRefundRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTING)),
):
    response, error = confirm_refund_by_accounting(
        db=db,
        request_id=request_id,
        payload=payload,
        confirmed_by_id=current_user.id,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only processing refund listings can be marked as refunded",
        "Admin forwarding is required before accounting can confirm this refund",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/requests", response_model=AdminSellLandReviewListResponse)
def list_requests(
    status_filter: SellLandStatus = Query(default=SellLandStatus.PENDING, alias="status"),
    search: str | None = Query(default=None, min_length=2, max_length=100),
    listing_id: int | None = Query(default=None),
    state: str | None = Query(default=None, min_length=2, max_length=100),
    district: str | None = Query(default=None, min_length=2, max_length=100),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_requests_for_review(
        db=db,
        current_user=current_user,
        status_filter=status_filter,
        search=search,
        state_filter=state,
        city_filter=district,
        skip=skip,
        limit=limit,
        listing_id=listing_id,
    )


@router.get("/requests/all", response_model=AdminSellLandReviewListResponse)
def list_all_requests(
    status_filter: SellLandStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, min_length=2, max_length=100),
    listing_id: int | None = Query(default=None),
    state: str | None = Query(default=None, min_length=2, max_length=100),
    district: str | None = Query(default=None, min_length=2, max_length=100),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_requests_for_review(
        db=db,
        current_user=current_user,
        status_filter=status_filter,
        search=search,
        state_filter=state,
        city_filter=district,
        skip=skip,
        limit=limit,
        listing_id=listing_id,
    )


@router.get("/requests/{request_id}", response_model=AdminSellLandReviewDetail)
def get_request_details(
    request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    detail, error = get_request_for_review(db, request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return detail


@router.patch("/requests/{request_id}/instagram", response_model=AdminInstagramUrlUpdateResponse)
def update_listing_instagram_url_endpoint(
    request_id: int,
    payload: AdminInstagramUrlUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    response = update_listing_instagram_url(db, request_id, payload.instagram_url)
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sell land request not found")
    return response


@router.patch("/requests/{request_id}/review", response_model=AdminReviewActionResponse)
def review_listing_request(
    request_id: int,
    payload: AdminReviewActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    entity, error = review_request(db, request_id, current_user, payload)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Only submitted listings can be reviewed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error == "rejection_reason is required when decision is rejected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    status_message = "Listing reviewed successfully"
    if entity.status == SellLandStatus.APPROVED.value:
        status_message = "Documents verified and forwarded to field officer"

    return AdminReviewActionResponse(
        status=status_message,
        request_id=entity.id,
        listing_status=entity.status,
        reviewed_by_id=entity.reviewed_by_id,
        reviewed_at=entity.reviewed_at,
        rejection_reason=entity.rejection_reason,
    )
