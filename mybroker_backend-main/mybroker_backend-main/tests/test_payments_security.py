from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import threading
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.payments import service as payment_service
from app.payments.models import RazorpayPaymentOrder, RazorpayWebhookLog
from app.payments.schemas import CreateOrderRequest, VerifyPaymentRequest
from app.sell_land.constants import BookingStatus, PaymentStatus, SellLandStatus
from app.sell_land.models import SellLandBooking, SellLandPayment, SellLandRequest
from app.sell_land.schemas import SellLandRazorpayVerifyRequest
from app.sell_land import service as sell_land_service
from app.users.model import User


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def payment_fixture(db):
    seller = User(fullname="Seller", email="seller@example.test", mobile="9111111111", password_hash="hash")
    buyer = User(fullname="Buyer", email="buyer@example.test", mobile="9222222222", password_hash="hash")
    other = User(fullname="Other", email="other@example.test", mobile="9333333333", password_hash="hash")
    db.add_all([seller, buyer, other])
    db.flush()
    listing = SellLandRequest(user_id=seller.id, title="Test listing", status=SellLandStatus.LIVE.value)
    db.add(listing)
    db.flush()
    booking = SellLandBooking(
        request_id=listing.id,
        buyer_id=buyer.id,
        buyer_name="Buyer",
        buyer_mobile=buyer.mobile,
        deal_amount=Decimal("500000"),
        booking_fee_amount=Decimal("1234.56"),
        payment_status=PaymentStatus.INITIATED.value,
        booking_status=BookingStatus.BOOKED.value,
    )
    db.add(booking)
    order = RazorpayPaymentOrder(
        user_id=buyer.id,
        property_id=listing.id,
        amount=1234.56,
        amount_paise=123456,
        currency="INR",
        order_id="order_test_12345",
        status="CREATED",
    )
    db.add(order)
    db.commit()
    return seller, buyer, other, listing, booking, order


class FakeClient:
    def __init__(self, amount=123456, status="captured", currency="INR"):
        self.fetch_count = 0
        self.utility = self
        self.payment = self
        self.amount = amount
        self.status = status
        self.currency = currency

    def verify_payment_signature(self, _payload):
        return None

    def fetch(self, payment_id):
        self.fetch_count += 1
        return {
            "id": payment_id,
            "order_id": "order_test_12345",
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
        }


def _verify_payload():
    return VerifyPaymentRequest(
        razorpay_order_id="order_test_12345",
        razorpay_payment_id="pay_test_12345",
        razorpay_signature="signature_test_12345",
    )


def test_payment_verification_rejects_another_users_order(db, payment_fixture, monkeypatch):
    _, _, other, _, _, _ = payment_fixture
    monkeypatch.setattr(payment_service, "_get_client", lambda: pytest.fail("gateway must not be called"))

    result, error = payment_service.verify_payment(db, _verify_payload(), user_id=other.id)

    assert result is None
    assert error == "Not authorized"


def test_payment_verification_rejects_provider_amount_mismatch(db, payment_fixture, monkeypatch):
    _, buyer, _, _, booking, order = payment_fixture
    client = FakeClient(amount=123455)
    monkeypatch.setattr(payment_service, "_get_client", lambda: client)

    result, error = payment_service.verify_payment(db, _verify_payload(), user_id=buyer.id)

    assert result is None
    assert error == "Payment details do not match the order"
    db.refresh(order)
    db.refresh(booking)
    assert order.status == "CREATED"
    assert booking.payment_status == PaymentStatus.INITIATED.value


@pytest.mark.parametrize(
    "client",
    [FakeClient(status="authorized"), FakeClient(currency="USD")],
    ids=["not-captured", "wrong-currency"],
)
def test_payment_verification_rejects_unsettled_or_wrong_currency_payment(
    db, payment_fixture, monkeypatch, client
):
    _, buyer, _, _, _, order = payment_fixture
    monkeypatch.setattr(payment_service, "_get_client", lambda: client)

    result, error = payment_service.verify_payment(db, _verify_payload(), user_id=buyer.id)

    assert result is None
    assert error == "Payment details do not match the order"
    db.refresh(order)
    assert order.status == "CREATED"


