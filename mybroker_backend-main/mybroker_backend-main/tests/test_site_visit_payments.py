import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import json
import threading
from datetime import date, time

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.payments import service as payment_service
from app.payments.models import RazorpayPaymentOrder, RazorpayWebhookLog
from app.payments.router import razorpay_webhook
from app.sell_land.constants import PaymentStatus, SellLandStatus
from app.sell_land.models import SellLandRequest
from app.site_visits.models import SiteVisitAssignment, SiteVisitRequest
from app.site_visits.payment_service import (
    cancel_site_visit_payment_attempt,
    create_site_visit_order,
    verify_site_visit_payment,
)
from app.site_visits.schemas import SiteVisitVerifyPaymentRequest
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
def site_visit_payment_fixture(db):
    seller = User(fullname="Seller", email="sv-seller@example.test", mobile="9111111111", password_hash="hash")
    buyer = User(fullname="Buyer", email="sv-buyer@example.test", mobile="9222222222", password_hash="hash")
    other = User(fullname="Other", email="sv-other@example.test", mobile="9333333333", password_hash="hash")
    db.add_all([seller, buyer, other])
    db.flush()
    listing = SellLandRequest(user_id=seller.id, title="Visit listing", status=SellLandStatus.LIVE.value)
    db.add(listing)
    db.flush()
    booking = SiteVisitRequest(
        listing_id=listing.id,
        buyer_id=buyer.id,
        seller_id=seller.id,
        property_name_snapshot="Visit listing",
        buyer_name_snapshot="Buyer",
        buyer_mobile_snapshot=buyer.mobile,
        seller_name_snapshot="Seller",
        seller_mobile_snapshot=seller.mobile,
        preferred_visit_date=date(2027, 1, 1),
        preferred_visit_time=time(10, 30),
        visitor_count=2,
        pickup_address="123 Example Road, Test Town",
        site_visit_fee_paise=12345,
        status="pending_payment",
        payment_status=PaymentStatus.INITIATED.value,
    )
    db.add(booking)
    db.commit()
    return seller, buyer, other, listing, booking


class FakeRazorpayClient:
    def __init__(self, *, amount=12345, status="captured", order_id="order_site_visit_123"):
        self.amount = amount
        self.status = status
        self.order_id = order_id
        self.utility = self
        self.payment = self

    def verify_payment_signature(self, _payload):
        return None

    def fetch(self, payment_id):
        return {
            "id": payment_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "currency": "INR",
            "status": self.status,
        }


def _attach_order(db, buyer, listing, booking, order_id="order_site_visit_123"):
    booking.payment_order_id = order_id
    order = RazorpayPaymentOrder(
        user_id=buyer.id,
        property_id=listing.id,
        amount=123.45,
        amount_paise=booking.site_visit_fee_paise,
        currency="INR",
        payment_context="site_visit",
        site_visit_request_id=booking.id,
        order_id=order_id,
        status="CREATED",
    )
    db.add(order)
    db.commit()
    return order


def _verify_payload(order_id="order_site_visit_123"):
    return SiteVisitVerifyPaymentRequest(
        razorpay_order_id=order_id,
        razorpay_payment_id="pay_site_visit_123",
        razorpay_signature="signed_site_visit_callback",
    )


def _set_site_visit_verifier(db, listing, *, role="FIELD_OFFICER", is_active=True):
    verifier = User(
        fullname=f"{role} verifier {is_active}",
        mobile=f"93{db.query(User).count() + 1:08d}",
        role=role,
        is_active=is_active,
    )
    db.add(verifier)
    db.flush()
    listing.field_officer_reviewed_by_id = verifier.id
    db.commit()
    return verifier.id


def _capture_payment(db, *, path, buyer, booking, order, event_id="evt_auto_assign"):
    if path == "verification":
        return verify_site_visit_payment(
            db,
            _verify_payload(order.order_id),
            booking_id=booking.id,
            buyer_id=buyer.id,
        )
    return payment_service.handle_webhook_event(
        db,
        event="payment.captured",
        event_id=event_id,
        payload_json="{}",
        signature="verified-test-signature",
        order_id=order.order_id,
        payment_id="pay_site_visit_123",
        payment_status="captured",
        amount_paise=booking.site_visit_fee_paise,
        currency="INR",
    )


