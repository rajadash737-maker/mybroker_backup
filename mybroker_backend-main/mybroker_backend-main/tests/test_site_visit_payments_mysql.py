"""Persistent, non-destructive MySQL/InnoDB Site Visit integration tests.

These tests use only the pre-existing approved test database. They require
SITE_VISIT_TEST_MYSQL_* connection settings. Test rows are intentionally left
in place; no schema setup, migrations, or real Razorpay requests are used.
"""

from __future__ import annotations

import os
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import URL, UniqueConstraint, create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

# Prevent python-dotenv from loading project credentials when application
# modules initialize Settings. The test engine below uses only explicit,
# test-specific process variables.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["DATABASE_ECHO"] = "0"

from app.payments import service as payment_service  # noqa: E402
from app.payments.models import RazorpayPaymentOrder, RazorpayWebhookLog  # noqa: E402
from app.sell_land.constants import SellLandStatus  # noqa: E402
from app.sell_land.models import SellLandPayment, SellLandRequest  # noqa: E402
from app.site_visits.models import SiteVisitRequest  # noqa: E402
import app.site_visits.completion_code as completion_code  # noqa: E402
import app.site_visits.service as site_visit_service  # noqa: E402
from app.site_visits import payment_service as site_visit_payment_service  # noqa: E402
from app.site_visits.payment_service import (  # noqa: E402
    cancel_site_visit_payment_attempt,
    create_site_visit_order,
    verify_site_visit_payment,
)
from app.site_visits.schemas import SiteVisitVerifyPaymentRequest  # noqa: E402
from app.users.model import User  # noqa: E402


