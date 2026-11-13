"""add refund payment detail fields in sell land requests

Revision ID: 20260223_0013
Revises: 20260223_0012
Create Date: 2026-02-23 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260223_0013"
down_revision = "20260223_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sell_land_requests",
        sa.Column("refund_amount", sa.Float(), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("refund_transaction_id", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("refund_confirmed_by_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_sell_land_requests_refund_confirmed_by_id",
        "sell_land_requests",
        ["refund_confirmed_by_id"],
    )
    op.create_foreign_key(
        "fk_sell_land_requests_refund_confirmed_by_id_users",
        "sell_land_requests",
        "users",
        ["refund_confirmed_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sell_land_requests_refund_confirmed_by_id_users",
        "sell_land_requests",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_sell_land_requests_refund_confirmed_by_id",
        table_name="sell_land_requests",
    )
    op.drop_column("sell_land_requests", "refund_confirmed_by_id")
    op.drop_column("sell_land_requests", "refund_transaction_id")
    op.drop_column("sell_land_requests", "refund_amount")
