from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic import StringConstraints
from typing import Annotated

from app.site_visits.constants import site_visit_today


class SiteVisitRequestCreate(BaseModel):
    """Validated buyer-supplied booking fields; identity and fee come from server state."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    listing_id: int = Field(gt=0)
    preferred_visit_date: date
    preferred_visit_time: time
    visitor_count: int = Field(ge=1, le=20)
    pickup_address: str = Field(min_length=10, max_length=1000)
    message: str | None = Field(default=None, max_length=2000)
    submission_key: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("pickup_address")
    @classmethod
    def pickup_address_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("pickup_address must contain an address")
        return value

    @field_validator("preferred_visit_date")
    @classmethod
    def preferred_date_cannot_be_in_the_past(cls, value: date) -> date:
        if value < site_visit_today():
            raise ValueError("preferred_visit_date cannot be in the past")
        return value


class SiteVisitCancelRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason must contain text")
        return value


class SiteVisitAdminActionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason must contain text")
        return value


class SiteVisitCorrectionResponseRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    preferred_visit_date: date
    preferred_visit_time: time
    visitor_count: int = Field(ge=1, le=20)
    pickup_address: str = Field(min_length=10, max_length=1000)
    message: str | None = Field(default=None, max_length=2000)

    @field_validator("preferred_visit_date")
    @classmethod
    def preferred_date_cannot_be_in_the_past(cls, value: date) -> date:
        if value < site_visit_today():
            raise ValueError("preferred_visit_date cannot be in the past")
        return value

    @field_validator("pickup_address")
    @classmethod
    def pickup_address_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("pickup_address must contain an address")
        return value


class SiteVisitWorkflowHistoryItem(BaseModel):
    id: int
    event_type: str
    actor_id: int
    actor_role: str
    reason: str | None
    previous_values: dict | None
    updated_values: dict | None
    created_at: datetime


class SiteVisitAdminActionResponse(BaseModel):
    booking_id: int
    booking_status: str
    reason: str
    actor_id: int
    actor_role: str
    occurred_at: datetime


class BuyerSiteVisitRefundResponse(BaseModel):
    eligible: bool
    eligible_amount_paise: int
    status: str | None
    actual_refunded_amount_paise: int | None
    transaction_reference: str | None
    refunded_at: datetime | None


class SiteVisitFeeResponse(BaseModel):
    site_visit_fee_rupees: Decimal
    site_visit_fee_paise: int
    currency: str = "INR"


class SiteVisitBookingResponse(BaseModel):
    id: int
    listing_id: int
    listing_code: str | None
    property_name: str
    buyer_name: str
    buyer_mobile: str
    preferred_visit_date: date
    preferred_visit_time: time
    visitor_count: int
    pickup_address: str
    message: str | None
    booking_status: str
    payment_status: str
    site_visit_fee_rupees: Decimal
    site_visit_fee_paise: int
    cancellation_reason: str | None
    cancelled_at: datetime | None
    cancelled_by_role: str | None = None
    correction_reason: str | None = None
    correction_requested_at: datetime | None = None
    workflow_history: list[SiteVisitWorkflowHistoryItem] = Field(default_factory=list)
    refund: BuyerSiteVisitRefundResponse | None = None
    created_at: datetime
    # Returned only by the buyer-owned Status Card list endpoint.
    completion_code: str | None = None
    completion_code_expires_at: datetime | None = None


class SiteVisitCompletionCodeVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completion_code: Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]


class SiteVisitLifecycleResponse(BaseModel):
    booking_id: int
    booking_status: str
    started_at: datetime | None = None
    completion_code_expires_at: datetime | None = None


class SiteVisitCancelResponse(BaseModel):
    status: str
    booking_id: int
    booking_status: str
    cancellation_reason: str
    cancelled_at: datetime
    cancelled_by_role: str | None = None


class BuyerSiteVisitRefundDetailsRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    upi_id: Annotated[str, StringConstraints(min_length=4, max_length=120, pattern=r"^[A-Za-z0-9._-]{2,80}@[A-Za-z0-9.-]{2,40}$")]


class SiteVisitAccountingRefundSummary(BaseModel):
    total_site_visit_bookings: int
    paid_site_visits: int
    pending_payments: int
    cancelled_bookings: int
    refund_requests: int
    refund_pending: int
    refunded: int
    refund_failed: int
    site_visit_revenue_paise: int
    refund_amount_paise: int


class SiteVisitAccountingRefundItem(BaseModel):
    refund_id: int
    booking_id: int
    listing_id: int
    listing_code: str | None
    property_name: str
    buyer_name: str
    buyer_mobile: str
    preferred_visit_date: date
    preferred_visit_time: time
    fee_paise: int
    payment_status: str
    original_payment_reference: str | None
    cancellation_reason: str | None
    eligible_amount_paise: int
    actual_refunded_amount_paise: int | None
    buyer_upi_id: str | None
    transaction_reference: str | None
    status: str
    refunded_at: datetime | None
    accounting_user_id: int | None
    internal_note: str | None
    failure_reason: str | None
    created_at: datetime
    history: list[dict] = Field(default_factory=list)


class SiteVisitAccountingRefundList(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[SiteVisitAccountingRefundItem]


class SiteVisitRefundConfirmRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    actual_refunded_amount_paise: int = Field(gt=0)
    transaction_reference: str = Field(min_length=6, max_length=120)
    internal_note: str | None = Field(default=None, max_length=500)


class SiteVisitRefundFailureRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    reason: str = Field(min_length=3, max_length=500)


class SiteVisitRefundActionResponse(BaseModel):
    refund_id: int
    booking_id: int
    status: str
    actual_refunded_amount_paise: int | None
    transaction_reference: str | None
    accounting_user_id: int
    occurred_at: datetime
    idempotent: bool = False


class SiteVisitPaymentOrderResponse(BaseModel):
    booking_id: int
    order_id: str
    amount_paise: int
    currency: str
    payment_status: str


class SiteVisitVerifyPaymentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    razorpay_order_id: str = Field(min_length=5, max_length=64)
    razorpay_payment_id: str = Field(min_length=5, max_length=64)
    razorpay_signature: str = Field(min_length=5, max_length=256)


class SiteVisitVerifyPaymentResponse(BaseModel):
    status: str
    order_id: str
    payment_id: str


class SiteVisitPaymentAttemptResponse(BaseModel):
    booking_id: int
    order_id: str
    payment_status: str


class AdminSiteVisitOfficerResponse(BaseModel):
    id: int
    fullname: str | None


class AdminSiteVisitListItem(BaseModel):
    id: int
    listing_id: int
    listing_code: str | None
    property_name: str
    buyer_name: str
    buyer_mobile: str
    preferred_visit_date: date
    preferred_visit_time: time
    visitor_count: int
    status: str
    payment_status: str
    site_visit_fee_rupees: Decimal
    paid_at: datetime | None
    assigned_field_officer: AdminSiteVisitOfficerResponse | None
    created_at: datetime


class AdminSiteVisitListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminSiteVisitListItem]


class SiteVisitBoundaryPoint(BaseModel):
    """Registered listing boundary coordinate shared with its assigned officer."""

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class FieldOfficerSiteVisitResponse(BaseModel):
    """Safe visit details for the authenticated officer's own assignments."""

    id: int
    listing_id: int
    listing_code: str | None
    land_boundary_points: list[SiteVisitBoundaryPoint] = Field(default_factory=list)
    property_name: str
    buyer_name: str
    buyer_mobile: str
    preferred_visit_date: date
    preferred_visit_time: time
    visitor_count: int
    pickup_address: str
    message: str | None
    status: str
    payment_status: str
    site_visit_fee_rupees: Decimal
    started_at: datetime | None
    completed_at: datetime | None
    assigned_at: datetime | None
    assignment_note: str | None


