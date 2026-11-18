from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.media.url_utils import to_public_url
from app.sell_land.constants import (
    AreaUnit,
    Availability,
    DocumentType,
    LandType,
    MediaType,
    OfferStatus,
    OwnershipType,
    SellerCategory,
    PaymentStatus,
    PriceType,
    BookingStatus,
    SellLandStatus,
)
from app.users.profile_image import resolve_profile_image_url


class ReviewDecision(StrEnum):
    APPROVED = SellLandStatus.APPROVED.value
    REJECTED = SellLandStatus.REJECTED.value


class AdminSellerSummary(BaseModel):
    id: int
    fullname: str
    mobile: str | None = None
    email: str


class AdminListingMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    media_type: MediaType
    document_type: DocumentType | None = None
    file_url: str
    file_name: str
    is_required: bool
    created_at: datetime

    @field_validator("file_url", mode="before")
    @classmethod
    def normalize_file_url(cls, value: str) -> str:
        return to_public_url(value) or value


class AdminSellLandReviewListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_code: str | None = None
    title: str | None = None
    owner_name: str | None = None
    owner_mobile: str | None = None
    land_type: LandType
    ownership_type: OwnershipType
    city: str | None = None
    state: str | None = None
    expected_price: float | None = None
    status: SellLandStatus
    payment_status: PaymentStatus
    created_at: datetime
    updated_at: datetime
    seller: AdminSellerSummary


class AdminSellLandReviewListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminSellLandReviewListItem]


class BoundaryPoint(BaseModel):
    lat: float
    lng: float


class AdminSellLandReviewDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    listing_code: str | None = None
    title: str | None = None
    instagram_url: str | None = None
    owner_name: str | None = None
    owner_mobile: str | None = None
    owner_category: SellerCategory | None = None
    land_type: LandType | None = None
    ownership_type: OwnershipType | None = None
    location: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    area: float | None = None
    area_unit: AreaUnit | None = None
    price_type: PriceType | None = None
    expected_price: float | None = None
    negotiable: bool
    availability: Availability | None = None
    description: str | None = None
    boundary_points: list[BoundaryPoint] = Field(default_factory=list)
    is_draft: bool
    draft_step: int
    payment_required_amount: float
    payment_status: PaymentStatus | None = None
    payment_paid_at: datetime | None = None
    payment_amount: float | None = None
    status: SellLandStatus
    reviewed_by_id: int | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    cancellation_reason: str | None = None
    refund_upi_id: str | None = None
    cancelled_at: datetime | None = None
    refund_due_at: datetime | None = None
    refund_completed_at: datetime | None = None
    refund_amount: float | None = None
    refund_transaction_id: str | None = None
    created_at: datetime
    updated_at: datetime
    seller: AdminSellerSummary
    admin_handler: "AdminCaseLockOfficerSummary | None" = None
    field_officer: "AdminCaseLockOfficerSummary | None" = None
    media: list[AdminListingMedia]


class AdminInstagramUrlUpdateRequest(BaseModel):
    instagram_url: str | None = Field(max_length=500)

    @field_validator("instagram_url")
    @classmethod
    def validate_instagram_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from app.sell_land.instagram_urls import normalize_instagram_url

        normalized = normalize_instagram_url(value)
        if normalized is None:
            raise ValueError("instagram_url must be a valid HTTPS Instagram profile, post, or reel URL")
        return normalized


class AdminInstagramUrlUpdateResponse(BaseModel):
    request_id: int
    instagram_url: str | None


