"""Property booking cancellation and refund ledger.

Revision ID: 20261117_0047_property_booking_refunds
Revises: 20261117_0046_site_visit_completion_audit_event
"""

from alembic import op
import sqlalchemy as sa


revision = "20261117_0047_property_booking_refunds"
down_revision = "20261117_0046_site_visit_completion_audit_event"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "property_booking_refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("sell_land_bookings.id"), nullable=False),
        sa.Column("listing_id", sa.Integer(), sa.ForeignKey("sell_land_requests.id"), nullable=False),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("cancellation_actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("cancellation_actor_role", sa.String(length=30), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=False),
        sa.Column("previous_listing_status", sa.String(length=20), nullable=False),
        sa.Column("refund_decision", sa.String(length=20), nullable=False),
        sa.Column("approved_refund_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("original_captured_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_order_id", sa.Integer(), sa.ForeignKey("razorpay_payment_orders.id"), nullable=False),
        sa.Column("refund_status", sa.String(length=30), nullable=False),
        sa.Column("buyer_upi_ciphertext", sa.Text(), nullable=True),
        sa.Column("buyer_upi_submitted_at", sa.DateTime(), nullable=True),
        sa.Column("actual_refunded_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("transaction_reference", sa.String(length=120), nullable=True),
        sa.Column("confirmation_note", sa.String(length=500), nullable=True),
        sa.Column("accounting_actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("accounting_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("accounting_failed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("booking_id", name="uq_property_booking_refund_booking"),
        sa.UniqueConstraint("transaction_reference", name="uq_property_booking_refund_transaction_ref"),
        sa.CheckConstraint("refund_decision IN ('REFUND', 'NO_REFUND')", name="ck_property_booking_refund_decision"),
        sa.CheckConstraint("refund_status IN ('AWAITING_BUYER_DETAILS', 'PENDING_ACCOUNTING', 'CONFIRMED', 'FAILED', 'NOT_REQUIRED')", name="ck_property_booking_refund_status"),
        sa.CheckConstraint("original_captured_amount > 0 AND approved_refund_amount >= 0", name="ck_property_booking_refund_amounts_nonnegative"),
        sa.CheckConstraint("(refund_decision = 'REFUND' AND approved_refund_amount > 0) OR (refund_decision = 'NO_REFUND' AND approved_refund_amount = 0)", name="ck_property_booking_refund_decision_amount"),
    )
    op.create_index("ix_property_booking_refunds_booking_id", "property_booking_refunds", ["booking_id"])
    op.create_index("ix_property_booking_refunds_listing_id", "property_booking_refunds", ["listing_id"])
    op.create_index("ix_property_booking_refunds_buyer_id", "property_booking_refunds", ["buyer_id"])
    op.create_index("ix_property_booking_refunds_refund_status", "property_booking_refunds", ["refund_status"])

    op.create_table(
        "property_booking_refund_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("refund_id", sa.Integer(), sa.ForeignKey("property_booking_refunds.id"), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("sell_land_bookings.id"), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("actor_role", sa.String(length=30), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_property_booking_refund_events_refund_id", "property_booking_refund_events", ["refund_id"])
    op.create_index("ix_property_booking_refund_events_booking_id", "property_booking_refund_events", ["booking_id"])


def downgrade() -> None:
    op.drop_index("ix_property_booking_refund_events_booking_id", table_name="property_booking_refund_events")
    op.drop_index("ix_property_booking_refund_events_refund_id", table_name="property_booking_refund_events")
    op.drop_table("property_booking_refund_events")
    op.drop_index("ix_property_booking_refunds_refund_status", table_name="property_booking_refunds")
    op.drop_index("ix_property_booking_refunds_buyer_id", table_name="property_booking_refunds")
    op.drop_index("ix_property_booking_refunds_listing_id", table_name="property_booking_refunds")
    op.drop_index("ix_property_booking_refunds_booking_id", table_name="property_booking_refunds")
    op.drop_table("property_booking_refunds")
