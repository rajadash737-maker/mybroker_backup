"""add refund upi id for sell land cancellation

Revision ID: 20260222_0010
Revises: 20260222_0009
Create Date: 2026-02-22 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260222_0010"
down_revision = "20260222_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sell_land_requests",
        sa.Column("refund_upi_id", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sell_land_requests", "refund_upi_id")
