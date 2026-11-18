from decimal import Decimal
from pathlib import Path
import importlib.util

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text

from app.settings.schemas import ProcessingFeeSettingsUpdateRequest
from app.settings import service


def test_site_visit_fee_accepts_bounded_currency_precision():
    payload = ProcessingFeeSettingsUpdateRequest(
        seller_processing_fee=999,
        buyer_processing_fee=1000,
        site_visit_fee="125.50",
    )

    assert payload.site_visit_fee == Decimal("125.50")


@pytest.mark.parametrize("fee", ["-0.01", "100000.01", "1.001"])
def test_site_visit_fee_rejects_invalid_amounts(fee):
    with pytest.raises(ValidationError):
        ProcessingFeeSettingsUpdateRequest(
            seller_processing_fee=999,
            buyer_processing_fee=1000,
            site_visit_fee=fee,
        )


def test_legacy_fee_update_preserves_site_visit_fee_when_omitted(monkeypatch):
    record = type(
        "FeeRecord",
        (),
        {
            "seller_processing_fee": 999.0,
            "buyer_processing_fee": 1000.0,
            "site_visit_fee": Decimal("78.25"),
        },
    )()
    monkeypatch.setattr(service, "get_or_create_processing_fees", lambda _db: record)
    monkeypatch.setattr(service, "save_processing_fee_settings", lambda _db, value: value)

    saved = service.update_processing_fees(
        object(),
        ProcessingFeeSettingsUpdateRequest(
            seller_processing_fee=1200,
            buyer_processing_fee=1300,
        ),
    )

    assert saved.seller_processing_fee == 1200
    assert saved.buyer_processing_fee == 1300
    assert saved.site_visit_fee == Decimal("78.25")


def test_site_visit_fee_migration_adds_default_without_changing_existing_fees():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20261115_0037_site_visit_fee.py"
    )
    spec = importlib.util.spec_from_file_location("site_visit_fee_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE processing_fee_settings ("
                "id INTEGER PRIMARY KEY, seller_processing_fee FLOAT NOT NULL, "
                "buyer_processing_fee FLOAT NOT NULL, updated_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO processing_fee_settings "
                "(id, seller_processing_fee, buyer_processing_fee, updated_at) "
                "VALUES (1, 999.0, 1000.0, CURRENT_TIMESTAMP)"
            )
        )

        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        row = connection.execute(
            text(
                "SELECT seller_processing_fee, buyer_processing_fee, site_visit_fee "
                "FROM processing_fee_settings WHERE id = 1"
            )
        ).one()
        assert row == (999.0, 1000.0, Decimal("0.00"))

        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert "site_visit_fee" not in {
            column["name"] for column in inspect(connection).get_columns("processing_fee_settings")
        }

    engine.dispose()
