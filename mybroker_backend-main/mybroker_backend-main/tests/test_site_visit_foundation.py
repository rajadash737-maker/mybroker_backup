from datetime import date, time
from pathlib import Path
import importlib.util

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy.orm import configure_mappers

import app.sell_land.models  # noqa: F401
import app.users.model  # noqa: F401
from app.payments.models import RazorpayPaymentOrder, RazorpayWebhookLog
from app.site_visits.models import SiteVisitAssignment, SiteVisitRequest
from app.site_visits.schemas import SiteVisitRequestCreate


def test_site_visit_request_has_expected_foreign_keys_and_relationships():
    configure_mappers()
    foreign_keys = {
        (fk.parent.name, fk.target_fullname)
        for fk in SiteVisitRequest.__table__.foreign_keys
    }

    assert ("listing_id", "sell_land_requests.id") in foreign_keys
    assert ("buyer_id", "users.id") in foreign_keys
    assert ("seller_id", "users.id") in foreign_keys
    assert ("assigned_field_officer_id", "users.id") in foreign_keys
    assert "assignment_history" in SiteVisitRequest.__mapper__.relationships
    assert "site_visit" in SiteVisitAssignment.__mapper__.relationships


def test_site_visit_mysql_ddl_uses_valid_identifier_lengths():
    tables = (
        SiteVisitRequest.__table__,
        SiteVisitAssignment.__table__,
        RazorpayPaymentOrder.__table__,
        RazorpayWebhookLog.__table__,
    )
    dialect = mysql.dialect()

    for table in tables:
        ddl = str(CreateTable(table).compile(dialect=dialect))
        for constraint in table.constraints:
            if constraint.name:
                assert len(constraint.name) <= 64, constraint.name
                assert constraint.name in ddl, constraint.name
        for index in table.indexes:
            assert len(index.name) <= 64, index.name
            index_ddl = str(CreateIndex(index).compile(dialect=dialect))
            assert index.name in index_ddl

    payment_fk = next(
        fk for fk in RazorpayPaymentOrder.__table__.foreign_key_constraints
        if "site_visit_request_id" in {column.name for column in fk.columns}
    )
    assert payment_fk.name == "fk_payment_order_site_visit"
    assert payment_fk.referred_table.name == "site_visit_requests"


def test_site_visit_schema_validates_booking_fields():
    request = SiteVisitRequestCreate(
        listing_id=24,
        preferred_visit_date=date(2027, 1, 5),
        preferred_visit_time=time(10, 30),
        visitor_count=3,
        pickup_address="Village, area, landmark, city, 751001",
        submission_key="retry-key-1",
    )

    assert request.listing_id == 24
    assert request.visitor_count == 3


@pytest.mark.parametrize(
    "overrides",
    [
        {"listing_id": 0},
        {"visitor_count": 0},
        {"visitor_count": 21},
        {"pickup_address": "   "},
    ],
)
def test_site_visit_schema_rejects_invalid_booking_fields(overrides):
    payload = {
        "listing_id": 24,
        "preferred_visit_date": date(2027, 1, 5),
        "preferred_visit_time": time(10, 30),
        "visitor_count": 3,
        "pickup_address": "Village, area, landmark, city, 751001",
    }
    payload.update(overrides)

    with pytest.raises(ValidationError):
        SiteVisitRequestCreate(**payload)


def test_site_visit_migration_creates_constraints_and_foreign_keys():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20261115_0038_site_visit_foundation.py"
    )
    spec = importlib.util.spec_from_file_location("site_visit_foundation_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)
    assert migration.down_revision == "20261115_0037_site_visit_fee"

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE sell_land_requests (id INTEGER PRIMARY KEY)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        inspector = inspect(connection)
        request_fks = {
            (fk["constrained_columns"][0], fk["referred_table"], fk["referred_columns"][0])
            for fk in inspector.get_foreign_keys("site_visit_requests")
        }
        assert ("listing_id", "sell_land_requests", "id") in request_fks
        assert ("buyer_id", "users", "id") in request_fks
        assert ("seller_id", "users", "id") in request_fks
        assert ("assigned_field_officer_id", "users", "id") in request_fks
        assert any(
            "site_visit_fee_paise >= 0" in (constraint["sqltext"] or "")
            for constraint in inspector.get_check_constraints("site_visit_requests")
        )
        assignment_fks = {
            (fk["constrained_columns"][0], fk["referred_table"], fk["referred_columns"][0])
            for fk in inspector.get_foreign_keys("site_visit_assignment_history")
        }
        assert ("site_visit_request_id", "site_visit_requests", "id") in assignment_fks
        assert ("previous_field_officer_id", "users", "id") in assignment_fks
        assert ("field_officer_id", "users", "id") in assignment_fks
        assert ("actor_id", "users", "id") in assignment_fks

        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert "site_visit_requests" not in inspect(connection).get_table_names()

    engine.dispose()


def test_site_visit_payment_attempt_migration_uses_model_fk_name_in_both_directions(monkeypatch):
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20261115_0040_site_visit_payment_attempt_link.py"
    )
    spec = importlib.util.spec_from_file_location("site_visit_payment_attempt_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)

    class OperationRecorder:
        def __init__(self):
            self.created_foreign_keys = []
            self.dropped_foreign_keys = []

        def add_column(self, *_args):
            pass

        def create_foreign_key(self, *args):
            self.created_foreign_keys.append(args)

        def execute(self, *_args):
            pass

        def create_index(self, *_args, **_kwargs):
            pass

        def drop_index(self, *_args, **_kwargs):
            pass

        def drop_constraint(self, *args, **kwargs):
            self.dropped_foreign_keys.append((*args, kwargs.get("type_")))

        def drop_column(self, *_args):
            pass

    operations = OperationRecorder()
    monkeypatch.setattr(migration, "op", operations)
    migration.upgrade()
    migration.downgrade()

    expected_name = "fk_payment_order_site_visit"
    assert len(expected_name) <= 64
    assert operations.created_foreign_keys == [
        (
            expected_name,
            "razorpay_payment_orders",
            "site_visit_requests",
            ["site_visit_request_id"],
            ["id"],
        )
    ]
    assert operations.dropped_foreign_keys == [
        (expected_name, "razorpay_payment_orders", "foreignkey")
    ]
    model_fk = next(
        fk for fk in RazorpayPaymentOrder.__table__.foreign_key_constraints
        if "site_visit_request_id" in {column.name for column in fk.columns}
    )
    assert model_fk.name == expected_name
    assert model_fk.referred_table.name == "site_visit_requests"
