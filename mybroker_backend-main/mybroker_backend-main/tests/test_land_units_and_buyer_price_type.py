from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.sell_land import service
from app.sell_land.constants import AreaUnit, PriceType
from app.sell_land.schemas import SellLandDraftUpsertRequest


@pytest.mark.parametrize(
    ("raw_unit", "expected_unit"),
    [
        ("Decimal", AreaUnit.DECIMAL),
        ("decimal", AreaUnit.DECIMAL),
        ("Hectare", AreaUnit.HECTARE),
        ("hectare", AreaUnit.HECTARE),
        ("Bigha", AreaUnit.BIGHA),
    ],
)
def test_draft_request_accepts_new_area_units_and_legacy_bigha(raw_unit, expected_unit):
    request = SellLandDraftUpsertRequest(area_unit=raw_unit)

    assert request.area_unit is expected_unit


def test_draft_request_rejects_unsupported_area_unit():
    with pytest.raises(ValidationError):
        SellLandDraftUpsertRequest(area_unit="kanal")


def _buyer_listing(**overrides):
    listing = {
        "id": 42,
        "user_id": 7,
        "title": "Farm parcel",
        "owner_category": "general",
        "land_type": "agricultural",
        "status": "live",
        "price_type": PriceType.PRICE_PER_UNIT,
        "expected_price": 125.0,
        "area": 2.5,
        "area_unit": AreaUnit.DECIMAL,
        "location": "Market Road",
        "city": "Cuttack",
        "state": "Odisha",
        "pincode": "753001",
        "boundary_points": None,
        "offer_lock_expires_at": None,
        "created_at": datetime(2026, 1, 2),
    }
    listing.update(overrides)
    return SimpleNamespace(**listing)


def test_buyer_explore_card_returns_stored_price_type():
    card = service._build_buyer_explore_card(_buyer_listing(), {}, set())

    assert card.price_type is PriceType.PRICE_PER_UNIT
    assert card.model_dump(mode="json")["price_type"] == "price_per_unit"


def test_buyer_explore_detail_returns_stored_price_type(monkeypatch):
    listing = _buyer_listing(price_type=PriceType.TOTAL_PRICE)
    monkeypatch.setattr(service, "get_live_sell_land_request_by_id", lambda db, request_id: listing)
    monkeypatch.setattr(service, "list_media", lambda db, request_id: [])

    detail = service.get_explore_land_detail(db=object(), request_id=listing.id)

    assert detail is not None
    assert detail.price_type is PriceType.TOTAL_PRICE
    assert detail.model_dump(mode="json")["price_type"] == "total_price"


