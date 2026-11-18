def test_site_visit_audit_is_super_admin_only_and_uses_global_aggregates(admin_site_visit_api):
    client, auth, actors, paid_one, paid_two, unpaid, Session = admin_site_visit_api
    assert client.get("/site-visits/super-admin/audit/summary").status_code == 403
    auth["user"] = actors["super_admin"]
    summary = client.get("/site-visits/super-admin/audit/summary")
    assert summary.status_code == 200
    assert summary.json()["total_bookings"] == 3
    assert summary.json()["paid_bookings"] == 2
    assert summary.json()["unpaid_bookings"] == 1
    assert summary.json()["pending_admin_review"] == 1
    assert summary.json()["assigned"] == 1

    response = client.get("/site-visits/super-admin/audit/bookings", params={"limit": 1})
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 1
    filtered = client.get("/site-visits/super-admin/audit/bookings", params={"booking_id": unpaid})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["payment_status"] == "initiated"
    by_officer = client.get("/site-visits/super-admin/audit/bookings", params={"officer_search": "Eligible Officer"})
    assert by_officer.status_code == 200
    assert by_officer.json()["total"] == 1
    by_admin = client.get("/site-visits/super-admin/audit/bookings", params={"admin_id": actors["admin"].id})
    assert by_admin.status_code == 200
    assert by_admin.json()["total"] == 1


def test_site_visit_audit_detail_contains_safe_chronological_history(admin_site_visit_api):
    client, auth, actors, booking_id, *_ = admin_site_visit_api
    client.post(f"/site-visits/admin/{booking_id}/correction", json={"reason": "Please correct the visit address"})
    auth["user"] = actors["super_admin"]
    response = client.get(f"/site-visits/super-admin/audit/bookings/{booking_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_history"][0]["event_type"] == "correction_requested"
    assert data["assignment_history"] == []
    assert data["notification_history"]
    encoded = str(data).lower()
    assert "completion_code_hash" not in encoded
    assert "completion_code_encrypted" not in encoded
    assert "buyer_upi_id" not in encoded
    assert "signature" not in encoded
    assert "ciphertext" not in encoded


def test_site_visit_audit_validates_date_range(admin_site_visit_api):
    client, auth, actors, *_ = admin_site_visit_api
    auth["user"] = actors["super_admin"]
    response = client.get("/site-visits/super-admin/audit/bookings", params={"date_from": "2026-12-02", "date_to": "2026-12-01"})
    assert response.status_code == 422


def test_site_visit_audit_assignment_history_shapes_are_consistent(admin_site_visit_api):
    client, auth, actors, first_booking, second_booking, _unpaid, Session = admin_site_visit_api
    from app.site_visits.models import SiteVisitAssignment

    with Session() as db:
        db.add(SiteVisitAssignment(
            site_visit_request_id=first_booking, previous_field_officer_id=None,
            field_officer_id=actors["officer"].id, actor_id=None, action="assigned",
            actor_type="system", note="Payment completed",
        ))
        db.add_all([
            SiteVisitAssignment(
                site_visit_request_id=second_booking, previous_field_officer_id=actors["officer"].id,
                field_officer_id=actors["inactive_officer"].id, actor_id=actors["super_admin"].id,
                action="reassigned", actor_type="super_admin", note="Reassigned",
            ),
            SiteVisitAssignment(
                site_visit_request_id=second_booking, previous_field_officer_id=actors["inactive_officer"].id,
                field_officer_id=None, actor_id=None, action="unassigned",
                actor_type="system", note="Cleared by system",
            ),
        ])
        db.commit()

    auth["user"] = actors["super_admin"]
    system = client.get(f"/site-visits/super-admin/audit/bookings/{first_booking}")
    assert system.status_code == 200
    item = system.json()["assignment_history"][0]
    assert item["action"] == "assigned"
    assert item["actor"] is None
    assert item["previous_field_officer"] is None
    assert item["field_officer"] == {"id": actors["officer"].id, "fullname": "Eligible Officer"}

    response = client.get(f"/site-visits/super-admin/audit/bookings/{second_booking}")
    assert response.status_code == 200
    history = response.json()["assignment_history"]
    assert len(history) == 3
    assert [entry["action"] for entry in history] == ["assigned", "reassigned", "unassigned"]
    admin_assignment, reassignment, unassignment = history
    assert admin_assignment["actor"] == {"id": actors["admin"].id, "fullname": "Admin"}
    assert admin_assignment["previous_field_officer"] is None
    assert reassignment["previous_field_officer"] == {"id": actors["officer"].id, "fullname": "Eligible Officer"}
    assert reassignment["field_officer"] == {"id": actors["inactive_officer"].id, "fullname": "Inactive Officer"}
    assert unassignment["actor"] is None
    assert unassignment["previous_field_officer"] == {"id": actors["inactive_officer"].id, "fullname": "Inactive Officer"}
    assert unassignment["field_officer"] is None
    assert all(set(entry) == {"id", "action", "actor_type", "actor", "previous_field_officer",
                              "field_officer", "note", "created_at"} for entry in history)
    encoded = str(response.json()).lower()
    for secret in ("completion_code", "upi_id", "signature", "credential", "password"):
        assert secret not in encoded
