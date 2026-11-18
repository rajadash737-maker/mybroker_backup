from datetime import datetime

import pytest

import app.notifications.models  # noqa: F401
import app.site_visits.service as site_visit_service
from app.notifications.models import Notification
from app.site_visits.models import SiteVisitAssignment, SiteVisitRequest
from app.users.model import User


@pytest.fixture
def assignment_notifications(monkeypatch):
    sent = []

    def capture(**kwargs):
        captured = {key: value for key, value in kwargs.items() if key != "users"}
        captured["user_ids"] = [user.id for user in kwargs["users"]]
        sent.append(captured)
        return []

    monkeypatch.setattr(site_visit_service, "notify_users", capture)
    return sent


def _new_active_officer(TestSession, *, name="Second Officer", role="FIELD_OFFICER", active=True):
    db = TestSession()
    officer = User(
        fullname=name,
        mobile=f"920{abs(hash(name)) % 10_000_000:07d}",
        role=role,
        is_active=active,
    )
    db.add(officer)
    db.commit()
    officer_id = officer.id
    db.close()
    return officer_id


def _eligible_officer_id(TestSession):
    db = TestSession()
    officer_id = db.query(User.id).filter_by(fullname="Eligible Officer", role="FIELD_OFFICER", is_active=True).scalar()
    db.close()
    return officer_id


