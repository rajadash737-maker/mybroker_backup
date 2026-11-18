from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.sell_land.models  # noqa: F401
import app.payments.models  # noqa: F401
import app.settings.models  # noqa: F401
import app.site_visits.models  # noqa: F401
import app.users.model  # noqa: F401
from app.core.dependencies import get_current_active_user, get_db
from app.database import Base
from app.sell_land.models import SellLandRequest
from app.settings.models import ProcessingFeeSettings
from app.site_visits.models import (
    SiteVisitAssignment,
    SiteVisitRefund,
    SiteVisitRefundHistory,
    SiteVisitRequest,
    SiteVisitWorkflowHistory,
)
from app.payments.models import RazorpayPaymentOrder
from app.site_visits.router import router as site_visits_router
from app.site_visits.constants import site_visit_today
from app.users.model import User


@pytest.fixture
def buyer_api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestSession()

    seller = User(fullname="Seller Name", mobile="9000000001", role="CUSTOMER", is_active=True)
    buyer = User(fullname="Buyer Name", mobile="9000000002", role="CUSTOMER", is_active=True)
    other_buyer = User(fullname="Other Buyer", mobile="9000000003", role="CUSTOMER", is_active=True)
    admin = User(fullname="Admin Name", mobile="9000000004", role="ADMIN", is_active=True)
    other_admin = User(fullname="Other Admin", mobile="9000000005", role="ADMIN", is_active=True)
    super_admin = User(fullname="Super Admin", mobile="9000000006", role="SUPER_ADMIN", is_active=True)
    db.add_all([seller, buyer, other_buyer, admin, other_admin, super_admin])
    db.flush()

    live_listing = SellLandRequest(
        user_id=seller.id,
        listing_code="LST-1001",
        title="Green Fields",
        owner_name="Seller Name",
        owner_mobile="9000000001",
        status="live",
        is_draft=False,
        reviewed_by_id=admin.id,
    )
    pending_listing = SellLandRequest(
        user_id=seller.id,
        listing_code="LST-1002",
        title="Pending Fields",
        owner_name="Seller Name",
        owner_mobile="9000000001",
        status="pending",
        is_draft=False,
    )
    db.add_all([live_listing, pending_listing])
    db.add(
        ProcessingFeeSettings(
            seller_processing_fee=999.0,
            buyer_processing_fee=1000.0,
            site_visit_fee=Decimal("125.50"),
        )
    )
    db.commit()
    listing_id = live_listing.id
    pending_listing_id = pending_listing.id
    buyer_identity = SimpleNamespace(
        id=buyer.id,
        fullname=buyer.fullname,
        mobile=buyer.mobile,
        username=None,
        role=buyer.role,
        is_active=buyer.is_active,
    )
    other_buyer_identity = SimpleNamespace(
        id=other_buyer.id,
        fullname=other_buyer.fullname,
        mobile=other_buyer.mobile,
        username=None,
        role=other_buyer.role,
        is_active=other_buyer.is_active,
    )
    admin_identity = SimpleNamespace(
        id=admin.id,
        fullname=admin.fullname,
        mobile=admin.mobile,
        username=None,
        role=admin.role,
        is_active=admin.is_active,
    )
    other_admin_identity = SimpleNamespace(id=other_admin.id, fullname=other_admin.fullname, role=other_admin.role, is_active=other_admin.is_active)
    super_admin_identity = SimpleNamespace(id=super_admin.id, fullname=super_admin.fullname, role=super_admin.role, is_active=super_admin.is_active)
    db.close()

    auth_state = {
        "user": buyer_identity,
        "buyer": buyer_identity,
        "other": other_buyer_identity,
        "admin": admin_identity,
        "other_admin": other_admin_identity,
        "super_admin": super_admin_identity,
    }
    app = FastAPI()
    app.include_router(site_visits_router)

    def override_db():
        request_db = TestSession()
        try:
            yield request_db
        finally:
            request_db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = lambda: auth_state["user"]
    client = TestClient(app)
    try:
        yield client, auth_state, TestSession, listing_id, pending_listing_id
    finally:
        client.close()
        engine.dispose()


