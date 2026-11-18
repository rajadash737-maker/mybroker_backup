from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.sell_land.constants import PaymentStatus
from app.site_visits.constants import (
    AssignmentAction,
    AssignmentActorType,
    SiteVisitStatus,
)


class SiteVisitRequest(Base):
    __tablename__ = "site_visit_requests"
    __table_args__ = (
        CheckConstraint("site_visit_fee_paise >= 0", name="ck_site_visit_requests_fee_nonnegative"),
        CheckConstraint("visitor_count BETWEEN 1 AND 20", name="ck_site_visit_requests_visitor_count"),
        CheckConstraint(
            "status IN ('pending_payment', 'pending', 'assigned', 'scheduled', 'in_progress', "
            "'completed', 'correction_required', 'cancelled', 'refund_pending', 'refunded', 'refund_failed')",
            name="ck_site_visit_requests_status",
        ),
        CheckConstraint(
            "payment_status IN ('initiated', 'success', 'failed')",
            name="ck_site_visit_requests_payment_status",
        ),
        CheckConstraint(
            "completion_code_failed_attempts BETWEEN 0 AND 5",
            name="ck_site_visit_requests_completion_attempts_range",
        ),
        UniqueConstraint("buyer_id", "submission_key", name="uq_site_visit_requests_buyer_submission"),
        UniqueConstraint("payment_order_id", name="uq_site_visit_requests_payment_order"),
        UniqueConstraint("payment_id", name="uq_site_visit_requests_payment_id"),
        {"mysql_engine": "InnoDB"},
    )

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(
        Integer,
        ForeignKey("sell_land_requests.id", name="fk_site_visit_requests_listing_id_sell_land_requests"),
        nullable=False,
        index=True,
    )
    buyer_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_site_visit_requests_buyer_id_users"),
        nullable=False,
        index=True,
    )
    seller_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_site_visit_requests_seller_id_users"),
        nullable=False,
        index=True,
    )
    assigned_field_officer_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_site_visit_requests_assigned_officer_id_users"),
        nullable=True,
        index=True,
    )

    # Booking-time display snapshots keep the request readable if profile or listing text changes.
    property_name_snapshot = Column(String(150), nullable=False)
    listing_code_snapshot = Column(String(30), nullable=True)
    buyer_name_snapshot = Column(String(120), nullable=False)
    buyer_mobile_snapshot = Column(String(20), nullable=False)
    seller_name_snapshot = Column(String(120), nullable=False)
    seller_mobile_snapshot = Column(String(20), nullable=False)

    preferred_visit_date = Column(Date, nullable=False)
    preferred_visit_time = Column(Time, nullable=False)
    visitor_count = Column(Integer, nullable=False)
    pickup_address = Column(Text, nullable=False)
    message = Column(Text, nullable=True)
    submission_key = Column(String(64), nullable=True)

    site_visit_fee_paise = Column(Integer, nullable=False)
    status = Column(
        String(30),
        nullable=False,
        default=SiteVisitStatus.PENDING_PAYMENT.value,
        server_default=SiteVisitStatus.PENDING_PAYMENT.value,
        index=True,
    )
    payment_status = Column(
        String(20),
        nullable=False,
        default=PaymentStatus.INITIATED.value,
        server_default=PaymentStatus.INITIATED.value,
        index=True,
    )
    payment_order_id = Column(String(64), nullable=True)
    payment_id = Column(String(64), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completion_code_hash = Column(String(64), nullable=True)
    completion_code_encrypted = Column(String(256), nullable=True)
    completion_code_expires_at = Column(DateTime, nullable=True)
    completion_code_failed_attempts = Column(Integer, nullable=False, default=0, server_default="0")
    completion_code_used_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(String(500), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id", name="fk_site_visit_requests_cancelled_by_users"), nullable=True, index=True)
    cancellation_actor_role = Column(String(30), nullable=True)
    correction_reason = Column(String(500), nullable=True)
    correction_requested_at = Column(DateTime, nullable=True)
    correction_requested_by_id = Column(Integer, ForeignKey("users.id", name="fk_site_visit_requests_correction_requested_by_users"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    listing = relationship("SellLandRequest", foreign_keys=[listing_id])
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])
    assigned_field_officer = relationship("User", foreign_keys=[assigned_field_officer_id])
    assignment_history = relationship(
        "SiteVisitAssignment",
        back_populates="site_visit",
        order_by="SiteVisitAssignment.created_at",
    )
    workflow_history = relationship(
        "SiteVisitWorkflowHistory",
        back_populates="site_visit",
        order_by="SiteVisitWorkflowHistory.created_at",
    )
    refund_record = relationship("SiteVisitRefund", back_populates="site_visit", uselist=False)


class SiteVisitAssignment(Base):
    __tablename__ = "site_visit_assignment_history"
    __table_args__ = (
        CheckConstraint(
            "action IN ('assigned', 'reassigned', 'unassigned')",
            name="ck_site_visit_assignment_history_action",
        ),
        CheckConstraint(
            "actor_type IN ('system', 'admin', 'super_admin')",
            name="ck_site_visit_assignment_history_actor_type",
        ),
        CheckConstraint(
            "(action = 'unassigned' AND field_officer_id IS NULL) OR "
            "(action IN ('assigned', 'reassigned') AND field_officer_id IS NOT NULL)",
            name="ck_site_visit_assignment_history_target",
        ),
        {"mysql_engine": "InnoDB"},
    )

    id = Column(Integer, primary_key=True, index=True)
    site_visit_request_id = Column(
        Integer,
        ForeignKey(
            "site_visit_requests.id",
            name="fk_site_visit_assignment_history_request_id_site_visit_requests",
        ),
        nullable=False,
        index=True,
    )
    previous_field_officer_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_site_visit_assignment_history_previous_officer_users"),
        nullable=True,
        index=True,
    )
    field_officer_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_site_visit_assignment_history_field_officer_users"),
        nullable=True,
        index=True,
    )
    actor_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_site_visit_assignment_history_actor_users"),
        nullable=True,
        index=True,
    )
    action = Column(String(20), nullable=False)
    actor_type = Column(String(20), nullable=False)
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    site_visit = relationship("SiteVisitRequest", back_populates="assignment_history")
    previous_field_officer = relationship("User", foreign_keys=[previous_field_officer_id])
    field_officer = relationship("User", foreign_keys=[field_officer_id])
    actor = relationship("User", foreign_keys=[actor_id])


