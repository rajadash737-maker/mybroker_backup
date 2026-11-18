from datetime import date, time

from app.sell_land.models import SellLandRequest
from app.site_visits.models import SiteVisitRequest
from app.users.model import User


def _add_booking(Session, *, listing_id, status="pending", suffix="extra"):
    db = Session()
    listing = db.get(SellLandRequest, listing_id)
    booking = SiteVisitRequest(
        listing_id=listing.id,
        buyer_id=listing.user_id,
        seller_id=listing.user_id,
        property_name_snapshot=listing.title or suffix,
        listing_code_snapshot=listing.listing_code,
        buyer_name_snapshot=f"Buyer {suffix}",
        buyer_mobile_snapshot="9100000099",
        seller_name_snapshot="Seller",
        seller_mobile_snapshot="9100000007",
        preferred_visit_date=date(2026, 12, 10),
        preferred_visit_time=time(10, 30),
        visitor_count=2,
        pickup_address="Test address, Listing City",
        site_visit_fee_paise=10000,
        payment_status="success",
        status=status,
    )
    db.add(booking)
    db.commit()
    booking_id = booking.id
    db.close()
    return booking_id


def _other_admin_listing(Session, *, reviewer_id, code="LST-ADMIN-B"):
    db = Session()
    seller = db.query(User).filter_by(role="CUSTOMER").first()
    listing = SellLandRequest(
        user_id=seller.id,
        listing_code=code,
        title=f"Property {code}",
        status="live",
        reviewed_by_id=reviewer_id,
    )
    db.add(listing)
    db.commit()
    listing_id = listing.id
    db.close()
    return listing_id


def test_admin_site_visit_list_filters_before_pagination_and_summary(admin_site_visit_api):
    client, auth, actors, paid_one_id, paid_two_id, _, Session = admin_site_visit_api
    other_listing_id = _other_admin_listing(Session, reviewer_id=actors["other_admin"].id)
    other_pending_id = _add_booking(Session, listing_id=other_listing_id, status="pending", suffix="B-pending")
    other_assigned_id = _add_booking(Session, listing_id=other_listing_id, status="assigned", suffix="B-assigned")

    own_list = client.get("/site-visits/admin", params={"skip": 0, "limit": 1})
    own_second_page = client.get("/site-visits/admin", params={"skip": 1, "limit": 1})
    own_summary = client.get("/site-visits/admin/summary").json()
    assert own_list.status_code == 200 and own_list.json()["total"] == 2
    assert own_second_page.json()["total"] == 2
    assert {own_list.json()["items"][0]["id"], own_second_page.json()["items"][0]["id"]} == {paid_one_id, paid_two_id}
    assert own_summary["total_paid"] == 2
    assert own_summary["pending"] == 1 and own_summary["assigned"] == 1

    auth["user"] = actors["other_admin"]
    other_first = client.get("/site-visits/admin", params={"skip": 0, "limit": 1})
    other_second = client.get("/site-visits/admin", params={"skip": 1, "limit": 1})
    other_pending = client.get("/site-visits/admin", params={"status": "pending"})
    other_summary = client.get("/site-visits/admin/summary").json()
    assert other_first.json()["total"] == 2 and other_second.json()["total"] == 2
    assert {other_first.json()["items"][0]["id"], other_second.json()["items"][0]["id"]} == {other_pending_id, other_assigned_id}
    assert [row["id"] for row in other_pending.json()["items"]] == [other_pending_id]
    assert other_summary["total_paid"] == 2
    assert other_summary["pending"] == 1 and other_summary["assigned"] == 1


def test_admin_cannot_open_or_mutate_another_admins_booking(admin_site_visit_api):
    client, auth, actors, booking_id, assigned_booking_id, *_ = admin_site_visit_api
    auth["user"] = actors["other_admin"]
    assert client.get(f"/site-visits/admin/{booking_id}").status_code == 404
    assert client.post(f"/site-visits/admin/{booking_id}/cancel", json={"reason": "Unauthorized"}).status_code == 404
    assert client.post(f"/site-visits/admin/{booking_id}/correction", json={"reason": "Unauthorized"}).status_code == 404
    assert client.put(
        f"/site-visits/admin/{booking_id}/assignment",
        json={"field_officer_id": actors["officer"].id, "note": "Unauthorized"},
    ).status_code == 404
    assert client.request(
        "DELETE", f"/site-visits/admin/{booking_id}/assignment", json={"note": "Unauthorized"}
    ).status_code == 404
    assert client.put(
        f"/site-visits/admin/{assigned_booking_id}/assignment",
        json={"field_officer_id": actors["inactive_officer"].id, "note": "Unauthorized reassignment"},
    ).status_code == 404


def test_super_admin_retains_organization_wide_site_visit_access(admin_site_visit_api):
    client, auth, actors, booking_id, paid_two_id, _, Session = admin_site_visit_api
    other_listing_id = _other_admin_listing(Session, reviewer_id=actors["other_admin"].id)
    other_booking_id = _add_booking(Session, listing_id=other_listing_id, suffix="other-admin")
    auth["user"] = actors["super_admin"]
    listing = client.get("/site-visits/admin", params={"limit": 100}).json()
    summary = client.get("/site-visits/admin/summary").json()
    assert listing["total"] == 3
    assert {row["id"] for row in listing["items"]} == {booking_id, paid_two_id, other_booking_id}
    assert summary["total_paid"] == 3
    assert client.get(f"/site-visits/admin/{booking_id}").status_code == 200


