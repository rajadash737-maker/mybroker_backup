"""add field officer visit review fields

Revision ID: 20260220_0008
Revises: 20260218_0007
Create Date: 2026-02-20 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260220_0008"
down_revision = "20260218_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sell_land_requests",
        sa.Column("field_officer_reviewed_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("field_officer_reviewed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("field_officer_decision", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("field_officer_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("field_officer_rejection_reason", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("field_officer_visit_photo_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "sell_land_requests",
        sa.Column("field_officer_visit_photo_name", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_sell_land_requests_field_officer_reviewed_by_id",
        "sell_land_requests",
        ["field_officer_reviewed_by_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_sell_land_requests_field_officer_reviewed_by_id_users",
        "sell_land_requests",
        "users",
        ["field_officer_reviewed_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sell_land_requests_field_officer_reviewed_by_id_users",
        "sell_land_requests",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_sell_land_requests_field_officer_reviewed_by_id",
        table_name="sell_land_requests",
    )
    op.drop_column("sell_land_requests", "field_officer_visit_photo_name")
    op.drop_column("sell_land_requests", "field_officer_visit_photo_url")
    op.drop_column("sell_land_requests", "field_officer_rejection_reason")
    op.drop_column("sell_land_requests", "field_officer_notes")
    op.drop_column("sell_land_requests", "field_officer_decision")
    op.drop_column("sell_land_requests", "field_officer_reviewed_at")
    op.drop_column("sell_land_requests", "field_officer_reviewed_by_id")
