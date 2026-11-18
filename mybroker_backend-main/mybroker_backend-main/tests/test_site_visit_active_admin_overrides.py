from datetime import datetime

import pytest

import app.site_visits.service as site_visit_service
from app.site_visits.models import SiteVisitAssignment, SiteVisitRefund, SiteVisitRefundHistory, SiteVisitRequest, SiteVisitWorkflowHistory
from app.users.model import User


@pytest.fixture
def override_notifications(monkeypatch):
    calls = []

    def capture(**kwargs):
        calls.append({
            "user_ids": [user.id for user in kwargs["users"]],
            "notif_type": kwargs["notif_type"],
            "reference_id": kwargs.get("reference_id"),
        })
        return []

    monkeypatch.setattr(site_visit_service, "notify_users", capture)
    return calls


def _start_visit(TestSession, booking_id):
    db = TestSession()
    booking = db.get(SiteVisitRequest, booking_id)
    booking.status = "in_progress"
    booking.started_at = datetime(2026, 11, 17, 10, 30)
    db.commit()
    db.close()
    return datetime(2026, 11, 17, 10, 30)


def _new_officer(TestSession, name="Override Target"):
    db = TestSession()
    officer = User(fullname=name, mobile=f"930{abs(hash(name)) % 10_000_000:07d}", role="FIELD_OFFICER", is_active=True)
    db.add(officer)
    db.commit()
    officer_id = officer.id
    db.close()
    return officer_id


