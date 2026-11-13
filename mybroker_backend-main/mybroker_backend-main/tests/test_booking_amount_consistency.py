from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.sell_land import service
from app.sell_land.constants import PaymentStatus, SellLandStatus
from app.sell_land.schemas import BuyerBookingCreateRequest


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("100.25", 100),
        ("100.50", 101),
        ("100.75", 101),
        ("100000.75", 100001),
    ],
)
def test_v2_direct_booking_preview_and_creation_use_same_whole_rupee_amount(
    monkeypatch, amount, expected
):
    listing = SimpleNamespace(
        id=41,
        user_id=7,
        status=SellLandStatus.LIVE.value,
        expected_price=Decimal(amount),
        pricing_version=2,
        accepted_offer_id=None,
        offer_lock_expires_at=None,
    )
    monkeypatch.setattr(service, "release_expired_offer_locks", lambda _db: None)
    monkeypatch.setattr(service, "get_live_sell_land_request_by_id", lambda _db, _id: listing)
    monkeypatch.setattr(service, "get_booking_for_listing_buyer", lambda *_args: None)
    monkeypatch.setattr(service, "get_processing_fees", lambda _db: (999.0, 1000.0))

    preview, error = service.get_booking_preview_for_buyer(object(), user_id=9, request_id=41)

    assert error is None
    assert preview.total_amount == expected
    assert preview.deal_amount == expected

    class Query:
        def filter(self, *_args):
            return self

        def with_for_update(self):
            return self

        def first(self):
            return listing

    class DB:
        def query(self, _model):
            return Query()

        def rollback(self):
            pass

    captured = {}

    def create_booking(**kwargs):
        captured["deal_amount"] = kwargs["deal_amount"]
        return SimpleNamespace(id=77, deal_amount=kwargs["deal_amount"], payment_status=PaymentStatus.INITIATED.value)

    monkeypatch.setattr(service, "create_booking", create_booking)
    monkeypatch.setattr(
        service,
        "save_booking_doc_file",
        lambda *, doc_label, **_kwargs: (f"{doc_label}.pdf", f"/private/{doc_label}.pdf"),
    )
    monkeypatch.setattr(service, "update_booking_documents", lambda *, booking, **_kwargs: booking)

    booking, error = service.create_booking_for_buyer(
        DB(),
        user_id=9,
        payload=BuyerBookingCreateRequest(request_id=41, buyer_name="Buyer Name", buyer_mobile="1234567890"),
        aadhaar_doc=object(),
        pan_doc=object(),
        bank_doc=object(),
    )

    assert error is None
    assert captured["deal_amount"] == Decimal(expected)
    assert booking.deal_amount == preview.deal_amount


def test_v1_direct_booking_amount_is_not_rounded_by_v2_helper():
    amount = Decimal("100.75")

    assert service._direct_booking_amount(amount, 1) is amount


def test_v2_accepted_offer_amount_does_not_use_land_area(monkeypatch):
    listing = SimpleNamespace(
        id=51,
        expected_price=Decimal("900000.00"),
        pricing_version=2,
        area=Decimal("5000"),
        area_unit="sqft",
        accepted_offer_id=8,
        offer_lock_expires_at=None,
    )
    offer = SimpleNamespace(
        id=8,
        status="accepted",
        counter_amount=Decimal("250000"),
        offered_amount=Decimal("260000"),
    )
    monkeypatch.setattr(service, "release_expired_offer_locks", lambda _db: None)
    monkeypatch.setattr(service, "get_live_sell_land_request_by_id", lambda _db, _id: listing)
    monkeypatch.setattr(service, "get_offer_by_id", lambda _db, **_kwargs: offer)
    monkeypatch.setattr(
        service,
        "_derive_buyer_booking_state",
        lambda **_kwargs: (None, None, False, None),
    )
    monkeypatch.setattr(service, "get_booking_for_listing_buyer", lambda *_args: None)
    monkeypatch.setattr(service, "get_processing_fees", lambda _db: (999.0, 1000.0))

    preview, error = service.get_booking_preview_for_buyer(object(), user_id=9, request_id=51)

    assert error is None
    assert preview.deal_amount == 250000
