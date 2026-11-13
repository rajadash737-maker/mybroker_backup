"""add sell land offers table

Revision ID: 20260225_0015
Revises: 20260224_0014
Create Date: 2026-02-25 10:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260225_0015"
down_revision = "20260224_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("sell_land_offers"):
        op.create_table(
            "sell_land_offers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("buyer_id", sa.Integer(), nullable=False),
            sa.Column("offered_amount", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["request_id"], ["sell_land_requests.id"]),
            sa.ForeignKeyConstraint(["buyer_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    index_names = {idx["name"] for idx in inspector.get_indexes("sell_land_offers")}
    if "ix_sell_land_offers_id" not in index_names:
        op.create_index("ix_sell_land_offers_id", "sell_land_offers", ["id"])
    if "ix_sell_land_offers_request_id" not in index_names:
        op.create_index("ix_sell_land_offers_request_id", "sell_land_offers", ["request_id"])
    if "ix_sell_land_offers_buyer_id" not in index_names:
        op.create_index("ix_sell_land_offers_buyer_id", "sell_land_offers", ["buyer_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("sell_land_offers"):
        return

    index_names = {idx["name"] for idx in inspector.get_indexes("sell_land_offers")}
    if "ix_sell_land_offers_buyer_id" in index_names:
        op.drop_index("ix_sell_land_offers_buyer_id", table_name="sell_land_offers")
    if "ix_sell_land_offers_request_id" in index_names:
        op.drop_index("ix_sell_land_offers_request_id", table_name="sell_land_offers")
    if "ix_sell_land_offers_id" in index_names:
        op.drop_index("ix_sell_land_offers_id", table_name="sell_land_offers")
    op.drop_table("sell_land_offers")
