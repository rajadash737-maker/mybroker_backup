from datetime import datetime
import json
from types import SimpleNamespace

import pytest

from app.site_visits.models import SiteVisitAssignment, SiteVisitRequest
from app.sell_land.models import SellLandRequest
from app.users.model import User


def test_active_officer_sees_only_own_paid_assignment_without_completion_secrets(admin_site_visit_api):
    client, auth, actors, _, assigned_id, _, Session = admin_site_visit_api
    auth["user"] = actors["officer"]
    db = Session()
    booking = db.get(SiteVisitRequest, assigned_id)
    listing = db.get(SellLandRequest, booking.listing_id)
    listing.boundary_points = json.dumps([
        {"lat": 19.1, "lng": 72.8},
        {"lat": 19.2, "lng": 72.8},
        {"lat": 19.1, "lng": 72.9},
    ])
    booking.completion_code_hash = "must-not-leak-hash"
    booking.completion_code_encrypted = "must-not-leak-ciphertext"
    db.commit()
    db.close()

    response = client.get("/site-visits/field-officer/my-visits")

    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [assigned_id]
    assert rows[0]["assignment_note"] == "Initial assignment"
    assert rows[0]["payment_status"] == "success"
    assert rows[0]["land_boundary_points"] == [
        {"lat": 19.1, "lng": 72.8},
        {"lat": 19.2, "lng": 72.8},
        {"lat": 19.1, "lng": 72.9},
    ]
    assert "completion_code_hash" not in rows[0]
    assert "completion_code_encrypted" not in rows[0]
    assert "completion_code" not in rows[0]


def test_officer_with_no_assignments_gets_empty_list(admin_site_visit_api):
    client, auth, actors, *_ = admin_site_visit_api
    auth["user"] = SimpleNamespace(id=987654, role="FIELD_OFFICER", is_active=True)
    response = client.get("/site-visits/field-officer/my-visits")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("actor_key", ["inactive_officer", "buyer", "admin", "accounting"])
def test_inactive_or_unauthorized_role_cannot_list_field_visits(admin_site_visit_api, actor_key):
    client, auth, actors, *_ = admin_site_visit_api
    auth["user"] = actors[actor_key]
    response = client.get("/site-visits/field-officer/my-visits")
    assert response.status_code == 403


def test_officer_a_cannot_see_officer_b_or_unassigned_bookings(admin_site_visit_api):
    client, auth, actors, paid_one_id, paid_two_id, unpaid_id, Session = admin_site_visit_api
    db = Session()
    officer_b = User(fullname="Officer B", mobile="9100000900", role="FIELD_OFFICER", is_active=True)
    db.add(officer_b)
    db.flush()
    booking_a = db.get(SiteVisitRequest, paid_two_id)
    booking_a.completion_code_hash = None
    booking_b = SiteVisitRequest(
        listing_id=booking_a.listing_id,
        buyer_id=booking_a.buyer_id,
        seller_id=booking_a.seller_id,
        property_name_snapshot="Officer B visit",
        buyer_name_snapshot=booking_a.buyer_name_snapshot,
        buyer_mobile_snapshot=booking_a.buyer_mobile_snapshot,
        seller_name_snapshot=booking_a.seller_name_snapshot,
        seller_mobile_snapshot=booking_a.seller_mobile_snapshot,
        preferred_visit_date=booking_a.preferred_visit_date,
        preferred_visit_time=booking_a.preferred_visit_time,
        visitor_count=1,
        pickup_address="Officer B pickup address",
        site_visit_fee_paise=booking_a.site_visit_fee_paise,
        payment_status="success",
        status="assigned",
        assigned_field_officer_id=officer_b.id,
    )
    db.add(booking_b)
    db.flush()
    db.add(SiteVisitAssignment(
        site_visit_request_id=booking_b.id,
        previous_field_officer_id=None,
        field_officer_id=officer_b.id,
        actor_id=actors["admin"].id,
        action="assigned",
        actor_type="admin",
        note="For B",
    ))
    officer_b_booking_id = booking_b.id
    db.commit()
    db.close()

    auth["user"] = actors["officer"]
    response = client.get("/site-visits/field-officer/my-visits")
    assert response.status_code == 200
    visible = {row["id"] for row in response.json()}
    assert visible == {paid_two_id}
    assert paid_one_id not in visible
    assert unpaid_id not in visible
    assert officer_b_booking_id not in visible

