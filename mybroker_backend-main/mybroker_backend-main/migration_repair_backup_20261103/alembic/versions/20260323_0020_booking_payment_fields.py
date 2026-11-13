"""add booking payment method and transaction id

Revision ID: 20260323_0020
Revises: b9d3f2c1a0b1
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260323_0020"
down_revision = "b9d3f2c1a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sell_land_bookings", sa.Column("payment_method", sa.String(length=30), nullable=True))
    op.add_column("sell_land_bookings", sa.Column("payment_transaction_id", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("sell_land_bookings", "payment_transaction_id")
    op.drop_column("sell_land_bookings", "payment_method")