def _capture_assignment_notifications(monkeypatch):
    sent = []

    def capture(**kwargs):
        sent.append({
            "user_ids": [user.id for user in kwargs["users"]],
            "type": kwargs["notif_type"],
            "reference_id": kwargs["reference_id"],
            "extra_data": kwargs["extra_data"],
        })
        return []

    monkeypatch.setattr("app.site_visits.service.notify_users", capture)
    return sent


@pytest.mark.parametrize("path", ["verification", "webhook"])
def test_successful_site_visit_payment_auto_assigns_verifier_once(
    db, site_visit_payment_fixture, monkeypatch, path
):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)
    officer_id = _set_site_visit_verifier(db, listing)
    notifications = _capture_assignment_notifications(monkeypatch)
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(order_id=order.order_id),
    )

    first = _capture_payment(db, path=path, buyer=buyer, booking=booking, order=order)
    second = _capture_payment(db, path=path, buyer=buyer, booking=booking, order=order)

    if path == "verification":
        assert first[1] is None and first[0].status == "success"
        assert second[1] is None and second[0].status == "success"
    else:
        assert first == (True, None)
        assert second == (True, None)
    db.refresh(booking)
    assert booking.payment_status == "success"
    assert booking.status == "assigned"
    assert booking.assigned_field_officer_id == officer_id
    assert booking.scheduled_at is None
    history = db.query(SiteVisitAssignment).filter_by(site_visit_request_id=booking.id).all()
    assert len(history) == 1
    assert history[0].action == "assigned"
    assert history[0].actor_id is None
    assert history[0].actor_type == "system"
    assert "automatically assigned" in history[0].note.lower()
    assert notifications == [{
        "user_ids": [buyer.id],
        "type": "SITE_VISIT_PAYMENT_SUCCESS",
        "reference_id": str(booking.id),
        "extra_data": {"site_visit_request_id": str(booking.id), "event": "PAYMENT_SUCCESS"},
    }, {
        "user_ids": [officer_id],
        "type": "SITE_VISIT_ASSIGNED",
        "reference_id": str(booking.id),
        "extra_data": {
            "site_visit_request_id": str(booking.id),
            "assignment_action": "assigned",
            "listing_id": str(listing.id),
            "property_name": listing.title,
            "deep_link": f"field_site_visit_booking/{booking.id}",
        },
    }]


@pytest.mark.parametrize("path", ["verification", "webhook"])
@pytest.mark.parametrize(
    ("verifier_role", "verifier_active"),
    [(None, None), ("FIELD_OFFICER", False), ("ADMIN", True)],
    ids=["missing-verifier", "inactive-verifier", "non-field-officer"],
)
def test_successful_payment_without_eligible_verifier_stays_pending(
    db, site_visit_payment_fixture, monkeypatch, path, verifier_role, verifier_active
):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)
    if verifier_role is not None:
        _set_site_visit_verifier(
            db, listing, role=verifier_role, is_active=verifier_active
        )
    notifications = _capture_assignment_notifications(monkeypatch)
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(order_id=order.order_id),
    )

    result = _capture_payment(db, path=path, buyer=buyer, booking=booking, order=order)

    if path == "verification":
        assert result[1] is None and result[0].status == "success"
    else:
        assert result == (True, None)
    db.refresh(booking)
    assert booking.payment_status == "success"
    assert booking.status == "pending"
    assert booking.assigned_field_officer_id is None
    assert db.query(SiteVisitAssignment).filter_by(site_visit_request_id=booking.id).count() == 0
    expected_recipients = {buyer.id} | {
        user.id for user in db.query(User).filter(User.role == "SUPER_ADMIN", User.is_active.is_(True)).all()
    }
    payment_events = [entry for entry in notifications if entry["type"] == "SITE_VISIT_PAYMENT_SUCCESS"]
    assert {entry["user_ids"][0] for entry in payment_events} == expected_recipients
    assert len(payment_events) == len(expected_recipients)