class AdminReviewActionRequest(BaseModel):
    decision: ReviewDecision
    rejection_reason: str | None = Field(default=None, max_length=500)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: ReviewDecision | str) -> ReviewDecision:
        if isinstance(value, ReviewDecision):
            return value
        cleaned = value.strip().lower()
        if cleaned not in {ReviewDecision.APPROVED.value, ReviewDecision.REJECTED.value}:
            raise ValueError("decision must be either 'approved' or 'rejected'")
        return ReviewDecision(cleaned)

    @field_validator("rejection_reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AdminReviewActionResponse(BaseModel):
    status: str
    request_id: int
    listing_status: SellLandStatus
    reviewed_by_id: int
    reviewed_at: datetime
    rejection_reason: str | None = None


class AdminDashboardViewer(BaseModel):
    id: int
    fullname: str
    role: str
    profile_image_url: str | None = None

    @field_validator("profile_image_url", mode="before")
    @classmethod
    def normalize_profile_image_url(cls, value: str | None, info: ValidationInfo) -> str | None:
        role = info.data.get("role") if info.data else None
        return resolve_profile_image_url(value, role)


class AdminDashboardWorkflowSummary(BaseModel):
    pending_admin_review: int
    assigned_to_field_officer: int
    field_verified_final_approval: int
    live_listings: int
    locked_listings: int
    booked_listings: int
    sold_listings: int
    rejected_listings: int
    cancel_refund_management: int
    pending_registry_verification: int
    viewer: AdminDashboardViewer


class AdminFieldOfficerOption(BaseModel):
    id: int
    fullname: str
    mobile: str | None = None
    is_active: bool


class AdminCaseLockOfficerSummary(BaseModel):
    id: int
    fullname: str
    mobile: str | None = None


class AdminCaseAssignmentBoardItem(BaseModel):
    id: int
    listing_code: str | None = None
    owner_name: str | None = None
    owner_mobile: str | None = None
    location: str | None = None
    assigned_field_officer: AdminCaseLockOfficerSummary | None = None
    lock_started_at: datetime | None = None
    lock_expires_at: datetime | None = None
    locked_for_seconds: int | None = None


class AdminCaseAssignmentBoardResponse(BaseModel):
    locked_total: int
    available_total: int
    locked_cases: list[AdminCaseAssignmentBoardItem]
    available_cases: list[AdminCaseAssignmentBoardItem]


class AdminAssignCaseRequest(BaseModel):
    field_officer_id: int = Field(ge=1)
    lock_hours: int = Field(default=12, ge=1, le=72)


class AdminAssignCaseResponse(BaseModel):
    status: str
    request_id: int
    assigned_field_officer: AdminCaseLockOfficerSummary
    lock_started_at: datetime
    lock_expires_at: datetime


class AdminForceReleaseCaseResponse(BaseModel):
    status: str
    request_id: int


class AdminLockedListingBuyerSummary(BaseModel):
    id: int
    fullname: str
    mobile: str | None = None


class AdminLockedListingItem(BaseModel):
    id: int
    listing_code: str | None = None
    owner_name: str | None = None
    owner_mobile: str | None = None
    expected_price: float | None = None
    lock_started_at: datetime | None = None
    lock_expires_at: datetime | None = None
    locked_for_seconds: int | None = None
    seller: AdminSellerSummary
    buyer: AdminLockedListingBuyerSummary | None = None
    offer_id: int | None = None
    offer_status: OfferStatus | None = None
    deal_price: float | None = None


class AdminLockedListingListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminLockedListingItem]


class AdminForceReleaseOfferLockResponse(BaseModel):
    status: str
    request_id: int


class AdminBookedListingBuyerSummary(BaseModel):
    id: int | None = None
    fullname: str
    mobile: str | None = None


class AdminBookedListingItem(BaseModel):
    id: int
    listing_code: str | None = None
    owner_name: str | None = None
    owner_mobile: str | None = None
    expected_price: float | None = None
    booked_at: datetime | None = None
    deal_price: float | None = None
    booking_fee_amount: float | None = None
    payment_status: PaymentStatus | None = None
    booking_status: BookingStatus | None = None
    field_officer: AdminCaseLockOfficerSummary | None = None
    seller: AdminSellerSummary
    buyer: AdminBookedListingBuyerSummary | None = None
    booking_id: int | None = None


class AdminBookedListingListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminBookedListingItem]


class AdminBookingDocument(BaseModel):
    name: str
    file_url: str

    @field_validator("file_url", mode="before")
    @classmethod
    def normalize_file_url(cls, value: str) -> str:
        return to_public_url(value) or value


class AdminRegistryProofItem(BaseModel):
    id: int
    file_url: str
    file_name: str
    created_at: datetime

    @field_validator("file_url", mode="before")
    @classmethod
    def normalize_file_url(cls, value: str) -> str:
        return to_public_url(value) or value