class SiteVisitWorkflowHistory(Base):
    __tablename__ = "site_visit_workflow_history"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('correction_requested', 'buyer_resubmitted', 'buyer_cancelled', 'admin_cancelled', "
            "'in_progress_reassigned', 'in_progress_unassigned', 'in_progress_cancelled', 'field_officer_completed')",
            name="ck_site_visit_workflow_history_event_type",
        ),
        {"mysql_engine": "InnoDB"},
    )

    id = Column(Integer, primary_key=True, index=True)
    site_visit_request_id = Column(
        Integer,
        ForeignKey("site_visit_requests.id", name="fk_site_visit_workflow_history_request_id"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(40), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", name="fk_site_visit_workflow_history_actor_id"), nullable=False, index=True)
    actor_role = Column(String(30), nullable=False)
    reason = Column(String(500), nullable=True)
    previous_values = Column(JSON, nullable=True)
    updated_values = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    site_visit = relationship("SiteVisitRequest", back_populates="workflow_history")
    actor = relationship("User")


class SiteVisitRefund(Base):
    __tablename__ = "site_visit_refunds"
    __table_args__ = (
        CheckConstraint("eligible_amount_paise > 0", name="ck_site_visit_refunds_eligible_amount_positive"),
        CheckConstraint("actual_refunded_amount_paise IS NULL OR (actual_refunded_amount_paise > 0 AND actual_refunded_amount_paise <= eligible_amount_paise)", name="ck_site_visit_refunds_actual_amount_in_range"),
        CheckConstraint(
            "status IN ('pending_details', 'pending', 'refunded', 'failed')",
            name="ck_site_visit_refunds_status",
        ),
        CheckConstraint(
            "status != 'refunded' OR (actual_refunded_amount_paise IS NOT NULL AND upi_transaction_reference IS NOT NULL AND refunded_at IS NOT NULL AND accounting_user_id IS NOT NULL)",
            name="ck_site_visit_refunds_confirmed_fields",
        ),
        CheckConstraint(
            "status != 'failed' OR (failure_reason IS NOT NULL AND accounting_user_id IS NOT NULL)",
            name="ck_site_visit_refunds_failed_fields",
        ),
        UniqueConstraint("site_visit_request_id", name="uq_site_visit_refunds_request_id"),
        UniqueConstraint("upi_transaction_reference", name="uq_site_visit_refunds_upi_reference"),
        {"mysql_engine": "InnoDB"},
    )

    id = Column(Integer, primary_key=True, index=True)
    site_visit_request_id = Column(
        Integer,
        ForeignKey("site_visit_requests.id", name="fk_site_visit_refunds_request_id"),
        nullable=False,
        index=True,
    )
    original_payment_reference = Column(String(120), nullable=True)
    eligible_amount_paise = Column(Integer, nullable=False)
    actual_refunded_amount_paise = Column(Integer, nullable=True)
    buyer_upi_ciphertext = Column(String(512), nullable=True)
    upi_transaction_reference = Column(String(120), nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    accounting_user_id = Column(Integer, ForeignKey("users.id", name="fk_site_visit_refunds_accounting_user_id"), nullable=True, index=True)
    internal_note = Column(Text, nullable=True)
    failure_reason = Column(String(500), nullable=True)
    status = Column(String(30), nullable=False, default="pending_details", server_default="pending_details", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    site_visit = relationship("SiteVisitRequest", back_populates="refund_record")
    accounting_user = relationship("User", foreign_keys=[accounting_user_id])
    history = relationship("SiteVisitRefundHistory", back_populates="refund", order_by="SiteVisitRefundHistory.created_at")


class SiteVisitRefundHistory(Base):
    __tablename__ = "site_visit_refund_history"
    __table_args__ = (
        CheckConstraint("action IN ('opened', 'details_submitted', 'confirmed', 'failed')", name="ck_site_visit_refund_history_action"),
        {"mysql_engine": "InnoDB"},
    )

    id = Column(Integer, primary_key=True, index=True)
    refund_id = Column(Integer, ForeignKey("site_visit_refunds.id", name="fk_site_visit_refund_history_refund_id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", name="fk_site_visit_refund_history_actor_id"), nullable=False, index=True)
    actor_role = Column(String(30), nullable=False)
    action = Column(String(30), nullable=False)
    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    actual_amount_paise = Column(Integer, nullable=True)
    transaction_reference = Column(String(120), nullable=True)
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    refund = relationship("SiteVisitRefund", back_populates="history")
    actor = relationship("User")


# Keep enum imports visible to migration autogeneration tooling and callers that
# build assignment records from these shared domain values.
__all__ = [
    "SiteVisitRequest",
    "SiteVisitAssignment",
    "SiteVisitWorkflowHistory",
    "SiteVisitRefund",
    "SiteVisitRefundHistory",
    "SiteVisitStatus",
    "AssignmentAction",
    "AssignmentActorType",
]