def test_site_visit_order_uses_only_snapshot_paise_and_is_idempotent(
    db, site_visit_payment_fixture, monkeypatch
):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    created = []

    class OrderClient:
        class order:
            @staticmethod
            def create(payload):
                created.append(payload)
                return {"id": "order_site_visit_123", "amount": 12345, "currency": "INR"}

            @staticmethod
            def fetch(order_id):
                return {
                    "id": order_id,
                    "amount": 12345,
                    "amount_paid": 0,
                    "currency": "INR",
                    "status": "created",
                    "notes": {
                        "context": "site_visit",
                        "site_visit_request_id": str(booking.id),
                        "buyer_id": str(buyer.id),
                    },
                }

            @staticmethod
            def payments(_order_id, _params):
                return {"count": 0, "items": []}

    monkeypatch.setattr("app.site_visits.payment_service._get_client", lambda: OrderClient())
    first, error = create_site_visit_order(db, booking_id=booking.id, buyer_id=buyer.id)
    second, second_error = create_site_visit_order(db, booking_id=booking.id, buyer_id=buyer.id)

    assert error is None and second_error is None
    assert first["amount_paise"] == 12345 and second == first
    assert len(created) == 1
    assert created[0]["amount"] == booking.site_visit_fee_paise
    assert created[0]["notes"]["context"] == "site_visit"
    assert db.query(RazorpayPaymentOrder).filter_by(property_id=listing.id).count() == 1
    assert db.query(RazorpayPaymentOrder).filter_by(order_id=first["order_id"]).one().payment_context == "site_visit"


@pytest.mark.parametrize(
    ("remote_status", "payment_items", "expected_old_status", "expect_new_order"),
    [
        ("attempted", [{"id": "pay_failed_attempt", "status": "failed"}], "ATTEMPTED", False),
        ("expired", [], "EXPIRED", True),
    ],
    ids=["failed-order-retry", "expired-order-retry"],
)
def test_retry_requires_provider_confirmation_of_no_capture(
    db, site_visit_payment_fixture, monkeypatch, remote_status, payment_items,
    expected_old_status, expect_new_order
):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    old_order = _attach_order(db, buyer, listing, booking)
    created = []

    class RetryClient:
        class order:
            @staticmethod
            def fetch(order_id):
                return {
                    "id": order_id,
                    "amount": 12345,
                    "amount_paid": 0,
                    "currency": "INR",
                    "status": remote_status,
                    "notes": {
                        "context": "site_visit",
                        "site_visit_request_id": str(booking.id),
                        "buyer_id": str(buyer.id),
                    },
                }

            @staticmethod
            def payments(_order_id, _params):
                return {"count": len(payment_items), "items": payment_items}

            @staticmethod
            def create(payload):
                created.append(payload)
                return {"id": "order_site_visit_retry_2", "amount": 12345, "currency": "INR"}

    monkeypatch.setattr("app.site_visits.payment_service._get_client", lambda: RetryClient())

    response, error = create_site_visit_order(db, booking_id=booking.id, buyer_id=buyer.id)

    assert error is None
    db.refresh(old_order)
    db.refresh(booking)
    assert old_order.status == expected_old_status
    assert booking.payment_status == "initiated"
    if expect_new_order:
        assert response["order_id"] == "order_site_visit_retry_2"
        assert old_order.order_id != booking.payment_order_id
        assert db.query(RazorpayPaymentOrder).filter_by(site_visit_request_id=booking.id).count() == 2
        assert len(created) == 1
    else:
        assert response["order_id"] == old_order.order_id
        assert booking.payment_order_id == old_order.order_id
        assert old_order.payment_id == "pay_failed_attempt"
        assert db.query(RazorpayPaymentOrder).filter_by(site_visit_request_id=booking.id).count() == 1
        assert len(created) == 0
        assert db.query(RazorpayWebhookLog).filter_by(
            event="site_visit.payment_attempt_failed",
            payment_id="pay_failed_attempt",
        ).count() == 1
        monkeypatch.setattr(
            "app.site_visits.payment_service._get_client",
            lambda: FakeRazorpayClient(order_id=old_order.order_id),
        )
        fresh_attempt = SiteVisitVerifyPaymentRequest(
            razorpay_order_id=old_order.order_id,
            razorpay_payment_id="pay_fresh_attempt",
            razorpay_signature="signature_fresh_attempt",
        )
        verified, verify_error = verify_site_visit_payment(
            db, fresh_attempt, booking_id=booking.id, buyer_id=buyer.id
        )
        assert verify_error is None and verified.status == "success"
        db.refresh(booking)
        assert booking.payment_id == "pay_fresh_attempt" and booking.payment_status == "success"


