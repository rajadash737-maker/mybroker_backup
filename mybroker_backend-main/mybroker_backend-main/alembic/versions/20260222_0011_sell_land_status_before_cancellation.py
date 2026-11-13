"""add status_before_cancellation in sell land requests

Revision ID: 20260222_0011
Revises: 20260222_0010
Create Date: 2026-02-22 01:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260222_0011"
down_revision = "20260222_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sell_land_requests",
        sa.Column("status_before_cancellation", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sell_land_requests", "status_before_cancellation")
