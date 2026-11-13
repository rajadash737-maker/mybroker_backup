from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.sell_land import service
from app.sell_land.constants import AreaUnit, PriceType, SellLandStatus
from app.sell_land.repository import create_sell_land_request, update_sell_land_request
from app.sell_land.schemas import (
    SellLandCreateRequest,
    SellLandDraftUpsertRequest,
    SellLandUpdateRequest,
)


def _create_payload(**overrides):
    values = {
        "title": "Farm parcel",
        "owner_name": "Seller Name",
        "owner_mobile": "1234567890",
        "location": "Market Road",
        "city": "Cuttack",
        "state": "Odisha",
        "pincode": "753001",
        "area": "2.5",
        "area_unit": AreaUnit.HECTARE,
        "price_type": PriceType.TOTAL_PRICE,
        "pricing_version": 2,
        "expected_price": "250000.75",
    }
    values.update(overrides)
    return SellLandCreateRequest(**values)


def test_v2_create_stores_total_unchanged_without_area_calculation(monkeypatch):
    payload = _create_payload()
    captured = {}
    monkeypatch.setattr(service, "get_processing_fees", lambda db: (Decimal("999"), None))
    monkeypatch.setattr(
        service,
        "create_sell_land_request",
        lambda db, user_id, body, **kwargs: captured.setdefault("payload", body),
    )

    result = service.create_request(object(), 5, payload)

    assert result is captured["payload"]
    assert result.expected_price == Decimal("250000.75")
    assert result.expected_price != Decimal("250000.75") * Decimal("2.5")
    assert result.pricing_version == 2
    assert not hasattr(result, "entered_unit_price")


def test_repository_persists_v2_total_and_null_entered_price_without_conversion():
    captured = {}

    class _DB:
        def add(self, entity):
            captured["entity"] = entity

        def commit(self):
            pass

        def refresh(self, entity):
            pass

    create_sell_land_request(_DB(), 5, _create_payload())
    entity = captured["entity"]

    assert entity.expected_price == Decimal("250000.75")
    assert entity.pricing_version == 2
    assert entity.entered_unit_price is None


def test_v2_create_requires_explicit_version_and_total_price():
    values = _create_payload().model_dump()
    values.pop("pricing_version")
    with pytest.raises(ValidationError):
        SellLandCreateRequest(**values)

    with pytest.raises(ValidationError, match="total land price only"):
        _create_payload(price_type=PriceType.PRICE_PER_UNIT)


def test_entered_unit_price_is_not_an_accepted_seller_input():
    with pytest.raises(ValidationError, match="entered_unit_price is not accepted"):
        SellLandDraftUpsertRequest(
            pricing_version=2,
            price_type=PriceType.TOTAL_PRICE,
            expected_price="1000",
            entered_unit_price="50",
        )


def test_new_v2_draft_create_and_update_keep_total_price(monkeypatch):
    entity = SimpleNamespace(payment_status="success", is_draft=True, status="draft")
    captured = []
    monkeypatch.setattr(
        service,
        "upsert_sell_land_draft",
        lambda db, user_id, payload, request_id=None: captured.append(payload) or entity,
    )
    monkeypatch.setattr(service, "_sync_seller_processing_fee", lambda db, item: item)

    draft = SellLandDraftUpsertRequest(
        pricing_version=2,
        price_type=PriceType.TOTAL_PRICE,
        area_unit=AreaUnit.BIGHA,
        expected_price="87654.32",
    )
    created, error = service.upsert_my_draft(object(), 8, draft)

    assert error is None
    assert created is entity
    assert captured[-1].expected_price == Decimal("87654.32")
    assert captured[-1].pricing_version == 2

    existing = SimpleNamespace(id=21, user_id=8, pricing_version=2, is_draft=True, status="draft")
    monkeypatch.setattr(service, "get_sell_land_request_by_id", lambda db, request_id: existing)
    edited = SellLandDraftUpsertRequest(
        pricing_version=2,
        expected_price="90000.50",
        price_type=PriceType.TOTAL_PRICE,
    )
    updated, error = service.upsert_my_draft(object(), 8, edited, request_id=21)

    assert error is None
    assert updated is entity
    assert captured[-1].expected_price == Decimal("90000.50")
    assert captured[-1].pricing_version == 2