class AdminBookingPartyInfo(BaseModel):
    name: str
    mobile: str | None = None
    documents: list[AdminBookingDocument] = Field(default_factory=list)


class AdminBookedLandInfo(BaseModel):
    expected_price: float | None = None
    deal_price: float | None = None
    location: str | None = None


class AdminBookedPaymentInfo(BaseModel):
    token_amount: float | None = None
    remaining_amount: float | None = None
    payment_status: PaymentStatus | None = None


class AdminRegistryInfo(BaseModel):
    registry_date: date | None = None
    registry_time: time | None = None
    registry_location: str | None = None
    proof_url: str | None = None
    proofs: list[AdminRegistryProofItem] = Field(default_factory=list)
    proof_notes: str | None = None
    status: BookingStatus | None = None

    @field_validator("proof_url", mode="before")
    @classmethod
    def normalize_proof_url(cls, value: str | None) -> str | None:
        if not value:
            return value
        return to_public_url(value) or value


class AdminBookedListingDetailResponse(BaseModel):
    booking_id: int
    listing_id: int
    status: SellLandStatus
    booked_at: datetime | None = None
    booking_status: BookingStatus
    buyer: AdminBookingPartyInfo
    seller: AdminBookingPartyInfo
    land: AdminBookedLandInfo
    payment: AdminBookedPaymentInfo
    field_officer: AdminCaseLockOfficerSummary | None = None
    registry: AdminRegistryInfo | None = None
    cancellation_reason: str | None = None
    refund_decision: str | None = None
    refund_status: str | None = None
    approved_refund_amount: Decimal | None = None
    actual_refunded_amount: Decimal | None = None
    refund_reference: str | None = None
    cancelled_at: datetime | None = None


class AdminBookingFieldOfficerUpdateRequest(BaseModel):
    field_officer_id: int = Field(ge=1)


class AdminBookingFieldOfficerUpdateResponse(BaseModel):
    status: str
    booking_id: int
    field_officer: AdminCaseLockOfficerSummary | None = None


class AdminRegistryScheduleRequest(BaseModel):
    registry_date: date
    registry_time: time
    registry_location: str = Field(min_length=2, max_length=255)


class AdminRegistryScheduleResponse(BaseModel):
    status: str
    booking_id: int
    booking_status: BookingStatus
    registry: AdminRegistryInfo