class AdminSiteVisitAssignmentHistoryItem(BaseModel):
    id: int
    action: str
    actor_type: str
    actor: AdminSiteVisitOfficerResponse | None
    previous_field_officer: AdminSiteVisitOfficerResponse | None
    field_officer: AdminSiteVisitOfficerResponse | None
    note: str | None
    created_at: datetime


class AdminSiteVisitPropertyResponse(BaseModel):
    id: int
    listing_code: str | None
    title: str | None
    status: str
    city: str | None
    state: str | None
    location: str | None
    field_officer_decision: str | None
    field_officer_reviewed_at: datetime | None
    verified_by: AdminSiteVisitOfficerResponse | None


class AdminSiteVisitSellerResponse(BaseModel):
    name: str | None
    mobile: str | None


class AdminSiteVisitDetailResponse(AdminSiteVisitListItem):
    pickup_address: str
    message: str | None
    completed_at: datetime | None
    started_at: datetime | None
    scheduled_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    cancelled_by_id: int | None = None
    cancellation_actor_role: str | None = None
    correction_reason: str | None = None
    workflow_history: list[SiteVisitWorkflowHistoryItem] = Field(default_factory=list)
    property: AdminSiteVisitPropertyResponse | None
    assignment_history: list[AdminSiteVisitAssignmentHistoryItem]


class AdminSiteVisitSummaryResponse(BaseModel):
    total_paid: int
    pending: int
    assigned: int
    scheduled: int
    in_progress: int
    completed: int
    cancelled: int
    refund_pending: int
    refunded: int
    refund_failed: int


class SuperAdminSiteVisitAuditSummary(BaseModel):
    total_bookings: int
    paid_bookings: int
    unpaid_bookings: int
    pending_admin_review: int
    assigned: int
    in_progress: int
    completed: int
    cancelled: int
    correction_requests: int
    refund_pending: int
    refunded_amount_paise: int
    failed_refunds: int
    notification_events: int


class SuperAdminSiteVisitAuditListItem(AdminSiteVisitListItem):
    seller_name: str
    payment_order_id: str | None
    payment_id: str | None


class SuperAdminSiteVisitAuditList(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[SuperAdminSiteVisitAuditListItem]


class SuperAdminSiteVisitAuditDetail(SuperAdminSiteVisitAuditListItem):
    pickup_address: str
    message: str | None
    paid_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    cancellation_actor_role: str | None
    assignment_history: list[AdminSiteVisitAssignmentHistoryItem]
    workflow_history: list[SiteVisitWorkflowHistoryItem]
    payment_history: list[dict]
    refund_history: list[dict]
    notification_history: list[dict]


class AdminSiteVisitAssignmentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    field_officer_id: int = Field(gt=0)
    note: str | None = Field(default=None, min_length=3, max_length=500)


class AdminSiteVisitUnassignmentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    note: str | None = Field(default=None, min_length=3, max_length=500)


class AdminSiteVisitAssignmentMutationResponse(BaseModel):
    request_id: int
    status: str
    action: str
    previous_field_officer_id: int | None
    field_officer_id: int | None
    actor_id: int
    actor_type: str
    note: str | None
    created_at: datetime