@pytest.mark.parametrize("actor_key", ["admin", "super_admin"])
def test_admin_roles_can_reassign_in_progress_with_audited_reason_and_notifications(
    admin_site_visit_api, override_notifications, actor_key
):
    client, auth, actors, _, booking_id, _, Session = admin_site_visit_api
    started_at = _start_visit(Session, booking_id)
    new_officer_id = _new_officer(Session)
    db = Session()
    old_officer_id = db.get(SiteVisitRequest, booking_id).assigned_field_officer_id
    db.close()
    auth["user"] = actors[actor_key]

    response = client.put(
        f"/site-visits/admin/{booking_id}/assignment",
        json={"field_officer_id": new_officer_id, "note": "Officer unavailable during visit"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    db = Session()
    booking = db.get(SiteVisitRequest, booking_id)
    assignment = db.query(SiteVisitAssignment).filter_by(site_visit_request_id=booking_id).order_by(SiteVisitAssignment.id.desc()).first()
    workflow = db.query(SiteVisitWorkflowHistory).filter_by(site_visit_request_id=booking_id).one()
    assert booking.status == "in_progress" and booking.started_at == started_at
    assert booking.assigned_field_officer_id == new_officer_id
    assert assignment.action == "reassigned" and assignment.previous_field_officer_id == old_officer_id
    assert assignment.field_officer_id == new_officer_id and assignment.actor_id == actors[actor_key].id
    assert assignment.note == "Officer unavailable during visit" and assignment.created_at is not None
    assert workflow.event_type == "in_progress_reassigned"
    assert workflow.reason == assignment.note and workflow.actor_role == actors[actor_key].role
    assert workflow.previous_values == {"status": "in_progress", "field_officer_id": old_officer_id}
    assert workflow.updated_values == {"status": "in_progress", "field_officer_id": new_officer_id}
    db.close()
    assert [c["user_ids"] for c in override_notifications[:2]] == [[new_officer_id], [old_officer_id]]
    assert len(override_notifications[0:2]) == 2
    assert override_notifications[0]["notif_type"] == "SITE_VISIT_ASSIGNED"
    assert override_notifications[1]["notif_type"] == "SITE_VISIT_ASSIGNMENT_REMOVED"
    assert sum(c["notif_type"] == "SITE_VISIT_IN_PROGRESS_ASSIGNMENT_OVERRIDE" for c in override_notifications) == 1
    duplicate = client.put(
        f"/site-visits/admin/{booking_id}/assignment",
        json={"field_officer_id": new_officer_id, "note": "Retry same assignment"},
    )
    assert duplicate.status_code == 409
    assert len(override_notifications) == 3


def test_admin_can_unassign_in_progress_and_preserves_status_started_and_history(
    admin_site_visit_api, override_notifications
):
    client, _, actors, _, booking_id, _, Session = admin_site_visit_api
    started_at = _start_visit(Session, booking_id)
    db = Session()
    old_officer_id = db.get(SiteVisitRequest, booking_id).assigned_field_officer_id
    before_history = db.query(SiteVisitAssignment).filter_by(site_visit_request_id=booking_id).count()
    db.close()

    response = client.request("DELETE", f"/site-visits/admin/{booking_id}/assignment", json={"note": "Officer emergency"})

    assert response.status_code == 200 and response.json()["status"] == "in_progress"
    db = Session()
    booking = db.get(SiteVisitRequest, booking_id)
    assignment = db.query(SiteVisitAssignment).filter_by(site_visit_request_id=booking_id).order_by(SiteVisitAssignment.id.desc()).first()
    workflow = db.query(SiteVisitWorkflowHistory).filter_by(site_visit_request_id=booking_id).one()
    assert booking.status == "in_progress" and booking.started_at == started_at and booking.assigned_field_officer_id is None
    assert db.query(SiteVisitAssignment).filter_by(site_visit_request_id=booking_id).count() == before_history + 1
    assert assignment.action == "unassigned" and assignment.previous_field_officer_id == old_officer_id
    assert assignment.note == "Officer emergency" and assignment.actor_id == actors["admin"].id
    assert workflow.event_type == "in_progress_unassigned" and workflow.reason == "Officer emergency"
    assert workflow.previous_values["field_officer_id"] == old_officer_id
    assert workflow.updated_values["field_officer_id"] is None
    db.close()
    assert sum(old_officer_id in c["user_ids"] and c["notif_type"] == "SITE_VISIT_ASSIGNMENT_REMOVED" for c in override_notifications) == 1
    assert sum(c["notif_type"] == "SITE_VISIT_IN_PROGRESS_ASSIGNMENT_OVERRIDE" for c in override_notifications) == 1
    auth = admin_site_visit_api[1]
    auth["user"] = actors["officer"]
    blocked = client.post(f"/site-visits/field-officer/{booking_id}/completion-code")
    assert blocked.status_code == 403


def test_admin_can_cancel_in_progress_opens_unpaid_refund_case_and_notifies_parties(
    admin_site_visit_api, override_notifications
):
    client, _, actors, _, booking_id, _, Session = admin_site_visit_api
    started_at = _start_visit(Session, booking_id)
    db = Session()
    officer_id = db.get(SiteVisitRequest, booking_id).assigned_field_officer_id
    db.close()

    response = client.post(f"/site-visits/admin/{booking_id}/cancel", json={"reason": "Unsafe access at property"})

    assert response.status_code == 200 and response.json()["booking_status"] == "cancelled"
    db = Session()
    booking = db.get(SiteVisitRequest, booking_id)
    workflow = db.query(SiteVisitWorkflowHistory).filter_by(site_visit_request_id=booking_id).one()
    refund = db.query(SiteVisitRefund).filter_by(site_visit_request_id=booking_id).one()
    refund_history = db.query(SiteVisitRefundHistory).filter_by(refund_id=refund.id).one()
    assert booking.status == "cancelled" and booking.started_at == started_at
    assert booking.cancelled_at is not None and booking.cancelled_by_id == actors["admin"].id
    assert booking.cancellation_actor_role == "ADMIN" and booking.cancellation_reason == "Unsafe access at property"
    assert workflow.event_type == "in_progress_cancelled" and workflow.reason == "Unsafe access at property"
    assert workflow.previous_values["status"] == "in_progress" and workflow.updated_values["status"] == "cancelled"
    assert workflow.previous_values["field_officer_id"] == officer_id
    assert refund.status == "pending_details" and refund.actual_refunded_amount_paise is None
    assert refund_history.action == "opened" and refund_history.actor_id == actors["admin"].id
    db.close()
    assert sum(actors["buyer"].id in c["user_ids"] and c["notif_type"] == "SITE_VISIT_ADMIN_CANCELLED" for c in override_notifications) == 1
    assert sum(officer_id in c["user_ids"] and c["notif_type"] == "SITE_VISIT_ASSIGNMENT_REMOVED" for c in override_notifications) == 1
    assert sum(c["notif_type"] == "SITE_VISIT_IN_PROGRESS_CANCELLED" for c in override_notifications) == 1
    prior_notification_count = len(override_notifications)
    duplicate = client.post(f"/site-visits/admin/{booking_id}/cancel", json={"reason": "Retry cancellation"})
    assert duplicate.status_code == 409
    assert len(override_notifications) == prior_notification_count

    auth = admin_site_visit_api[1]
    auth["user"] = actors["officer"]
    completion = client.post(f"/site-visits/field-officer/{booking_id}/completion-code")
    assert completion.status_code == 409


@pytest.mark.parametrize("operation", ["reassign", "unassign"])
def test_active_assignment_override_requires_reason(admin_site_visit_api, operation):
    client, _, _, _, booking_id, _, Session = admin_site_visit_api
    _start_visit(Session, booking_id)
    if operation == "reassign":
        target = _new_officer(Session, name="Reason Required Target")
        response = client.put(f"/site-visits/admin/{booking_id}/assignment", json={"field_officer_id": target})
    else:
        response = client.request("DELETE", f"/site-visits/admin/{booking_id}/assignment", json={})
    assert response.status_code == 409
    assert "override reason" in response.json()["detail"]


def test_admin_can_assign_replacement_after_active_unassignment(admin_site_visit_api, override_notifications):
    client, _, _, _, booking_id, _, Session = admin_site_visit_api
    started_at = _start_visit(Session, booking_id)
    client.request("DELETE", f"/site-visits/admin/{booking_id}/assignment", json={"note": "Officer unavailable"})
    replacement_id = _new_officer(Session, name="Post-Unassign Replacement")

    response = client.put(
        f"/site-visits/admin/{booking_id}/assignment",
        json={"field_officer_id": replacement_id, "note": "Replacement needed during active visit"},
    )

    assert response.status_code == 200 and response.json()["status"] == "in_progress"
    db = Session()
    booking = db.get(SiteVisitRequest, booking_id)
    history = db.query(SiteVisitWorkflowHistory).filter_by(site_visit_request_id=booking_id).order_by(SiteVisitWorkflowHistory.id).all()
    assert booking.status == "in_progress" and booking.started_at == started_at
    assert booking.assigned_field_officer_id == replacement_id
    assert [event.event_type for event in history] == ["in_progress_unassigned", "in_progress_reassigned"]
    db.close()
    assert sum(c["notif_type"] == "SITE_VISIT_ASSIGNED" and replacement_id in c["user_ids"] for c in override_notifications) == 1


@pytest.mark.parametrize("role_key", ["buyer", "officer"])
def test_buyer_and_field_officer_cannot_use_active_admin_overrides(admin_site_visit_api, role_key):
    client, auth, actors, _, booking_id, _, Session = admin_site_visit_api
    _start_visit(Session, booking_id)
    target = _new_officer(Session, name=f"Unauthorized Target {role_key}")
    auth["user"] = actors[role_key]
    assignment = client.put(f"/site-visits/admin/{booking_id}/assignment", json={"field_officer_id": target, "note": "Unauthorized attempt"})
    unassignment = client.request("DELETE", f"/site-visits/admin/{booking_id}/assignment", json={"note": "Unauthorized attempt"})
    cancellation = client.post(f"/site-visits/admin/{booking_id}/cancel", json={"reason": "Unauthorized attempt"})
    assert [assignment.status_code, unassignment.status_code, cancellation.status_code] == [403, 403, 403]


def test_active_cancellation_requires_reason_and_rejects_stale_completed_state(admin_site_visit_api):
    client, _, _, _, booking_id, _, Session = admin_site_visit_api
    _start_visit(Session, booking_id)
    missing_reason = client.post(f"/site-visits/admin/{booking_id}/cancel", json={})
    assert missing_reason.status_code == 422
    db = Session()
    booking = db.get(SiteVisitRequest, booking_id)
    booking.status = "completed"
    db.commit()
    db.close()
    stale = client.post(f"/site-visits/admin/{booking_id}/cancel", json={"reason": "Cancel stale visit"})
    assert stale.status_code == 409