def booking_payload(listing_id: int, **overrides):
    payload = {
        "listing_id": listing_id,
        "preferred_visit_date": (site_visit_today() + timedelta(days=2)).isoformat(),
        "preferred_visit_time": "10:30:00",
        "visitor_count": 2,
        "pickup_address": "Village, Area, Landmark, City, 751001",
        "message": "Please call on arrival",
        "submission_key": "attempt-1",
    }
    payload.update(overrides)
    return payload


def test_site_visit_fee_returns_rupees_and_paise(buyer_api):
    client, _, _, _, _ = buyer_api

    response = client.get("/site-visits/fee")

    assert response.status_code == 200
    assert response.json()["site_visit_fee_rupees"] == "125.50"
    assert response.json()["site_visit_fee_paise"] == 12550


def test_create_site_visit_snapshots_authenticated_buyer_listing_and_fee(buyer_api):
    client, _, _, listing_id, _ = buyer_api

    response = client.post("/site-visits", json=booking_payload(listing_id))

    assert response.status_code == 201
    body = response.json()
    assert body["listing_id"] == listing_id
    assert body["property_name"] == "Green Fields"
    assert body["buyer_name"] == "Buyer Name"
    assert body["buyer_mobile"] == "9000000002"
    assert body["site_visit_fee_paise"] == 12550
    assert body["booking_status"] == "pending_payment"
    assert body["payment_status"] == "initiated"
    assert "buyer_id" not in body
    assert "payment_amount" not in body


def test_create_rejects_non_live_listing_duplicate_and_client_fee(buyer_api):
    client, _, _, listing_id, pending_listing_id = buyer_api

    not_live = client.post("/site-visits", json=booking_payload(pending_listing_id))
    assert not_live.status_code == 409

    first = client.post("/site-visits", json=booking_payload(listing_id))
    assert first.status_code == 201
    duplicate = client.post("/site-visits", json=booking_payload(listing_id, submission_key="attempt-2"))
    assert duplicate.status_code == 409

    buyer_amount = client.post("/site-visits", json=booking_payload(listing_id + 999, site_visit_fee=1))
    assert buyer_amount.status_code == 422


def test_site_visit_booking_is_scoped_per_buyer_and_idempotent_per_request(buyer_api):
    client, auth_state, TestSession, listing_id, _ = buyer_api
    payload = booking_payload(listing_id, submission_key="buyer-a-request-1")

    buyer_a = client.post("/site-visits", json=payload)
    assert buyer_a.status_code == 201

    # A separate authenticated buyer may book the same listing independently.
    auth_state["user"] = auth_state["other"]
    buyer_b_payload = booking_payload(listing_id, submission_key="buyer-b-request-1")
    buyer_b = client.post("/site-visits", json=buyer_b_payload)
    assert buyer_b.status_code == 201
    assert buyer_b.json()["id"] != buyer_a.json()["id"]

    # Retrying an identical buyer A request returns the same booking ID.
    auth_state["user"] = auth_state["buyer"]
    retry = client.post("/site-visits", json=payload)
    assert retry.status_code == 201
    assert retry.json()["id"] == buyer_a.json()["id"]
    db = TestSession()
    assert db.query(SiteVisitRequest).filter(SiteVisitRequest.listing_id == listing_id).count() == 2
    db.close()

    # A new request key still cannot bypass the same-buyer active booking rule.
    blocked = client.post("/site-visits", json=booking_payload(listing_id, submission_key="buyer-a-request-2"))
    assert blocked.status_code == 409

    # A paid cancellation creates durable refund history. Rebooking must create
    # a new request without altering that old booking or its refund ledger.
    db = TestSession()
    old = db.get(SiteVisitRequest, buyer_a.json()["id"])
    old.status = "pending"
    old.payment_status = "success"
    old.payment_id = "payment-before-cancel"
    db.commit()
    db.close()
    cancelled = client.post(f"/site-visits/{buyer_a.json()['id']}/cancel", json={"reason": "Schedule changed"})
    assert cancelled.status_code == 200
    db = TestSession()
    old = db.get(SiteVisitRequest, buyer_a.json()["id"])
    refund = db.query(SiteVisitRefund).filter_by(site_visit_request_id=old.id).one()
    history_before = db.query(SiteVisitRefundHistory).filter_by(refund_id=refund.id).all()
    old_snapshot = (old.status, old.payment_status, old.payment_id, old.cancellation_reason, old.cancelled_at)
    refund_snapshot = (refund.id, refund.status, refund.eligible_amount_paise, refund.original_payment_reference)
    history_snapshot = [(row.id, row.action, row.new_status) for row in history_before]
    db.close()

    separate = client.post("/site-visits", json=booking_payload(listing_id, submission_key="buyer-a-request-2"))
    assert separate.status_code == 201
    assert separate.json()["id"] != buyer_a.json()["id"]
    assert separate.json()["id"] != buyer_b.json()["id"]
    assert separate.json()["listing_id"] == listing_id

    db = TestSession()
    old = db.get(SiteVisitRequest, buyer_a.json()["id"])
    refund = db.query(SiteVisitRefund).filter_by(site_visit_request_id=old.id).one()
    history_after = db.query(SiteVisitRefundHistory).filter_by(refund_id=refund.id).all()
    assert (old.status, old.payment_status, old.payment_id, old.cancellation_reason, old.cancelled_at) == old_snapshot
    assert (refund.id, refund.status, refund.eligible_amount_paise, refund.original_payment_reference) == refund_snapshot
    assert [(row.id, row.action, row.new_status) for row in history_after] == history_snapshot
    assert db.query(SiteVisitRequest).filter_by(buyer_id=auth_state["buyer"].id, listing_id=listing_id).count() == 2
    assert db.query(SiteVisitRequest).filter_by(listing_id=listing_id).count() == 3
    db.close()


