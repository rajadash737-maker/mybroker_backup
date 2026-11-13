from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    PaymentMethod,
    PaymentStatus,
    PriceType,
    SellLandStatus,
    BookingStatus,
    get_required_documents_for_ownership,
)
class BoundaryPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class SellLandDraftUpsertRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=150)
    owner_name: str | None = Field(default=None, min_length=2, max_length=100)
    owner_mobile: str | None = Field(default=None, min_length=10, max_length=20)
    owner_category: SellerCategory | None = None
    land_type: LandType | None = None
    ownership_type: OwnershipType | None = None
    location: str | None = Field(default=None, min_length=3, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    pincode: str | None = Field(default=None, min_length=5, max_length=10)
    area: float | None = Field(default=None, gt=0)
    area_unit: AreaUnit | None = None
    price_type: PriceType | None = None
    expected_price: Decimal | None = Field(default=None, gt=0)
    pricing_version: int | None = Field(default=None, ge=1, le=2)
    negotiable: bool | None = None
    availability: Availability | None = None
    description: str | None = Field(default=None, max_length=5000)
    draft_step: int | None = Field(default=None, ge=1, le=8)

    @model_validator(mode="after")
    def validate_versioned_pricing(self):
        if self.price_type is PriceType.PRICE_PER_UNIT and self.pricing_version == 2:
            raise ValueError("V2 seller pricing supports total land price only")
        return self

    @model_validator(mode="before")
    @classmethod
    def reject_entered_unit_price(cls, value):
        if isinstance(value, dict) and "entered_unit_price" in value:
            raise ValueError("entered_unit_price is not accepted; submit total expected_price")
        return value

    @field_validator(
        "title",
        "owner_name",
        "owner_mobile",
        "location",
        "city",
        "state",
        "pincode",
        "description",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: str | None):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @staticmethod
    def _coerce_enum(value: object, enum_cls: type[Enum]) -> object:
        if value is None or isinstance(value, enum_cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            alias = normalized.replace(".", "").replace("-", "_").replace(" ", "_")
            for member in enum_cls:
                member_value = str(member.value).lower()
                member_alias = member_value.replace(".", "").replace("-", "_").replace(" ", "_")
                if normalized == member_value or alias == member_alias:
                    return member
        return value

    @field_validator("land_type", mode="before")
    @classmethod
    def normalize_land_type(cls, value: object):
        return cls._coerce_enum(value, LandType)

    @field_validator("ownership_type", mode="before")
    @classmethod
    def normalize_ownership_type(cls, value: object):
        return cls._coerce_enum(value, OwnershipType)

    @field_validator("owner_category", mode="before")
    @classmethod
    def normalize_owner_category(cls, value: object):
        return cls._coerce_enum(value, SellerCategory)

    @field_validator("area_unit", mode="before")
    @classmethod
    def normalize_area_unit(cls, value: object):
        return cls._coerce_enum(value, AreaUnit)

    @field_validator("price_type", mode="before")
    @classmethod
    def normalize_price_type(cls, value: object):
        return cls._coerce_enum(value, PriceType)

    @field_validator("availability", mode="before")
    @classmethod
    def normalize_availability(cls, value: object):
        return cls._coerce_enum(value, Availability)


class SellLandCreateRequest(SellLandDraftUpsertRequest):
    title: str = Field(min_length=3, max_length=150)
    owner_name: str = Field(min_length=2, max_length=100)
    owner_mobile: str = Field(min_length=10, max_length=20)
    owner_category: SellerCategory = SellerCategory.GENERAL
    land_type: LandType = LandType.RESIDENTIAL
    ownership_type: OwnershipType = OwnershipType.SINGLE_OWNER
    location: str = Field(min_length=3, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pincode: str = Field(min_length=5, max_length=10)
    area: float = Field(gt=0)
    area_unit: AreaUnit = AreaUnit.SQFT
    price_type: PriceType = PriceType.TOTAL_PRICE
    expected_price: Decimal = Field(gt=0)
    pricing_version: Literal[2]
    negotiable: bool = True
    availability: Availability = Availability.IMMEDIATE

    @model_validator(mode="after")
    def require_price_for_create(self):
        if self.pricing_version != 2:
            raise ValueError("New seller listings must use pricing_version=2")
        if self.price_type is PriceType.PRICE_PER_UNIT:
            raise ValueError("Seller pricing supports total land price only")


class SellLandUpdateRequest(SellLandDraftUpsertRequest):
    pass


class SellLandBoundaryRequest(BaseModel):
    points: list[BoundaryPoint] = Field(min_length=3, max_length=100)


class SellLandMediaUploadResponse(BaseModel):
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


class SellLandSubmitRequest(BaseModel):
    request_id: int = Field(gt=0)


class SellLandSubmitResponse(BaseModel):
    status: str
    request_id: int
    listing_code: str


class SellLandPaymentInitRequest(BaseModel):
    request_id: int = Field(gt=0)
    method: PaymentMethod
    provider_ref: str | None = Field(default=None, max_length=100)


class SellLandPaymentMarkPaidRequest(BaseModel):
    payment_id: int = Field(gt=0)
    provider_ref: str | None = Field(default=None, max_length=100)


class SellLandPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    method: PaymentMethod
    amount: float
    status: PaymentStatus
    provider_ref: str | None = None
    paid_at: datetime | None = None
    created_at: datetime


class SellLandRazorpayOrderRequest(BaseModel):
    request_id: int = Field(gt=0)


class SellLandRazorpayOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str


class SellLandRazorpayVerifyRequest(BaseModel):
    razorpay_order_id: str = Field(min_length=5, max_length=64)
    razorpay_payment_id: str = Field(min_length=5, max_length=64)
    razorpay_signature: str = Field(min_length=5, max_length=256)

    @field_validator(
        "razorpay_order_id",
        "razorpay_payment_id",
        "razorpay_signature",
        mode="before",
    )
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned


class SellLandRazorpayVerifyResponse(BaseModel):
    status: str
    order_id: str
    payment_id: str


class SellLandCancellationReason(str, Enum):
    PRICE_ISSUE = "price_issue"
    FOUND_ANOTHER_BUYER = "found_another_buyer"
    PERSONAL_REASON = "personal_reason"
    DOCUMENT_PROBLEM = "document_problem"


class SellLandCancelRequest(BaseModel):
    reason: SellLandCancellationReason
    upi_id: str = Field(min_length=3, max_length=120)
    notes: str | None = Field(default=None, max_length=200)

    @field_validator("upi_id")
    @classmethod
    def normalize_upi_id(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned:
            raise ValueError("upi_id must be a valid UPI id")
        return cleaned

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SellLandCancelResponse(BaseModel):
    status: str
    request_id: int
    listing_status: SellLandStatus
    cancellation_reason: str
    refund_upi_id: str
    refund_due_at: datetime
    cancellation_requires_admin_review: bool


class SellLandWorkflowStage(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    FIELD_VERIFIED = "field_verified"
    LIVE = "live"
    NEEDS_CORRECTION = "needs_correction"
    SOLD = "sold"
    BOOKED = "booked"
    PROCESSING_REFUND = "processing_refund"
    REFUND_SUCCESSFUL = "refund_successful"


class SellLandWorkflowProgress(BaseModel):
    draft: bool
    under_review: bool
    approved: bool
    field_verified: bool
    live: bool
    sold: bool
    processing_refund: bool
    refund_successful: bool


class SellLandWorkflowTracking(BaseModel):
    stage: SellLandWorkflowStage
    label: str
    progress: SellLandWorkflowProgress
    needs_correction: bool = False
    correction_by: str | None = None
    correction_reason: str | None = None
    refund_due_at: datetime | None = None


def _build_tracking(
    status: SellLandStatus,
    is_draft: bool,
    rejection_reason: str | None,
    field_officer_rejection_reason: str | None,
    refund_due_at: datetime | None = None,
) -> SellLandWorkflowTracking:
    needs_correction = False
    correction_reason = None
    correction_by = None
    stage = SellLandWorkflowStage.DRAFT
    label = "DRAFT"

    if status == SellLandStatus.REJECTED:
        needs_correction = True
        correction_reason = field_officer_rejection_reason or rejection_reason
        if field_officer_rejection_reason:
            correction_by = "field_officer"
        elif rejection_reason:
            correction_by = "admin"
        stage = SellLandWorkflowStage.NEEDS_CORRECTION
        label = "NEEDS_CORRECTION"
    elif status == SellLandStatus.REFUND_SUCCESSFUL:
        stage = SellLandWorkflowStage.REFUND_SUCCESSFUL
        label = "REFUND_SUCCESSFUL"
    elif status == SellLandStatus.PROCESSING_REFUND:
        stage = SellLandWorkflowStage.PROCESSING_REFUND
        label = "PROCESSING_REFUND"
    elif status == SellLandStatus.BOOKED:
        stage = SellLandWorkflowStage.BOOKED
        label = "BOOKED"
    elif status == SellLandStatus.SOLD:
        stage = SellLandWorkflowStage.SOLD
        label = "SOLD"
    elif status == SellLandStatus.LIVE:
        stage = SellLandWorkflowStage.LIVE
        label = "LIVE"
    elif status == SellLandStatus.FIELD_VERIFIED:
        stage = SellLandWorkflowStage.FIELD_VERIFIED
        label = "FIELD_VERIFIED"
    elif status == SellLandStatus.APPROVED:
        stage = SellLandWorkflowStage.APPROVED
        label = "APPROVED"
    elif status == SellLandStatus.PENDING:
        stage = SellLandWorkflowStage.UNDER_REVIEW
        label = "UNDER_REVIEW"
    elif status == SellLandStatus.DRAFT or is_draft:
        stage = SellLandWorkflowStage.DRAFT
        label = "DRAFT"

    progress = SellLandWorkflowProgress(
        draft=True,
        under_review=stage
        in {
            SellLandWorkflowStage.UNDER_REVIEW,
            SellLandWorkflowStage.APPROVED,
            SellLandWorkflowStage.FIELD_VERIFIED,
            SellLandWorkflowStage.LIVE,
            SellLandWorkflowStage.SOLD,
            SellLandWorkflowStage.BOOKED,
            SellLandWorkflowStage.NEEDS_CORRECTION,
            SellLandWorkflowStage.PROCESSING_REFUND,
            SellLandWorkflowStage.REFUND_SUCCESSFUL,
        },
        approved=stage
        in {
            SellLandWorkflowStage.APPROVED,
            SellLandWorkflowStage.FIELD_VERIFIED,
            SellLandWorkflowStage.LIVE,
            SellLandWorkflowStage.SOLD,
            SellLandWorkflowStage.BOOKED,
            SellLandWorkflowStage.PROCESSING_REFUND,
            SellLandWorkflowStage.REFUND_SUCCESSFUL,
        },
        field_verified=stage
        in {
            SellLandWorkflowStage.FIELD_VERIFIED,
            SellLandWorkflowStage.LIVE,
            SellLandWorkflowStage.SOLD,
            SellLandWorkflowStage.BOOKED,
            SellLandWorkflowStage.PROCESSING_REFUND,
            SellLandWorkflowStage.REFUND_SUCCESSFUL,
        },
        live=stage
        in {
            SellLandWorkflowStage.LIVE,
            SellLandWorkflowStage.SOLD,
            SellLandWorkflowStage.BOOKED,
            SellLandWorkflowStage.PROCESSING_REFUND,
            SellLandWorkflowStage.REFUND_SUCCESSFUL,
        },
        sold=stage
        in {
            SellLandWorkflowStage.SOLD,
            SellLandWorkflowStage.BOOKED,
            SellLandWorkflowStage.PROCESSING_REFUND,
            SellLandWorkflowStage.REFUND_SUCCESSFUL,
        },
        processing_refund=stage == SellLandWorkflowStage.PROCESSING_REFUND,
        refund_successful=stage == SellLandWorkflowStage.REFUND_SUCCESSFUL,
    )
    return SellLandWorkflowTracking(
        stage=stage,
        label=label,
        progress=progress,
        needs_correction=needs_correction,
        correction_by=correction_by,
        correction_reason=correction_reason,
        refund_due_at=refund_due_at,
    )


def _can_cancel_listing(
    status: SellLandStatus,
    is_draft: bool,
    payment_status: PaymentStatus,
) -> bool:
    if is_draft:
        return False
    if payment_status != PaymentStatus.SUCCESS:
        return False
    return status not in {
        SellLandStatus.DRAFT,
        SellLandStatus.SOLD,
        SellLandStatus.BOOKED,
        SellLandStatus.PROCESSING_REFUND,
        SellLandStatus.REFUND_SUCCESSFUL,
    }


class SellLandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    listing_code: str | None = None
    title: str | None = None
    owner_name: str | None = None
    owner_mobile: str | None = None
    owner_category: SellerCategory | None = None
    land_type: LandType
    ownership_type: OwnershipType
    location: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    area: float | None = None
    area_unit: AreaUnit
    price_type: PriceType
    expected_price: Decimal | None = None
    pricing_version: int = 1
    negotiable: bool
    availability: Availability
    description: str | None = None
    boundary_points: str | None = None
    is_draft: bool
    draft_step: int
    payment_required_amount: float
    payment_status: PaymentStatus
    status: SellLandStatus
    reviewed_by_id: int | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    field_officer_rejection_reason: str | None = None
    status_before_cancellation: SellLandStatus | None = None
    cancellation_reason: str | None = None
    refund_upi_id: str | None = None
    cancelled_at: datetime | None = None
    refund_due_at: datetime | None = None
    refund_completed_at: datetime | None = None
    cancellation_requires_admin_review: bool = False
    refund_forwarded_to_accounting_by_id: int | None = None
    refund_forwarded_to_accounting_at: datetime | None = None
    can_cancel_listing: bool = False
    tracking: SellLandWorkflowTracking | None = None
    required_document_types: list[DocumentType] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def populate_tracking(self):
        self.tracking = _build_tracking(
            status=self.status,
            is_draft=self.is_draft,
            rejection_reason=self.rejection_reason,
            field_officer_rejection_reason=self.field_officer_rejection_reason,
            refund_due_at=self.refund_due_at,
        )
        self.can_cancel_listing = _can_cancel_listing(
            status=self.status,
            is_draft=self.is_draft,
            payment_status=self.payment_status,
        )
        self.required_document_types = list(get_required_documents_for_ownership(self.ownership_type))
        return self


class SellLandTrackingCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_code: str | None = None
    title: str | None = None
    area: float | None = None
    area_unit: AreaUnit
    expected_price: float | None = None
    status: SellLandStatus
    is_draft: bool
    payment_status: PaymentStatus
    rejection_reason: str | None = None
    field_officer_rejection_reason: str | None = None
    status_before_cancellation: SellLandStatus | None = None
    cancellation_reason: str | None = None
    refund_upi_id: str | None = None
    refund_due_at: datetime | None = None
    cancellation_requires_admin_review: bool = False
    refund_forwarded_to_accounting_by_id: int | None = None
    refund_forwarded_to_accounting_at: datetime | None = None
    can_cancel_listing: bool = False
    likes_count: int = 0
    offer_count: int = 0
    deal_amount: float | None = None
    booking_status: BookingStatus | None = None
    registry_date: date | None = None
    registry_time: time | None = None
    registry_location: str | None = None
    registry_proofs: list["RegistryProofItem"] = Field(default_factory=list)
    tracking: SellLandWorkflowTracking | None = None
    updated_at: datetime

    @model_validator(mode="after")
    def populate_tracking(self):
        self.tracking = _build_tracking(
            status=self.status,
            is_draft=self.is_draft,
            rejection_reason=self.rejection_reason,
            field_officer_rejection_reason=self.field_officer_rejection_reason,
            refund_due_at=self.refund_due_at,
        )
        self.can_cancel_listing = _can_cancel_listing(
            status=self.status,
            is_draft=self.is_draft,
            payment_status=self.payment_status,
        )
        return self


class SellLandDeleteResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"status": "Sell land request deleted"}}
    )

    status: str


class SellLandMediaDeleteResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"status": "Media deleted", "media_id": 12}}
    )

    status: str
    media_id: int