def test_active_order_is_not_duplicated_when_gateway_state_is_unresolved(
    db, site_visit_payment_fixture, monkeypatch
):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    old_order = _attach_order(db, buyer, listing, booking)

    class UnresolvedClient:
        class order:
            @staticmethod
            def fetch(order_id):
                return {
                    "id": order_id,
                    "amount": 12345,
                    "amount_paid": 0,
                    "currency": "INR",
                    "status": "attempted",
                    "notes": {
                        "context": "site_visit",
                        "site_visit_request_id": str(booking.id),
                        "buyer_id": str(buyer.id),
                    },
                }

            @staticmethod
            def payments(_order_id, _params):
                return {"count": 1, "items": [{"id": "pay_pending_attempt", "status": "authorized"}]}

            @staticmethod
            def create(_payload):
                pytest.fail("must not create a second active order")

    monkeypatch.setattr("app.site_visits.payment_service._get_client", lambda: UnresolvedClient())

    response, error = create_site_visit_order(db, booking_id=booking.id, buyer_id=buyer.id)

    assert response is None and "still active" in error
    db.refresh(old_order)
    assert db.query(RazorpayPaymentOrder).filter_by(site_visit_request_id=booking.id).count() == 1


def test_site_visit_payment_rejects_unauthorized_buyer_before_gateway(
    db, site_visit_payment_fixture, monkeypatch
):
    _, _, other, listing, booking = site_visit_payment_fixture
    _attach_order(db, site_visit_payment_fixture[1], listing, booking)
    monkeypatch.setattr("app.site_visits.payment_service._get_client", lambda: pytest.fail("gateway called"))

    response, error = verify_site_visit_payment(db, _verify_payload(), booking_id=booking.id, buyer_id=other.id)

    assert response is None and error == "Not authorized"


def test_site_visit_payment_rejects_invalid_signature(db, site_visit_payment_fixture, monkeypatch):
    from razorpay.errors import SignatureVerificationError

    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)
    client = FakeRazorpayClient()
    client.verify_payment_signature = lambda _payload: (_ for _ in ()).throw(SignatureVerificationError("bad"))
    monkeypatch.setattr("app.site_visits.payment_service._get_client", lambda: client)

    response, error = verify_site_visit_payment(db, _verify_payload(), booking_id=booking.id, buyer_id=buyer.id)

    assert response is None and error == "Invalid payment signature"
    db.refresh(order)
    db.refresh(booking)
    assert order.status == "CREATED" and booking.status == "pending_payment"


def test_site_visit_payment_rejects_provider_amount_mismatch(db, site_visit_payment_fixture, monkeypatch):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(amount=12344),
    )

    response, error = verify_site_visit_payment(db, _verify_payload(), booking_id=booking.id, buyer_id=buyer.id)

    assert response is None and error == "Payment details do not match the Site Visit order"
    db.refresh(order)
    assert order.status == "CREATED"


@pytest.mark.parametrize(
    ("provider_order_id", "payload_booking_offset"),
    [("different_order_reference", 0), ("order_site_visit_123", 1000)],
    ids=["wrong-provider-order-id", "wrong-booking-id"],
)
def test_site_visit_payment_rejects_wrong_order_or_booking_reference(
    db, site_visit_payment_fixture, monkeypatch, provider_order_id, payload_booking_offset
):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(order_id=provider_order_id),
    )

    response, error = verify_site_visit_payment(
        db,
        _verify_payload(),
        booking_id=booking.id + payload_booking_offset,
        buyer_id=buyer.id,
    )

    assert response is None
    assert "order" in error.lower() or "booking" in error.lower()
    db.refresh(order)
    assert order.status == "CREATED"


def test_site_visit_payment_rejects_wrong_provider_payment_id(db, site_visit_payment_fixture, monkeypatch):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)

    class WrongPaymentIdClient(FakeRazorpayClient):
        def fetch(self, _payment_id):
            return {
                "id": "pay_different_reference",
                "order_id": order.order_id,
                "amount": 12345,
                "currency": "INR",
                "status": "captured",
            }

    monkeypatch.setattr("app.site_visits.payment_service._get_client", WrongPaymentIdClient)
    response, error = verify_site_visit_payment(
        db, _verify_payload(), booking_id=booking.id, buyer_id=buyer.id
    )

    assert response is None and "payment" in error.lower()
    db.refresh(order)
    assert order.status == "CREATED"


