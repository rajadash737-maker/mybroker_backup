from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.site_visits.schemas import (
    SiteVisitBookingResponse,
    SiteVisitCancelRequest,
    SiteVisitCancelResponse,
    SiteVisitFeeResponse,
    SiteVisitRequestCreate,
    SiteVisitPaymentOrderResponse,
    SiteVisitPaymentAttemptResponse,
    SiteVisitVerifyPaymentRequest,
    SiteVisitVerifyPaymentResponse,
    AdminSiteVisitDetailResponse,
    AdminSiteVisitListResponse,
    AdminSiteVisitOfficerResponse,
    AdminSiteVisitSummaryResponse,
    AdminSiteVisitAssignmentRequest,
    AdminSiteVisitUnassignmentRequest,
    AdminSiteVisitAssignmentMutationResponse,
    SiteVisitCompletionCodeVerifyRequest,
    SiteVisitLifecycleResponse,
    FieldOfficerSiteVisitResponse,
    SiteVisitAdminActionRequest,
    SiteVisitAdminActionResponse,
    SiteVisitCorrectionResponseRequest,
    BuyerSiteVisitRefundDetailsRequest,
    SiteVisitAccountingRefundSummary,
    SiteVisitAccountingRefundList,
    SiteVisitRefundConfirmRequest,
    SiteVisitRefundFailureRequest,
    SiteVisitRefundActionResponse,
    SuperAdminSiteVisitAuditSummary,
    SuperAdminSiteVisitAuditList,
    SuperAdminSiteVisitAuditDetail,
)
from app.site_visits.payment_service import (
    cancel_site_visit_payment_attempt,
    create_site_visit_order,
    verify_site_visit_payment,
)
from app.site_visits.service import (
    cancel_my_site_visit,
    create_site_visit_request,
    get_site_visit_fee,
    list_my_site_visits,
    list_admin_site_visits,
    get_admin_site_visit,
    list_eligible_site_visit_field_officers,
    get_admin_site_visit_summary,
    mutate_admin_site_visit_assignment,
    start_site_visit,
    initiate_site_visit_completion,
    verify_site_visit_completion,
    list_field_officer_site_visits,
    request_site_visit_correction,
    resubmit_site_visit_correction,
    cancel_site_visit_by_admin,
    get_super_admin_site_visit_audit_summary,
    list_super_admin_site_visit_audit,
    get_super_admin_site_visit_audit_detail,
)
from app.site_visits.constants import SiteVisitStatus
from app.site_visits.refund_crypto import RefundEncryptionConfigurationError
from app.site_visits.refund_service import (
    RefundUPIDecryptionError,
    submit_site_visit_refund_details,
    get_site_visit_accounting_summary,
    list_site_visit_accounting_refunds,
    confirm_site_visit_refund,
    fail_site_visit_refund,
)
from app.users.model import User
from app.users.roles import UserRole


router = APIRouter(prefix="/site-visits", tags=["Site Visits"])
buyer_dependency = require_roles(UserRole.CUSTOMER)
admin_dependency = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
field_officer_dependency = require_roles(UserRole.FIELD_OFFICER)
accounting_dependency = require_roles(UserRole.ACCOUNTING)
super_admin_dependency = require_roles(UserRole.SUPER_ADMIN)


@router.get("/super-admin/audit/summary", response_model=SuperAdminSiteVisitAuditSummary)
def super_admin_site_visit_audit_summary_endpoint(
    db: Session = Depends(get_db), _: User = Depends(super_admin_dependency),
):
    return get_super_admin_site_visit_audit_summary(db)


