from datetime import datetime
from types import SimpleNamespace

from app.sell_land import service
from app.sell_land.schemas import ExploreSortType


def _listing(request_id: int = 23):
    return SimpleNamespace(
        id=request_id,
        title="Land",
        instagram_url=None,
        land_type="residential",
        status="live",
        price_type="total_price",
        expected_price=100,
        area=1,
        area_unit="acre",
        location="Road",
        city="City",
        state="State",
        pincode="12345",
        boundary_points=None,
        offer_lock_expires_at=None,
        created_at=datetime(2026, 1, 1),
    )


def test_explore_response_includes_actual_aggregate_favorite_count(monkeypatch):
    listing = _listing()
    monkeypatch.setattr(service, "list_live_sell_land_requests", lambda **kwargs: ([listing], 1))
    monkeypatch.setattr(service, "list_media_for_requests", lambda db, ids: [])
    monkeypatch.setattr(service, "list_favorite_request_ids_for_user", lambda db, user_id, ids: {listing.id})
    monkeypatch.setattr(service, "get_favorite_counts_for_request_ids", lambda db, ids: {listing.id: 12})

    response = service.list_explore_lands(
        db=object(), user_id=1, search=None, min_price=None, max_price=None,
        min_area=None, max_area=None, sort_by=ExploreSortType.LATEST, skip=0, limit=20,
    )

    assert response.items[0].is_liked is True
    assert response.items[0].likes_count == 12


def test_like_and_unlike_responses_return_current_aggregate_count(monkeypatch):
    listing = _listing()
    monkeypatch.setattr(service, "get_live_sell_land_request_by_id", lambda db, request_id: listing)
    monkeypatch.setattr(service, "get_favorite_for_user", lambda db, user_id, request_id: None)
    monkeypatch.setattr(service, "create_favorite", lambda db, user_id, request_id: None)
    monkeypatch.setattr(service, "get_favorite_counts_for_request_ids", lambda db, ids: {listing.id: 13})

    liked, error = service.like_explore_land(object(), 1, listing.id)
    assert error is None
    assert liked.liked is True
    assert liked.likes_count == 13

    favorite = object()
    monkeypatch.setattr(service, "get_favorite_for_user", lambda db, user_id, request_id: favorite)
    monkeypatch.setattr(service, "delete_favorite", lambda db, entity: None)
    monkeypatch.setattr(service, "get_favorite_counts_for_request_ids", lambda db, ids: {listing.id: 12})

    unliked, error = service.unlike_explore_land(object(), 1, listing.id)
    assert error is None
    assert unliked.liked is False
    assert unliked.likes_count == 12
