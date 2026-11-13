"""add role and active status to users

Revision ID: 20260215_0006
Revises: 20260212_0005
Create Date: 2026-02-15 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260215_0006"
down_revision = "20260212_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=30), nullable=False, server_default="CUSTOMER"),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )


def downgrade() -> None:
    op.drop_column("users", "is_active")
    op.drop_column("users", "role")

