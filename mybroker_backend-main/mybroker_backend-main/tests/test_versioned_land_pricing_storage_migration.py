from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import sqlalchemy as sa
import pytest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / "alembic" / "versions" / "20261111_0035_versioned_land_pricing_storage.py"


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("versioned_land_pricing_storage_migration", MIGRATION_PATH)
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
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        sql = str(statement)
        assert "pricing_version = 2" in sql
        assert "entered_unit_price IS NOT NULL" in sql
        count = sum(
            row["pricing_version"] == 2 or row["entered_unit_price"] is not None
            for row in self.rows
        )
        return _ScalarResult(count)


class _FakeOperations:
    def __init__(self, rows=()):
        self.bind = _FakeBind(rows)
        self.add_column = Mock()
        self.drop_column = Mock()

    def get_bind(self):
        return self.bind


def test_revision_linkage_and_model_columns_match_migration():
    migration = _load_migration()
    assert migration.revision == "20261111_0035_versioned_land_pricing_storage"
    assert migration.down_revision == "20261111_0034_expected_price_precision"

    from app.sell_land.models import SellLandRequest

    table = SellLandRequest.__table__
    version = table.c.pricing_version
    entered = table.c.entered_unit_price
    assert isinstance(version.type, sa.Integer)
    assert version.nullable is False
    assert version.default.arg == 1
    assert str(version.server_default.arg) == "1"
    assert isinstance(entered.type, sa.Numeric)
    assert (entered.type.precision, entered.type.scale) == (18, 6)
    assert entered.nullable is True


def test_upgrade_adds_only_the_two_columns_with_legacy_safe_defaults(monkeypatch):
    migration = _load_migration()
    operations = _FakeOperations()
    monkeypatch.setattr(migration, "op", operations)

    migration.upgrade()

    assert operations.add_column.call_count == 2
    calls = operations.add_column.call_args_list
    assert all(call.args[0] == "sell_land_requests" for call in calls)
    version_column = calls[0].args[1]
    entered_column = calls[1].args[1]
    assert version_column.name == "pricing_version"
    assert isinstance(version_column.type, sa.Integer)
    assert version_column.nullable is False
    assert str(version_column.server_default.arg) == "1"
    assert entered_column.name == "entered_unit_price"
    assert isinstance(entered_column.type, sa.Numeric)
    assert (entered_column.type.precision, entered_column.type.scale) == (18, 6)
    assert entered_column.nullable is True
    assert entered_column.server_default is None


@pytest.mark.parametrize(
    "row",
    [
        {"pricing_version": 2, "entered_unit_price": None},
        {"pricing_version": 1, "entered_unit_price": "12.34"},
    ],
)
def test_downgrade_refuses_version_two_or_entered_price_data(monkeypatch, row):
    migration = _load_migration()
    operations = _FakeOperations(rows=[row])
    monkeypatch.setattr(migration, "op", operations)

    with pytest.raises(RuntimeError, match=r"1 row\(s\) contain pricing_version=2 or entered_unit_price"):
        migration.downgrade()

    operations.drop_column.assert_not_called()


def test_downgrade_succeeds_for_legacy_rows_and_drops_only_added_columns(monkeypatch):
    migration = _load_migration()
    operations = _FakeOperations(
        rows=[
            {"pricing_version": 1, "entered_unit_price": None},
            {"pricing_version": 1, "entered_unit_price": None},
        ]
    )
    monkeypatch.setattr(migration, "op", operations)

    migration.downgrade()

    assert operations.drop_column.call_args_list == [
        (("sell_land_requests", "entered_unit_price"), {}),
        (("sell_land_requests", "pricing_version"), {}),
    ]