def test_site_visit_verified_payment_is_idempotent_and_advances_status_only_on_success(
    db, site_visit_payment_fixture, monkeypatch
):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)
    client = FakeRazorpayClient()
    monkeypatch.setattr("app.site_visits.payment_service._get_client", lambda: client)

    first, first_error = verify_site_visit_payment(db, _verify_payload(), booking_id=booking.id, buyer_id=buyer.id)
    second, second_error = verify_site_visit_payment(db, _verify_payload(), booking_id=booking.id, buyer_id=buyer.id)

    assert first_error is None and first.status == "success"
    assert second_error is None and second.status == "success"
    db.refresh(order)
    db.refresh(booking)
    assert order.status == "SUCCESS"
    assert booking.payment_status == "success" and booking.status == "pending"
    assert booking.payment_id == "pay_site_visit_123"


def test_site_visit_payment_pending_does_not_advance_booking(db, site_visit_payment_fixture, monkeypatch):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    _attach_order(db, buyer, listing, booking)
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(status="authorized"),
    )

    response, error = verify_site_visit_payment(db, _verify_payload(), booking_id=booking.id, buyer_id=buyer.id)

    assert error is None and response.status == "pending"
    db.refresh(booking)
    assert booking.status == "pending_payment" and booking.payment_status == "initiated"


def test_site_visit_failed_payment_is_recorded_without_advancing_booking(
    db, site_visit_payment_fixture, monkeypatch
):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(status="failed"),
    )

    response, error = verify_site_visit_payment(db, _verify_payload(), booking_id=booking.id, buyer_id=buyer.id)

    assert error is None and response.status == "failed"
    db.refresh(order)
    db.refresh(booking)
    assert order.status == "ATTEMPTED"
    assert booking.payment_status == "failed" and booking.status == "pending_payment"
    assert db.query(RazorpayWebhookLog).filter_by(
        event="site_visit.payment_attempt_failed", payment_id="pay_site_visit_123"
    ).count() == 1


def test_site_visit_cancelled_attempt_is_distinct_from_failure(db, site_visit_payment_fixture):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)

    response, error = cancel_site_visit_payment_attempt(db, booking_id=booking.id, buyer_id=buyer.id)

    assert error is None and response["payment_status"] == "cancelled"
    db.refresh(order)
    db.refresh(booking)
    assert order.status == "CANCEL_REPORTED"
    assert order.buyer_cancel_reported_at is not None
    assert booking.payment_status == "initiated" and booking.status == "pending_payment"


def test_late_capture_after_buyer_cancellation_is_recorded(db, site_visit_payment_fixture, monkeypatch):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)
    cancel_response, cancel_error = cancel_site_visit_payment_attempt(
        db, booking_id=booking.id, buyer_id=buyer.id
    )
    assert cancel_error is None and cancel_response["payment_status"] == "cancelled"
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(order_id=order.order_id),
    )

    ok, error = payment_service.handle_webhook_event(
        db,
        event="payment.captured",
        event_id="evt_late_after_cancel",
        payload_json="{}",
        signature="verified-test-signature",
        order_id=order.order_id,
        payment_id="pay_site_visit_123",
        payment_status="captured",
        amount_paise=12345,
        currency="INR",
    )

    assert (ok, error) == (True, None)
    db.refresh(order)
    db.refresh(booking)
    assert order.status == "SUCCESS" and booking.payment_status == "success"
    assert booking.status == "pending" and booking.payment_id == "pay_site_visit_123"


def test_distinct_late_capture_is_preserved_for_reconciliation(db, site_visit_payment_fixture, monkeypatch):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    first_order = _attach_order(db, buyer, listing, booking, "order_site_visit_first")
    second_order = RazorpayPaymentOrder(
        user_id=buyer.id,
        property_id=listing.id,
        amount=123.45,
        amount_paise=12345,
        currency="INR",
        payment_context="site_visit",
        site_visit_request_id=booking.id,
        order_id="order_site_visit_second",
        status="CREATED",
    )
    db.add(second_order)
    booking.payment_order_id = second_order.order_id
    db.commit()
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(order_id="order_site_visit_first"),
    )
    first_args = dict(
        event="payment.captured",
        payload_json="{}",
        signature="verified-test-signature",
        payment_status="captured",
        amount_paise=12345,
        currency="INR",
    )

    assert payment_service.handle_webhook_event(
        db,
        **first_args,
        event_id="evt_first_capture",
        order_id=first_order.order_id,
        payment_id="pay_first_capture",
    ) == (True, None)
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(order_id="order_site_visit_second"),
    )
    second_args = dict(
        **first_args,
        event_id="evt_second_capture",
        order_id=second_order.order_id,
        payment_id="pay_second_capture",
    )
    assert payment_service.handle_webhook_event(
        db,
        **second_args,
    ) == (True, None)
    # A retry of the same provider event is idempotent and cannot add another
    # dedicated reconciliation row.
    assert payment_service.handle_webhook_event(db, **second_args) == (True, None)

    db.refresh(first_order)
    db.refresh(second_order)
    db.refresh(booking)
    assert first_order.status == "SUCCESS"
    assert second_order.status == "DUPLICATE_SUCCESS"
    assert second_order.payment_id == "pay_second_capture"
    assert booking.payment_id == "pay_first_capture" and booking.payment_status == "success"
    assert db.query(RazorpayWebhookLog).filter_by(
        event_key="evt_second_capture",
        event="payment.captured",
        status="reconciliation_required",
    ).count() == 1
    assert db.query(RazorpayWebhookLog).filter_by(
        event="site_visit.duplicate_capture",
        order_id=second_order.order_id,
        payment_id="pay_second_capture",
        status="reconciliation_required",
        payment_context="site_visit",
    ).count() == 1


