"""add sell land favorites table

Revision ID: 20260224_0014
Revises: 20260223_0013
Create Date: 2026-02-24 12:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260224_0014"
down_revision = "20260223_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sell_land_favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["sell_land_requests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "request_id", name="uq_sell_land_favorites_user_request"),
    )
    op.create_index("ix_sell_land_favorites_id", "sell_land_favorites", ["id"])
    op.create_index("ix_sell_land_favorites_user_id", "sell_land_favorites", ["user_id"])
    op.create_index("ix_sell_land_favorites_request_id", "sell_land_favorites", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_sell_land_favorites_request_id", table_name="sell_land_favorites")
    op.drop_index("ix_sell_land_favorites_user_id", table_name="sell_land_favorites")
    op.drop_index("ix_sell_land_favorites_id", table_name="sell_land_favorites")
    op.drop_table("sell_land_favorites")
