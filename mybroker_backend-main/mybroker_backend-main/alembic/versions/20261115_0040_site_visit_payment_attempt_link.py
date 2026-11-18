"""Link shared Razorpay orders to Site Visit requests for retry history.

Revision ID: 20261115_0040_site_visit_payment_attempt_link
Revises: 20261115_0039_site_visit_payment_context
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20261115_0040_site_visit_payment_attempt_link"
down_revision = "20261115_0039_site_visit_payment_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "razorpay_payment_orders",
        sa.Column("site_visit_request_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "razorpay_payment_orders",
        sa.Column("buyer_cancel_reported_at", sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        "fk_payment_order_site_visit",
        "razorpay_payment_orders",
        "site_visit_requests",
        ["site_visit_request_id"],
        ["id"],
    )
    # Adopt the one Site Visit order reference created before attempt history
    # was linked. Older attempted payments remain associated for late webhooks.
    op.execute(
        sa.text(
            "UPDATE razorpay_payment_orders "
            "SET site_visit_request_id = ("
            "SELECT site_visit_requests.id FROM site_visit_requests "
            "WHERE site_visit_requests.payment_order_id = razorpay_payment_orders.order_id) "
            "WHERE payment_context = 'site_visit' AND site_visit_request_id IS NULL "
            "AND EXISTS (SELECT 1 FROM site_visit_requests "
            "WHERE site_visit_requests.payment_order_id = razorpay_payment_orders.order_id)"
        )
    )
    op.execute(
        sa.text(
            "UPDATE razorpay_payment_orders "
            "SET status = 'CANCEL_REPORTED', buyer_cancel_reported_at = updated_at "
            "WHERE payment_context = 'site_visit' AND status = 'CANCELLED'"
        )
    )
    op.create_index(
        "ix_razorpay_payment_orders_site_visit_request_id",
        "razorpay_payment_orders",
        ["site_visit_request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_razorpay_payment_orders_site_visit_request_id",
        table_name="razorpay_payment_orders",
    )
    op.drop_constraint(
        "fk_payment_order_site_visit",
        "razorpay_payment_orders",
        type_="foreignkey",
    )
    op.drop_column("razorpay_payment_orders", "buyer_cancel_reported_at")
    op.drop_column("razorpay_payment_orders", "site_visit_request_id")
