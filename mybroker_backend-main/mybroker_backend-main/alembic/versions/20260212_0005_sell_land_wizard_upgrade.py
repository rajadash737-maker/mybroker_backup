"""upgrade sell_land for wizard flow

Revision ID: 20260212_0005
Revises: 20260210_0004
Create Date: 2026-02-12 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260212_0005"
down_revision = "20260210_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sell_land_requests", sa.Column("listing_code", sa.String(length=30), nullable=True))
    op.add_column(
        "sell_land_requests",
        sa.Column("price_type", sa.String(length=20), nullable=False, server_default="total_price"),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("availability", sa.String(length=30), nullable=False, server_default="immediate"),
    )
    op.add_column("sell_land_requests", sa.Column("boundary_points", sa.Text(), nullable=True))
    op.add_column(
        "sell_land_requests",
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("draft_step", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("payment_required_amount", sa.Float(), nullable=False, server_default=sa.text("999")),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("payment_status", sa.String(length=20), nullable=False, server_default="initiated"),
    )

    op.alter_column("sell_land_requests", "title", existing_type=sa.String(length=150), nullable=True)
    op.alter_column("sell_land_requests", "owner_name", existing_type=sa.String(length=100), nullable=True)
    op.alter_column("sell_land_requests", "owner_mobile", existing_type=sa.String(length=20), nullable=True)
    op.alter_column("sell_land_requests", "location", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("sell_land_requests", "city", existing_type=sa.String(length=100), nullable=True)
    op.alter_column("sell_land_requests", "state", existing_type=sa.String(length=100), nullable=True)
    op.alter_column("sell_land_requests", "pincode", existing_type=sa.String(length=10), nullable=True)
    op.alter_column("sell_land_requests", "area", existing_type=sa.Float(), nullable=True)
    op.alter_column("sell_land_requests", "expected_price", existing_type=sa.Float(), nullable=True)
    op.alter_column("sell_land_requests", "status", existing_type=sa.String(length=20), server_default="draft")

    op.create_index("ix_sell_land_requests_listing_code", "sell_land_requests", ["listing_code"], unique=True)

    op.create_table(
        "sell_land_media",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=True),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["request_id"], ["sell_land_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sell_land_media_id", "sell_land_media", ["id"], unique=False)
    op.create_index("ix_sell_land_media_request_id", "sell_land_media", ["request_id"], unique=False)

    op.create_table(
        "sell_land_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="initiated"),
        sa.Column("provider_ref", sa.String(length=100), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["request_id"], ["sell_land_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sell_land_payments_id", "sell_land_payments", ["id"], unique=False)
    op.create_index("ix_sell_land_payments_request_id", "sell_land_payments", ["request_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sell_land_payments_request_id", table_name="sell_land_payments")
    op.drop_index("ix_sell_land_payments_id", table_name="sell_land_payments")
    op.drop_table("sell_land_payments")

    op.drop_index("ix_sell_land_media_request_id", table_name="sell_land_media")
    op.drop_index("ix_sell_land_media_id", table_name="sell_land_media")
    op.drop_table("sell_land_media")

    op.drop_index("ix_sell_land_requests_listing_code", table_name="sell_land_requests")

    op.alter_column("sell_land_requests", "status", existing_type=sa.String(length=20), server_default="pending")
    op.alter_column("sell_land_requests", "expected_price", existing_type=sa.Float(), nullable=False)
    op.alter_column("sell_land_requests", "area", existing_type=sa.Float(), nullable=False)
    op.alter_column("sell_land_requests", "pincode", existing_type=sa.String(length=10), nullable=False)
    op.alter_column("sell_land_requests", "state", existing_type=sa.String(length=100), nullable=False)
    op.alter_column("sell_land_requests", "city", existing_type=sa.String(length=100), nullable=False)
    op.alter_column("sell_land_requests", "location", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("sell_land_requests", "owner_mobile", existing_type=sa.String(length=20), nullable=False)
    op.alter_column("sell_land_requests", "owner_name", existing_type=sa.String(length=100), nullable=False)
    op.alter_column("sell_land_requests", "title", existing_type=sa.String(length=150), nullable=False)

    op.drop_column("sell_land_requests", "payment_status")
    op.drop_column("sell_land_requests", "payment_required_amount")
    op.drop_column("sell_land_requests", "draft_step")
    op.drop_column("sell_land_requests", "is_draft")
    op.drop_column("sell_land_requests", "boundary_points")
    op.drop_column("sell_land_requests", "availability")
    op.drop_column("sell_land_requests", "price_type")
    op.drop_column("sell_land_requests", "listing_code")
