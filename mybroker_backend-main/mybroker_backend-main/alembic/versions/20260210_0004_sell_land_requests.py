"""add sell_land_requests table

Revision ID: 20260210_0004
Revises: 20260208_0003
Create Date: 2026-02-10 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260210_0004"
down_revision = "20260208_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sell_land_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("owner_name", sa.String(length=100), nullable=False),
        sa.Column("owner_mobile", sa.String(length=20), nullable=False),
        sa.Column("land_type", sa.String(length=20), nullable=False),
        sa.Column("ownership_type", sa.String(length=30), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("pincode", sa.String(length=10), nullable=False),
        sa.Column("area", sa.Float(), nullable=False),
        sa.Column("area_unit", sa.String(length=10), nullable=False),
        sa.Column("expected_price", sa.Float(), nullable=False),
        sa.Column("negotiable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sell_land_requests_id", "sell_land_requests", ["id"], unique=False)
    op.create_index("ix_sell_land_requests_user_id", "sell_land_requests", ["user_id"], unique=False)
    op.create_index("ix_sell_land_requests_owner_mobile", "sell_land_requests", ["owner_mobile"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sell_land_requests_owner_mobile", table_name="sell_land_requests")
    op.drop_index("ix_sell_land_requests_user_id", table_name="sell_land_requests")
    op.drop_index("ix_sell_land_requests_id", table_name="sell_land_requests")
    op.drop_table("sell_land_requests")
