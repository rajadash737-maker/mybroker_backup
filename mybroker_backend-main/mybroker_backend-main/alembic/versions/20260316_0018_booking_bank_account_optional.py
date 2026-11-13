"""make booking bank account optional

Revision ID: 20260316_0018
Revises: 20260316_0017
Create Date: 2026-03-16 20:24:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260316_0018"
down_revision = "20260316_0017"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("sell_land_bookings"):
        return

    if _has_column(inspector, "sell_land_bookings", "bank_account"):
        op.alter_column(
            "sell_land_bookings",
            "bank_account",
            existing_type=sa.String(length=30),
            nullable=True,
            server_default="",
        )
    else:
        op.add_column(
            "sell_land_bookings",
            sa.Column("bank_account", sa.String(length=30), nullable=True, server_default=""),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("sell_land_bookings"):
        return

    if _has_column(inspector, "sell_land_bookings", "bank_account"):
        op.alter_column(
            "sell_land_bookings",
            "bank_account",
            existing_type=sa.String(length=30),
            nullable=False,
            server_default=None,
        )
