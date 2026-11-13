"""Change sell_land_requests.expected_price to numeric

Revision ID: 20260404_0022
Revises: 20260403_0021_add_seller_category
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260404_0022"
down_revision = "20260403_0021_add_seller_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "sell_land_requests",
        "expected_price",
        existing_type=sa.Float(),
        type_=sa.Numeric(18, 0),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "sell_land_requests",
        "expected_price",
        existing_type=sa.Numeric(18, 0),
        type_=sa.Float(),
        existing_nullable=True,
    )