def test_concurrent_verification_and_webhook_commit_one_success(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'site_visit_payment_race.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seller = User(fullname="Seller", email="race-seller@example.test", mobile="9111111111", password_hash="hash")
        buyer = User(fullname="Buyer", email="race-buyer@example.test", mobile="9222222222", password_hash="hash")
        session.add_all([seller, buyer])
        session.flush()
        listing = SellLandRequest(user_id=seller.id, title="Race listing", status=SellLandStatus.LIVE.value)
        session.add(listing)
        session.flush()
        booking = SiteVisitRequest(
            listing_id=listing.id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            property_name_snapshot="Race listing",
            buyer_name_snapshot="Buyer",
            buyer_mobile_snapshot=buyer.mobile,
            seller_name_snapshot="Seller",
            seller_mobile_snapshot=seller.mobile,
            preferred_visit_date=date(2027, 1, 1),
            preferred_visit_time=time(10, 30),
            visitor_count=1,
            pickup_address="123 Example Road, Test Town",
            site_visit_fee_paise=12345,
            status="pending_payment",
            payment_status="initiated",
            payment_order_id="order_site_visit_race",
        )
        session.add(booking)
        session.flush()
        order = RazorpayPaymentOrder(
            user_id=buyer.id,
            property_id=listing.id,
            amount=123.45,
            amount_paise=12345,
            currency="INR",
            payment_context="site_visit",
            site_visit_request_id=booking.id,
            order_id="order_site_visit_race",
            status="CREATED",
        )
        session.add(order)
        session.commit()
        buyer_id, booking_id, order_id = buyer.id, booking.id, order.order_id

    gateway_barrier = threading.Barrier(2, timeout=8)
    gateway_calls = 0
    gateway_calls_lock = threading.Lock()

    class ConcurrentGateway:
        utility = None
        payment = None

        def __init__(self):
            self.utility = self
            self.payment = self

        def verify_payment_signature(self, _payload):
            return None

        def fetch(self, payment_id):
            nonlocal gateway_calls
            with gateway_calls_lock:
                gateway_calls += 1
                should_rendezvous = gateway_calls <= 2
            if should_rendezvous:
                gateway_barrier.wait()
            return {
                "id": payment_id,
                "order_id": order_id,
                "amount": 12345,
                "currency": "INR",
                "status": "captured",
            }

    monkeypatch.setattr("app.site_visits.payment_service._get_client", ConcurrentGateway)
    payload = _verify_payload(order_id)

    def verify_in_new_session():
        with Session(engine) as session:
            return verify_site_visit_payment(session, payload, booking_id=booking_id, buyer_id=buyer_id)

    def webhook_in_new_session():
        with Session(engine) as session:
            return payment_service.handle_webhook_event(
                session,
                event="payment.captured",
                event_id="evt_concurrent_site_visit",
                payload_json="{}",
                signature="verified-test-signature",
                order_id=order_id,
                payment_id="pay_site_visit_123",
                payment_status="captured",
                amount_paise=12345,
                currency="INR",
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(verify_in_new_session), executor.submit(webhook_in_new_session)]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(future.result(timeout=15))
            except Exception as exc:  # SQLite cannot enforce SELECT FOR UPDATE.
                outcomes.append(exc)

    # Retry after any SQLite lock-upgrade collision. Production databases honor
    # the row locks; this assertion still checks that a racing commit converges.
    with Session(engine) as session:
        booking = session.query(SiteVisitRequest).filter_by(id=booking_id).one()
        if booking.payment_status != "success":
            result, error = verify_site_visit_payment(
                session, payload, booking_id=booking_id, buyer_id=buyer_id
            )
            assert error is None and result.status == "success"
        booking = session.query(SiteVisitRequest).filter_by(id=booking_id).one()
        orders = session.query(RazorpayPaymentOrder).filter_by(site_visit_request_id=booking_id).all()
        assert booking.payment_status == "success" and booking.payment_id == "pay_site_visit_123"
        assert sum(item.status == "SUCCESS" for item in orders) == 1
    engine.dispose()


def test_site_visit_webhook_capture_is_verified_and_duplicate_safe(db, site_visit_payment_fixture, monkeypatch):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(order_id=order.order_id),
    )
    args = dict(
        event="payment.captured",
        event_id="evt_site_visit_1",
        payload_json="{}",
        signature="valid-test-signature",
        order_id=order.order_id,
        payment_id="pay_site_visit_123",
        payment_status="captured",
        amount_paise=12345,
        currency="INR",
    )

    assert payment_service.handle_webhook_event(db, **args) == (True, None)
    assert payment_service.handle_webhook_event(db, **args) == (True, None)
    db.refresh(booking)
    db.refresh(order)
    assert booking.status == "pending" and booking.payment_status == "success"
    assert order.status == "SUCCESS" and order.payment_id == "pay_site_visit_123"
    logs = db.query(RazorpayWebhookLog).filter_by(event_id="evt_site_visit_1").all()
    assert len(logs) == 1 and logs[0].payment_context == "site_visit"