def test_payment_verification_rejects_local_order_amount_drift(db, payment_fixture, monkeypatch):
    _, buyer, _, _, _, order = payment_fixture
    order.amount_paise += 1
    db.commit()
    monkeypatch.setattr(payment_service, "_get_client", lambda: pytest.fail("gateway must not be called"))

    result, error = payment_service.verify_payment(db, _verify_payload(), user_id=buyer.id)

    assert result is None
    assert error == "Order amount or currency does not match the booking"


def test_successful_payment_verification_is_idempotent(db, payment_fixture, monkeypatch):
    _, buyer, _, listing, booking, order = payment_fixture
    client = FakeClient()
    monkeypatch.setattr(payment_service, "_get_client", lambda: client)

    first, first_error = payment_service.verify_payment(db, _verify_payload(), user_id=buyer.id)
    second, second_error = payment_service.verify_payment(db, _verify_payload(), user_id=buyer.id)

    assert first_error is None and first.status == "success"
    assert second_error is None and second.status == "success"
    assert client.fetch_count == 1
    db.refresh(order)
    db.refresh(booking)
    db.refresh(listing)
    assert order.status == "SUCCESS"
    assert booking.payment_status == PaymentStatus.SUCCESS.value
    assert listing.status == SellLandStatus.BOOKED.value


def test_order_amount_comes_from_backend_booking_fee(db, payment_fixture, monkeypatch):
    _, buyer, _, listing, _, _ = payment_fixture

    class OrderClient:
        class order:
            @staticmethod
            def create(payload):
                assert payload["amount"] == 123456
                return {"id": "order_created_12345", "amount": 123456, "currency": "INR"}

    monkeypatch.setattr(payment_service, "_get_client", lambda: OrderClient())
    request = CreateOrderRequest(amount=1, user_id=buyer.id, property_id=listing.id)

    response, error = payment_service.create_order(db, request, user_id=buyer.id)

    assert error is None
    assert response.amount == 123456
    stored = db.query(RazorpayPaymentOrder).filter_by(order_id=response.order_id).one()
    assert stored.amount_paise == 123456


def test_duplicate_webhook_is_idempotent(db, payment_fixture):
    _, buyer, _, listing, booking, order = payment_fixture
    event = {
        "event": "payment.captured",
        "event_id": "evt_test_12345",
        "payload": "{}",
    }
    args = dict(
        event=event["event"],
        event_id=event["event_id"],
        payload_json=event["payload"],
        signature="verified-test-signature",
        order_id=order.order_id,
        payment_id="pay_test_12345",
        payment_status="captured",
        amount_paise=order.amount_paise,
        currency=order.currency,
    )

    first = payment_service.handle_webhook_event(db, **args)
    second = payment_service.handle_webhook_event(db, **args)

    assert first == (True, None)
    assert second == (True, None)
    db.refresh(order)
    db.refresh(booking)
    db.refresh(listing)
    assert order.status == "SUCCESS"
    assert booking.payment_status == PaymentStatus.SUCCESS.value
    assert listing.status == SellLandStatus.BOOKED.value
    assert db.query(RazorpayPaymentOrder).filter_by(order_id=order.order_id).count() == 1
    event_logs = db.query(RazorpayWebhookLog).filter_by(event_key=event["event_id"]).all()
    assert len(event_logs) == 1
    assert event_logs[0].event_id == event["event_id"]


def test_legacy_duplicate_event_ids_remain_compatible_when_canonical_key_is_null(db):
    for payload in ("legacy first", "legacy second"):
        db.add(
            RazorpayWebhookLog(
                event_id="legacy-payload-id",
                event_key=None,
                event="payment.captured",
                payload=payload,
                status="processed",
            )
        )
    db.commit()

    assert db.query(RazorpayWebhookLog).filter_by(
        event_id="legacy-payload-id", event_key=None
    ).count() == 2