def test_admin_assigns_paid_pending_request_and_records_history(
    admin_site_visit_api, assignment_notifications
):
    client, auth_state, actors, paid_one_id, _, _, TestSession = admin_site_visit_api
    officer_id = _new_active_officer(TestSession)

    response = client.put(
        f"/site-visits/admin/{paid_one_id}/assignment",
        json={"field_officer_id": officer_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "assigned"
    assert body["action"] == "assigned"
    assert body["previous_field_officer_id"] is None
    assert body["field_officer_id"] == officer_id
    assert body["actor_id"] == actors["admin"].id
    assert body["actor_type"] == "admin"
    assert body["note"] is None

    db = TestSession()
    entity = db.get(SiteVisitRequest, paid_one_id)
    history = db.query(SiteVisitAssignment).filter_by(site_visit_request_id=paid_one_id).one()
    assert entity.status == "assigned"
    assert entity.assigned_field_officer_id == officer_id
    assert history.action == "assigned"
    assert history.actor_id == actors["admin"].id
    assert history.actor_type == "admin"
    assert history.previous_field_officer_id is None
    assert history.field_officer_id == officer_id
    assert history.note is None
    assert history.created_at is not None
    db.close()

    assert len(assignment_notifications) == 1
    assert assignment_notifications[0]["user_ids"] == [officer_id]
    assert assignment_notifications[0]["notif_type"] == "SITE_VISIT_ASSIGNED"
    assert assignment_notifications[0]["reference_id"] == str(paid_one_id)


def test_super_admin_can_reassign_and_notifies_new_and_former_officers(
    admin_site_visit_api, assignment_notifications
):
    client, auth_state, actors, _, paid_two_id, _, TestSession = admin_site_visit_api
    new_officer_id = _new_active_officer(TestSession, name="Replacement Officer")
    db = TestSession()
    old_officer_id = db.query(SiteVisitRequest).filter_by(id=paid_two_id).one().assigned_field_officer_id
    db.close()
    auth_state["user"] = actors["super_admin"]

    response = client.put(
        f"/site-visits/admin/{paid_two_id}/assignment",
        json={"field_officer_id": new_officer_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "assigned"
    assert body["action"] == "reassigned"
    assert body["previous_field_officer_id"] == old_officer_id
    assert body["field_officer_id"] == new_officer_id
    assert body["actor_type"] == "super_admin"

    db = TestSession()
    entity = db.get(SiteVisitRequest, paid_two_id)
    rows = db.query(SiteVisitAssignment).filter_by(site_visit_request_id=paid_two_id).order_by(SiteVisitAssignment.id).all()
    assert entity.status == "assigned"
    assert entity.assigned_field_officer_id == new_officer_id
    assert len(rows) == 2
    assert rows[-1].action == "reassigned"
    assert rows[-1].previous_field_officer_id == old_officer_id
    assert rows[-1].field_officer_id == new_officer_id
    assert rows[-1].note is None
    assert rows[-1].actor_type == "super_admin"
    db.close()

    assert [call["user_ids"][0] for call in assignment_notifications] == [new_officer_id, old_officer_id]
    assert assignment_notifications[0]["notif_type"] == "SITE_VISIT_ASSIGNED"
    assert assignment_notifications[1]["notif_type"] == "SITE_VISIT_ASSIGNMENT_REMOVED"


def test_unassign_returns_request_to_pending_and_notifies_former_officer(
    admin_site_visit_api, assignment_notifications
):
    client, _, actors, _, paid_two_id, _, TestSession = admin_site_visit_api
    db = TestSession()
    old_officer_id = db.query(SiteVisitRequest).filter_by(id=paid_two_id).one().assigned_field_officer_id
    old_officer = db.get(User, old_officer_id)
    assert old_officer.role == "FIELD_OFFICER"
    assert old_officer.is_active is True
    db.close()

    response = client.request(
        "DELETE",
        f"/site-visits/admin/{paid_two_id}/assignment",
        json={},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["action"] == "unassigned"
    assert body["previous_field_officer_id"] == old_officer_id
    assert body["field_officer_id"] is None
    assert body["note"] is None

    db = TestSession()
    entity = db.get(SiteVisitRequest, paid_two_id)
    history = db.query(SiteVisitAssignment).filter_by(site_visit_request_id=paid_two_id).order_by(SiteVisitAssignment.id.desc()).first()
    assert entity.status == "pending"
    assert entity.assigned_field_officer_id is None
    assert history.action == "unassigned"
    assert history.previous_field_officer_id == old_officer_id
    assert history.field_officer_id is None
    assert history.note is None
    assert history.actor_id == actors["admin"].id
    assert history.actor_type == "admin"
    assert history.created_at is not None
    db.close()

    assert len(assignment_notifications) == 1
    assert assignment_notifications[0]["user_ids"] == [old_officer_id]
    assert assignment_notifications[0]["notif_type"] == "SITE_VISIT_ASSIGNMENT_REMOVED"


@pytest.mark.parametrize("timestamp_field", ["scheduled_at", "started_at", "completed_at", "cancelled_at"])
def test_unassignment_rejects_assigned_booking_with_lifecycle_timestamp(
    admin_site_visit_api, timestamp_field, assignment_notifications
):
    client, _, _, _, paid_two_id, _, TestSession = admin_site_visit_api
    db = TestSession()
    entity = db.get(SiteVisitRequest, paid_two_id)
    assert entity.payment_status == "success"
    assert entity.assigned_field_officer_id is not None
    entity.status = "assigned"
    setattr(entity, timestamp_field, datetime.utcnow())
    db.commit()
    previous_officer_id = entity.assigned_field_officer_id
    initial_history_count = db.query(SiteVisitAssignment).filter_by(site_visit_request_id=paid_two_id).count()
    db.close()

    response = client.request(
        "DELETE",
        f"/site-visits/admin/{paid_two_id}/assignment",
        json={},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Site Visit request cannot be unassigned in its current state"
    db = TestSession()
    unchanged = db.get(SiteVisitRequest, paid_two_id)
    assert unchanged.status == "assigned"
    assert unchanged.assigned_field_officer_id == previous_officer_id
    assert db.query(SiteVisitAssignment).filter_by(site_visit_request_id=paid_two_id).count() == initial_history_count
    db.close()
    assert assignment_notifications == []


@pytest.mark.parametrize("role,active", [("FIELD_OFFICER", False), ("CUSTOMER", True)])
def test_assign_rejects_inactive_or_non_field_officer(
    admin_site_visit_api, role, active, assignment_notifications
):
    client, _, _, paid_one_id, _, _, TestSession = admin_site_visit_api
    invalid_officer_id = _new_active_officer(
        TestSession,
        name=f"Ineligible {role} {active}",
        role=role,
        active=active,
    )

    response = client.put(
        f"/site-visits/admin/{paid_one_id}/assignment",
        json={"field_officer_id": invalid_officer_id, "note": "Assign after eligibility check"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Field Officer is not eligible for assignment"
    assert assignment_notifications == []


def test_assign_rejects_unknown_officer_and_unpaid_request(admin_site_visit_api, assignment_notifications):
    client, _, _, _, _, unpaid_id, _ = admin_site_visit_api

    unknown = client.put("/site-visits/admin/1/assignment", json={"field_officer_id": 999999, "note": "Unknown officer test"})
    unpaid = client.put(f"/site-visits/admin/{unpaid_id}/assignment", json={"field_officer_id": 1, "note": "Unpaid request test"})

    assert unknown.status_code == 422
    assert unpaid.status_code == 409
    assert "paid" in unpaid.json()["detail"].lower()
    assert assignment_notifications == []


@pytest.mark.parametrize("state", ["scheduled", "in_progress", "completed", "cancelled", "refund_pending"])
def test_assignment_and_unassignment_reject_lifecycle_states(
    admin_site_visit_api, state, assignment_notifications
):
    client, _, _, paid_one_id, _, _, TestSession = admin_site_visit_api
    officer_id = _eligible_officer_id(TestSession)
    db = TestSession()
    entity = db.get(SiteVisitRequest, paid_one_id)
    entity.status = state
    db.commit()
    db.close()

    assign_response = client.put(
        f"/site-visits/admin/{paid_one_id}/assignment",
        json={"field_officer_id": officer_id},
    )
    unassign_response = client.request(
        "DELETE",
        f"/site-visits/admin/{paid_one_id}/assignment",
        json={},
    )

    assert assign_response.status_code == 409
    assert unassign_response.status_code == 409
    assert assignment_notifications == []


@pytest.mark.parametrize("actor", ["buyer", "officer", "inactive_officer", "accounting"])
def test_assignment_mutations_are_admin_only(admin_site_visit_api, actor, assignment_notifications):
    client, auth_state, actors, paid_one_id, *_ = admin_site_visit_api
    auth_state["user"] = actors[actor]

    assign_response = client.put(
        f"/site-visits/admin/{paid_one_id}/assignment",
        json={"field_officer_id": 1},
    )
    unassign_response = client.request(
        "DELETE",
        f"/site-visits/admin/{paid_one_id}/assignment",
        json={},
    )

    assert assign_response.status_code == 403
    assert unassign_response.status_code == 403
    assert assignment_notifications == []


def test_same_officer_reassignment_is_rejected_without_duplicate_history(
    admin_site_visit_api, assignment_notifications
):
    client, _, _, _, paid_two_id, _, TestSession = admin_site_visit_api
    db = TestSession()
    officer_id = db.query(SiteVisitRequest).filter_by(id=paid_two_id).one().assigned_field_officer_id
    original_history_count = db.query(SiteVisitAssignment).filter_by(site_visit_request_id=paid_two_id).count()
    db.close()

    response = client.put(
        f"/site-visits/admin/{paid_two_id}/assignment",
        json={"field_officer_id": officer_id},
    )

    assert response.status_code == 409
    db = TestSession()
    assert db.query(SiteVisitAssignment).filter_by(site_visit_request_id=paid_two_id).count() == original_history_count
    db.close()
    assert assignment_notifications == []


def test_assignment_notification_is_persisted_and_sent(admin_site_visit_api, monkeypatch):
    client, _, _, paid_one_id, _, _, TestSession = admin_site_visit_api
    officer_id = _new_active_officer(TestSession, name="Notification Officer")
    sent = []
    monkeypatch.setattr("app.notifications.service.send_notification", lambda **kwargs: sent.append(kwargs))
    send_via_existing_service = site_visit_service.notify_users

    def assert_committed_then_notify(**kwargs):
        check_db = TestSession()
        assigned = check_db.get(SiteVisitRequest, paid_one_id)
        assert assigned.status == "assigned"
        assert assigned.assigned_field_officer_id == officer_id
        check_db.close()
        return send_via_existing_service(**kwargs)

    monkeypatch.setattr(site_visit_service, "notify_users", assert_committed_then_notify)

    response = client.put(
        f"/site-visits/admin/{paid_one_id}/assignment",
        json={"field_officer_id": officer_id},
    )

    assert response.status_code == 200
    db = TestSession()
    notification = db.query(Notification).filter_by(
        user_id=officer_id,
        reference_id=str(paid_one_id),
        type="SITE_VISIT_ASSIGNED",
    ).one()
    assert notification.title == "Site Visit Assigned"
    assert notification.role_target == "FIELD_OFFICER"
    assert notification.is_read is False
    db.close()
    assert len(sent) == 1
    assert sent[0]["data"]["site_visit_request_id"] == str(paid_one_id)
    assert sent[0]["data"]["assignment_action"] == "assigned"
    assert sent[0]["data"]["deep_link"] == f"field_site_visit_booking/{paid_one_id}"
    assert sent[0]["data"]["listing_id"]
    assert sent[0]["data"]["property_name"] == "Admin Test Property 1"
    assert "Listing #" in sent[0]["body"]
    assert "completion_code" not in sent[0]["data"]
    assert "upi" not in " ".join(sent[0]["data"].keys()).lower()


def test_notification_delivery_failure_does_not_undo_assignment(admin_site_visit_api, monkeypatch):
    client, _, _, paid_one_id, _, _, TestSession = admin_site_visit_api
    officer_id = _new_active_officer(TestSession, name="Delivery Failure Officer")

    def fail_delivery(**_kwargs):
        raise RuntimeError("FCM unavailable")

    monkeypatch.setattr(site_visit_service, "notify_users", fail_delivery)
    response = client.put(
        f"/site-visits/admin/{paid_one_id}/assignment",
        json={"field_officer_id": officer_id},
    )
    assert response.status_code == 200

    db = TestSession()
    assigned = db.get(SiteVisitRequest, paid_one_id)
    history = db.query(SiteVisitAssignment).filter_by(site_visit_request_id=paid_one_id).one()
    assert assigned.status == "assigned"
    assert assigned.assigned_field_officer_id == officer_id
    assert history.action == "assigned"
    assert history.field_officer_id == officer_id
    db.close()
