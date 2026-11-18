from datetime import date, time

from app.site_visits.models import SiteVisitRequest, SiteVisitWorkflowHistory


def test_admin_correction_requires_reason_and_preserves_old_values(admin_site_visit_api):
    client, _, actors, booking_id, *_ = admin_site_visit_api
    missing_reason = client.post(f"/site-visits/admin/{booking_id}/correction", json={})
    assert missing_reason.status_code == 422

    response = client.post(
        f"/site-visits/admin/{booking_id}/correction",
        json={"reason": "Please provide the full pickup address"},
    )
    assert response.status_code == 200
    assert response.json()["booking_status"] == "correction_required"
    assert response.json()["actor_id"] == actors["admin"].id

    _, _, _, _, _, _, Session = admin_site_visit_api
    db = Session()
    booking = db.get(SiteVisitRequest, booking_id)
    history = db.query(SiteVisitWorkflowHistory).filter_by(site_visit_request_id=booking_id).one()
    assert booking.status == "correction_required"
    assert booking.correction_reason == "Please provide the full pickup address"
    assert booking.correction_requested_by_id == actors["admin"].id
    assert history.event_type == "correction_requested"
    assert history.actor_role == "ADMIN"
    assert history.previous_values["pickup_address"] == "Test pickup address, Test City"
    db.close()


def test_buyer_resubmission_records_before_after_and_returns_to_review(admin_site_visit_api):
    client, auth, actors, booking_id, *_ = admin_site_visit_api
    client.post(f"/site-visits/admin/{booking_id}/correction", json={"reason": "Update visit date and address"})
    auth["user"] = actors["buyer"]
    response = client.post(
        f"/site-visits/{booking_id}/correction-response",
        json={
            "preferred_visit_date": "2027-01-05",
            "preferred_visit_time": "11:45:00",
            "visitor_count": 3,
            "pickup_address": "Updated pickup address, New City",
            "message": "Please call before arrival",
        },
    )
    assert response.status_code == 200
    assert response.json()["booking_status"] == "pending"
    assert response.json()["preferred_visit_date"] == "2027-01-05"
    assert response.json()["workflow_history"][-1]["event_type"] == "buyer_resubmitted"

    _, _, _, _, _, _, Session = admin_site_visit_api
    db = Session()
    booking = db.get(SiteVisitRequest, booking_id)
    history = db.query(SiteVisitWorkflowHistory).filter_by(site_visit_request_id=booking_id).order_by(SiteVisitWorkflowHistory.id).all()
    assert booking.preferred_visit_date == date(2027, 1, 5)
    assert booking.preferred_visit_time == time(11, 45)
    assert history[-1].actor_id == actors["buyer"].id
    assert history[-1].actor_role == "CUSTOMER"
    assert history[-1].previous_values["visitor_count"] == 2
    assert history[-1].updated_values["visitor_count"] == 3
    db.close()


def test_admin_cancel_records_actor_reason_and_buyer_sees_it(admin_site_visit_api):
    client, auth, actors, booking_id, *_ = admin_site_visit_api
    response = client.post(
        f"/site-visits/admin/{booking_id}/cancel",
        json={"reason": "Listing access is unavailable"},
    )
    assert response.status_code == 200
    assert response.json()["booking_status"] == "cancelled"
    assert response.json()["actor_id"] == actors["admin"].id

    auth["user"] = actors["buyer"]
    buyer_response = client.get("/site-visits/my-bookings")
    booking = next(item for item in buyer_response.json() if item["id"] == booking_id)
    assert booking["cancellation_reason"] == "Listing access is unavailable"
    assert booking["cancelled_by_role"] == "ADMIN"

    _, _, _, _, _, _, Session = admin_site_visit_api
    db = Session()
    entity = db.get(SiteVisitRequest, booking_id)
    history = db.query(SiteVisitWorkflowHistory).filter_by(site_visit_request_id=booking_id).one()
    assert entity.cancelled_by_id == actors["admin"].id
    assert entity.cancellation_actor_role == "ADMIN"
    assert history.event_type == "admin_cancelled"
    assert history.reason == "Listing access is unavailable"
    db.close()


def test_correction_transition_rejects_wrong_actor_and_invalid_states(admin_site_visit_api):
    client, auth, actors, booking_id, _, unpaid_id, Session = admin_site_visit_api
    auth["user"] = actors["buyer"]
    denied = client.post(f"/site-visits/admin/{booking_id}/correction", json={"reason": "Correct details"})
    assert denied.status_code == 403
    auth["user"] = actors["admin"]
    unpaid = client.post(f"/site-visits/admin/{unpaid_id}/cancel", json={"reason": "Cancel unpaid"})
    assert unpaid.status_code == 404

    db = Session()
    entity = db.get(SiteVisitRequest, booking_id)
    entity.status = "in_progress"
    db.commit()
    db.close()
    active_cancel = client.post(f"/site-visits/admin/{booking_id}/cancel", json={"reason": "Visit started"})
    assert active_cancel.status_code == 200
    assert active_cancel.json()["booking_status"] == "cancelled"


def test_buyer_cannot_resubmit_unrequested_correction(admin_site_visit_api):
    client, auth, actors, booking_id, *_ = admin_site_visit_api
    auth["user"] = actors["buyer"]
    response = client.post(
        f"/site-visits/{booking_id}/correction-response",
        json={
            "preferred_visit_date": "2027-01-05",
            "preferred_visit_time": "11:45:00",
            "visitor_count": 2,
            "pickup_address": "Updated pickup address, New City",
            "message": None,
        },
    )
    assert response.status_code == 409
