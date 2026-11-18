import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _migration(filename: str):
    path = Path(__file__).parents[1] / "alembic" / "versions" / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_site_visit_correction_and_refund_migrations_upgrade_backfill_and_downgrade():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        metadata = sa.MetaData()
        sa.Table("users", metadata, sa.Column("id", sa.Integer(), primary_key=True))
        requests = sa.Table(
            "site_visit_requests",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("payment_status", sa.String(20), nullable=False),
            sa.Column("site_visit_fee_paise", sa.Integer(), nullable=False),
            sa.Column("payment_id", sa.String(64)),
            sa.Column("payment_order_id", sa.String(64)),
            sa.Column("cancelled_at", sa.DateTime()),
            sa.CheckConstraint(
                "status IN ('pending_payment', 'pending', 'assigned', 'scheduled', 'in_progress', 'completed', 'cancelled', 'refund_pending', 'refunded', 'refund_failed')",
                name="ck_site_visit_requests_status",
            ),
        )
        metadata.create_all(connection)
        connection.execute(sa.text("INSERT INTO users (id) VALUES (1)"))
        connection.execute(sa.text(
            "INSERT INTO site_visit_requests "
            "(id, status, payment_status, site_visit_fee_paise, payment_id, cancelled_at) "
            "VALUES (11, 'cancelled', 'success', 12500, 'pay_ref_11', CURRENT_TIMESTAMP)"
        ))

        workflow = _migration("20261116_0043_site_visit_workflow_history.py")
        refund = _migration("20261116_0044_site_visit_refund_ledger.py")
        overrides = _migration("20261117_0045_site_visit_active_admin_overrides.py")
        completion_audit = _migration("20261117_0046_site_visit_completion_audit_event.py")
        with Operations.context(MigrationContext.configure(connection)):
            workflow.upgrade()
            refund.upgrade()
            overrides.upgrade()
            completion_audit.upgrade()
        tables = set(sa.inspect(connection).get_table_names())
        assert "site_visit_workflow_history" in tables
        assert "site_visit_refunds" in tables
        migrated = connection.execute(sa.text("SELECT original_payment_reference, eligible_amount_paise, status FROM site_visit_refunds WHERE site_visit_request_id = 11")).one()
        assert tuple(migrated) == ("pay_ref_11", 12500, "pending_details")
        connection.execute(sa.text(
            "INSERT INTO site_visit_workflow_history "
            "(site_visit_request_id, event_type, actor_id, actor_role, reason) "
            "VALUES (11, 'field_officer_completed', 1, 'FIELD_OFFICER', 'completion code verified')"
        ))
        with Operations.context(MigrationContext.configure(connection)):
            try:
                completion_audit.downgrade()
            except RuntimeError as exc:
                assert "without losing history" in str(exc)
            else:
                raise AssertionError("Downgrade must preserve Field Officer completion history")
        connection.execute(sa.text("DELETE FROM site_visit_workflow_history WHERE event_type = 'field_officer_completed'"))
        connection.execute(sa.text(
            "INSERT INTO site_visit_workflow_history "
            "(site_visit_request_id, event_type, actor_id, actor_role, reason) "
            "VALUES (11, 'in_progress_cancelled', 1, 'ADMIN', 'authorized override test')"
        ))
        with Operations.context(MigrationContext.configure(connection)):
            try:
                overrides.downgrade()
            except RuntimeError as exc:
                assert "without losing history" in str(exc)
            else:
                raise AssertionError("Downgrade must preserve active-visit override history")
        connection.execute(sa.text("DELETE FROM site_visit_workflow_history WHERE event_type = 'in_progress_cancelled'"))

        with Operations.context(MigrationContext.configure(connection)):
            completion_audit.downgrade()
            overrides.downgrade()
            refund.downgrade()
            workflow.downgrade()
        tables = set(sa.inspect(connection).get_table_names())
        assert "site_visit_refunds" not in tables
        assert "site_visit_workflow_history" not in tables
        assert "correction_reason" not in {column["name"] for column in sa.inspect(connection).get_columns("site_visit_requests")}
    engine.dispose()
