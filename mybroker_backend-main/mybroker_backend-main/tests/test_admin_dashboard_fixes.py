from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.sell_land import admin_service, repository
from app.sell_land.admin_schemas import AdminSellLandReviewListResponse
from app.sell_land.constants import SellLandStatus
from app.sell_land.models import SellLandBooking, SellLandRequest


def test_admin_listing_response_accepts_seller_with_null_mobile(monkeypatch):
    listing = SimpleNamespace(
        id=7,
        user_id=10,
        listing_code="LST-7",
        title="Land",
        owner_name="Seller",
        owner_mobile=None,
        land_type="residential",
        ownership_type="single_owner",
        city=None,
        state=None,
        expected_price=None,
        status="pending",
        payment_status="initiated",
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )
    seller = SimpleNamespace(id=10, fullname="Seller", mobile=None, email="seller@example.test")
    monkeypatch.setattr(
        admin_service,
        "list_sell_land_requests_for_admin_review",
        lambda **kwargs: ([listing], 1),
    )
    monkeypatch.setattr(admin_service, "list_users_by_ids", lambda db, ids: [seller])

    response = admin_service.list_requests_for_review(
        db=object(),
        current_user=SimpleNamespace(role="SUPER_ADMIN", id=1),
        status_filter=None,
        search=None,
        state_filter=None,
        city_filter=None,
        skip=0,
        limit=20,
    )

    validated = AdminSellLandReviewListResponse.model_validate(response)
    assert validated.items[0].seller.mobile is None
    assert validated.model_dump(mode="json")["items"][0]["seller"]["mobile"] is None


def test_workflow_summary_counts_only_pending_status(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[SellLandRequest.__table__, SellLandBooking.__table__],
    )
    monkeypatch.setattr(repository, "release_expired_offer_locks", lambda db: 0)

    with Session(engine) as db:
        db.add_all(
            [
                SellLandRequest(user_id=1, status=SellLandStatus.PENDING.value),
                SellLandRequest(user_id=2, status=SellLandStatus.DRAFT.value),
                SellLandRequest(user_id=3, status=SellLandStatus.APPROVED.value),
            ]
        )
        db.commit()

        counts = repository.get_admin_workflow_summary_counts(db)

    assert counts["pending_admin_review"] == 1
