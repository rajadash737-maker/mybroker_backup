"""add fcm_token to users

Revision ID: 20260413_0027
Revises: 20260405_0026
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_0027"
down_revision = "20260405_0026"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("users"):
        raise RuntimeError("users must exist before fcm_token can be added.")
    columns = {column["name"]: column for column in inspector.get_columns("users")}
    if "fcm_token" not in columns:
        op.add_column("users", sa.Column("fcm_token", sa.String(length=512), nullable=True))
        return

    column = columns["fcm_token"]
    if not isinstance(column["type"], sa.String) or column["type"].length != 512 or not column["nullable"]:
        raise RuntimeError("Incompatible users.fcm_token; expected nullable String(512).")


def downgrade():
    op.drop_column("users", "fcm_token")