@router.get("/super-admin/audit/bookings", response_model=SuperAdminSiteVisitAuditList)
def super_admin_site_visit_audit_list_endpoint(
    db: Session = Depends(get_db), _: User = Depends(super_admin_dependency),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=25, ge=1, le=100),
    date_from: date | None = Query(default=None), date_to: date | None = Query(default=None),
    booking_id: int | None = Query(default=None, gt=0), listing_id: int | None = Query(default=None, gt=0),
    listing_code: str | None = Query(default=None, min_length=1, max_length=80),
    buyer_search: str | None = Query(default=None, min_length=1, max_length=120),
    officer_id: int | None = Query(default=None, gt=0), admin_id: int | None = Query(default=None, gt=0),
    officer_search: str | None = Query(default=None, min_length=1, max_length=120),
    accounting_id: int | None = Query(default=None, gt=0),
    reference_search: str | None = Query(default=None, min_length=1, max_length=120),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be on or before date_to")
    return list_super_admin_site_visit_audit(db, skip=skip, limit=limit, date_from=date_from, date_to=date_to,
        booking_id=booking_id, listing_id=listing_id, listing_code=listing_code, buyer_search=buyer_search,
        officer_id=officer_id, officer_search=officer_search, admin_id=admin_id, accounting_id=accounting_id, reference_search=reference_search)


@router.get("/super-admin/audit/bookings/{booking_id}", response_model=SuperAdminSiteVisitAuditDetail)
def super_admin_site_visit_audit_detail_endpoint(
    booking_id: int, db: Session = Depends(get_db), _: User = Depends(super_admin_dependency),
):
    result = get_super_admin_site_visit_audit_detail(db, request_id=booking_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Site Visit booking not found")
    return result


@router.get("/field-officer/my-visits", response_model=list[FieldOfficerSiteVisitResponse])
def list_field_officer_site_visits_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(field_officer_dependency),
):
    return list_field_officer_site_visits(db, officer_id=current_user.id)


def _field_officer_lifecycle_error(error: str | None) -> None:
    if not error:
        return
    if error == "Site Visit request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Only the assigned active Field Officer can perform this action":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
    if error == "Site Visit completion-code service is unavailable":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Completion service is temporarily unavailable. Please try again later.",
        )
    if error in {
        "Site Visit completion could not be initiated",
        "Site Visit completion could not be verified",
    }:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Completion could not be processed. Please retry shortly.",
        )
    code = status.HTTP_429_TOO_MANY_REQUESTS if "locked" in error else status.HTTP_409_CONFLICT
    raise HTTPException(status_code=code, detail=error)


@router.post("/field-officer/{booking_id}/start", response_model=SiteVisitLifecycleResponse)
def start_site_visit_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(field_officer_dependency),
):
    result, error = start_site_visit(db, request_id=booking_id, officer_id=current_user.id)
    _field_officer_lifecycle_error(error)
    return result


@router.post("/field-officer/{booking_id}/completion-code", response_model=SiteVisitLifecycleResponse)
def initiate_site_visit_completion_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(field_officer_dependency),
):
    result, error = initiate_site_visit_completion(db, request_id=booking_id, officer_id=current_user.id)
    _field_officer_lifecycle_error(error)
    return result


@router.post("/field-officer/{booking_id}/verify-completion", response_model=SiteVisitLifecycleResponse)
def verify_site_visit_completion_endpoint(
    booking_id: int,
    payload: SiteVisitCompletionCodeVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(field_officer_dependency),
):
    result, error = verify_site_visit_completion(
        db, request_id=booking_id, officer_id=current_user.id, code=payload.completion_code
    )
    _field_officer_lifecycle_error(error)
    return result


@router.get("/admin", response_model=AdminSiteVisitListResponse)
def list_admin_site_visits_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    request_status: str | None = Query(default=None, alias="status"),
    assigned_field_officer_id: int | None = Query(default=None, gt=0),
    preferred_date_from: date | None = Query(default=None),
    preferred_date_to: date | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=120),
):
    allowed_statuses = {item.value for item in SiteVisitStatus if item != SiteVisitStatus.PENDING_PAYMENT}
    if request_status is not None and request_status not in allowed_statuses:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported paid Site Visit status")
    if preferred_date_from and preferred_date_to and preferred_date_from > preferred_date_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="preferred_date_from must be on or before preferred_date_to")
    return list_admin_site_visits(
        db,
        skip=skip,
        limit=limit,
        request_status=request_status,
        assigned_field_officer_id=assigned_field_officer_id,
        preferred_date_from=preferred_date_from,
        preferred_date_to=preferred_date_to,
        search=search,
        actor=current_user,
    )


