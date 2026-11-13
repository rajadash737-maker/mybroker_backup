"""Add versioned land pricing storage fields.

Revision ID: 20261111_0035_versioned_land_pricing_storage
Revises: 20261111_0034_expected_price_precision
Create Date: 2026-11-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20261111_0035_versioned_land_pricing_storage"
down_revision = "20261111_0034_expected_price_precision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The server default both backfills existing rows as legacy version 1 and
    # preserves the required default for inserts from older application code.
    op.add_column(
        "sell_land_requests",
        sa.Column("pricing_version", sa.Integer(), server_default="1", nullable=False),
    )
    # Existing listings have no known original selected-unit rate to backfill.
    op.add_column(
        "sell_land_requests",
        sa.Column("entered_unit_price", sa.Numeric(18, 6), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    incompatible_rows = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM sell_land_requests "
            "WHERE pricing_version = 2 OR entered_unit_price IS NOT NULL"
        )
    ).scalar_one()
    if incompatible_rows:
        raise RuntimeError(
            "Cannot downgrade versioned land pricing storage: "
            f"{incompatible_rows} row(s) contain pricing_version=2 or entered_unit_price data. "
            "Resolve or preserve this data explicitly before retrying."
        )

    op.drop_column("sell_land_requests", "entered_unit_price")
    op.drop_column("sell_land_requests", "pricing_version")
