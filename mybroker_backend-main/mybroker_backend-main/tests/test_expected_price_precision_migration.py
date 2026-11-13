from __future__ import annotations

import importlib.util
import re
from decimal import Decimal
from io import StringIO
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / "alembic" / "versions" / "20261111_0034_expected_price_precision.py"


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("expected_price_precision_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ScalarResult:
    def __init__(self, value: int):
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class _FakeBind:
    """Evaluate only the migration's two COUNT predicates, without a database."""

    def __init__(self, values):
        self.values = [Decimal(str(value)) for value in values if value is not None]
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        sql = str(statement)
        if "expected_price >" in sql and "expected_price < -" in sql:
            bounds = re.search(
                r"expected_price > ([0-9.]+) OR expected_price < -([0-9.]+)", sql
            )
            assert bounds is not None, f"Unexpected upgrade range predicate: {sql}"
            upper, lower_magnitude = map(Decimal, bounds.groups())
            count = sum(value > upper or value < -lower_magnitude for value in self.values)
            return _ScalarResult(count)
        if "expected_price <> ROUND(expected_price, 0)" in sql:
            count = sum(value != value.to_integral_value() for value in self.values)
            return _ScalarResult(count)
        raise AssertionError(f"Unexpected migration query: {sql}")


class _FakeOperations:
    def __init__(self, values):
        self.bind = _FakeBind(values)
        self.alter_column = Mock()

    def get_bind(self):
        return self.bind


def _install_fake_operations(monkeypatch, migration, values) -> _FakeOperations:
    operations = _FakeOperations(values)
    monkeypatch.setattr(migration, "op", operations)
    return operations


def test_revision_parent_and_model_use_numeric_18_6():
    migration = _load_migration()

    assert migration.revision == "20261111_0034_expected_price_precision"
    assert migration.down_revision == "20261110_0033_social_links_ratings"

    from app.sell_land.models import SellLandRequest

    column = SellLandRequest.__table__.c.expected_price
    assert isinstance(column.type, sa.Numeric)
    assert (column.type.precision, column.type.scale) == (18, 6)
    assert column.nullable is True


@pytest.mark.parametrize(
    "boundary_value",
    [Decimal("999999999999.999999"), Decimal("-999999999999.999999")],
)
def test_upgrade_accepts_both_exact_numeric_18_6_boundaries(monkeypatch, boundary_value):
    migration = _load_migration()
    operations = _install_fake_operations(monkeypatch, migration, values=[boundary_value])

    migration.upgrade()

    assert "999999999999.999999" in str(operations.bind.statements[0])
    operations.alter_column.assert_called_once()
    args, kwargs = operations.alter_column.call_args
    assert args == ("sell_land_requests", "expected_price")
    assert (kwargs["existing_type"].precision, kwargs["existing_type"].scale) == (18, 0)
    assert (kwargs["type_"].precision, kwargs["type_"].scale) == (18, 6)
    assert kwargs["existing_nullable"] is True


@pytest.mark.parametrize(
    "out_of_range_value",
    [Decimal("1000000000000"), Decimal("-1000000000000")],
)
def test_upgrade_rejects_values_just_outside_both_boundaries(monkeypatch, out_of_range_value):
    migration = _load_migration()
    operations = _install_fake_operations(monkeypatch, migration, values=[out_of_range_value])

    with pytest.raises(RuntimeError, match=r"1 value\(s\).*target range"):
        migration.upgrade()

    operations.alter_column.assert_not_called()


@pytest.mark.parametrize("fractional_value", [Decimal("1.25"), Decimal("-1.25")])
def test_downgrade_refuses_positive_and_negative_fractional_values(monkeypatch, fractional_value):
    migration = _load_migration()
    operations = _install_fake_operations(monkeypatch, migration, values=[fractional_value])

    with pytest.raises(RuntimeError, match=r"1 value\(s\) have fractional digits"):
        migration.downgrade()

    assert "ROUND(expected_price, 0)" in str(operations.bind.statements[0])
    operations.alter_column.assert_not_called()


def test_downgrade_alters_only_expected_price_when_values_are_integral(monkeypatch):
    migration = _load_migration()
    operations = _install_fake_operations(
        monkeypatch, migration, values=[Decimal("0"), Decimal("1"), Decimal("-123456")]
    )

    migration.downgrade()

    operations.alter_column.assert_called_once()
    args, kwargs = operations.alter_column.call_args
    assert args == ("sell_land_requests", "expected_price")
    assert (kwargs["existing_type"].precision, kwargs["existing_type"].scale) == (18, 6)
    assert (kwargs["type_"].precision, kwargs["type_"].scale) == (18, 0)
    assert kwargs["existing_nullable"] is True


def test_mysql_offline_alter_column_ddl_preserves_nullable_column():
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="mysql",
        opts={"as_sql": True, "output_buffer": output},
    )
    Operations(context).alter_column(
        "sell_land_requests",
        "expected_price",
        existing_type=sa.Numeric(18, 0),
        type_=sa.Numeric(18, 6),
        existing_nullable=True,
    )

    ddl = output.getvalue().upper()
    assert "ALTER TABLE SELL_LAND_REQUESTS MODIFY EXPECTED_PRICE NUMERIC(18, 6) NULL" in ddl