def test_completed_booking_allows_new_booking_and_preserves_old_records(buyer_api):
    client, auth_state, TestSession, listing_id, _ = buyer_api
    old_response = client.post(
        "/site-visits",
        json=booking_payload(listing_id, submission_key="completed-visit-original"),
    )
    assert old_response.status_code == 201
    old_id = old_response.json()["id"]

    db = TestSession()
    officer = User(fullname="Completion Officer", mobile="9000000099", role="FIELD_OFFICER", is_active=True)
    db.add(officer)
    db.flush()
    old = db.get(SiteVisitRequest, old_id)
    completed_at = datetime.utcnow()
    code_used_at = completed_at - timedelta(minutes=1)
    code_expires_at = code_used_at + timedelta(minutes=10)
    old.status = "completed"
    old.payment_status = "success"
    old.payment_order_id = "old-site-visit-order"
    old.payment_id = "old-site-visit-payment"
    old.paid_at = completed_at - timedelta(hours=1)
    old.assigned_field_officer_id = officer.id
    old.started_at = completed_at - timedelta(minutes=30)
    old.completed_at = completed_at
    # Successful verification clears the reusable hash/ciphertext while retaining
    # the one-time-use and expiry audit fields on this completed booking.
    old.completion_code_hash = None
    old.completion_code_encrypted = None
    old.completion_code_expires_at = code_expires_at
    old.completion_code_used_at = code_used_at
    old.completion_code_failed_attempts = 1
    assignment = SiteVisitAssignment(
        site_visit_request_id=old_id,
        previous_field_officer_id=None,
        field_officer_id=officer.id,
        actor_id=auth_state["admin"].id,
        action="assigned",
        actor_type="admin",
        note="Original visit assignment",
    )
    workflow = SiteVisitWorkflowHistory(
        site_visit_request_id=old_id,
        event_type="field_officer_completed",
        actor_id=officer.id,
        actor_role="FIELD_OFFICER",
        reason="Buyer completion code verified",
        previous_values={"status": "in_progress"},
        updated_values={"status": "completed"},
        created_at=completed_at,
    )
    payment_order = RazorpayPaymentOrder(
        user_id=auth_state["buyer"].id,
        property_id=listing_id,
        amount=125.50,
        amount_paise=12550,
        payment_context="site_visit",
        site_visit_request_id=old_id,
        order_id="old-site-visit-order",
        payment_id="old-site-visit-payment",
        status="PAID",
        paid_at=old.paid_at,
    )
    db.add_all([assignment, workflow, payment_order])
    db.commit()
    old_snapshot = (
        old.id,
        old.status,
        old.payment_status,
        old.payment_order_id,
        old.payment_id,
        old.paid_at,
        old.assigned_field_officer_id,
        old.started_at,
        old.completed_at,
        old.completion_code_hash,
        old.completion_code_encrypted,
        old.completion_code_expires_at,
        old.completion_code_used_at,
        old.completion_code_failed_attempts,
    )
    assignment_id = assignment.id
    workflow_id = workflow.id
    payment_record_id = payment_order.id
    db.close()

    new_payload = booking_payload(listing_id, submission_key="completed-visit-new-request")
    new_response = client.post("/site-visits", json=new_payload)
    assert new_response.status_code == 201
    new_id = new_response.json()["id"]
    assert new_id != old_id
    assert new_response.json()["booking_status"] == "pending_payment"
    assert new_response.json()["payment_status"] == "initiated"

    # A retry of the new submission key returns the same new booking ID.
    retry = client.post("/site-visits", json=new_payload)
    assert retry.status_code == 201
    assert retry.json()["id"] == new_id

    db = TestSession()
    old = db.get(SiteVisitRequest, old_id)
    assert (
        old.id,
        old.status,
        old.payment_status,
        old.payment_order_id,
        old.payment_id,
        old.paid_at,
        old.assigned_field_officer_id,
        old.started_at,
        old.completed_at,
        old.completion_code_hash,
        old.completion_code_encrypted,
        old.completion_code_expires_at,
        old.completion_code_used_at,
        old.completion_code_failed_attempts,
    ) == old_snapshot
    assert db.query(SiteVisitAssignment).filter_by(id=assignment_id, site_visit_request_id=old_id).count() == 1
    assert db.query(SiteVisitWorkflowHistory).filter_by(id=workflow_id, site_visit_request_id=old_id).count() == 1
    assert db.query(RazorpayPaymentOrder).filter_by(id=payment_record_id, site_visit_request_id=old_id).count() == 1
    assert db.query(SiteVisitRequest).filter_by(buyer_id=auth_state["buyer"].id, listing_id=listing_id).count() == 2
    db.close()


