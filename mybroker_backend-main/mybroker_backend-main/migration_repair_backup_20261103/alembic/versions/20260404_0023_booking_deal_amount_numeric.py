"""Change sell_land_bookings.deal_amount to numeric

Revision ID: 20260404_0023
Revises: 20260404_0022
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260404_0023"
down_revision = "20260404_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "sell_land_bookings",
        "deal_amount",
        existing_type=sa.Float(),
        type_=sa.Numeric(18, 0),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "sell_land_bookings",
        "deal_amount",
        existing_type=sa.Numeric(18, 0),
        type_=sa.Float(),
        existing_nullable=False,
    )