class SellLandDocumentRequirementsResponse(BaseModel):
    ownership_type: OwnershipType
    required_document_types: list[DocumentType]
    optional_document_types: list[DocumentType] = Field(default_factory=lambda: [DocumentType.OTHER])


class ExploreSortType(str, Enum):
    LATEST = "latest"
    PRICE_LOW_TO_HIGH = "price_low_to_high"
    PRICE_HIGH_TO_LOW = "price_high_to_low"


class BuyerExploreLandCard(BaseModel):
    id: int
    title: str | None = None
    instagram_url: str | None = None
    land_type: LandType
    listing_status: SellLandStatus
    price_type: PriceType
    expected_price: float | None = None
    area: float | None = None
    area_unit: AreaUnit
    location: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    boundary_points: list[BoundaryPoint] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    is_liked: bool = False
    likes_count: int = 0
    is_offer_locked: bool = False
    offer_lock_expires_at: datetime | None = None
    created_at: datetime


class BuyerExploreLandListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[BuyerExploreLandCard]


class BuyerExploreLikeResponse(BaseModel):
    status: str
    request_id: int
    liked: bool
    likes_count: int = 0


class BuyerExploreLandDetailResponse(BaseModel):
    id: int
    user_id: int
    title: str | None = None
    owner_category: SellerCategory | None = None
    land_type: LandType
    listing_status: SellLandStatus
    status_label: str
    price_type: PriceType
    expected_price: float | None = None
    area: float | None = None
    area_unit: AreaUnit
    location: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    boundary_points: list[BoundaryPoint] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    is_offer_locked: bool = False
    offer_lock_expires_at: datetime | None = None
    map_query: str | None = None
    map_url: str | None = None
    documents: list[SellLandMediaUploadResponse] = Field(default_factory=list)
    deal_amount: float | None = None
    booking_status: BookingStatus | None = None
    registry_date: date | None = None
    registry_time: time | None = None
    registry_location: str | None = None
    registry_proofs: list["RegistryProofItem"] = Field(default_factory=list)


