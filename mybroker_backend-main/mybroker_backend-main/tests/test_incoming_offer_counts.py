from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest
from fastapi import HTTPException

from app.database import Base
from app.sell_land.constants import OfferStatus
from app.sell_land.models import SellLandOffer, SellLandRequest
from app.sell_land.repository import get_incoming_offer_counts
from app.users.model import User
from app.sell_land.router import customer_dependency


def _database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, SellLandRequest.__table__, SellLandOffer.__table__],
    )
    return engine


def test_incoming_offer_counts_are_owned_and_status_filtered():
    engine = _database()
    with Session(engine) as db:
        users = [User(fullname=f"User {i}", email=f"user{i}@test", role="CUSTOMER") for i in range(1, 5)]
        db.add_all(users)
        db.flush()
        own_listing = SellLandRequest(user_id=1, status="live")
        other_listing = SellLandRequest(user_id=2, status="live")
        db.add_all([own_listing, other_listing])
        db.flush()
        db.add_all(
            [
                SellLandOffer(request_id=own_listing.id, buyer_id=2, offered_amount=100, status=OfferStatus.PENDING.value),
                SellLandOffer(request_id=own_listing.id, buyer_id=3, offered_amount=100, status=OfferStatus.ACCEPTED.value),
                SellLandOffer(request_id=own_listing.id, buyer_id=4, offered_amount=100, status=OfferStatus.REJECTED.value),
                SellLandOffer(request_id=other_listing.id, buyer_id=1, offered_amount=100, status=OfferStatus.COUNTERED.value),
                SellLandOffer(request_id=other_listing.id, buyer_id=3, offered_amount=100, status=OfferStatus.PENDING.value),
                SellLandOffer(request_id=own_listing.id, buyer_id=1, offered_amount=100, status=OfferStatus.PENDING.value),
            ]
        )
        db.commit()

        counts = get_incoming_offer_counts(db, users[0].id)

    assert counts == {"seller_pending": 1, "buyer_countered": 1, "total": 2}


def test_incoming_offer_counts_return_zero_for_user_without_incoming_offers():
    engine = _database()
    with Session(engine) as db:
        user = User(fullname="Empty", email="empty@test", role="CUSTOMER")
        db.add(user)
        db.commit()

        counts = get_incoming_offer_counts(db, user.id)

    assert counts == {"seller_pending": 0, "buyer_countered": 0, "total": 0}


def test_count_endpoint_role_allows_customer_and_rejects_staff():
    customer = type("Actor", (), {"role": "CUSTOMER", "is_active": True})()
    assert customer_dependency(customer) is customer

    staff = type("Actor", (), {"role": "ADMIN", "is_active": True})()
    with pytest.raises(HTTPException) as error:
        customer_dependency(staff)
    assert error.value.status_code == 403