@router.get("/admin/summary", response_model=AdminSiteVisitSummaryResponse)
def admin_site_visit_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    return get_admin_site_visit_summary(db, actor=current_user)


@router.get("/admin/field-officers", response_model=list[AdminSiteVisitOfficerResponse])
def admin_site_visit_field_officers_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(admin_dependency),
):
    return list_eligible_site_visit_field_officers(db)


@router.get("/admin/{request_id}", response_model=AdminSiteVisitDetailResponse)
def get_admin_site_visit_endpoint(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    result = get_admin_site_visit(db, request_id=request_id, actor=current_user)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paid Site Visit request not found")
    return result


@router.post("/admin/{request_id}/correction", response_model=SiteVisitAdminActionResponse)
def request_site_visit_correction_endpoint(
    request_id: int,
    payload: SiteVisitAdminActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    result, error = request_site_visit_correction(db, request_id=request_id, actor=current_user, payload=payload)
    if error == "Paid Site Visit request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return result


@router.post("/admin/{request_id}/cancel", response_model=SiteVisitAdminActionResponse)
def cancel_site_visit_by_admin_endpoint(
    request_id: int,
    payload: SiteVisitAdminActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    result, error = cancel_site_visit_by_admin(db, request_id=request_id, actor=current_user, payload=payload)
    if error == "Paid Site Visit request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return result


@router.put(
    "/admin/{request_id}/assignment",
    response_model=AdminSiteVisitAssignmentMutationResponse,
)
def assign_admin_site_visit_endpoint(
    request_id: int,
    payload: AdminSiteVisitAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    result, error = mutate_admin_site_visit_assignment(
        db,
        request_id=request_id,
        actor=current_user,
        field_officer_id=payload.field_officer_id,
        note=payload.note,
    )
    if error == "Site Visit request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Field Officer is not eligible for assignment":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return result


@router.delete(
    "/admin/{request_id}/assignment",
    response_model=AdminSiteVisitAssignmentMutationResponse,
)
def unassign_admin_site_visit_endpoint(
    request_id: int,
    payload: AdminSiteVisitUnassignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    result, error = mutate_admin_site_visit_assignment(
        db,
        request_id=request_id,
        actor=current_user,
        field_officer_id=None,
        note=payload.note,
    )
    if error == "Site Visit request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return result


@router.get("/fee", response_model=SiteVisitFeeResponse)
def get_site_visit_fee_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(buyer_dependency),
):
    return get_site_visit_fee(db)


@router.post("", response_model=SiteVisitBookingResponse, status_code=status.HTTP_201_CREATED)
def create_site_visit_endpoint(
    payload: SiteVisitRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(buyer_dependency),
):
    response, error = create_site_visit_request(db, buyer=current_user, payload=payload)
    if error == "Listing not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only live listings can receive Site Visit requests",
        "You cannot request a Site Visit for your own listing",
        "Duplicate Site Visit submission",
        "Submission key was already used for a different Site Visit request",
        "An active Site Visit request already exists for this listing",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error == "Listing seller not found":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error == "A registered mobile number is required to request a Site Visit":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)
    if error == "Preferred visit date cannot be in the past":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/my-bookings", response_model=list[SiteVisitBookingResponse])
def get_my_site_visits_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(buyer_dependency),
):
    return list_my_site_visits(db, buyer_id=current_user.id)


@router.post("/{booking_id}/cancel", response_model=SiteVisitCancelResponse)
def cancel_my_site_visit_endpoint(
    booking_id: int,
    payload: SiteVisitCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(buyer_dependency),
):
    response, error = cancel_my_site_visit(
        db,
        buyer_id=current_user.id,
        booking_id=booking_id,
        payload=payload,
    )
    if error == "Site Visit request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "This Site Visit request can no longer be cancelled by the buyer":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/{booking_id}/correction-response", response_model=SiteVisitBookingResponse)
def resubmit_site_visit_correction_endpoint(
    booking_id: int,
    payload: SiteVisitCorrectionResponseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(buyer_dependency),
):
    response, error = resubmit_site_visit_correction(db, request_id=booking_id, actor=current_user, payload=payload)
    if error == "Site Visit request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return response


@router.post("/{booking_id}/refund-details")
def submit_site_visit_refund_details_endpoint(
    booking_id: int,
    payload: BuyerSiteVisitRefundDetailsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(buyer_dependency),
):
    try:
        result, error = submit_site_visit_refund_details(db, booking_id=booking_id, buyer_id=current_user.id, payload=payload)
    except RefundEncryptionConfigurationError:
          raise HTTPException(
              status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
              detail="Refund details could not be saved securely. Your booking remains cancelled and refund details are still required; try again later or contact support.",
          ) from None
    except RefundUPIDecryptionError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored refund details could not be decrypted") from None
    if error == "Site Visit request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return result


@router.get("/accounting/summary", response_model=SiteVisitAccountingRefundSummary)
def site_visit_accounting_summary_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(accounting_dependency),
):
    return get_site_visit_accounting_summary(db)