def test_unverified_listing_uses_super_admin_fallback_not_arbitrary_admin(admin_site_visit_api):
    client, auth, actors, _, _, _, Session = admin_site_visit_api
    unverified_listing_id = _other_admin_listing(Session, reviewer_id=None, code="LST-NO-VERIFIER")
    unverified_booking_id = _add_booking(Session, listing_id=unverified_listing_id, suffix="unverified")
    super_verified_listing_id = _other_admin_listing(
        Session, reviewer_id=actors["super_admin"].id, code="LST-SUPER-VERIFIED"
    )
    super_verified_booking_id = _add_booking(Session, listing_id=super_verified_listing_id, suffix="super-verified")

    auth["user"] = actors["admin"]
    assert client.get(f"/site-visits/admin/{unverified_booking_id}").status_code == 404
    assert client.get(f"/site-visits/admin/{super_verified_booking_id}").status_code == 404
    assert client.get("/site-visits/admin").json()["total"] == 2
    auth["user"] = actors["super_admin"]
    assert client.get(f"/site-visits/admin/{unverified_booking_id}").status_code == 200
    assert client.get(f"/site-visits/admin/{super_verified_booking_id}").status_code == 200
    assert client.get("/site-visits/admin").json()["total"] == 4


def test_listing_reassignment_follows_current_reviewed_by_owner(admin_site_visit_api):
    client, auth, actors, booking_id, *_ = admin_site_visit_api
    auth["user"] = actors["other_admin"]
    assert client.get(f"/site-visits/admin/{booking_id}").status_code == 404
    db = admin_site_visit_api[-1]()
    booking = db.get(SiteVisitRequest, booking_id)
    listing = db.get(SellLandRequest, booking.listing_id)
    listing.reviewed_by_id = actors["other_admin"].id
    db.commit()
    db.close()
    assert client.get(f"/site-visits/admin/{booking_id}").status_code == 200
    auth["user"] = actors["admin"]
    assert client.get(f"/site-visits/admin/{booking_id}").status_code == 404


def test_invalid_or_inactive_listing_reviewer_routes_to_super_admin(admin_site_visit_api):
    client, auth, actors, _, _, _, Session = admin_site_visit_api
    db = Session()
    listing = db.query(SellLandRequest).filter_by(listing_code="LST-ADMIN-1").one()
    listing.reviewed_by_id = actors["buyer"].id  # Existing user, but not an Admin verifier.
    db.commit()
    booking_id = db.query(SiteVisitRequest.id).filter_by(listing_id=listing.id).first()[0]
    db.close()

    auth["user"] = actors["admin"]
    assert client.get(f"/site-visits/admin/{booking_id}").status_code == 404
    assert client.get("/site-visits/admin").json()["total"] == 0
    assert client.get("/site-visits/admin/summary").json()["total_paid"] == 0
    auth["user"] = actors["super_admin"]
    assert client.get(f"/site-visits/admin/{booking_id}").status_code == 200
    assert client.get("/site-visits/admin").json()["total"] == 2

    db = Session()
    listing = db.query(SellLandRequest).filter_by(listing_code="LST-ADMIN-1").one()
    listing.reviewed_by_id = actors["other_admin"].id
    db.get(User, actors["other_admin"].id).is_active = False
    db.commit()
    db.close()
    auth["user"] = actors["admin"]
    assert client.get(f"/site-visits/admin/{booking_id}").status_code == 404
    auth["user"] = actors["super_admin"]
    assert client.get(f"/site-visits/admin/{booking_id}").status_code == 200


def test_admin_notifications_follow_valid_listing_owner_and_super_admin_fallback(
    admin_site_visit_api, monkeypatch
):
    from app.site_visits.service import _notify_site_visit_admins
    from app.site_visits.models import SiteVisitRequest
    from app.sell_land.models import SellLandRequest

    _, _, actors, booking_id, _, _, Session = admin_site_visit_api
    calls = []
    monkeypatch.setattr(
        "app.site_visits.service.notify_users",
        lambda **kwargs: calls.append([user.id for user in kwargs["users"]]),
    )
    db = Session()
    booking = db.get(SiteVisitRequest, booking_id)
    _notify_site_visit_admins(db, booking, title="Notice", body="Body", event="TEST")
    assert calls[-1] == [actors["admin"].id, actors["super_admin"].id]

    listing = db.get(SellLandRequest, booking.listing_id)
    listing.reviewed_by_id = actors["buyer"].id
    db.commit()
    _notify_site_visit_admins(db, booking, title="Notice", body="Body", event="TEST")
    assert calls[-1] == [actors["super_admin"].id]

    listing.reviewed_by_id = None
    db.commit()
    _notify_site_visit_admins(db, booking, title="Notice", body="Body", event="TEST")
    assert calls[-1] == [actors["super_admin"].id]

    listing.reviewed_by_id = actors["other_admin"].id
    db.get(User, actors["other_admin"].id).is_active = False
    db.commit()
    _notify_site_visit_admins(db, booking, title="Notice", body="Body", event="TEST")
    assert calls[-1] == [actors["super_admin"].id]
    db.close()