class BuyerOfferCreateRequest(BaseModel):
    amount: float = Field(gt=0, strict=True)


class BuyerOfferCreateResponse(BaseModel):
    status: str
    offer_id: int
    request_id: int
    offered_amount: float
    offer_status: OfferStatus = OfferStatus.PENDING


class SellerOfferBuyerSummary(BaseModel):
    id: int
    fullname: str
    mobile: str | None = None


class SellerOfferItem(BaseModel):
    id: int
    request_id: int
    buyer_id: int
    offered_amount: float
    counter_amount: float | None = None
    offer_status: OfferStatus
    created_at: datetime
    seller_response_at: datetime | None = None
    buyer: SellerOfferBuyerSummary


class SellerOfferListResponse(BaseModel):
    request_id: int
    total: int
    is_offer_locked: bool = False
    offer_lock_expires_at: datetime | None = None
    items: list[SellerOfferItem]


class SellerOfferCounterRequest(BaseModel):
    counter_amount: float = Field(gt=0, strict=True)


class SellerOfferActionResponse(BaseModel):
    status: str
    request_id: int
    offer_id: int
    offer_status: OfferStatus
    offer_lock_expires_at: datetime | None = None


class BuyerOfferBookingStatus(str, Enum):
    OFFER_SENT = "offer_sent"
    COUNTER_RECEIVED = "counter_received"
    REJECTED = "rejected"
    ACCEPTED_BOOK_NOW = "accepted_book_now"
    BOOKED = "booked"
    IN_PROCESS = "in_process"
    REGISTRY_SCHEDULED = "registry_scheduled"
    REGISTRY_DONE = "registry_done"
    SOLD = "sold"
    EXPIRED = "expired"


