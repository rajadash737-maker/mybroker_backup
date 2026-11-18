"""Add encrypted Site Visit completion code state.

Revision ID: 20261115_0042_site_visit_completion_code
Revises: 20261115_0041_unique_razorpay_webhook_event_key
"""

from alembic import op
import sqlalchemy as sa


revision = "20261115_0042_site_visit_completion_code"
down_revision = "20261115_0041_unique_razorpay_webhook_event_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("site_visit_requests") as batch_op:
        batch_op.add_column(
            sa.Column("completion_code_hash", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("completion_code_encrypted", sa.String(length=256), nullable=True)
        )
        batch_op.add_column(
            sa.Column("completion_code_expires_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "completion_code_failed_attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(
            sa.Column("completion_code_used_at", sa.DateTime(), nullable=True)
        )
        batch_op.create_check_constraint(
            "ck_site_visit_requests_completion_attempts_range",
            "completion_code_failed_attempts BETWEEN 0 AND 5",
        )


def downgrade() -> None:
    with op.batch_alter_table("site_visit_requests") as batch_op:
        batch_op.drop_constraint(
            "ck_site_visit_requests_completion_attempts_range",
            type_="check",
        )
        batch_op.drop_column("completion_code_used_at")
        batch_op.drop_column("completion_code_failed_attempts")
        batch_op.drop_column("completion_code_expires_at")
        batch_op.drop_column("completion_code_encrypted")
        batch_op.drop_column("completion_code_hash")