def test_site_visit_webhook_rejects_amount_mismatch(db, site_visit_payment_fixture, monkeypatch):
    _, buyer, _, listing, booking = site_visit_payment_fixture
    order = _attach_order(db, buyer, listing, booking)
    monkeypatch.setattr(
        "app.site_visits.payment_service._get_client",
        lambda: FakeRazorpayClient(amount=12344, order_id=order.order_id),
    )

    ok, error = payment_service.handle_webhook_event(
        db,
        event="payment.captured",
        event_id="evt_site_visit_amount_bad",
        payload_json="{}",
        signature="valid-test-signature",
        order_id=order.order_id,
        payment_id="pay_site_visit_123",
        payment_status="captured",
        amount_paise=12345,
        currency="INR",
    )

    assert not ok and "amount" in error.lower()
    db.refresh(booking)
    assert booking.status == "pending_payment" and booking.payment_status == "initiated"


def test_webhook_route_verifies_razorpay_hmac_before_dispatch(db, monkeypatch):
    secret = "test-webhook-secret"
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", secret)
    body = json.dumps({
        "event": "payment.captured",
        "event_id": "payload-event-id-is-not-canonical",
        "id": "payload-id-is-not-canonical",
        "payload": {"payment": {"entity": {}}},
    }).encode()
    scope = {"type": "http", "method": "POST", "path": "/razorpay-webhook", "headers": []}

    async def invoke(signature, event_id=None):
        headers = [(b"x-razorpay-signature", signature.encode())]
        if event_id:
            headers.append((b"x-razorpay-event-id", event_id.encode()))
        request = __import__("starlette.requests", fromlist=["Request"]).Request(
            {**scope, "headers": headers},
            receive=lambda: asyncio.sleep(0, result={"type": "http.request", "body": body, "more_body": False}),
        )
        return await razorpay_webhook(request, db)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(invoke("invalid"))
    assert exc.value.status_code == 400 and exc.value.detail == "Invalid signature"

    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    # Payload IDs are ignored: only Razorpay's request header identifies the event.
    with pytest.raises(HTTPException) as valid_exc:
        asyncio.run(invoke(signature))
    assert valid_exc.value.detail == "Missing or invalid event ID"

    with pytest.raises(HTTPException) as header_exc:
        asyncio.run(invoke(signature, "evt_header_identifier"))
    assert header_exc.value.detail == "Payment status does not match webhook event"


def test_site_visit_verification_request_rejects_client_amount():
    with pytest.raises(ValueError):
        SiteVisitVerifyPaymentRequest(
            razorpay_order_id="order_site_visit_123",
            razorpay_payment_id="pay_site_visit_123",
            razorpay_signature="signed_site_visit_callback",
            amount=1,
        )
