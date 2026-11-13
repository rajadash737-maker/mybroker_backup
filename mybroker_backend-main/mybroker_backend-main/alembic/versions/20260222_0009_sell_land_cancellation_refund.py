"""add sell land cancellation and refund fields

Revision ID: 20260222_0009
Revises: 20260220_0008
Create Date: 2026-02-22 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260222_0009"
down_revision = "20260220_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sell_land_requests",
        sa.Column("cancellation_reason", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("refund_due_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("refund_completed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sell_land_requests", "refund_completed_at")
    op.drop_column("sell_land_requests", "refund_due_at")
    op.drop_column("sell_land_requests", "cancelled_at")
    op.drop_column("sell_land_requests", "cancellation_reason")
