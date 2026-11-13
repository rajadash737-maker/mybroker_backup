"""add user profile photo field

Revision ID: 20260208_0003
Revises: 20260208_0002
Create Date: 2026-02-08 22:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260208_0003"
down_revision = "20260208_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_image_url", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_image_url")
