"""Add configurable Site Visit fee to existing processing fee settings.

Revision ID: 20261115_0037_site_visit_fee
Revises: 20261113_0036_listing_instagram_url
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20261115_0037_site_visit_fee"
down_revision = "20261113_0036_listing_instagram_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "processing_fee_settings",
        sa.Column(
            "site_visit_fee",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0.00",
        ),
    )


def downgrade() -> None:
    op.drop_column("processing_fee_settings", "site_visit_fee")