def test_event_key_migration_preserves_legacy_duplicates_and_enforces_new_uniqueness():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20261115_0041_unique_razorpay_webhook_event_key.py"
    )
    spec = importlib.util.spec_from_file_location("webhook_event_key_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE razorpay_webhook_logs (id INTEGER PRIMARY KEY, event_id VARCHAR(80))"
        ))
        connection.execute(text(
            "INSERT INTO razorpay_webhook_logs (event_id) VALUES ('legacy-duplicate'), ('legacy-duplicate'), (NULL)"
        ))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

    assert "event_key" in {column["name"] for column in inspect(engine).get_columns("razorpay_webhook_logs")}
    with engine.begin() as connection:
        assert connection.execute(text(
            "SELECT COUNT(*) FROM razorpay_webhook_logs WHERE event_id = 'legacy-duplicate' AND event_key IS NULL"
        )).scalar_one() == 2
        connection.execute(text(
            "INSERT INTO razorpay_webhook_logs (event_id, event_key) VALUES ('new-a', 'evt_unique_1')"
        ))
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(text(
                    "INSERT INTO razorpay_webhook_logs (event_id, event_key) VALUES ('new-b', 'evt_unique_1')"
                ))
    engine.dispose()


def test_webhook_claim_rolls_back_and_same_event_can_retry(db, payment_fixture):
    _, _, _, _, booking, order = payment_fixture
    args = dict(
        event="payment.captured",
        event_id="evt_retry_after_rollback",
        payload_json="{}",
        signature="verified-test-signature",
        order_id=order.order_id,
        payment_id="pay_test_12345",
        payment_status="captured",
        amount_paise=order.amount_paise - 1,
        currency=order.currency,
    )

    failed, error = payment_service.handle_webhook_event(db, **args)
    assert not failed and "amount" in error.lower()
    assert db.query(RazorpayWebhookLog).filter_by(event_key=args["event_id"]).count() == 0
    db.refresh(order)
    db.refresh(booking)
    assert order.status == "CREATED"
    assert booking.payment_status == PaymentStatus.INITIATED.value

    args["amount_paise"] = order.amount_paise
    retried, retry_error = payment_service.handle_webhook_event(db, **args)
    assert retried and retry_error is None
    assert db.query(RazorpayWebhookLog).filter_by(event_key=args["event_id"]).count() == 1
    db.refresh(order)
    assert order.status == "SUCCESS"


def test_concurrent_duplicate_webhook_delivery_creates_one_log_and_one_transition(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'duplicate_webhook_race.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seller = User(fullname="Seller", email="dupe-seller@example.test", mobile="9111111111", password_hash="hash")
        buyer = User(fullname="Buyer", email="dupe-buyer@example.test", mobile="9222222222", password_hash="hash")
        session.add_all([seller, buyer])
        session.flush()
        listing = SellLandRequest(user_id=seller.id, title="Duplicate event listing", status=SellLandStatus.LIVE.value)
        session.add(listing)
        session.flush()
        booking = SellLandBooking(
            request_id=listing.id,
            buyer_id=buyer.id,
            buyer_name="Buyer",
            buyer_mobile=buyer.mobile,
            deal_amount=Decimal("500000"),
            booking_fee_amount=Decimal("1234.56"),
            payment_status=PaymentStatus.INITIATED.value,
            booking_status=BookingStatus.BOOKED.value,
        )
        order = RazorpayPaymentOrder(
            user_id=buyer.id,
            property_id=listing.id,
            amount=1234.56,
            amount_paise=123456,
            currency="INR",
            order_id="order_duplicate_event_race",
            status="CREATED",
        )
        session.add_all([booking, order])
        session.commit()
        order_id = order.order_id

    monkeypatch.setattr(payment_service, "_notify_buyer_booking_paid", lambda *_args, **_kwargs: None)
    start = threading.Barrier(2, timeout=10)
    args = dict(
        event="payment.captured",
        event_id="evt_concurrent_duplicate",
        payload_json="{}",
        signature="verified-test-signature",
        order_id=order_id,
        payment_id="pay_duplicate_event_race",
        payment_status="captured",
        amount_paise=123456,
        currency="INR",
    )

    def deliver():
        with Session(engine) as session:
            start.wait()
            return payment_service.handle_webhook_event(session, **args)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(deliver) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]

    with Session(engine) as session:
        order = session.query(RazorpayPaymentOrder).filter_by(order_id=order_id).one()
        booking = session.query(SellLandBooking).one()
        logs = session.query(RazorpayWebhookLog).filter_by(event_key="evt_concurrent_duplicate").all()
        assert results == [(True, None), (True, None)]
        assert len(logs) == 1
        assert order.status == "SUCCESS" and order.payment_id == "pay_duplicate_event_race"
        assert booking.payment_status == PaymentStatus.SUCCESS.value
    engine.dispose()


