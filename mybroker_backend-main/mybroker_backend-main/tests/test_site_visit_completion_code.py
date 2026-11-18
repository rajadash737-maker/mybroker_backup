from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import app.site_visits.service as site_visit_service
import app.site_visits.completion_code as completion_code
from app.site_visits.models import SiteVisitRequest, SiteVisitWorkflowHistory
from app.users.model import User


@pytest.fixture
def otp_keys(monkeypatch):
    monkeypatch.setattr(
        completion_code,
        "settings",
        SimpleNamespace(site_visit_otp_encryption_key="11" * 32, site_visit_otp_hmac_key="22" * 32),
    )


@pytest.fixture
def completion_setup(admin_site_visit_api, otp_keys):
    client, auth_state, actors, _, booking_id, _, TestSession = admin_site_visit_api
    db = TestSession()
    request = db.get(SiteVisitRequest, booking_id)
    request.payment_status = "success"
    request.status = "assigned"
    officer_id = request.assigned_field_officer_id
    buyer_id = request.buyer_id
    db.commit()
    db.close()
    return client, auth_state, actors, TestSession, booking_id, officer_id, buyer_id


def _as_officer(setup):
    client, auth_state, actors, *_ = setup
    auth_state["user"] = actors["officer"]
    return client


@pytest.mark.parametrize(
    ("encryption_key", "hmac_key"),
    [
        ("", "22" * 32),
        ("11" * 32, ""),
        ("not-hex", "22" * 32),
        ("11" * 32, "not-hex"),
        ("11" * 31, "22" * 32),
        ("11" * 32, "22" * 31),
        ("11" * 32, "11" * 32),
    ],
)
def test_completion_code_helpers_reject_missing_invalid_or_reused_keys(
    monkeypatch, encryption_key, hmac_key
):
    monkeypatch.setattr(
        completion_code,
        "settings",
        SimpleNamespace(
            site_visit_otp_encryption_key=encryption_key,
            site_visit_otp_hmac_key=hmac_key,
        ),
    )

    with pytest.raises(completion_code.CompletionCodeConfigurationError):
        completion_code.hash_completion_code(123, "123456")


@pytest.mark.parametrize(
    ("encryption_key", "hmac_key", "expected_issues"),
    [
        ("", "", ("SITE_VISIT_OTP_ENCRYPTION_KEY", "SITE_VISIT_OTP_HMAC_KEY")),
        ("aa" * 32 + "\n", "bb" * 32, ("SITE_VISIT_OTP_ENCRYPTION_KEY",)),
        ("aa" * 32, "not-hex-secret", ("SITE_VISIT_OTP_HMAC_KEY",)),
        ("aa" * 32, "aa" * 32, ("SITE_VISIT_OTP_ENCRYPTION_KEY", "SITE_VISIT_OTP_HMAC_KEY")),
        ("11" * 32, "22" * 32, ()),
    ],
)
def test_configuration_validation_reports_variable_names_only(
    monkeypatch, encryption_key, hmac_key, expected_issues
):
    monkeypatch.setattr(
        completion_code,
        "settings",
        SimpleNamespace(
            site_visit_otp_encryption_key=encryption_key,
            site_visit_otp_hmac_key=hmac_key,
        ),
    )

    issues = completion_code.completion_code_configuration_issues()

    assert issues == expected_issues
    assert not encryption_key or encryption_key not in repr(issues)
    assert not hmac_key or hmac_key not in repr(issues)


