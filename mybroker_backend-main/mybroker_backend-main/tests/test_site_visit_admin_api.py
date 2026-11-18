import pytest


@pytest.mark.parametrize("actor", ["buyer", "officer", "inactive_officer", "accounting"])
def test_admin_site_visit_endpoints_reject_non_admin_roles(admin_site_visit_api, actor):
    client, auth_state, actors, *_ = admin_site_visit_api
    auth_state["user"] = actors[actor]

    assert client.get("/site-visits/admin").status_code == 403
    assert client.get("/site-visits/admin/1").status_code == 403
    assert client.get("/site-visits/admin/field-officers").status_code == 403
    assert client.get("/site-visits/admin/summary").status_code == 403


@pytest.mark.parametrize("actor", ["admin", "super_admin"])
def test_admin_and_super_admin_can_read_site_visit_data(admin_site_visit_api, actor):
    client, auth_state, actors, *_ = admin_site_visit_api
    auth_state["user"] = actors[actor]
    assert client.get("/site-visits/admin").status_code == 200
    assert client.get("/site-visits/admin/summary").status_code == 200


def test_admin_list_is_paid_only_and_supports_status_filter_and_pagination(admin_site_visit_api):
    client, _, _, paid_one_id, paid_two_id, unpaid_id, _ = admin_site_visit_api

    first_page = client.get("/site-visits/admin", params={"skip": 0, "limit": 1})
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 2
    assert len(first_page.json()["items"]) == 1
    assert first_page.json()["items"][0]["payment_status"] == "success"

    second_page = client.get("/site-visits/admin", params={"skip": 1, "limit": 1})
    assert second_page.status_code == 200
    assert len(second_page.json()["items"]) == 1
    assert second_page.json()["items"][0]["id"] != first_page.json()["items"][0]["id"]
    assert unpaid_id not in {item["id"] for item in first_page.json()["items"] + second_page.json()["items"]}

    assigned = client.get("/site-visits/admin", params={"status": "assigned"})
    assert assigned.status_code == 200
    assert [item["id"] for item in assigned.json()["items"]] == [paid_two_id]

    bad_status = client.get("/site-visits/admin", params={"status": "pending_payment"})
    assert bad_status.status_code == 422
    assert paid_one_id != paid_two_id


def test_admin_detail_returns_scoped_snapshots_payment_summary_and_history(admin_site_visit_api):
    client, _, _, _, paid_two_id, unpaid_id, _ = admin_site_visit_api

    response = client.get(f"/site-visits/admin/{paid_two_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["buyer_name"] == "Buyer Snapshot"
    assert body["buyer_mobile"] == "9100000003"
    assert body["property"]["title"] == "Admin Test Property"
    assert body["property"]["verified_by"]["fullname"] == "Eligible Officer"
    assert body["payment_status"] == "success"
    assert body["site_visit_fee_rupees"] == "125.50"
    assert len(body["assignment_history"]) == 1
    assert body["assignment_history"][0]["note"] == "Initial assignment"
    assert "password_hash" not in str(body)
    assert "payment_id" not in body
    assert client.get(f"/site-visits/admin/{unpaid_id}").status_code == 404


def test_field_officer_choices_include_only_active_field_officers(admin_site_visit_api):
    client, _, _, *_ = admin_site_visit_api

    response = client.get("/site-visits/admin/field-officers")
    assert response.status_code == 200
    officers = response.json()
    assert len(officers) == 1
    assert officers[0]["fullname"] == "Eligible Officer"
    assert set(officers[0]) == {"id", "fullname"}


def test_summary_counts_only_successfully_paid_requests(admin_site_visit_api):
    client, _, _, *_ = admin_site_visit_api

    response = client.get("/site-visits/admin/summary")
    assert response.status_code == 200
    assert response.json()["total_paid"] == 2
    assert response.json()["pending"] == 1
    assert response.json()["assigned"] == 1