class PropertyBookingCancellationRequest(BaseModel):
    refund_decision: str
    refund_amount: Decimal | None = None
    cancellation_reason: str = Field(min_length=5, max_length=500)

    @field_validator("refund_decision")
    @classmethod
    def validate_refund_decision(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if cleaned not in {"REFUND", "NO_REFUND"}:
            raise ValueError("refund_decision must be REFUND or NO_REFUND")
        return cleaned

    @field_validator("cancellation_reason")
    @classmethod
    def validate_cancellation_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("cancellation_reason is required")
        return cleaned

    @field_validator("refund_amount")
    @classmethod
    def validate_refund_precision(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and (not value.is_finite() or value.as_tuple().exponent < -2):
            raise ValueError("refund_amount must use at most two decimal places")
        return value


class PropertyBookingCancellationResponse(BaseModel):
    booking_id: int
    listing_id: int
    refund_id: int
    booking_status: str
    listing_status: str
    refund_decision: str
    refund_status: str
    original_captured_amount: Decimal
    approved_refund_amount: Decimal


class PropertyBookingCancellationPreview(BaseModel):
    booking_id: int
    listing_id: int
    listing_code: str | None = None
    property_name: str | None = None
    buyer_name: str
    buyer_mobile: str
    booking_status: str
    listing_status: str
    captured_payment_amount: Decimal | None = None
    captured_at: datetime | None = None
    can_cancel: bool
    blocking_reason: str | None = None


class PropertyBookingRefundQueueItem(BaseModel):
    refund_id: int
    booking_id: int
    listing_id: int
    listing_code: str | None = None
    property_name: str | None = None
    buyer_name: str
    buyer_mobile: str
    original_captured_amount: Decimal
    approved_refund_amount: Decimal
    cancellation_reason: str
    refund_status: str
    cancelled_at: datetime
    buyer_upi_id: str | None = None


class PropertyBookingRefundQueueResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[PropertyBookingRefundQueueItem]


class PropertyBookingRefundHistoryItem(BaseModel):
    event_type: str
    from_status: str | None = None
    to_status: str
    actor_role: str
    note: str | None = None
    created_at: datetime


class AccountingPropertyBookingRefundDetail(PropertyBookingRefundQueueItem):
    buyer_id: int
    buyer_upi_id: str | None = None
    transaction_reference: str | None = None
    actual_refunded_amount: Decimal | None = None
    confirmation_note: str | None = None
    accounting_confirmed_at: datetime | None = None
    payment_order_id: int
    history: list[PropertyBookingRefundHistoryItem]


class AccountingPropertyBookingRefundConfirmRequest(BaseModel):
    actual_refunded_amount: Decimal
    transaction_reference: str = Field(min_length=3, max_length=120)
    confirmation_note: str | None = Field(default=None, max_length=500)

    @field_validator("actual_refunded_amount")
    @classmethod
    def validate_amount_precision(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value.as_tuple().exponent < -2:
            raise ValueError("actual_refunded_amount must use at most two decimal places")
        return value

    @field_validator("transaction_reference")
    @classmethod
    def normalize_reference(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("transaction_reference is required")
        return cleaned


class AccountingPropertyBookingRefundFailRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AdminRegistryVerificationRequest(BaseModel):
    decision: str

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"approve", "reject"}:
            raise ValueError("decision must be 'approve' or 'reject'")
        return cleaned


class AdminRegistryVerificationResponse(BaseModel):
    status: str
    booking_id: int
    booking_status: BookingStatus


class AdminRegistryPendingItem(BaseModel):
    booking_id: int
    listing_id: int
    seller_name: str | None = None
    seller_mobile: str | None = None
    buyer_name: str
    buyer_mobile: str
    registry_date: date | None = None
    registry_time: time | None = None
    registry_location: str | None = None
    proof_url: str | None = None
    proofs: list[AdminRegistryProofItem] = Field(default_factory=list)

    @field_validator("proof_url", mode="before")
    @classmethod
    def normalize_registry_proof_url(cls, value: str | None) -> str | None:
        if not value:
            return value
        return to_public_url(value) or value


class AdminRegistryPendingListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminRegistryPendingItem]


class FinalApprovalDecision(StrEnum):
    APPROVE_GO_LIVE = "approve_go_live"
    REJECT = "reject"
    REASSIGN_TO_FIELD_OFFICER = "reassign_to_field_officer"


class AdminFieldVerifiedCaseItem(BaseModel):
    id: int
    listing_code: str | None = None
    owner_name: str | None = None
    owner_mobile: str | None = None
    location: str | None = None
    field_officer: AdminCaseLockOfficerSummary | None = None
    field_officer_notes: str | None = None
    field_officer_reviewed_at: datetime | None = None
    visit_photo_url: str | None = None

    @field_validator("visit_photo_url", mode="before")
    @classmethod
    def normalize_visit_photo_url(cls, value: str | None) -> str | None:
        return to_public_url(value)


class AdminFieldVerifiedCaseListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminFieldVerifiedCaseItem]


class AdminFinalApprovalActionRequest(BaseModel):
    decision: FinalApprovalDecision
    rejection_reason: str | None = Field(default=None, max_length=500)

    @field_validator("rejection_reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AdminFinalApprovalActionResponse(BaseModel):
    status: str
    request_id: int
    listing_status: SellLandStatus
    rejection_reason: str | None = None


class AdminRefundMarkPaidResponse(BaseModel):
    status: str
    request_id: int
    listing_status: SellLandStatus
    refund_completed_at: datetime


class AdminRefundQueueSellerSummary(BaseModel):
    id: int
    fullname: str
    mobile: str


class AdminRefundQueueItem(BaseModel):
    request_id: int
    listing_code: str | None = None
    seller_uid: int
    seller: AdminRefundQueueSellerSummary
    cancellation_reason: str
    cancelled_at: datetime
    refund_due_at: datetime | None = None
    refund_upi_id: str | None = None
    total_paid: float


class AdminRefundQueueListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminRefundQueueItem]


class AdminForwardRefundToAccountingResponse(BaseModel):
    status: str
    request_id: int
    forwarded_to_accounting_at: datetime


class AdminRefundSuccessItem(BaseModel):
    request_id: int
    listing_code: str | None = None
    seller_uid: int
    seller: AdminRefundQueueSellerSummary
    cancellation_reason: str
    status_before_cancellation: SellLandStatus | None = None
    status_before_cancellation_label: str | None = None
    cancellation_stage: str | None = None
    cancelled_at: datetime
    refund_completed_at: datetime
    refund_amount: float | None = None
    refund_transaction_id: str | None = None
    status: SellLandStatus


class AdminRefundSuccessListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AdminRefundSuccessItem]