def test_buyer_cannot_retrieve_another_buyers_completion_code_by_known_booking_id(
    completion_setup, monkeypatch
):
    setup = completion_setup
    client = _as_officer(setup)
    monkeypatch.setattr(site_visit_service, "notify_users", lambda **kwargs: [])
    client.post(f"/site-visits/field-officer/{setup[4]}/start")
    client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")

    db = setup[3]()
    buyer_b = User(fullname="Buyer B", mobile="9100000998", role="CUSTOMER", is_active=True)
    db.add(buyer_b)
    db.flush()
    buyer_a_booking = db.get(SiteVisitRequest, setup[4])
    buyer_b_booking = SiteVisitRequest(
        listing_id=buyer_a_booking.listing_id,
        buyer_id=buyer_b.id,
        seller_id=buyer_a_booking.seller_id,
        property_name_snapshot="Buyer B booking",
        buyer_name_snapshot=buyer_b.fullname,
        buyer_mobile_snapshot=buyer_b.mobile,
        seller_name_snapshot=buyer_a_booking.seller_name_snapshot,
        seller_mobile_snapshot=buyer_a_booking.seller_mobile_snapshot,
        preferred_visit_date=buyer_a_booking.preferred_visit_date,
        preferred_visit_time=buyer_a_booking.preferred_visit_time,
        visitor_count=1,
        pickup_address="Buyer B pickup address",
        site_visit_fee_paise=buyer_a_booking.site_visit_fee_paise,
        payment_status="success",
        status="in_progress",
        assigned_field_officer_id=setup[5],
        started_at=datetime.utcnow(),
    )
    db.add(buyer_b_booking)
    db.flush()
    buyer_b_booking.completion_code_hash = completion_code.hash_completion_code(
        buyer_b_booking.id, "123456"
    )
    buyer_b_booking.completion_code_encrypted = completion_code.encrypt_completion_code(
        buyer_b_booking.id, "123456"
    )
    buyer_b_booking.completion_code_expires_at = datetime.utcnow() + timedelta(minutes=10)
    buyer_b_booking_id = buyer_b_booking.id
    db.commit()
    db.close()

    setup[1]["user"] = setup[2]["buyer"]
    known_id_response = client.get(f"/site-visits/my-bookings/{buyer_b_booking_id}")
    assert known_id_response.status_code == 404
    own_bookings = client.get("/site-visits/my-bookings")
    assert own_bookings.status_code == 200
    assert all(item["id"] != buyer_b_booking_id for item in own_bookings.json())

    db = setup[3]()
    stored_booking = db.get(SiteVisitRequest, buyer_b_booking_id)
    assert completion_code.decrypt_completion_code(
        stored_booking.id, stored_booking.completion_code_encrypted
    ) == "123456"
    db.close()


def test_officer_start_is_separate_and_does_not_generate_code(completion_setup, monkeypatch):
    setup = completion_setup
    client = _as_officer(setup)
    monkeypatch.setattr(site_visit_service, "notify_users", lambda **kwargs: [])

    response = client.post(f"/site-visits/field-officer/{setup[4]}/start")

    assert response.status_code == 200
    assert response.json()["booking_status"] == "in_progress"
    assert "completion_code" not in response.json()
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    assert entity.started_at is not None
    assert entity.completion_code_hash is None
    assert entity.completion_code_encrypted is None
    db.close()


def test_initiation_conflict_explains_visit_must_be_started_first(completion_setup):
    setup = completion_setup
    client = _as_officer(setup)

    response = client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")

    assert response.status_code == 409
    assert response.json()["detail"] == "Site Visit must be In Progress before completion can be initiated"
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    assert entity.payment_status == "success"
    assert entity.status == "assigned"
    assert entity.assigned_field_officer_id == setup[5]
    assert entity.started_at is None
    assert entity.completion_code_hash is None
    assert entity.completion_code_encrypted is None
    db.close()


def test_start_then_initiate_completion_succeeds_without_returning_code(completion_setup, monkeypatch):
    setup = completion_setup
    client = _as_officer(setup)
    monkeypatch.setattr(site_visit_service, "notify_users", lambda *args, **kwargs: [])

    start = client.post(f"/site-visits/field-officer/{setup[4]}/start")
    initiated = client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")

    assert start.status_code == 200
    assert initiated.status_code == 200
    assert initiated.json()["booking_status"] == "in_progress"
    assert "completion_code" not in initiated.json()
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    assert entity.payment_status == "success"
    assert entity.assigned_field_officer_id == setup[5]
    assert entity.started_at is not None
    assert entity.completion_code_hash
    assert entity.completion_code_encrypted
    db.close()


def test_missing_completion_key_is_service_unavailable_not_lifecycle_conflict(completion_setup, monkeypatch):
    setup = completion_setup
    client = _as_officer(setup)
    client.post(f"/site-visits/field-officer/{setup[4]}/start")
    monkeypatch.setattr(
        completion_code,
        "settings",
        SimpleNamespace(site_visit_otp_encryption_key="", site_visit_otp_hmac_key=""),
    )

    response = client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")

    assert response.status_code == 503
    assert response.json()["detail"] == "Completion service is temporarily unavailable. Please try again later."
    assert "key" not in response.text.lower()
    assert "completion_code" not in response.text


