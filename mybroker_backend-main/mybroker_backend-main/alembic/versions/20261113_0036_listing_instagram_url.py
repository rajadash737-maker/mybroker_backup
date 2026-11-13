"""Add optional Instagram promotion URL to listings.

Revision ID: 20261113_0036_listing_instagram_url
Revises: 20261111_0035_versioned_land_pricing_storage
Create Date: 2026-11-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20261113_0036_listing_instagram_url"
down_revision = "20261111_0035_versioned_land_pricing_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sell_land_requests",
        sa.Column("instagram_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sell_land_requests", "instagram_url")