def test_v1_legacy_price_is_not_changed_or_upgraded_by_nonpricing_update(monkeypatch):
    legacy = SimpleNamespace(
        id=22,
        user_id=8,
        pricing_version=1,
        price_type=PriceType.PRICE_PER_UNIT.value,
        expected_price=Decimal("125.50"),
        status=SellLandStatus.DRAFT.value,
    )
    payload = SellLandUpdateRequest(title="Updated title")
    prepared, error = service._prepare_seller_pricing_write(payload, existing=legacy)

    assert error is None
    assert prepared is payload
    assert legacy.expected_price == Decimal("125.50")
    assert legacy.pricing_version == 1

    marked_nonpricing, error = service._prepare_seller_pricing_write(
        SellLandUpdateRequest(title="Still legacy", pricing_version=2),
        existing=legacy,
    )
    assert error is None
    assert marked_nonpricing.pricing_version == 1

    class _DB:
        def commit(self):
            pass

        def refresh(self, entity):
            pass

    update_sell_land_request(_DB(), legacy, prepared)
    assert legacy.title == "Updated title"
    assert legacy.expected_price == Decimal("125.50")
    assert legacy.pricing_version == 1


def test_omitted_price_update_preserves_v2_price_and_version(monkeypatch):
    existing = SimpleNamespace(
        id=23,
        user_id=8,
        pricing_version=2,
        expected_price=Decimal("50000.25"),
        price_type=PriceType.TOTAL_PRICE.value,
        status=SellLandStatus.DRAFT.value,
    )
    monkeypatch.setattr(service, "get_my_request", lambda db, user_id, request_id: existing)

    class _DB:
        def commit(self):
            pass

        def refresh(self, entity):
            pass

    monkeypatch.setattr(service, "update_sell_land_request", update_sell_land_request)
    payload = SellLandUpdateRequest(title="Changed title")
    result, error = service.update_my_request(_DB(), 8, 23, payload)

    assert error is None
    assert result.title == "Changed title"
    assert result.expected_price == Decimal("50000.25")
    assert result.pricing_version == 2


def test_final_submission_changes_status_only_and_keeps_price(monkeypatch):
    listing = SimpleNamespace(
        id=31,
        user_id=8,
        status=SellLandStatus.DRAFT.value,
        is_draft=True,
        draft_step=5,
        title="Land",
        owner_name="Seller",
        owner_mobile="1234567890",
        city="Cuttack",
        state="Odisha",
        pincode="753001",
        location="Market Road",
        area=Decimal("2.5"),
        expected_price=Decimal("43210.75"),
        pricing_version=2,
        entered_unit_price=None,
        boundary_points="[]",
        ownership_type="single_owner",
        payment_status="success",
        listing_code="MB-123456",
    )
    monkeypatch.setattr(service, "get_my_request", lambda db, user_id, request_id: listing)
    monkeypatch.setattr(service, "_required_fields_missing", lambda entity: [])
    monkeypatch.setattr(service, "list_media", lambda db, request_id: [SimpleNamespace(media_type="photo")])
    monkeypatch.setattr(service, "_has_required_documents", lambda media, ownership: True)

    class _DB:
        def commit(self):
            pass

        def refresh(self, entity):
            pass

    result, error = service.submit_my_request(_DB(), 8, 31)

    assert error is None
    assert result is listing
    assert listing.status == SellLandStatus.PENDING.value
    assert listing.is_draft is False
    assert listing.expected_price == Decimal("43210.75")
    assert listing.pricing_version == 2
    assert listing.entered_unit_price is None