class BuyerOfferTimelineEvent(BaseModel):
    key: str
    label: str
    at: datetime


class BuyerOfferLandSummary(BaseModel):
    id: int
    title: str | None = None
    land_type: LandType
    location: str | None = None
    city: str | None = None
    state: str | None = None
    expected_price: float | None = None


class BuyerOfferItem(BaseModel):
    offer_id: int
    request_id: int
    offered_amount: float
    counter_amount: float | None = None
    final_amount: float
    offer_status: OfferStatus
    booking_status: BuyerOfferBookingStatus
    status_label: str
    is_book_window_active: bool = False
    offer_lock_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    seller_response_at: datetime | None = None
    can_accept_counter: bool = False
    can_reject_counter: bool = False
    timeline: list[BuyerOfferTimelineEvent] = Field(default_factory=list)
    registry_date: date | None = None
    registry_time: time | None = None
    registry_location: str | None = None
    land: BuyerOfferLandSummary


class RegistryProofItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_url: str
    file_name: str
    created_at: datetime

    @field_validator("file_url", mode="before")
    @classmethod
    def normalize_file_url(cls, value: str) -> str:
        return to_public_url(value) or value


class BuyerOfferListResponse(BaseModel):
    total: int
    items: list[BuyerOfferItem]


class BuyerOfferActionResponse(BaseModel):
    status: str
    request_id: int
    offer_id: int
    offer_status: OfferStatus
    booking_status: BuyerOfferBookingStatus
    offer_lock_expires_at: datetime | None = None


