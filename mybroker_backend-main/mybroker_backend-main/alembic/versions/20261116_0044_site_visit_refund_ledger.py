"""Add Site Visit accounting refund ledger and audit trail.

Revision ID: 20261116_0044_site_visit_refund_ledger
Revises: 20261116_0043_site_visit_workflow_history
"""

from alembic import op
import sqlalchemy as sa


revision = "20261116_0044_site_visit_refund_ledger"
down_revision = "20261116_0043_site_visit_workflow_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_visit_refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_visit_request_id", sa.Integer(), nullable=False),
        sa.Column("original_payment_reference", sa.String(length=120), nullable=True),
        sa.Column("eligible_amount_paise", sa.Integer(), nullable=False),
        sa.Column("actual_refunded_amount_paise", sa.Integer(), nullable=True),
        sa.Column("buyer_upi_ciphertext", sa.String(length=512), nullable=True),
        sa.Column("upi_transaction_reference", sa.String(length=120), nullable=True),
        sa.Column("refunded_at", sa.DateTime(), nullable=True),
        sa.Column("accounting_user_id", sa.Integer(), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending_details"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("eligible_amount_paise > 0", name="ck_site_visit_refunds_eligible_amount_positive"),
        sa.CheckConstraint("actual_refunded_amount_paise IS NULL OR (actual_refunded_amount_paise > 0 AND actual_refunded_amount_paise <= eligible_amount_paise)", name="ck_site_visit_refunds_actual_amount_in_range"),
        sa.CheckConstraint("status IN ('pending_details', 'pending', 'refunded', 'failed')", name="ck_site_visit_refunds_status"),
        sa.CheckConstraint("status != 'refunded' OR (actual_refunded_amount_paise IS NOT NULL AND upi_transaction_reference IS NOT NULL AND refunded_at IS NOT NULL AND accounting_user_id IS NOT NULL)", name="ck_site_visit_refunds_confirmed_fields"),
        sa.CheckConstraint("status != 'failed' OR (failure_reason IS NOT NULL AND accounting_user_id IS NOT NULL)", name="ck_site_visit_refunds_failed_fields"),
        sa.ForeignKeyConstraint(["site_visit_request_id"], ["site_visit_requests.id"], name="fk_site_visit_refunds_request_id"),
        sa.ForeignKeyConstraint(["accounting_user_id"], ["users.id"], name="fk_site_visit_refunds_accounting_user_id"),
        sa.UniqueConstraint("site_visit_request_id", name="uq_site_visit_refunds_request_id"),
        sa.UniqueConstraint("upi_transaction_reference", name="uq_site_visit_refunds_upi_reference"),
        mysql_engine="InnoDB",
    )
    for name, column in (
        ("ix_site_visit_refunds_id", "id"),
        ("ix_site_visit_refunds_site_visit_request_id", "site_visit_request_id"),
        ("ix_site_visit_refunds_accounting_user_id", "accounting_user_id"),
        ("ix_site_visit_refunds_status", "status"),
    ):
        op.create_index(name, "site_visit_refunds", [column])

    op.create_table(
        "site_visit_refund_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("refund_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("actor_role", sa.String(length=30), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("actual_amount_paise", sa.Integer(), nullable=True),
        sa.Column("transaction_reference", sa.String(length=120), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('opened', 'details_submitted', 'confirmed', 'failed')", name="ck_site_visit_refund_history_action"),
        sa.ForeignKeyConstraint(["refund_id"], ["site_visit_refunds.id"], name="fk_site_visit_refund_history_refund_id"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name="fk_site_visit_refund_history_actor_id"),
        mysql_engine="InnoDB",
    )
    for name, column in (
        ("ix_site_visit_refund_history_id", "id"),
        ("ix_site_visit_refund_history_refund_id", "refund_id"),
        ("ix_site_visit_refund_history_actor_id", "actor_id"),
    ):
        op.create_index(name, "site_visit_refund_history", [column])

    op.execute(sa.text(
        "INSERT INTO site_visit_refunds "
        "(site_visit_request_id, original_payment_reference, eligible_amount_paise, status, created_at, updated_at) "
        "SELECT id, COALESCE(payment_id, payment_order_id), site_visit_fee_paise, 'pending_details', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
        "FROM site_visit_requests WHERE payment_status = 'success' AND status = 'cancelled' "
        "AND cancelled_at IS NOT NULL AND site_visit_fee_paise > 0"
    ))


def downgrade() -> None:
    for name in ("ix_site_visit_refund_history_actor_id", "ix_site_visit_refund_history_refund_id", "ix_site_visit_refund_history_id"):
        op.drop_index(name, table_name="site_visit_refund_history")
    op.drop_table("site_visit_refund_history")
    for name in ("ix_site_visit_refunds_status", "ix_site_visit_refunds_accounting_user_id", "ix_site_visit_refunds_site_visit_request_id", "ix_site_visit_refunds_id"):
        op.drop_index(name, table_name="site_visit_refunds")
    op.drop_table("site_visit_refunds")
