"""add offer workflow fields and listing lock support

Revision ID: 20260225_0016
Revises: 20260225_0015
Create Date: 2026-02-25 16:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260225_0016"
down_revision = "20260225_0015"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("sell_land_offers"):
        if not _has_column(inspector, "sell_land_offers", "status"):
            op.add_column("sell_land_offers", sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"))
        if not _has_column(inspector, "sell_land_offers", "counter_amount"):
            op.add_column("sell_land_offers", sa.Column("counter_amount", sa.Float(), nullable=True))
        if not _has_column(inspector, "sell_land_offers", "seller_response_at"):
            op.add_column("sell_land_offers", sa.Column("seller_response_at", sa.DateTime(), nullable=True))
        if not _has_column(inspector, "sell_land_offers", "updated_at"):
            op.add_column(
                "sell_land_offers",
                sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            )

        index_names = {idx["name"] for idx in inspector.get_indexes("sell_land_offers")}
        if "ix_sell_land_offers_status" not in index_names:
            op.create_index("ix_sell_land_offers_status", "sell_land_offers", ["status"])

    if inspector.has_table("sell_land_requests"):
        if not _has_column(inspector, "sell_land_requests", "offer_locked_by_buyer_id"):
            op.add_column("sell_land_requests", sa.Column("offer_locked_by_buyer_id", sa.Integer(), nullable=True))
            op.create_foreign_key(
                "fk_sell_land_requests_offer_locked_by_buyer",
                "sell_land_requests",
                "users",
                ["offer_locked_by_buyer_id"],
                ["id"],
            )
        if not _has_column(inspector, "sell_land_requests", "offer_lock_expires_at"):
            op.add_column("sell_land_requests", sa.Column("offer_lock_expires_at", sa.DateTime(), nullable=True))
        if not _has_column(inspector, "sell_land_requests", "accepted_offer_id"):
            op.add_column("sell_land_requests", sa.Column("accepted_offer_id", sa.Integer(), nullable=True))
            op.create_foreign_key(
                "fk_sell_land_requests_accepted_offer",
                "sell_land_requests",
                "sell_land_offers",
                ["accepted_offer_id"],
                ["id"],
            )

        index_names = {idx["name"] for idx in inspector.get_indexes("sell_land_requests")}
        if "ix_sell_land_requests_offer_locked_by_buyer_id" not in index_names:
            op.create_index("ix_sell_land_requests_offer_locked_by_buyer_id", "sell_land_requests", ["offer_locked_by_buyer_id"])
        if "ix_sell_land_requests_offer_lock_expires_at" not in index_names:
            op.create_index("ix_sell_land_requests_offer_lock_expires_at", "sell_land_requests", ["offer_lock_expires_at"])
        if "ix_sell_land_requests_accepted_offer_id" not in index_names:
            op.create_index("ix_sell_land_requests_accepted_offer_id", "sell_land_requests", ["accepted_offer_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("sell_land_requests"):
        index_names = {idx["name"] for idx in inspector.get_indexes("sell_land_requests")}
        if "ix_sell_land_requests_accepted_offer_id" in index_names:
            op.drop_index("ix_sell_land_requests_accepted_offer_id", table_name="sell_land_requests")
        if "ix_sell_land_requests_offer_lock_expires_at" in index_names:
            op.drop_index("ix_sell_land_requests_offer_lock_expires_at", table_name="sell_land_requests")
        if "ix_sell_land_requests_offer_locked_by_buyer_id" in index_names:
            op.drop_index("ix_sell_land_requests_offer_locked_by_buyer_id", table_name="sell_land_requests")

        fk_names = {fk["name"] for fk in inspector.get_foreign_keys("sell_land_requests") if fk.get("name")}
        if "fk_sell_land_requests_accepted_offer" in fk_names:
            op.drop_constraint("fk_sell_land_requests_accepted_offer", "sell_land_requests", type_="foreignkey")
        if "fk_sell_land_requests_offer_locked_by_buyer" in fk_names:
            op.drop_constraint("fk_sell_land_requests_offer_locked_by_buyer", "sell_land_requests", type_="foreignkey")

        if _has_column(inspector, "sell_land_requests", "accepted_offer_id"):
            op.drop_column("sell_land_requests", "accepted_offer_id")
        if _has_column(inspector, "sell_land_requests", "offer_lock_expires_at"):
            op.drop_column("sell_land_requests", "offer_lock_expires_at")
        if _has_column(inspector, "sell_land_requests", "offer_locked_by_buyer_id"):
            op.drop_column("sell_land_requests", "offer_locked_by_buyer_id")

    if inspector.has_table("sell_land_offers"):
        index_names = {idx["name"] for idx in inspector.get_indexes("sell_land_offers")}
        if "ix_sell_land_offers_status" in index_names:
            op.drop_index("ix_sell_land_offers_status", table_name="sell_land_offers")

        if _has_column(inspector, "sell_land_offers", "updated_at"):
            op.drop_column("sell_land_offers", "updated_at")
        if _has_column(inspector, "sell_land_offers", "seller_response_at"):
            op.drop_column("sell_land_offers", "seller_response_at")
        if _has_column(inspector, "sell_land_offers", "counter_amount"):
            op.drop_column("sell_land_offers", "counter_amount")
        if _has_column(inspector, "sell_land_offers", "status"):
            op.drop_column("sell_land_offers", "status")