class BuyerBookingCreateRequest(BaseModel):
    request_id: int = Field(gt=0)
    buyer_name: str = Field(min_length=2, max_length=120)
    buyer_mobile: str = Field(min_length=10, max_length=20)

    @field_validator(
        "buyer_name",
        "buyer_mobile",
        mode="before",
    )
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned


class BuyerBookingCreateResponse(BaseModel):
    status: str
    booking_id: int
    payment_status: PaymentStatus
    deal_amount: float
    booking_fee_amount: float


class BuyerBookingPaymentResponse(BaseModel):
    status: str
    booking_id: int
    payment_status: PaymentStatus
    payment_method: PaymentMethod | None = None
    transaction_id: str | None = None
    paid_at: datetime | None = None


class BuyerBookingPaymentRequest(BaseModel):
    method: PaymentMethod
    transaction_id: str | None = Field(default=None, max_length=120)

    @field_validator("transaction_id")
    @classmethod
    def normalize_transaction_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class BuyerBookingPreviewResponse(BaseModel):
    request_id: int
    total_amount: float | None = None
    deal_amount: float
    booking_fee_amount: float
    can_book: bool
    booking_status: BuyerOfferBookingStatus | None = None
    status_label: str | None = None
    offer_id: int | None = None
    offer_status: OfferStatus | None = None
    offer_lock_expires_at: datetime | None = None
    is_book_window_active: bool = False


SellLandTrackingCardResponse.model_rebuild()
BuyerExploreLandDetailResponse.model_rebuild()
