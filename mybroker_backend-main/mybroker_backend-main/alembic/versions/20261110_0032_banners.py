"""Create banners table.

Revision ID: 20261110_0032_banners
Revises: 20261106_0031_otp_security
"""

from alembic import op
import sqlalchemy as sa


revision = "20261110_0032_banners"
down_revision = "20261106_0031_otp_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "banners",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("image_url", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banners_id", "banners", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_banners_id", table_name="banners")
    op.drop_table("banners")
