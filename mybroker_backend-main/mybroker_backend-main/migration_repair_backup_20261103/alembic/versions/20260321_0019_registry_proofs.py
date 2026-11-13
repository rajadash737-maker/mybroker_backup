"""add registry proofs table

Revision ID: b9d3f2c1a0b1
Revises: a67d159913e2
Create Date: 2026-03-21 22:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b9d3f2c1a0b1"
down_revision = "a67d159913e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sell_land_registry_proofs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("sell_land_bookings.id"), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sell_land_registry_proofs_booking_id", "sell_land_registry_proofs", ["booking_id"])


def downgrade() -> None:
    op.drop_index("ix_sell_land_registry_proofs_booking_id", table_name="sell_land_registry_proofs")
    op.drop_table("sell_land_registry_proofs")
