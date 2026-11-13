from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Date,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)

from app.database import Base
from app.sell_land.constants import (
    AreaUnit,
    Availability,
    LandType,
    MediaType,
    OfferStatus,
    OwnershipType,
    PaymentStatus,
    PriceType,
    BookingStatus,
    SellLandStatus,
)


class SellLandRequest(Base):
    __tablename__ = "sell_land_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    listing_code = Column(String(30), nullable=True, unique=True, index=True)

    title = Column(String(150), nullable=True)
    owner_name = Column(String(100), nullable=True)
    owner_mobile = Column(String(20), nullable=True, index=True)
    owner_category = Column(String(20), nullable=True, default="general")
    land_type = Column(String(20), nullable=False, default=LandType.RESIDENTIAL.value)
    ownership_type = Column(String(30), nullable=False, default=OwnershipType.SINGLE_OWNER.value)
    location = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    area = Column(Float, nullable=True)
    area_unit = Column(String(10), nullable=False, default=AreaUnit.SQFT.value)

    price_type = Column(String(20), nullable=False, default=PriceType.TOTAL_PRICE.value)
    expected_price = Column(Numeric(18, 6), nullable=True)
    pricing_version = Column(Integer, nullable=False, default=1, server_default="1")
    entered_unit_price = Column(Numeric(18, 6), nullable=True)
    negotiable = Column(Boolean, nullable=False, default=True)
    availability = Column(String(30), nullable=False, default=Availability.IMMEDIATE.value)

    description = Column(Text, nullable=True)
    instagram_url = Column(String(500), nullable=True)
    boundary_points = Column(Text, nullable=True)

    is_draft = Column(Boolean, nullable=False, default=True)
    draft_step = Column(Integer, nullable=False, default=1)
    payment_required_amount = Column(Float, nullable=False, default=999.0)
    payment_status = Column(String(20), nullable=False, default=PaymentStatus.INITIATED.value)
    status = Column(String(20), nullable=False, default=SellLandStatus.DRAFT.value)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(500), nullable=True)
    assigned_field_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    lock_started_at = Column(DateTime, nullable=True)
    lock_expires_at = Column(DateTime, nullable=True)
    field_officer_reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    field_officer_reviewed_at = Column(DateTime, nullable=True)
    field_officer_decision = Column(String(20), nullable=True)
    field_officer_notes = Column(Text, nullable=True)
    field_officer_rejection_reason = Column(String(500), nullable=True)
    field_officer_visit_photo_url = Column(String(500), nullable=True)
    field_officer_visit_photo_name = Column(String(255), nullable=True)
    status_before_cancellation = Column(String(20), nullable=True)
    cancellation_reason = Column(String(200), nullable=True)
    refund_upi_id = Column(String(120), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    refund_due_at = Column(DateTime, nullable=True)
    refund_completed_at = Column(DateTime, nullable=True)
    cancellation_requires_admin_review = Column(Boolean, nullable=False, default=False, server_default="0")
    refund_forwarded_to_accounting_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    refund_forwarded_to_accounting_at = Column(DateTime, nullable=True)
    refund_amount = Column(Float, nullable=True)
    refund_transaction_id = Column(String(120), nullable=True)
    refund_confirmed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    offer_locked_by_buyer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    offer_lock_expires_at = Column(DateTime, nullable=True, index=True)
    accepted_offer_id = Column(Integer, ForeignKey("sell_land_offers.id"), nullable=True, index=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class SellLandMedia(Base):
    __tablename__ = "sell_land_media"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("sell_land_requests.id"), nullable=False, index=True)
    media_type = Column(String(20), nullable=False, default=MediaType.PHOTO.value)
    document_type = Column(String(50), nullable=True)
    file_url = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    is_required = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class SellLandPayment(Base):
    __tablename__ = "sell_land_payments"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("sell_land_requests.id"), nullable=False, index=True)
    method = Column(String(30), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default=PaymentStatus.INITIATED.value)
    provider_ref = Column(String(100), nullable=True)
    gateway_payment_id = Column(String(64), nullable=True, unique=True, index=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class SellLandFavorite(Base):
    __tablename__ = "sell_land_favorites"
    __table_args__ = (UniqueConstraint("user_id", "request_id", name="uq_sell_land_favorites_user_request"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_id = Column(Integer, ForeignKey("sell_land_requests.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class SellLandOffer(Base):
    __tablename__ = "sell_land_offers"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("sell_land_requests.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Use fixed-precision numeric to avoid rounding large integer rupee amounts.
    offered_amount = Column(Numeric(18, 0), nullable=False)
    status = Column(String(20), nullable=False, default=OfferStatus.PENDING.value, index=True)
    counter_amount = Column(Numeric(18, 0), nullable=True)
    seller_response_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class SellLandBooking(Base):
    __tablename__ = "sell_land_bookings"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("sell_land_requests.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    buyer_name = Column(String(120), nullable=False)
    buyer_mobile = Column(String(20), nullable=False)
    # These fields were made optional by revisions 0017 and 0018. Keep the ORM
    # definition aligned with that migration intent and its database defaults.
    aadhaar_number = Column(String(20), nullable=True, default="", server_default="")
    pan_number = Column(String(20), nullable=True, default="", server_default="")
    bank_account = Column(String(30), nullable=True, default="", server_default="")
    aadhaar_doc_url = Column(String(500), nullable=True)
    aadhaar_doc_name = Column(String(255), nullable=True)
    pan_doc_url = Column(String(500), nullable=True)
    pan_doc_name = Column(String(255), nullable=True)
    bank_doc_url = Column(String(500), nullable=True)
    bank_doc_name = Column(String(255), nullable=True)
    deal_amount = Column(Numeric(18, 0), nullable=False)
    booking_fee_amount = Column(Float, nullable=False, default=1000.0)
    payment_method = Column(String(30), nullable=True)
    payment_transaction_id = Column(String(120), nullable=True)
    payment_status = Column(String(20), nullable=False, default=PaymentStatus.INITIATED.value)
    paid_at = Column(DateTime, nullable=True)
    assigned_field_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    booking_status = Column(String(30), nullable=False, default=BookingStatus.BOOKED.value)
    registry_date = Column(Date, nullable=True)
    registry_time = Column(Time, nullable=True)
    registry_location = Column(String(255), nullable=True)
    registry_proof_url = Column(String(500), nullable=True)
    registry_proof_name = Column(String(255), nullable=True)
    registry_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class SellLandRegistryProof(Base):
    __tablename__ = "sell_land_registry_proofs"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("sell_land_bookings.id"), nullable=False, index=True)
    file_url = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
