"""add sell land review fields

Revision ID: 20260218_0007
Revises: 20260215_0006
Create Date: 2026-02-18 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260218_0007"
down_revision = "20260215_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sell_land_requests",
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
    )
    op.create_index(
        "ix_sell_land_requests_reviewed_by_id",
        "sell_land_requests",
        ["reviewed_by_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_sell_land_requests_reviewed_by_id_users",
        "sell_land_requests",
        "users",
        ["reviewed_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_sell_land_requests_reviewed_by_id_users", "sell_land_requests", type_="foreignkey")
    op.drop_index("ix_sell_land_requests_reviewed_by_id", table_name="sell_land_requests")
    op.drop_column("sell_land_requests", "rejection_reason")
    op.drop_column("sell_land_requests", "reviewed_at")
    op.drop_column("sell_land_requests", "reviewed_by_id")