class AccountingRefundPendingItem(BaseModel):
    request_id: int
    listing_code: str | None = None
    seller_uid: int
    seller_fullname: str
    seller_mobile: str
    cancellation_reason: str
    cancelled_at: datetime
    refund_due_at: datetime | None = None
    refund_upi_id: str | None = None
    total_paid: float
    admin_involved: bool
    admin_name: str | None = None
    admin_mobile: str | None = None
    admin_status: str | None = None


class AccountingRefundPendingListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AccountingRefundPendingItem]


class AccountingRefundHistoryItem(BaseModel):
    request_id: int
    listing_code: str | None = None
    seller_uid: int
    seller_fullname: str
    seller_mobile: str
    cancellation_reason: str
    cancelled_at: datetime
    refund_upi_id: str | None = None
    refund_completed_at: datetime
    total_paid: float
    admin_involved: bool
    admin_name: str | None = None
    admin_mobile: str | None = None
    admin_status: str | None = None
    refund_amount: float | None = None
    refund_transaction_id: str | None = None
    status: SellLandStatus


class AccountingRefundHistoryListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AccountingRefundHistoryItem]


class AccountingConfirmRefundResponse(BaseModel):
    status: str
    request_id: int
    listing_status: SellLandStatus
    refund_completed_at: datetime
    refund_amount: float | None = None
    refund_transaction_id: str | None = None


class AccountingConfirmRefundRequest(BaseModel):
    refund_amount: float | None = Field(default=None, gt=0)
    transaction_id: str | None = Field(default=None, min_length=2, max_length=120)

    @field_validator("transaction_id")
    @classmethod
    def normalize_transaction_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AccountingCompletedTransactionItem(BaseModel):
    listing_id: int
    listing_code: str | None = None
    seller_name: str
    seller_fee: float
    seller_fee_status: str
    buyer_name: str | None = None
    buyer_fee: float | None = None
    buyer_fee_status: str
    status: str
    date: datetime


class AccountingPaymentInfo(BaseModel):
    method: str | None = None
    transaction_id: str | None = None
    paid_at: datetime | None = None
    status: str | None = None


class AccountingPaymentDetails(BaseModel):
    seller: AccountingPaymentInfo | None = None
    buyer: AccountingPaymentInfo | None = None


class AccountingCompletedTransactionListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AccountingCompletedTransactionItem]


class AccountingCompletedTransactionDetailResponse(BaseModel):
    transaction: AccountingCompletedTransactionItem
    payment_details: AccountingPaymentDetails
    land_price_note: str
    final_status: str


class AccountingDashboardSummaryResponse(BaseModel):
    total_revenue: float
    pending_payments: int
    completed_transactions: int
    pending_refunds: int


class RevenueRangeType(StrEnum):
    ALL = "all"
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    CUSTOM = "custom"


class RevenueRangeInfo(BaseModel):
    type: RevenueRangeType
    start: datetime
    end: datetime


class RevenueBreakdown(BaseModel):
    total: float
    seller: float
    buyer: float


class RevenueTransactionItem(BaseModel):
    date: datetime
    type: str
    user_name: str
    amount: float
    status: str


class SuperAdminRevenueDashboardResponse(BaseModel):
    range: RevenueRangeInfo
    revenue: RevenueBreakdown
    transactions: list[RevenueTransactionItem]
