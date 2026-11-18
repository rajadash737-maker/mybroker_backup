"""Allow Field Officer completion-code verification audit events.

Revision ID: 20261117_0046_site_visit_completion_audit_event
Revises: 20261117_0045_site_visit_active_admin_overrides
"""

from alembic import op
import sqlalchemy as sa


revision = "20261117_0046_site_visit_completion_audit_event"
down_revision = "20261117_0045_site_visit_active_admin_overrides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("site_visit_workflow_history") as batch_op:
        batch_op.drop_constraint("ck_site_visit_workflow_history_event_type", type_="check")
        batch_op.create_check_constraint(
            "ck_site_visit_workflow_history_event_type",
            "event_type IN ('correction_requested', 'buyer_resubmitted', 'buyer_cancelled', "
            "'admin_cancelled', 'in_progress_reassigned', 'in_progress_unassigned', "
            "'in_progress_cancelled', 'field_officer_completed')",
        )


def downgrade() -> None:
    connection = op.get_bind()
    retained = connection.execute(sa.text(
        "SELECT COUNT(*) FROM site_visit_workflow_history WHERE event_type = 'field_officer_completed'"
    )).scalar_one()
    if retained:
        raise RuntimeError("Cannot downgrade Field Officer completion audit events without losing history")
    with op.batch_alter_table("site_visit_workflow_history") as batch_op:
        batch_op.drop_constraint("ck_site_visit_workflow_history_event_type", type_="check")
        batch_op.create_check_constraint(
            "ck_site_visit_workflow_history_event_type",
            "event_type IN ('correction_requested', 'buyer_resubmitted', 'buyer_cancelled', "
            "'admin_cancelled', 'in_progress_reassigned', 'in_progress_unassigned', "
            "'in_progress_cancelled')",
        )
