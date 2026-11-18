from app.site_visits.models import SiteVisitRefund, SiteVisitRefundHistory
from app.users.model import User


def test_accounting_refund_ledger_encryption_limits_and_idempotency(admin_site_visit_api, monkeypatch):
    from app.site_visits import refund_crypto

    monkeypatch.setattr(refund_crypto, "_key", lambda: b"r" * 32)
    client, auth, actors, booking_id, second_booking_id, *_ = admin_site_visit_api

    cancelled = client.post(
        f"/site-visits/admin/{booking_id}/cancel",
        json={"reason": "Visit cannot proceed"},
    )
    assert cancelled.status_code == 200
    second_cancelled = client.post(
        f"/site-visits/admin/{second_booking_id}/cancel",
        json={"reason": "Officer unavailable"},
    )
    assert second_cancelled.status_code == 200

    auth["user"] = actors["buyer"]
    supplied = client.post(f"/site-visits/{booking_id}/refund-details", json={"upi_id": "buyer.name@okaxis"})
    assert supplied.status_code == 200
    refund_id = supplied.json()["refund_id"]
    retry = client.post(f"/site-visits/{booking_id}/refund-details", json={"upi_id": "buyer.name@okaxis"})
    assert retry.status_code == 200
    assert retry.json()["refund_id"] == refund_id
    assert retry.json()["status"] == "pending"
    second_supplied = client.post(f"/site-visits/{second_booking_id}/refund-details", json={"upi_id": "buyer.name@okaxis"})
    assert second_supplied.status_code == 200
    second_refund_id = second_supplied.json()["refund_id"]
    buyer_booking = next(row for row in client.get("/site-visits/my-bookings").json() if row["id"] == booking_id)
    assert buyer_booking["refund"]["status"] == "pending"
    assert "buyer_upi_id" not in buyer_booking["refund"]

    _, _, _, _, _, _, Session = admin_site_visit_api
    db = Session()
    refund = db.get(SiteVisitRefund, refund_id)
    assert refund.status == "pending"
    assert refund.buyer_upi_ciphertext != "buyer.name@okaxis"
    assert refund.buyer_upi_ciphertext.startswith("v1:")
    assert db.query(SiteVisitRefundHistory).filter_by(refund_id=refund_id).count() == 2
    db.close()

    auth["user"] = actors["admin"]
    forbidden = client.get("/site-visits/accounting/refunds")
    assert forbidden.status_code == 403
    auth["user"] = actors["accounting"]
    rows = client.get("/site-visits/accounting/refunds")
    assert rows.status_code == 200
    item = next(row for row in rows.json()["items"] if row["refund_id"] == refund_id)
    assert item["buyer_upi_id"] == "buyer.name@okaxis"
    assert item["eligible_amount_paise"] == 12550
    assert item["original_payment_reference"] is None
    assert item["property_name"]
    assert item["created_at"]

    too_much = client.post(
        f"/site-visits/accounting/refunds/{refund_id}/confirm",
        json={"actual_refunded_amount_paise": 12551, "transaction_reference": "UPIREF-123456"},
    )
    assert too_much.status_code == 409

    payload = {"actual_refunded_amount_paise": 12000, "transaction_reference": "UPIREF-123456", "internal_note": "Refund sent manually"}
    confirmed = client.post(f"/site-visits/accounting/refunds/{refund_id}/confirm", json=payload)
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "refunded"
    assert confirmed.json()["idempotent"] is False
    duplicate = client.post(f"/site-visits/accounting/refunds/{refund_id}/confirm", json=payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["idempotent"] is True
    duplicate_reference = client.post(f"/site-visits/accounting/refunds/{second_refund_id}/confirm", json=payload)
    assert duplicate_reference.status_code == 409
    failed = client.post(
        f"/site-visits/accounting/refunds/{second_refund_id}/fail",
        json={"reason": "Beneficiary validation failed"},
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    summary = client.get("/site-visits/accounting/summary")
    assert summary.status_code == 200
    assert summary.json()["refund_amount_paise"] == 12000
    assert summary.json()["refund_failed"] == 1


def test_refund_details_are_owner_only_and_confirmation_needs_buyer_details(admin_site_visit_api, monkeypatch):
    from types import SimpleNamespace
    from app.site_visits import refund_crypto

    monkeypatch.setattr(refund_crypto, "_key", lambda: b"r" * 32)
    client, auth, actors, booking_id, *_rest = admin_site_visit_api
    Session = _rest[-1]
    client.post(f"/site-visits/admin/{booking_id}/cancel", json={"reason": "Visit cannot proceed"})
    db = Session()
    other = User(fullname="Other buyer", mobile="9100000199", role="CUSTOMER", is_active=True)
    db.add(other)
    db.commit()
    other_id = other.id
    db.close()
    auth["user"] = SimpleNamespace(id=other_id, role="CUSTOMER", is_active=True)
    response = client.post(f"/site-visits/{booking_id}/refund-details", json={"upi_id": "buyer.name@okaxis"})
    assert response.status_code == 404

    auth["user"] = actors["accounting"]
    rows = client.get("/site-visits/accounting/refunds")
    assert rows.status_code == 200
    refund_id = rows.json()["items"][0]["refund_id"]
    response = client.post(
        f"/site-visits/accounting/refunds/{refund_id}/confirm",
        json={"actual_refunded_amount_paise": 10000, "transaction_reference": "UPIREF-NEED-DATA"},
    )
    assert response.status_code == 409


def test_unregistered_fcm_does_not_rollback_confirmed_refund(admin_site_visit_api, monkeypatch):
    from app.site_visits import refund_crypto
    from app.notifications import service as notification_service

    monkeypatch.setattr(refund_crypto, "_key", lambda: b"r" * 32)
    monkeypatch.setattr(
        notification_service,
        "send_notification",
        lambda **kwargs: {"success": False, "error": "fcm_send_failed"},
    )
    client, auth, actors, booking_id, *_rest = admin_site_visit_api
    Session = _rest[-1]
    db = Session()
    buyer = db.get(User, actors["buyer"].id)
    buyer.fcm_token = "stale-buyer-token"
    db.commit()
    db.close()

    cancelled = client.post(
        f"/site-visits/admin/{booking_id}/cancel",
        json={"reason": "Visit cannot proceed"},
    )
    assert cancelled.status_code == 200
    auth["user"] = actors["buyer"]
    details = client.post(
        f"/site-visits/{booking_id}/refund-details",
        json={"upi_id": "buyer.name@okaxis"},
    )
    assert details.status_code == 200
    refund_id = details.json()["refund_id"]

    monkeypatch.setattr(
        notification_service,
        "send_notification",
        lambda **kwargs: {"success": False, "error": "unregistered"},
    )
    auth["user"] = actors["accounting"]
    response = client.post(
        f"/site-visits/accounting/refunds/{refund_id}/confirm",
        json={
            "actual_refunded_amount_paise": 12000,
            "transaction_reference": "UPIREF-FCM-FAIL-001",
            "internal_note": "Recorded despite notification failure",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "refunded"
    db = Session()
    persisted = db.get(SiteVisitRefund, refund_id)
    assert persisted.status == "refunded"
    assert db.query(SiteVisitRefundHistory).filter_by(refund_id=refund_id).count() >= 2
    assert db.get(User, actors["buyer"].id).fcm_token is None
    db.close()


def test_refund_details_refuse_missing_encryption_key_without_storing_upi(admin_site_visit_api, monkeypatch):
    from types import SimpleNamespace
    from app.site_visits import refund_crypto
    client, auth, actors, booking_id, *_rest = admin_site_visit_api
    Session = _rest[-1]
    cancelled = client.post(f"/site-visits/admin/{booking_id}/cancel", json={"reason": "Visit cannot proceed"})
    assert cancelled.status_code == 200
    auth["user"] = actors["buyer"]
    monkeypatch.setattr(refund_crypto, "settings", SimpleNamespace(site_visit_refund_encryption_key=""))
    response = client.post(f"/site-visits/{booking_id}/refund-details", json={"upi_id": "buyer.name@okaxis"})
    assert response.status_code == 503
    assert "booking remains cancelled" in response.json()["detail"]
    assert "still required" in response.json()["detail"]
    assert "buyer.name@okaxis" not in response.text
    db = Session()
    refund = db.query(SiteVisitRefund).filter_by(site_visit_request_id=booking_id).one()
    assert refund.buyer_upi_ciphertext is None
    assert refund.status == "pending_details"
    refund_id = refund.id
    db.close()

    monkeypatch.setattr(refund_crypto, "settings", SimpleNamespace(site_visit_refund_encryption_key="ab" * 32))
    retry = client.post(f"/site-visits/{booking_id}/refund-details", json={"upi_id": "buyer.name@okaxis"})
    assert retry.status_code == 200
    assert retry.json()["refund_id"] == refund_id
    db = Session()
    refund = db.query(SiteVisitRefund).filter_by(site_visit_request_id=booking_id).one()
    assert refund.status == "pending"
    assert refund.buyer_upi_ciphertext and not refund.buyer_upi_ciphertext.endswith("buyer.name@okaxis")
    assert db.query(SiteVisitRefundHistory).filter_by(refund_id=refund_id).count() == 2
    db.close()


def test_refund_upi_encryption_round_trips_with_nonproduction_key(monkeypatch):
    from types import SimpleNamespace
    from app.site_visits import refund_crypto

    monkeypatch.setattr(refund_crypto, "settings", SimpleNamespace(site_visit_refund_encryption_key="cd" * 32))
    encrypted = refund_crypto.encrypt_buyer_upi(57, "test.buyer@okaxis")
    assert encrypted.startswith("v1:")
    assert "test.buyer@okaxis" not in encrypted
    assert refund_crypto.decrypt_buyer_upi(57, encrypted) == "test.buyer@okaxis"
