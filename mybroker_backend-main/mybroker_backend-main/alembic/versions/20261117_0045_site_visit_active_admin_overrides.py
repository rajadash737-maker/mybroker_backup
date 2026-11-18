"""Allow explicit active-visit Admin override audit events.

Revision ID: 20261117_0045_site_visit_active_admin_overrides
Revises: 20261116_0044_site_visit_refund_ledger
"""

from alembic import op
import sqlalchemy as sa


revision = "20261117_0045_site_visit_active_admin_overrides"
down_revision = "20261116_0044_site_visit_refund_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("site_visit_workflow_history") as batch_op:
        batch_op.drop_constraint("ck_site_visit_workflow_history_event_type", type_="check")
        batch_op.create_check_constraint(
            "ck_site_visit_workflow_history_event_type",
            "event_type IN ('correction_requested', 'buyer_resubmitted', 'buyer_cancelled', "
            "'admin_cancelled', 'in_progress_reassigned', 'in_progress_unassigned', "
            "'in_progress_cancelled')",
        )


def downgrade() -> None:
    connection = op.get_bind()
    retained = connection.execute(sa.text(
        "SELECT COUNT(*) FROM site_visit_workflow_history "
        "WHERE event_type IN ('in_progress_reassigned', 'in_progress_unassigned', 'in_progress_cancelled')"
    )).scalar_one()
    if retained:
        raise RuntimeError("Cannot downgrade active-visit override audit events without losing history")
    with op.batch_alter_table("site_visit_workflow_history") as batch_op:
        batch_op.drop_constraint("ck_site_visit_workflow_history_event_type", type_="check")
        batch_op.create_check_constraint(
            "ck_site_visit_workflow_history_event_type",
            "event_type IN ('correction_requested', 'buyer_resubmitted', 'buyer_cancelled', 'admin_cancelled')",
        )