def test_initiation_requires_started_at_even_when_status_says_in_progress(completion_setup):
    setup = completion_setup
    client = _as_officer(setup)
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    entity.status = "in_progress"
    entity.started_at = None
    db.commit()
    db.close()

    response = client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")

    assert response.status_code == 409
    assert response.json()["detail"] == "Site Visit request cannot initiate completion before it has started"
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    assert entity.completion_code_hash is None
    assert entity.completion_code_encrypted is None
    db.close()


def test_verification_rejects_in_progress_record_without_started_at(completion_setup, monkeypatch):
    setup = completion_setup
    client = _as_officer(setup)
    monkeypatch.setattr(site_visit_service, "notify_users", lambda **kwargs: [])
    client.post(f"/site-visits/field-officer/{setup[4]}/start")
    client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    code = completion_code.decrypt_completion_code(entity.id, entity.completion_code_encrypted)
    entity.started_at = None
    db.commit()
    db.close()

    response = client.post(
        f"/site-visits/field-officer/{setup[4]}/verify-completion",
        json={"completion_code": code},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Site Visit request cannot be completed before it has started"
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    assert entity.status == "in_progress"
    assert entity.completed_at is None
    db.close()


def test_initiation_is_idempotent_and_buyer_status_card_is_only_code_surface(completion_setup, monkeypatch):
    setup = completion_setup
    client = _as_officer(setup)
    client.post(f"/site-visits/field-officer/{setup[4]}/start")
    notifications = []
    monkeypatch.setattr(site_visit_service, "notify_users", lambda **kwargs: notifications.append(kwargs) or [])

    first = client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    original_hash = entity.completion_code_hash
    original_ciphertext = entity.completion_code_encrypted
    expires = entity.completion_code_expires_at
    code = completion_code.decrypt_completion_code(entity.id, original_ciphertext)
    db.close()
    second = client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")

    assert first.status_code == second.status_code == 200
    assert first.json()["completion_code_expires_at"] == second.json()["completion_code_expires_at"]
    assert "completion_code" not in first.json()
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    assert entity.completion_code_hash == original_hash
    assert entity.completion_code_encrypted == original_ciphertext
    assert entity.completion_code_expires_at == expires
    db.close()
    assert len(notifications) == 1
    assert {user.id for user in notifications[0]["users"]} == {
        setup[6], setup[2]["admin"].id, setup[2]["super_admin"].id
    }
    assert notifications[0]["notif_type"] == "SITE_VISIT_COMPLETION_CODE_READY"
    assert all("completion_code" not in call.get("extra_data", {}) for call in notifications)

    setup[1]["user"] = setup[2]["buyer"]
    buyer_cards = client.get("/site-visits/my-bookings")
    assert buyer_cards.status_code == 200
    card = next(item for item in buyer_cards.json() if item["id"] == setup[4])
    assert card["completion_code"] == code

    setup[1]["user"] = SimpleNamespace(id=99999, role="CUSTOMER", is_active=True)
    assert client.get("/site-visits/my-bookings").json() == []


@pytest.mark.parametrize("actor_key", ["admin", "officer"])
def test_only_authenticated_buyer_can_access_code_bearing_booking_response(completion_setup, actor_key):
    setup = completion_setup
    client = _as_officer(setup)
    client.post(f"/site-visits/field-officer/{setup[4]}/start")
    client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")

    setup[1]["user"] = setup[2][actor_key]
    response = client.get("/site-visits/my-bookings")

    assert response.status_code == 403


def test_admin_and_field_officer_responses_never_include_completion_secrets(completion_setup, monkeypatch):
    setup = completion_setup
    client = _as_officer(setup)
    monkeypatch.setattr(site_visit_service, "notify_users", lambda **kwargs: [])
    client.post(f"/site-visits/field-officer/{setup[4]}/start")
    client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")

    officer_response = client.get("/site-visits/field-officer/my-visits")
    setup[1]["user"] = setup[2]["admin"]
    admin_response = client.get(f"/site-visits/admin/{setup[4]}")

    assert officer_response.status_code == admin_response.status_code == 200
    combined = str(officer_response.json()) + str(admin_response.json())
    assert "completion_code" not in combined
    assert "completion_code_hash" not in combined
    assert "completion_code_encrypted" not in combined


def test_in_progress_reassignment_invalidates_old_code_and_old_officer_cannot_verify(
    completion_setup, monkeypatch
):
    setup = completion_setup
    client, auth_state, actors, TestSession, booking_id, old_officer_id, _ = setup
    monkeypatch.setattr(site_visit_service, "notify_users", lambda **kwargs: [])
    auth_state["user"] = actors["officer"]
    client.post(f"/site-visits/field-officer/{booking_id}/start")
    client.post(f"/site-visits/field-officer/{booking_id}/completion-code")
    db = TestSession()
    entity = db.get(SiteVisitRequest, booking_id)
    old_code = completion_code.decrypt_completion_code(entity.id, entity.completion_code_encrypted)
    new_officer = User(fullname="Replacement Officer", mobile="9100000997", role="FIELD_OFFICER", is_active=True)
    db.add(new_officer)
    db.commit()
    new_officer_id = new_officer.id
    db.close()

    auth_state["user"] = actors["admin"]
    reassigned = client.put(
        f"/site-visits/admin/{booking_id}/assignment",
        json={"field_officer_id": new_officer_id, "note": "Replace officer"},
    )
    assert reassigned.status_code == 200

    auth_state["user"] = actors["officer"]
    old_officer_verify = client.post(
        f"/site-visits/field-officer/{booking_id}/verify-completion",
        json={"completion_code": old_code},
    )
    assert old_officer_verify.status_code == 403
    auth_state["user"] = SimpleNamespace(id=new_officer_id, role="FIELD_OFFICER", is_active=True)
    replacement_verify = client.post(
        f"/site-visits/field-officer/{booking_id}/verify-completion",
        json={"completion_code": old_code},
    )
    assert replacement_verify.status_code == 409
    assert replacement_verify.json()["detail"] == "No active Site Visit completion code"
    db = TestSession()
    entity = db.get(SiteVisitRequest, booking_id)
    assert entity.assigned_field_officer_id == new_officer_id
    assert entity.status == "in_progress"
    assert entity.completion_code_hash is None
    assert entity.completion_code_encrypted is None
    db.close()


def test_cancellation_invalidates_active_code_and_blocks_completion(completion_setup, monkeypatch):
    setup = completion_setup
    client, auth_state, actors, TestSession, booking_id, _, _ = setup
    monkeypatch.setattr(site_visit_service, "notify_users", lambda **kwargs: [])
    auth_state["user"] = actors["officer"]
    client.post(f"/site-visits/field-officer/{booking_id}/start")
    client.post(f"/site-visits/field-officer/{booking_id}/completion-code")

    auth_state["user"] = actors["admin"]
    cancelled = client.post(
        f"/site-visits/admin/{booking_id}/cancel", json={"reason": "Visit cancelled by Admin"}
    )
    assert cancelled.status_code == 200
    auth_state["user"] = actors["officer"]
    verify = client.post(
        f"/site-visits/field-officer/{booking_id}/verify-completion",
        json={"completion_code": "123456"},
    )
    assert verify.status_code == 409
    db = TestSession()
    entity = db.get(SiteVisitRequest, booking_id)
    assert entity.status == "cancelled"
    assert entity.completion_code_hash is None
    assert entity.completion_code_encrypted is None
    db.close()


def test_expired_code_requires_reinitiation_and_preserves_attempts(completion_setup, monkeypatch):
    setup = completion_setup
    client = _as_officer(setup)
    monkeypatch.setattr(site_visit_service, "notify_users", lambda **kwargs: [])
    client.post(f"/site-visits/field-officer/{setup[4]}/start")
    client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    entity.completion_code_expires_at = datetime.utcnow() - timedelta(seconds=1)
    entity.completion_code_failed_attempts = 2
    db.commit()
    db.close()

    expired = client.post(
        f"/site-visits/field-officer/{setup[4]}/verify-completion",
        json={"completion_code": "000000"},
    )
    assert expired.status_code == 409
    restarted = client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")
    assert restarted.status_code == 200
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    assert entity.completion_code_failed_attempts == 2
    assert entity.completion_code_expires_at > datetime.utcnow()
    db.close()


def test_five_failed_attempts_lock_code_and_do_not_complete(completion_setup, monkeypatch):
    setup = completion_setup
    client = _as_officer(setup)
    monkeypatch.setattr(site_visit_service, "notify_users", lambda **kwargs: [])
    client.post(f"/site-visits/field-officer/{setup[4]}/start")
    client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")
    for attempt in range(5):
        response = client.post(
            f"/site-visits/field-officer/{setup[4]}/verify-completion",
            json={"completion_code": "000000"},
        )
        assert response.status_code in {409, 429}
    assert client.post(f"/site-visits/field-officer/{setup[4]}/completion-code").status_code == 429
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    assert entity.completion_code_failed_attempts == 5
    assert entity.status == "in_progress"
    assert entity.completion_code_hash is None
    db.close()


def test_valid_code_is_single_use_and_notification_failure_does_not_rollback(completion_setup, monkeypatch):
    setup = completion_setup
    client = _as_officer(setup)
    notification_calls = []
    def fail_notification(**kwargs):
        notification_calls.append(kwargs)
        raise RuntimeError("private error")
    monkeypatch.setattr(site_visit_service, "notify_users", fail_notification)
    client.post(f"/site-visits/field-officer/{setup[4]}/start")
    client.post(f"/site-visits/field-officer/{setup[4]}/completion-code")
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    code = completion_code.decrypt_completion_code(entity.id, entity.completion_code_encrypted)
    db.close()

    verified = client.post(
        f"/site-visits/field-officer/{setup[4]}/verify-completion",
        json={"completion_code": code},
    )
    reused = client.post(
        f"/site-visits/field-officer/{setup[4]}/verify-completion",
        json={"completion_code": code},
    )
    assert verified.status_code == 200
    assert verified.json()["booking_status"] == "completed"
    assert "completion_code" not in verified.json()
    assert reused.status_code == 409
    db = setup[3]()
    entity = db.get(SiteVisitRequest, setup[4])
    assert entity.status == "completed"
    assert entity.completion_code_used_at is not None
    assert entity.completion_code_hash is None
    assert entity.completion_code_encrypted is None
    completion_event = db.query(SiteVisitWorkflowHistory).filter_by(
        site_visit_request_id=setup[4], event_type="field_officer_completed"
    ).one()
    assert completion_event.actor_id == setup[5]
    assert completion_event.actor_role == "FIELD_OFFICER"
    assert completion_event.previous_values["status"] == "in_progress"
    assert completion_event.updated_values["status"] == "completed"
    assert "completion_code" not in str(completion_event.previous_values) + str(completion_event.updated_values)
    db.close()
    assert notification_calls
    assert all("completion_code" not in call.get("extra_data", {}) for call in notification_calls)
    assert all(code not in call.get("body", "") and code not in call.get("title", "") for call in notification_calls)


@pytest.mark.parametrize("actor_key", ["buyer", "admin", "accounting", "inactive_officer"])
def test_non_assigned_active_field_officer_cannot_start_or_verify(completion_setup, actor_key):
    setup = completion_setup
    client, auth_state, actors, _, booking_id, *_ = setup
    auth_state["user"] = actors[actor_key]
    response = client.post(f"/site-visits/field-officer/{booking_id}/start")
    assert response.status_code == 403


def test_different_active_field_officer_cannot_start_or_verify(completion_setup):
    setup = completion_setup
    db = setup[3]()
    other_officer = User(
        fullname="Unassigned Officer",
        mobile="9100000999",
        role="FIELD_OFFICER",
        is_active=True,
    )
    db.add(other_officer)
    db.commit()
    other_id = other_officer.id
    db.close()
    setup[1]["user"] = SimpleNamespace(id=other_id, role="FIELD_OFFICER", is_active=True)
    client = setup[0]

    start = client.post(f"/site-visits/field-officer/{setup[4]}/start")
    verify = client.post(
        f"/site-visits/field-officer/{setup[4]}/verify-completion",
        json={"completion_code": "000000"},
    )
    assert start.status_code == 403
    assert verify.status_code == 403
