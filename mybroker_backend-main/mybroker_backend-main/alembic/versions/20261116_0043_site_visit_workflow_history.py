"""Add Site Visit correction and cancellation audit history.

Revision ID: 20261116_0043_site_visit_workflow_history
Revises: 20261115_0042_site_visit_completion_code
"""

from alembic import op
import sqlalchemy as sa


revision = "20261116_0043_site_visit_workflow_history"
down_revision = "20261115_0042_site_visit_completion_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("site_visit_requests") as batch_op:
        batch_op.drop_constraint("ck_site_visit_requests_status", type_="check")
        batch_op.create_check_constraint(
            "ck_site_visit_requests_status",
            "status IN ('pending_payment', 'pending', 'assigned', 'scheduled', 'in_progress', "
            "'completed', 'correction_required', 'cancelled', 'refund_pending', 'refunded', 'refund_failed')",
        )
        batch_op.add_column(sa.Column("cancelled_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("cancellation_actor_role", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("correction_reason", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("correction_requested_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("correction_requested_by_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_site_visit_requests_cancelled_by_users", "users", ["cancelled_by_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_site_visit_requests_correction_requested_by_users", "users", ["correction_requested_by_id"], ["id"]
        )
        batch_op.create_index("ix_site_visit_requests_cancelled_by_id", ["cancelled_by_id"])
        batch_op.create_index("ix_site_visit_requests_correction_requested_by_id", ["correction_requested_by_id"])

    op.create_table(
        "site_visit_workflow_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_visit_request_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("actor_role", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("previous_values", sa.JSON(), nullable=True),
        sa.Column("updated_values", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "event_type IN ('correction_requested', 'buyer_resubmitted', 'buyer_cancelled', 'admin_cancelled')",
            name="ck_site_visit_workflow_history_event_type",
        ),
        sa.ForeignKeyConstraint(["site_visit_request_id"], ["site_visit_requests.id"], name="fk_site_visit_workflow_history_request_id"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name="fk_site_visit_workflow_history_actor_id"),
    )
    op.create_index("ix_site_visit_workflow_history_id", "site_visit_workflow_history", ["id"])
    op.create_index("ix_site_visit_workflow_history_site_visit_request_id", "site_visit_workflow_history", ["site_visit_request_id"])
    op.create_index("ix_site_visit_workflow_history_event_type", "site_visit_workflow_history", ["event_type"])
    op.create_index("ix_site_visit_workflow_history_actor_id", "site_visit_workflow_history", ["actor_id"])


def downgrade() -> None:
    op.drop_index("ix_site_visit_workflow_history_actor_id", table_name="site_visit_workflow_history")
    op.drop_index("ix_site_visit_workflow_history_event_type", table_name="site_visit_workflow_history")
    op.drop_index("ix_site_visit_workflow_history_site_visit_request_id", table_name="site_visit_workflow_history")
    op.drop_index("ix_site_visit_workflow_history_id", table_name="site_visit_workflow_history")
    op.drop_table("site_visit_workflow_history")
    with op.batch_alter_table("site_visit_requests") as batch_op:
        batch_op.drop_index("ix_site_visit_requests_correction_requested_by_id")
        batch_op.drop_index("ix_site_visit_requests_cancelled_by_id")
        batch_op.drop_constraint("fk_site_visit_requests_correction_requested_by_users", type_="foreignkey")
        batch_op.drop_constraint("fk_site_visit_requests_cancelled_by_users", type_="foreignkey")
        batch_op.drop_column("correction_requested_by_id")
        batch_op.drop_column("correction_requested_at")
        batch_op.drop_column("correction_reason")
        batch_op.drop_column("cancellation_actor_role")
        batch_op.drop_column("cancelled_by_id")
        batch_op.drop_constraint("ck_site_visit_requests_status", type_="check")
        batch_op.create_check_constraint(
            "ck_site_visit_requests_status",
            "status IN ('pending_payment', 'pending', 'assigned', 'scheduled', 'in_progress', "
            "'completed', 'cancelled', 'refund_pending', 'refunded', 'refund_failed')",
        )