@pytest.mark.parametrize(
    "active_status",
    ["pending_payment", "pending", "correction_required", "assigned", "scheduled", "in_progress"],
)
def test_each_active_status_blocks_a_new_booking_for_same_listing(buyer_api, active_status):
    client, _, TestSession, listing_id, _ = buyer_api
    first = client.post(
        "/site-visits",
        json=booking_payload(listing_id, submission_key=f"active-{active_status}-first"),
    )
    assert first.status_code == 201
    db = TestSession()
    existing = db.get(SiteVisitRequest, first.json()["id"])
    existing.status = active_status
    db.commit()
    db.close()

    duplicate = client.post(
        "/site-visits",
        json=booking_payload(listing_id, submission_key=f"active-{active_status}-second"),
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "An active Site Visit request already exists for this listing"


def test_site_visit_submission_key_cannot_be_reused_for_different_payload(buyer_api):
    client, _, _, listing_id, _ = buyer_api
    payload = booking_payload(listing_id, submission_key="stable-request-key")
    created = client.post("/site-visits", json=payload)
    assert created.status_code == 201
    changed = client.post("/site-visits", json=booking_payload(
        listing_id, submission_key="stable-request-key", visitor_count=3
    ))
    assert changed.status_code == 409


def test_site_visit_missing_buyer_mobile_is_the_registered_mobile_422(buyer_api):
    client, auth_state, _, listing_id, _ = buyer_api
    auth_state["user"] = SimpleNamespace(
        id=auth_state["other"].id, fullname="Other Buyer", mobile="", username=None,
        role="CUSTOMER", is_active=True,
    )
    response = client.post("/site-visits", json=booking_payload(listing_id))
    assert response.status_code == 422
    assert response.json()["detail"] == "A registered mobile number is required to request a Site Visit"


def test_buyer_can_only_list_and_cancel_own_requests(buyer_api):
    client, auth_state, TestSession, listing_id, _ = buyer_api
    created = client.post("/site-visits", json=booking_payload(listing_id))
    booking_id = created.json()["id"]

    auth_state["user"] = auth_state["other"]
    assert client.get("/site-visits/my-bookings").json() == []
    foreign_cancel = client.post(f"/site-visits/{booking_id}/cancel", json={"reason": "Changed plans"})
    assert foreign_cancel.status_code == 404

    auth_state["user"] = auth_state["buyer"]
    cancelled = client.post(f"/site-visits/{booking_id}/cancel", json={"reason": "Changed plans"})
    assert cancelled.status_code == 200
    assert cancelled.json()["booking_status"] == "cancelled"
    assert cancelled.json()["cancellation_reason"] == "Changed plans"

    db = TestSession()
    stored = db.get(SiteVisitRequest, booking_id)
    assert stored.cancelled_at is not None
    db.close()


def test_cancel_is_limited_to_pre_start_statuses_and_role_is_customer_only(buyer_api):
    client, auth_state, TestSession, listing_id, _ = buyer_api
    created = client.post("/site-visits", json=booking_payload(listing_id))
    booking_id = created.json()["id"]
    db = TestSession()
    stored = db.get(SiteVisitRequest, booking_id)
    stored.status = "in_progress"
    db.commit()
    db.close()

    denied_cancel = client.post(f"/site-visits/{booking_id}/cancel", json={"reason": "Changed plans"})
    assert denied_cancel.status_code == 409

    auth_state["user"] = auth_state["admin"]
    denied_fee = client.get("/site-visits/fee")
    assert denied_fee.status_code == 403


def test_booking_schema_rejects_past_date_and_unknown_payment_fields(buyer_api):
    client, _, _, listing_id, _ = buyer_api
    past_date = client.post(
        "/site-visits",
        json=booking_payload(listing_id, preferred_visit_date=(site_visit_today() - timedelta(days=1)).isoformat()),
    )
    assert past_date.status_code == 422

    client_payment = client.post("/site-visits", json=booking_payload(listing_id, payment_amount=125.50))
    assert client_payment.status_code == 422


def test_site_visit_booking_notification_targets_listing_admin_and_super_admins_only(buyer_api, monkeypatch):
    client, auth, _, listing_id, _ = buyer_api
    calls = []

    def capture(**kwargs):
        calls.append((kwargs["notif_type"], [user.id for user in kwargs["users"]]))

    monkeypatch.setattr("app.site_visits.service.notify_users", capture)
    response = client.post("/site-visits", json=booking_payload(listing_id, submission_key="admin-visibility-notification"))
    assert response.status_code == 201
    booking_notices = [users for event, users in calls if event == "SITE_VISIT_BOOKING_CREATED" and auth["buyer"].id not in users]
    assert booking_notices == [[auth["admin"].id, auth["super_admin"].id]]
    assert auth["other_admin"].id not in booking_notices[0]


@pytest.mark.parametrize("reviewer", ["missing", "super_admin"])
def test_missing_or_super_admin_listing_reviewer_uses_super_admin_notification_fallback(buyer_api, monkeypatch, reviewer):
    client, auth, TestSession, listing_id, _ = buyer_api
    db = TestSession()
    listing = db.get(SellLandRequest, listing_id)
    listing.reviewed_by_id = None if reviewer == "missing" else auth["super_admin"].id
    db.commit()
    db.close()
    calls = []

    def capture(**kwargs):
        calls.append((kwargs["notif_type"], [user.id for user in kwargs["users"]]))

    monkeypatch.setattr("app.site_visits.service.notify_users", capture)
    response = client.post("/site-visits", json=booking_payload(listing_id, submission_key=f"fallback-{reviewer}"))
    assert response.status_code == 201
    booking_notices = [users for event, users in calls if event == "SITE_VISIT_BOOKING_CREATED" and auth["buyer"].id not in users]
    assert booking_notices == [[auth["super_admin"].id]]
    assert auth["admin"].id not in booking_notices[0]
    assert auth["other_admin"].id not in booking_notices[0]
