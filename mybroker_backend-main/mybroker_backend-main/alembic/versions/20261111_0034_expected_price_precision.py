"""Increase expected_price fractional precision.

Revision ID: 20261111_0034_expected_price_precision
Revises: 20261110_0033_social_links_ratings
Create Date: 2026-11-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20261111_0034_expected_price_precision"
down_revision = "20261110_0033_social_links_ratings"
branch_labels = None
depends_on = None


_TARGET_MAX = "999999999999.999999"


def upgrade() -> None:
    bind = op.get_bind()
    out_of_range = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM sell_land_requests "
            "WHERE expected_price IS NOT NULL AND "
            f"(expected_price > {_TARGET_MAX} OR expected_price < -{_TARGET_MAX})"
        )
    ).scalar_one()
    if out_of_range:
        raise RuntimeError(
            "Cannot convert sell_land_requests.expected_price to Numeric(18, 6): "
            f"{out_of_range} value(s) exceed the target range "
            f"[-{_TARGET_MAX}, {_TARGET_MAX}]. Resolve these values explicitly before retrying."
        )

    op.alter_column(
        "sell_land_requests",
        "expected_price",
        existing_type=sa.Numeric(18, 0),
        type_=sa.Numeric(18, 6),
        existing_nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    fractional_values = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM sell_land_requests "
            "WHERE expected_price IS NOT NULL "
            "AND expected_price <> ROUND(expected_price, 0)"
        )
    ).scalar_one()
    if fractional_values:
        raise RuntimeError(
            "Cannot downgrade sell_land_requests.expected_price to Numeric(18, 0): "
            f"{fractional_values} value(s) have fractional digits. "
            "Resolve these values explicitly before retrying."
        )

    op.alter_column(
        "sell_land_requests",
        "expected_price",
        existing_type=sa.Numeric(18, 6),
        type_=sa.Numeric(18, 0),
        existing_nullable=True,
    )
