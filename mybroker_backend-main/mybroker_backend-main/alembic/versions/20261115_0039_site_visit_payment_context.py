"""Persist payment context on shared Razorpay order records.

Revision ID: 20261115_0039_site_visit_payment_context
Revises: 20261115_0038_site_visit_foundation
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20261115_0039_site_visit_payment_context"
down_revision = "20261115_0038_site_visit_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "razorpay_payment_orders",
        sa.Column("payment_context", sa.String(length=20), server_default="buyer", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("razorpay_payment_orders", "payment_context")
