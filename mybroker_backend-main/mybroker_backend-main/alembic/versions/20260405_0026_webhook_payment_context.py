"""add payment_context to webhook logs

Revision ID: 20260405_0026
Revises: 20260405_0025
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_0026"
down_revision = "20260405_0025"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    table = "razorpay_webhook_logs"
    if not inspector.has_table(table):
        raise RuntimeError(f"{table} must exist before payment_context can be added.")
    columns = {column["name"]: column for column in inspector.get_columns(table)}
    if "payment_context" not in columns:
        op.add_column(
            table,
            sa.Column("payment_context", sa.String(length=20), nullable=False, server_default="unknown"),
        )
        return

    column = columns["payment_context"]
    default = str(column.get("default")).strip().strip("()'\"").lower()
    if (
        not isinstance(column["type"], sa.String)
        or column["type"].length != 20
        or column["nullable"]
        or default != "unknown"
    ):
        raise RuntimeError(
            "Incompatible razorpay_webhook_logs.payment_context; expected NOT NULL String(20) DEFAULT 'unknown'."
        )


def downgrade():
    op.drop_column("razorpay_webhook_logs", "payment_context")
