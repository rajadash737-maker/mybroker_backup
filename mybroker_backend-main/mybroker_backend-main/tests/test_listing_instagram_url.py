from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.sell_land import admin_service, service
from app.sell_land.admin_schemas import AdminInstagramUrlUpdateRequest
from app.sell_land.instagram_urls import normalize_instagram_url
from app.sell_land.models import SellLandRequest
from app.sell_land.schemas import BuyerExploreLandCard
from app.users.roles import UserRole


@pytest.mark.parametrize("url", [
    "https://www.instagram.com/mybroker/",
    "https://www.instagram.com/p/AbC_123/",
    "https://www.instagram.com/reel/AbC-123/",
    "https://instagram.com/reels/AbC123",
])
def test_accepts_profile_post_and_reel_urls(url):
    assert normalize_instagram_url(url) == url


@pytest.mark.parametrize("url", [
    "http://www.instagram.com/name/",
    "https://instagram.com.evil.example/name/",
    "https://www.instagram.com@evil.example/name/",
    "https://user:pass@www.instagram.com/name/",
    "https://www.instagram.com/p/",
    "https://www.instagram.com/name/posts/1/",
    "https://www.instagram.com:444/name/",
    "",
])
def test_rejects_invalid_instagram_urls(url):
    with pytest.raises(ValueError):
        AdminInstagramUrlUpdateRequest(instagram_url=url)


def test_null_removes_url_and_empty_or_missing_field_is_rejected():
    assert AdminInstagramUrlUpdateRequest(instagram_url=None).instagram_url is None
    with pytest.raises(ValueError):
        AdminInstagramUrlUpdateRequest(instagram_url=" ")
    with pytest.raises(ValueError):
        AdminInstagramUrlUpdateRequest()


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.FIELD_OFFICER, UserRole.ACCOUNTING])
def test_instagram_write_role_is_super_admin_only(role):
    dependency = require_roles(UserRole.SUPER_ADMIN)
    with pytest.raises(HTTPException) as error:
        dependency(SimpleNamespace(role=role.value, is_active=True))
    assert error.value.status_code == 403


def test_super_admin_is_allowed_to_write_instagram_url():
    dependency = require_roles(UserRole.SUPER_ADMIN)
    user = SimpleNamespace(role=UserRole.SUPER_ADMIN.value, is_active=True)
    assert dependency(user) is user


def test_update_and_remove_are_listing_specific_and_existing_rows_stay_null():
    engine = create_engine("sqlite://")
    SellLandRequest.__table__.create(engine)
    with Session(engine) as db:
        db.add_all([
            SellLandRequest(user_id=1, status="live", created_at=datetime(2026, 1, 1)),
            SellLandRequest(user_id=2, status="live", created_at=datetime(2026, 1, 1)),
        ])
        db.commit()
        first, second = db.query(SellLandRequest).order_by(SellLandRequest.id).all()
        assert first.instagram_url is None and second.instagram_url is None
        result = admin_service.update_listing_instagram_url(db, first.id, "https://instagram.com/one/")
        assert result.instagram_url == "https://instagram.com/one/"
        db.refresh(second)
        assert second.instagram_url is None
        admin_service.update_listing_instagram_url(db, first.id, None)
        db.refresh(first)
        assert first.instagram_url is None
        assert admin_service.update_listing_instagram_url(db, 9999, None) is None


def test_buyer_explore_card_only_exposes_valid_saved_instagram_url():
    listing = SimpleNamespace(
        id=23, title="Land", instagram_url="https://www.instagram.com/reel/xyz/",
        land_type="residential", status="live", price_type="total_price", expected_price=1,
        area=1, area_unit="sqft", location=None, city=None, state=None, pincode=None,
        boundary_points=None, offer_lock_expires_at=None, created_at=datetime(2026, 1, 1),
    )
    card = service._build_buyer_explore_card(listing, {}, set())
    assert card.instagram_url == listing.instagram_url
    assert BuyerExploreLandCard.model_validate(card).instagram_url == listing.instagram_url
    listing.instagram_url = "https://instagram.com.evil.example/reel/xyz/"
    assert service._build_buyer_explore_card(listing, {}, set()).instagram_url is None
    listing.instagram_url = None
    assert service._build_buyer_explore_card(listing, {}, set()).instagram_url is None


def test_migration_adds_only_nullable_instagram_column():
    column = SellLandRequest.__table__.c.instagram_url
    assert column.nullable is True
    assert column.type.length == 500
