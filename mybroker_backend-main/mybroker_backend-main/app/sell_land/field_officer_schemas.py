from datetime import date, datetime, time
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.media.url_utils import to_public_url
from app.sell_land.constants import (
    AreaUnit,
    Availability,
    DocumentType,
    LandType,
    MediaType,
    OwnershipType,
    PaymentStatus,
    PriceType,
    SellLandStatus,
    BookingStatus,
    SellerCategory,
)
from app.users.profile_image import resolve_profile_image_url


class FieldOfficerDecision(StrEnum):
    APPROVED = SellLandStatus.APPROVED.value
    REJECTED = SellLandStatus.REJECTED.value


class FieldOfficerAvailableCaseItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_code: str | None = None
    title: str | None = None
    owner_name: str | None = None
    owner_mobile: str | None = None
    land_type: LandType
    location: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    expected_price: float | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class FieldOfficerAvailableCaseListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[FieldOfficerAvailableCaseItem]


class FieldOfficerDashboardViewer(BaseModel):
    id: int
    fullname: str
    role: str
    profile_image_url: str | None = None

    @field_validator("profile_image_url", mode="before")
    @classmethod
    def normalize_profile_image_url(cls, value: str | None, info: ValidationInfo) -> str | None:
        role = info.data.get("role") if info.data else None
        return resolve_profile_image_url(value, role)


class FieldOfficerDashboardResponse(BaseModel):
    status: str
    viewer: FieldOfficerDashboardViewer
    active_case_id: int | None = None
    active_case: FieldOfficerAvailableCaseItem | None = None
    lock_remaining_seconds: int | None = None
    total_cases: int
    available_cases: int
    completed_visits: int


class FieldOfficerCaseActionResponse(BaseModel):
    status: str
    request_id: int
    lock_expires_at: datetime | None = None


class FieldOfficerSellerSummary(BaseModel):
    id: int
    fullname: str
    mobile: str
    email: str
    profile_image_url: str | None = None

    @field_validator("profile_image_url", mode="before")
    @classmethod
    def normalize_profile_image_url(cls, value: str | None) -> str | None:
        return resolve_profile_image_url(value)


class FieldOfficerBoundaryPoint(BaseModel):
    lat: float
    lng: float


class FieldOfficerListingMedia(BaseModel):
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


class FieldOfficerCaseDetailResponse(BaseModel):
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
    expected_price: float | None = None
    negotiable: bool
    availability: Availability
    description: str | None = None
    boundary_points: list[FieldOfficerBoundaryPoint] = Field(default_factory=list)
    payment_status: PaymentStatus
    status: SellLandStatus
    lock_expires_at: datetime | None = None
    field_officer_decision: FieldOfficerDecision | None = None
    field_officer_reviewed_at: datetime | None = None
    field_officer_notes: str | None = None
    field_officer_rejection_reason: str | None = None
    field_officer_visit_photo_url: str | None = None
    seller: FieldOfficerSellerSummary
    media: list[FieldOfficerListingMedia]

    @field_validator("field_officer_visit_photo_url", mode="before")
    @classmethod
    def normalize_visit_photo_url(cls, value: str | None) -> str | None:
        return to_public_url(value)


class FieldOfficerReviewActionRequest(BaseModel):
    decision: FieldOfficerDecision
    inspection_notes: str | None = Field(default=None, max_length=2000)
    rejection_reason: str | None = Field(default=None, max_length=500)

    @field_validator("inspection_notes", "rejection_reason")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class FieldOfficerReviewActionResponse(BaseModel):
    status: str
    request_id: int
    listing_status: SellLandStatus
    field_officer_decision: FieldOfficerDecision
    field_officer_reviewed_at: datetime
    field_officer_rejection_reason: str | None = None


class FieldOfficerVisitPhotoUploadResponse(BaseModel):
    status: str
    request_id: int
    visit_photo_url: str

    @field_validator("visit_photo_url", mode="before")
    @classmethod
    def normalize_visit_photo_url(cls, value: str) -> str:
        return to_public_url(value) or value


class FieldOfficerRegistryProofItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_url: str
    file_name: str
    created_at: datetime

    @field_validator("file_url", mode="before")
    @classmethod
    def normalize_file_url(cls, value: str) -> str:
        return to_public_url(value) or value


class FieldOfficerRegistryAssignmentItem(BaseModel):
    booking_id: int
    listing_id: int
    deal_amount: float | None = None
    property_name: str | None = None
    property_type: str | None = None
    property_area: str | None = None
    property_address: str | None = None
    buyer_name: str
    buyer_mobile: str
    seller_name: str | None = None
    seller_mobile: str | None = None
    registry_date: date | None = None
    registry_time: time | None = None
    registry_location: str | None = None
    status: BookingStatus
    assigned_officer_name: str | None = None
    assigned_officer_mobile: str | None = None


class FieldOfficerRegistryAssignmentDetail(FieldOfficerRegistryAssignmentItem):
    proofs: list[FieldOfficerRegistryProofItem] = Field(default_factory=list)


class FieldOfficerRegistryAssignmentListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[FieldOfficerRegistryAssignmentItem]


class FieldOfficerRegistryAssignmentDetailResponse(BaseModel):
    status: str
    assignment: FieldOfficerRegistryAssignmentDetail


class FieldOfficerRegistryProofUploadResponse(BaseModel):
    status: str
    booking_id: int
    proofs: list[FieldOfficerRegistryProofItem] = Field(default_factory=list)


class FieldOfficerRegistryCompleteResponse(BaseModel):
    status: str
    booking_id: int
    proofs: list[FieldOfficerRegistryProofItem] = Field(default_factory=list)
