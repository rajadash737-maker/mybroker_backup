"""Add a nullable unique key for provider webhook event IDs.

Revision ID: 20261115_0041_unique_razorpay_webhook_event_key
Revises: 20261115_0040_site_visit_payment_attempt_link
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20261115_0041_unique_razorpay_webhook_event_key"
down_revision = "20261115_0040_site_visit_payment_attempt_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing event_id values came from the payload, not Razorpay's event-ID
    # header. Leave them unchanged for audit; new canonical keys start NULL.
    op.add_column("razorpay_webhook_logs", sa.Column("event_key", sa.String(length=80), nullable=True))
    op.create_index(
        "ix_razorpay_webhook_logs_event_key",
        "razorpay_webhook_logs",
        ["event_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_razorpay_webhook_logs_event_key", table_name="razorpay_webhook_logs")
    op.drop_column("razorpay_webhook_logs", "event_key")