@router.get("/accounting/refunds", response_model=SiteVisitAccountingRefundList)
def list_site_visit_accounting_refunds_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(accounting_dependency),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    refund_status: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, min_length=1, max_length=120),
):
    allowed = {"pending_details", "pending", "refunded", "failed"}
    if refund_status is not None and refund_status not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported refund status")
    try:
        return list_site_visit_accounting_refunds(db, skip=skip, limit=limit, status_filter=refund_status, search=search)
    except RefundEncryptionConfigurationError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Refund detail encryption is not configured") from None
    except RefundUPIDecryptionError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored refund details could not be decrypted") from None


@router.post("/accounting/refunds/{refund_id}/confirm", response_model=SiteVisitRefundActionResponse)
def confirm_site_visit_accounting_refund_endpoint(
    refund_id: int,
    payload: SiteVisitRefundConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(accounting_dependency),
):
    result, error = confirm_site_visit_refund(db, refund_id=refund_id, actor=current_user, payload=payload)
    if error == "Site Visit refund not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return result


@router.post("/accounting/refunds/{refund_id}/fail", response_model=SiteVisitRefundActionResponse)
def fail_site_visit_accounting_refund_endpoint(
    refund_id: int,
    payload: SiteVisitRefundFailureRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(accounting_dependency),
):
    result, error = fail_site_visit_refund(db, refund_id=refund_id, actor=current_user, payload=payload)
    if error == "Site Visit refund not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return result


@router.post("/{booking_id}/payment-order", response_model=SiteVisitPaymentOrderResponse)
def create_site_visit_payment_order_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(buyer_dependency),
):
    response, error = create_site_visit_order(db, booking_id=booking_id, buyer_id=current_user.id)
    if error == "Site Visit request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Payment gateway is not configured":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return response


@router.post("/{booking_id}/verify-payment", response_model=SiteVisitVerifyPaymentResponse)
def verify_site_visit_payment_endpoint(
    booking_id: int,
    payload: SiteVisitVerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(buyer_dependency),
):
    # The booking ID in the path and the authenticated buyer are checked against
    # the order-linked request in the service; amount is intentionally absent.
    response, error = verify_site_visit_payment(
        db,
        payload,
        booking_id=booking_id,
        buyer_id=current_user.id,
    )
    if error == "Site Visit payment order not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Not authorized":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if response is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment verification failed")
    return response


@router.post("/{booking_id}/cancel-payment", response_model=SiteVisitPaymentAttemptResponse)
def cancel_site_visit_payment_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(buyer_dependency),
):
    response, error = cancel_site_visit_payment_attempt(db, booking_id=booking_id, buyer_id=current_user.id)
    if error == "Site Visit request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return response
