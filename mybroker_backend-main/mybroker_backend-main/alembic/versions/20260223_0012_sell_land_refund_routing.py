"""add refund routing fields for admin/accounting workflow

Revision ID: 20260223_0012
Revises: 20260222_0011
Create Date: 2026-02-23 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260223_0012"
down_revision = "20260222_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sell_land_requests",
        sa.Column(
            "cancellation_requires_admin_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("refund_forwarded_to_accounting_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("refund_forwarded_to_accounting_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_sell_land_requests_refund_forwarded_to_accounting_by_id",
        "sell_land_requests",
        ["refund_forwarded_to_accounting_by_id"],
    )
    op.create_foreign_key(
        "fk_sell_land_requests_refund_forwarded_to_accounting_by_id_users",
        "sell_land_requests",
        "users",
        ["refund_forwarded_to_accounting_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sell_land_requests_refund_forwarded_to_accounting_by_id_users",
        "sell_land_requests",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_sell_land_requests_refund_forwarded_to_accounting_by_id",
        table_name="sell_land_requests",
    )
    op.drop_column("sell_land_requests", "refund_forwarded_to_accounting_at")
    op.drop_column("sell_land_requests", "refund_forwarded_to_accounting_by_id")
    op.drop_column("sell_land_requests", "cancellation_requires_admin_review")