APPROVED_DATABASE = "mybroker_sitevisit_test_0174e41d408a4d31bdb3012ae84c2d51"
APPROVED_USERNAME = "mybroker_sitevisit_test_admin"
ALLOWED_TEST_HOSTS = {"localhost", "127.0.0.1", "::1"}
ALLOWED_MYSQL_ACCOUNT_HOSTS = {"localhost", "127.0.0.1", "::1"}
REQUIRED_SCHEMA_MODELS = {
    "users": User,
    "sell_land_requests": SellLandRequest,
    "sell_land_payments": SellLandPayment,
    "site_visit_requests": SiteVisitRequest,
    "razorpay_payment_orders": RazorpayPaymentOrder,
    "razorpay_webhook_logs": RazorpayWebhookLog,
}
REQUIRED_COLUMNS = {
    table_name: {column.name for column in model.__table__.columns}
    for table_name, model in REQUIRED_SCHEMA_MODELS.items()
}
REQUIRED_COMPLETION_CODE_COLUMNS = {
    "completion_code_hash",
    "completion_code_encrypted",
    "completion_code_expires_at",
    "completion_code_failed_attempts",
    "completion_code_used_at",
}
REQUIRED_TABLE_PRIVILEGES = {
    "users": {"SELECT", "INSERT"},
    "sell_land_requests": {"SELECT", "INSERT", "UPDATE"},
    "sell_land_payments": {"SELECT", "UPDATE"},
    "site_visit_requests": {"SELECT", "INSERT", "UPDATE"},
    "razorpay_payment_orders": {"SELECT", "INSERT", "UPDATE"},
    "razorpay_webhook_logs": {"SELECT", "INSERT", "UPDATE"},
}
REQUIRED_UNIQUE_KEYS = {
    table_name: {
        tuple(column.name for column in constraint.columns)
        for constraint in model.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    | {
        tuple(column.name for column in index.columns)
        for index in model.__table__.indexes
        if index.unique
    }
    | {tuple(column.name for column in model.__table__.primary_key.columns)}
    for table_name, model in REQUIRED_SCHEMA_MODELS.items()
}
ENV_KEYS = (
    "SITE_VISIT_TEST_MYSQL_HOST",
    "SITE_VISIT_TEST_MYSQL_PORT",
    "SITE_VISIT_TEST_MYSQL_USER",
    "SITE_VISIT_TEST_MYSQL_PASSWORD",
)
PREFLIGHT_ONLY_ENV = "SITE_VISIT_MYSQL_PREFLIGHT_ONLY"


class _SafePreflightError(RuntimeError):
    """A preflight failure whose message is safe to show without credentials."""


def _assert_approved_database(name: str | None) -> None:
    if name == "mybroker_db" or name != APPROVED_DATABASE:
        raise _SafePreflightError("refusing any database other than the approved Site Visit test database")


def _validate_grants(grant_rows) -> None:
    observed: dict[str, set[str]] = {table: set() for table in REQUIRED_TABLE_PRIVILEGES}
    table_grant = re.compile(
        r"^GRANT\s+(.+?)\s+ON\s+`([^`]+)`\.`([^`]+)`\s+TO\s+.+$",
        flags=re.IGNORECASE,
    )
    usage_grant = re.compile(r"^GRANT\s+USAGE\s+ON\s+\*\.\*\s+TO\s+.+$", flags=re.IGNORECASE)

    def unmatched_grant_category(grant: str) -> str:
        if re.search(r"\bON\s+\*\s*\.\s*\*\s+TO\b", grant, flags=re.IGNORECASE):
            return "global privilege grant"
        if re.search(
            r"\bON\s+(?:`[^`]+`|[^.\s]+)\s*\.\s*\*\s+TO\b",
            grant,
            flags=re.IGNORECASE,
        ):
            return "schema-level grant"
        if re.fullmatch(r"GRANT\s+.+?\s+TO\s+.+", grant, flags=re.IGNORECASE) and not re.search(
            r"\bON\b", grant, flags=re.IGNORECASE
        ):
            return "role grant"
        return "unsupported grant format"

    for row in grant_rows:
        grant = str(row[0]).strip()
        upper_grant = grant.upper()
        if "WITH GRANT OPTION" in upper_grant or "WITH ADMIN OPTION" in upper_grant:
            raise _SafePreflightError("MySQL account has a prohibited grant option")
        if usage_grant.fullmatch(grant):
            continue

        match = table_grant.fullmatch(grant)
        if match is None:
            # This rejects global/schema grants, roles, and administrative grants.
            category = unmatched_grant_category(grant)
            raise _SafePreflightError(
                f"MySQL account has a grant outside the allowed table-level privileges ({category})"
            )
        privileges = {value.strip().upper() for value in match.group(1).split(",")}
        database_name, table_name = match.group(2), match.group(3)
        allowed = REQUIRED_TABLE_PRIVILEGES.get(table_name)
        if database_name != APPROVED_DATABASE or allowed is None or not privileges:
            raise _SafePreflightError("MySQL account has a grant outside the approved database and tables")
        if not privileges <= allowed:
            raise _SafePreflightError("MySQL account has a privilege not required by the Site Visit tests")
        observed[table_name].update(privileges)

    for table_name, required in REQUIRED_TABLE_PRIVILEGES.items():
        if observed[table_name] != required:
            raise _SafePreflightError("MySQL account is missing a required table-level privilege")


def _validate_columns(column_rows) -> None:
    actual: dict[str, dict[str, str]] = {table: {} for table in REQUIRED_COLUMNS}
    for table_name, column_name, is_nullable in column_rows:
        if table_name in actual:
            actual[str(table_name)][str(column_name)] = str(is_nullable).upper()

    for table_name, required_columns in REQUIRED_COLUMNS.items():
        if not required_columns <= set(actual[table_name]):
            raise _SafePreflightError("A required mapped MySQL column is missing")

    if not REQUIRED_COMPLETION_CODE_COLUMNS <= REQUIRED_COLUMNS["site_visit_requests"]:
        raise _SafePreflightError("Site Visit completion-code columns are missing from the ORM mapping")
    if not REQUIRED_COMPLETION_CODE_COLUMNS <= set(actual["site_visit_requests"]):
        raise _SafePreflightError("A Site Visit completion-code column is missing from MySQL")
    if actual["razorpay_webhook_logs"].get("event_key") != "YES":
        raise _SafePreflightError("Webhook event_key must exist and allow NULL legacy rows")


def _validate_unique_keys(index_rows) -> None:
    grouped: dict[tuple[str, str], list[tuple[int, int, str | None]]] = {}
    for table_name, index_name, non_unique, sequence, column_name in index_rows:
        grouped.setdefault((str(table_name), str(index_name)), []).append(
            (int(sequence), int(non_unique), None if column_name is None else str(column_name))
        )

    actual: dict[str, set[tuple[str, ...]]] = {table: set() for table in REQUIRED_UNIQUE_KEYS}
    for (table_name, _), index_rows_for_index in grouped.items():
        if table_name not in actual or any(non_unique != 0 for _, non_unique, _ in index_rows_for_index):
            continue
        if any(column_name is None for _, _, column_name in index_rows_for_index):
            # Discard the whole index: its ordinary-column rows are only part of an expression index.
            continue
        ordered_columns = sorted(
            (sequence, column_name)
            for sequence, _, column_name in index_rows_for_index
        )
        actual[table_name].add(tuple(column_name for _, column_name in ordered_columns))

    for table_name, required_keys in REQUIRED_UNIQUE_KEYS.items():
        if not required_keys <= actual[table_name]:
            raise _SafePreflightError("A required MySQL primary or unique index is missing")

    if ("event_key",) not in actual["razorpay_webhook_logs"]:
        raise _SafePreflightError("Webhook event_key must have a unique index")


def test_validate_unique_keys_discards_entire_expression_index():
    index_rows = []
    for table_name, required_keys in REQUIRED_UNIQUE_KEYS.items():
        for index_number, columns in enumerate(sorted(required_keys)):
            if table_name == "razorpay_webhook_logs" and columns == ("event_key",):
                continue
            index_name = f"test_required_{table_name}_{index_number}"
            index_rows.extend(
                (table_name, index_name, 0, sequence, column_name)
                for sequence, column_name in enumerate(columns, start=1)
            )

    index_rows.extend(
        [
            ("razorpay_webhook_logs", "test_event_key_expression", 0, 1, "event_key"),
            ("razorpay_webhook_logs", "test_event_key_expression", 0, 2, None),
        ]
    )

    with pytest.raises(_SafePreflightError, match="required MySQL primary or unique index"):
        _validate_unique_keys(index_rows)


@pytest.fixture(scope="module")
def existing_mysql_sessions():
    """Connect only to the approved existing test database; test rows persist."""
    missing = [key for key in ENV_KEYS if not os.environ.get(key)]
    if missing:
        pytest.fail("MySQL Site Visit preflight failed: required test connection settings are missing", pytrace=False)

    host = os.environ["SITE_VISIT_TEST_MYSQL_HOST"].strip().lower()
    if host not in ALLOWED_TEST_HOSTS:
        pytest.fail("MySQL Site Visit preflight failed: only loopback hosts are allowed", pytrace=False)

    username = os.environ["SITE_VISIT_TEST_MYSQL_USER"]
    if username != APPROVED_USERNAME:
        pytest.fail("MySQL Site Visit preflight failed: the approved test account is required", pytrace=False)

    try:
        _assert_approved_database(APPROVED_DATABASE)
    except _SafePreflightError as exc:
        pytest.fail(f"MySQL Site Visit preflight failed: {exc}", pytrace=False)

    try:
        port = int(os.environ["SITE_VISIT_TEST_MYSQL_PORT"])
    except ValueError:
        pytest.fail("SITE_VISIT_TEST_MYSQL_PORT must be an integer", pytrace=False)
    if not 1 <= port <= 65535:
        pytest.fail("SITE_VISIT_TEST_MYSQL_PORT is outside the valid range", pytrace=False)

    test_engine = create_engine(
        URL.create(
            "mysql+pymysql",
            username=username,
            password=os.environ["SITE_VISIT_TEST_MYSQL_PASSWORD"],
            host=host,
            port=port,
            database=APPROVED_DATABASE,
        ),
        pool_size=8,
        max_overflow=4,
        pool_pre_ping=True,
        pool_recycle=60,
    )
    try:
        with test_engine.connect() as connection:
            current_user, database_name, server_version, version_comment = connection.execute(
                text("SELECT CURRENT_USER(), DATABASE(), VERSION(), @@version_comment")
            ).one()
            _assert_approved_database(database_name)
            identity_parts = str(current_user).rsplit("@", 1)
            if len(identity_parts) != 2:
                raise _SafePreflightError("Connected MySQL account identity is malformed")
            authenticated_username, authenticated_host = identity_parts
            if (
                authenticated_username != APPROVED_USERNAME
                or authenticated_host.lower() not in ALLOWED_MYSQL_ACCOUNT_HOSTS
            ):
                raise _SafePreflightError("Connected MySQL account identity is not explicitly approved")
            if not str(server_version).startswith("8.0.46") or "Community Server" not in str(version_comment):
                raise _SafePreflightError("MySQL Site Visit tests require the approved MySQL 8.0.46 Community Server")

            table_names = tuple(REQUIRED_TABLE_PRIVILEGES)
            table_rows = connection.execute(
                text(
                    "SELECT table_name, engine FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name IN "
                    "('users', 'sell_land_requests', 'sell_land_payments', 'site_visit_requests', "
                    "'razorpay_payment_orders', 'razorpay_webhook_logs')"
                )
            ).all()
            engines = {str(table_name): str(engine).upper() for table_name, engine in table_rows}
            if set(engines) != set(table_names) or any(engine != "INNODB" for engine in engines.values()):
                raise _SafePreflightError("Required Site Visit test tables are missing or are not InnoDB")

            column_rows = connection.execute(
                text(
                    "SELECT table_name, column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name IN "
                    "('users', 'sell_land_requests', 'sell_land_payments', 'site_visit_requests', "
                    "'razorpay_payment_orders', 'razorpay_webhook_logs')"
                )
            ).all()
            _validate_columns(column_rows)

            unique_index_rows = connection.execute(
                text(
                    "SELECT table_name, index_name, non_unique, seq_in_index, column_name "
                    "FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name IN "
                    "('users', 'sell_land_requests', 'sell_land_payments', 'site_visit_requests', "
                    "'razorpay_payment_orders', 'razorpay_webhook_logs') "
                    "ORDER BY table_name, index_name, seq_in_index"
                )
            ).all()
            _validate_unique_keys(unique_index_rows)

            grants = connection.exec_driver_sql("SHOW GRANTS FOR CURRENT_USER()").all()
            _validate_grants(grants)

        if os.environ.get(PREFLIGHT_ONLY_ENV) == "1":
            test_engine.dispose()
            print("MySQL Site Visit preflight: PASS")
            yield None
            return

        factory = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    except _SafePreflightError as exc:
        test_engine.dispose()
        pytest.fail(f"MySQL Site Visit preflight failed: {exc}", pytrace=False)
    except Exception:
        test_engine.dispose()
        pytest.fail(
            "MySQL Site Visit preflight failed: connection or read-only validation error; details suppressed",
            pytrace=False,
        )

    try:
        yield factory
    finally:
        # Dispose pooled connections only. Database and test rows are left intact.
        test_engine.dispose()


@pytest.mark.skipif(
    os.environ.get(PREFLIGHT_ONLY_ENV) != "1",
    reason="set SITE_VISIT_MYSQL_PREFLIGHT_ONLY=1 to run the read-only preflight",
)
def test_mysql_preflight_only(existing_mysql_sessions):
    """The fixture exits after read-only validation when preflight mode is enabled."""
    pass


@pytest.fixture
def records(existing_mysql_sessions):
    token = uuid.uuid4().hex
    with existing_mysql_sessions() as db:
        seller = User(
            fullname="Site Visit Seller",
            email=f"seller-{token}@example.test",
            mobile=f"91{uuid.uuid4().int % 10**13:013d}",
            password_hash="test-only-hash",
        )
        buyer = User(
            fullname="Site Visit Buyer",
            email=f"buyer-{token}@example.test",
            mobile=f"92{uuid.uuid4().int % 10**13:013d}",
            password_hash="test-only-hash",
        )
        db.add_all([seller, buyer])
        db.flush()
        listing = SellLandRequest(
            user_id=seller.id,
            title="MySQL Site Visit Test Listing",
            status=SellLandStatus.LIVE.value,
        )
        db.add(listing)
        db.flush()
        booking = SiteVisitRequest(
            listing_id=listing.id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            property_name_snapshot="MySQL Site Visit Test Listing",
            buyer_name_snapshot=buyer.fullname,
            buyer_mobile_snapshot=buyer.mobile,
            seller_name_snapshot=seller.fullname,
            seller_mobile_snapshot=seller.mobile,
            preferred_visit_date=date(2027, 1, 1),
            preferred_visit_time=time(10, 30),
            visitor_count=2,
            pickup_address="Test-only pickup address",
            site_visit_fee_paise=12345,
            status="pending_payment",
            payment_status="initiated",
        )
        db.add(booking)
        db.commit()
        ids = (seller.id, buyer.id, listing.id, booking.id)
    return ids


def _add_order(existing_mysql_sessions, records, order_id: str) -> None:
    _, buyer_id, listing_id, booking_id = records
    with existing_mysql_sessions() as db:
        db.add(
            RazorpayPaymentOrder(
                user_id=buyer_id,
                property_id=listing_id,
                amount=123.45,
                amount_paise=12345,
                currency="INR",
                payment_context="site_visit",
                site_visit_request_id=booking_id,
                order_id=order_id,
                status="CREATED",
            )
        )
        booking = db.get(SiteVisitRequest, booking_id)
        booking.payment_order_id = order_id
        db.commit()


class FakeRazorpay:
    """Deterministic gateway double; no network calls are made."""

    def __init__(self, order_id: str, *, amount: int = 12345, status: str = "captured"):
        self.order_id = order_id
        self.amount = amount
        self.status = status
        self.utility = self
        self.payment = _FakePaymentAPI(self)
        self.order = _FakeOrderAPI(self)
        self.create_calls = 0
        self.order_notes = {}
        self._lock = threading.Lock()

    def verify_payment_signature(self, _payload):
        return None

    def fetch_payment(self, payment_id):
        return {
            "id": payment_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "currency": "INR",
            "status": self.status,
        }

    def create_order(self, payload):
        with self._lock:
            self.create_calls += 1
            self.order_notes = payload["notes"]
        return {"id": self.order_id, "amount": payload["amount"], "currency": "INR"}

    def fetch_order(self, order_id):
        return {
            "id": order_id,
            "amount": self.amount,
            "amount_paid": 0,
            "currency": "INR",
            "status": "created",
            "notes": self.order_notes,
        }

    def order_payments(self, _order_id, _params):
        return {"count": 0, "items": []}


class _FakePaymentAPI:
    def __init__(self, client):
        self.client = client

    def fetch(self, payment_id):
        return self.client.fetch_payment(payment_id)


class _FakeOrderAPI:
    def __init__(self, client):
        self.client = client

    def create(self, payload):
        return self.client.create_order(payload)

    def fetch(self, order_id):
        return self.client.fetch_order(order_id)

    def payments(self, order_id, params):
        return self.client.order_payments(order_id, params)


def _verified_payload(order_id: str, payment_id: str) -> SiteVisitVerifyPaymentRequest:
    return SiteVisitVerifyPaymentRequest(
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature="test-signature",
    )


def _captured_webhook(order_id: str, payment_id: str, event_id: str) -> dict:
    return {
        "event": "payment.captured",
        "event_id": event_id,
        "payload_json": "{}",
        "signature": "test-signature",
        "order_id": order_id,
        "payment_id": payment_id,
        "payment_status": "captured",
        "amount_paise": 12345,
        "currency": "INR",
    }


def _race(workers):
    barrier = threading.Barrier(len(workers), timeout=20)

    def invoke(work):
        barrier.wait()
        return work()

    with ThreadPoolExecutor(max_workers=len(workers)) as executor:
        return [future.result(timeout=45) for future in [executor.submit(invoke, work) for work in workers]]


def test_mysql_concurrent_duplicate_webhook_delivery(existing_mysql_sessions, records, monkeypatch):
    _, _, _, booking_id = records
    order_id = f"order_sv_{uuid.uuid4().hex[:20]}"
    event_id = f"evt_{uuid.uuid4().hex[:32]}"
    payment_id = f"pay_{uuid.uuid4().hex[:20]}"
    _add_order(existing_mysql_sessions, records, order_id)
    monkeypatch.setattr(site_visit_payment_service, "_get_client", lambda: FakeRazorpay(order_id))
    args = _captured_webhook(order_id, payment_id, event_id)

    results = _race(
        [
            lambda: _deliver_webhook(existing_mysql_sessions, args),
            lambda: _deliver_webhook(existing_mysql_sessions, args),
        ]
    )

    with existing_mysql_sessions() as db:
        booking = db.get(SiteVisitRequest, booking_id)
        order = db.query(RazorpayPaymentOrder).filter_by(order_id=order_id).one()
        logs = db.query(RazorpayWebhookLog).filter_by(event_key=event_id).all()
        assert results == [(True, None), (True, None)]
        assert len(logs) == 1
        assert booking.payment_status == "success" and booking.payment_id == payment_id
        assert order.status == "SUCCESS" and order.payment_id == payment_id


def _deliver_webhook(existing_mysql_sessions, args):
    with existing_mysql_sessions() as db:
        return payment_service.handle_webhook_event(db, **args)


def test_mysql_concurrent_verification_and_webhook(existing_mysql_sessions, records, monkeypatch):
    _, buyer_id, _, booking_id = records
    order_id = f"order_sv_{uuid.uuid4().hex[:20]}"
    payment_id = f"pay_{uuid.uuid4().hex[:20]}"
    _add_order(existing_mysql_sessions, records, order_id)
    monkeypatch.setattr(site_visit_payment_service, "_get_client", lambda: FakeRazorpay(order_id))
    args = _captured_webhook(order_id, payment_id, f"evt_{uuid.uuid4().hex[:32]}")

    def verify():
        with existing_mysql_sessions() as db:
            return verify_site_visit_payment(
                db,
                _verified_payload(order_id, payment_id),
                booking_id=booking_id,
                buyer_id=buyer_id,
            )

    results = _race([verify, lambda: _deliver_webhook(existing_mysql_sessions, args)])
    with existing_mysql_sessions() as db:
        booking = db.get(SiteVisitRequest, booking_id)
        order = db.query(RazorpayPaymentOrder).filter_by(order_id=order_id).one()
        assert booking.payment_status == "success" and booking.payment_id == payment_id
        assert order.status == "SUCCESS" and order.payment_id == payment_id
        assert sum(1 for result in results if result == (True, None)) == 1
        assert sum(
            1 for result in results
            if isinstance(result, tuple) and len(result) == 2 and getattr(result[0], "status", None) == "success"
        ) == 1


def test_mysql_concurrent_order_creation_is_single_active_order(existing_mysql_sessions, records, monkeypatch):
    _, buyer_id, _, booking_id = records
    order_id = f"order_sv_{uuid.uuid4().hex[:20]}"
    client = FakeRazorpay(order_id)
    monkeypatch.setattr(site_visit_payment_service, "_get_client", lambda: client)

    def create():
        with existing_mysql_sessions() as db:
            return create_site_visit_order(db, booking_id=booking_id, buyer_id=buyer_id)

    results = _race([create, create])
    with existing_mysql_sessions() as db:
        orders = db.query(RazorpayPaymentOrder).filter_by(site_visit_request_id=booking_id).all()
        booking = db.get(SiteVisitRequest, booking_id)
        assert all(error is None for _, error in results)
        assert len(orders) == 1 and client.create_calls == 1
        assert booking.payment_order_id == order_id


def test_mysql_late_capture_after_buyer_cancellation(existing_mysql_sessions, records, monkeypatch):
    _, buyer_id, _, booking_id = records
    order_id = f"order_sv_{uuid.uuid4().hex[:20]}"
    payment_id = f"pay_{uuid.uuid4().hex[:20]}"
    _add_order(existing_mysql_sessions, records, order_id)
    with existing_mysql_sessions() as db:
        response, error = cancel_site_visit_payment_attempt(db, booking_id=booking_id, buyer_id=buyer_id)
        assert error is None and response["payment_status"] == "cancelled"

    monkeypatch.setattr(site_visit_payment_service, "_get_client", lambda: FakeRazorpay(order_id))
    result = _deliver_webhook(
        existing_mysql_sessions,
        _captured_webhook(order_id, payment_id, f"evt_{uuid.uuid4().hex[:32]}"),
    )
    with existing_mysql_sessions() as db:
        booking = db.get(SiteVisitRequest, booking_id)
        order = db.query(RazorpayPaymentOrder).filter_by(order_id=order_id).one()
        assert result == (True, None)
        assert booking.payment_status == "success" and booking.payment_id == payment_id
        assert order.status == "SUCCESS" and order.buyer_cancel_reported_at is not None


def test_mysql_duplicate_captured_payment_is_preserved_for_reconciliation(existing_mysql_sessions, records, monkeypatch):
    _, _, _, booking_id = records
    first_order_id = f"order_sv_{uuid.uuid4().hex[:20]}"
    second_order_id = f"order_sv_{uuid.uuid4().hex[:20]}"
    first_payment_id = f"pay_{uuid.uuid4().hex[:20]}"
    second_payment_id = f"pay_{uuid.uuid4().hex[:20]}"
    _add_order(existing_mysql_sessions, records, first_order_id)
    with existing_mysql_sessions() as db:
        booking = db.get(SiteVisitRequest, booking_id)
        db.add(
            RazorpayPaymentOrder(
                user_id=booking.buyer_id,
                property_id=booking.listing_id,
                amount=123.45,
                amount_paise=12345,
                currency="INR",
                payment_context="site_visit",
                site_visit_request_id=booking_id,
                order_id=second_order_id,
                status="CREATED",
            )
        )
        db.commit()

    monkeypatch.setattr(site_visit_payment_service, "_get_client", lambda: FakeRazorpay(first_order_id))
    first = _deliver_webhook(
        existing_mysql_sessions,
        _captured_webhook(first_order_id, first_payment_id, f"evt_{uuid.uuid4().hex[:32]}"),
    )
    monkeypatch.setattr(site_visit_payment_service, "_get_client", lambda: FakeRazorpay(second_order_id))
    second_event_id = f"evt_{uuid.uuid4().hex[:32]}"
    second = _deliver_webhook(
        existing_mysql_sessions,
        _captured_webhook(second_order_id, second_payment_id, second_event_id),
    )

    with existing_mysql_sessions() as db:
        booking = db.get(SiteVisitRequest, booking_id)
        second_order = db.query(RazorpayPaymentOrder).filter_by(order_id=second_order_id).one()
        reconciliation = db.query(RazorpayWebhookLog).filter_by(
            event="site_visit.duplicate_capture",
            order_id=second_order_id,
            payment_id=second_payment_id,
            status="reconciliation_required",
        ).one()
        assert first == (True, None) and second == (True, None)
        assert booking.payment_id == first_payment_id and booking.payment_status == "success"
        assert second_order.status == "DUPLICATE_SUCCESS" and second_order.payment_id == second_payment_id
        assert reconciliation.payment_context == "site_visit"


def test_mysql_unique_event_key_allows_legacy_nulls_and_rejects_duplicate_key(existing_mysql_sessions):
    legacy_event_id = f"legacy_{uuid.uuid4().hex[:20]}"
    event_key = f"evt_{uuid.uuid4().hex[:32]}"
    with existing_mysql_sessions() as db:
        db.add_all(
            [
                RazorpayWebhookLog(event_id=legacy_event_id, event="legacy", payload="{}", event_key=None),
                RazorpayWebhookLog(event_id=legacy_event_id, event="legacy", payload="{}", event_key=None),
            ]
        )
        db.commit()
        assert db.query(RazorpayWebhookLog).filter_by(event_id=legacy_event_id, event_key=None).count() == 2

        db.add(RazorpayWebhookLog(event_id=event_key, event_key=event_key, event="test", payload="{}"))
        db.commit()
        db.add(RazorpayWebhookLog(event_id=event_key, event_key=event_key, event="test", payload="{}"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert db.query(RazorpayWebhookLog).filter_by(event_key=event_key).count() == 1


def test_mysql_concurrent_completion_verification_is_single_use(existing_mysql_sessions, records, monkeypatch):
    """InnoDB row locking permits exactly one successful concurrent redemption."""
    monkeypatch.setattr(
        completion_code,
        "settings",
        SimpleNamespace(site_visit_otp_encryption_key="31" * 32, site_visit_otp_hmac_key="42" * 32),
    )
    monkeypatch.setattr(site_visit_service, "notify_users", lambda **kwargs: [])
    _, buyer_id, _, booking_id = records
    with existing_mysql_sessions() as db:
        officer = User(
            fullname="Completion Officer",
            email=f"officer-{uuid.uuid4().hex}@example.test",
            mobile=f"93{uuid.uuid4().int % 10**13:013d}",
            password_hash="test-only-hash",
            role="FIELD_OFFICER",
            is_active=True,
        )
        db.add(officer)
        db.flush()
        booking = db.get(SiteVisitRequest, booking_id)
        booking.payment_status = "success"
        booking.status = "in_progress"
        booking.assigned_field_officer_id = officer.id
        booking.started_at = datetime.utcnow()
        booking.completion_code_hash = completion_code.hash_completion_code(booking.id, "000007")
        booking.completion_code_encrypted = completion_code.encrypt_completion_code(booking.id, "000007")
        booking.completion_code_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.commit()
        officer_id = officer.id

    barrier = threading.Barrier(2)

    def redeem():
        with existing_mysql_sessions() as db:
            barrier.wait(timeout=10)
            return site_visit_service.verify_site_visit_completion(
                db, request_id=booking_id, officer_id=officer_id, code="000007"
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: redeem(), range(2)))

    successful_results = [result for result in results if result[0] is not None]
    failed_results = [result for result in results if result[0] is None]
    assert len(successful_results) == 1
    assert successful_results[0][0]["booking_status"] == "completed"
    assert len(failed_results) == 1
    assert failed_results[0][1] in {
        "Site Visit completion code has already been used",
        "Site Visit request cannot be completed in its current state",
    }
    with existing_mysql_sessions() as db:
        booking = db.get(SiteVisitRequest, booking_id)
        assert booking.status == "completed"
        assert booking.completion_code_used_at is not None
        assert booking.completion_code_hash is None
        assert booking.completion_code_encrypted is None
        completed_at = booking.completed_at

    with existing_mysql_sessions() as db:
        reused, error = site_visit_service.verify_site_visit_completion(
            db, request_id=booking_id, officer_id=officer_id, code="000007"
        )
        assert reused is None
        assert error == "Site Visit request cannot be completed in its current state"
        booking = db.get(SiteVisitRequest, booking_id)
        assert booking.status == "completed"
        assert booking.completed_at == completed_at