def test_seller_payment_callback_verifies_amount_owner_and_replay(db, payment_fixture, monkeypatch):
    seller, _, other, listing, _, _ = payment_fixture
    listing.status = SellLandStatus.DRAFT.value
    payment = SellLandPayment(
        request_id=listing.id,
        method="razorpay",
        amount=1234.56,
        status=PaymentStatus.INITIATED.value,
        provider_ref="order_seller_12345",
    )
    db.add(payment)
    db.commit()
    client = FakeClient()
    client.payment.fetch = lambda _payment_id: {
        "order_id": "order_seller_12345",
        "amount": 123456,
        "currency": "INR",
        "status": "captured",
    }
    monkeypatch.setattr(sell_land_service, "_get_razorpay_client", lambda: client)
    payload = SellLandRazorpayVerifyRequest(
        razorpay_order_id="order_seller_12345",
        razorpay_payment_id="pay_seller_12345",
        razorpay_signature="signature_seller_12345",
    )

    denied, denied_error = sell_land_service.verify_seller_razorpay_payment(db, other.id, payload)
    first, first_error = sell_land_service.verify_seller_razorpay_payment(db, seller.id, payload)
    second, second_error = sell_land_service.verify_seller_razorpay_payment(db, seller.id, payload)

    assert denied is None and denied_error == "Sell land request not found"
    assert first_error is None and first.status == "success"
    assert second_error is None and second.status == "success"
    db.refresh(payment)
    db.refresh(listing)
    assert payment.gateway_payment_id == "pay_seller_12345"
    assert listing.status == SellLandStatus.PENDING.value


def test_seller_payment_callback_rejects_amount_mismatch(db, payment_fixture, monkeypatch):
    seller, _, _, listing, _, _ = payment_fixture
    payment = SellLandPayment(
        request_id=listing.id,
        method="razorpay",
        amount=1234.56,
        status=PaymentStatus.INITIATED.value,
        provider_ref="order_seller_12345",
    )
    db.add(payment)
    db.commit()
    client = FakeClient(amount=123455)
    client.payment.fetch = lambda _payment_id: {
        "order_id": "order_seller_12345",
        "amount": 123455,
        "currency": "INR",
        "status": "captured",
    }
    monkeypatch.setattr(sell_land_service, "_get_razorpay_client", lambda: client)
    payload = SellLandRazorpayVerifyRequest(
        razorpay_order_id="order_seller_12345",
        razorpay_payment_id="pay_seller_12345",
        razorpay_signature="signature_seller_12345",
    )

    result, error = sell_land_service.verify_seller_razorpay_payment(db, seller.id, payload)

    assert result is None
    assert error == "Payment details do not match the order"
    db.refresh(payment)
    assert payment.status == PaymentStatus.INITIATED.value
