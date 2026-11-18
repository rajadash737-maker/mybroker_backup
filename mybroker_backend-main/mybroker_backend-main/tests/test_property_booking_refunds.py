from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.payments.models import RazorpayPaymentOrder
from app.sell_land.admin_schemas import (
    AccountingPropertyBookingRefundConfirmRequest,
    AccountingPropertyBookingRefundFailRequest,
    PropertyBookingCancellationRequest,
)
from app.sell_land.models import (
    PropertyBookingRefund,
    PropertyBookingRefundEvent,
    SellLandBooking,
    SellLandOffer,
    SellLandRequest,
)
from app.sell_land.constants import OfferStatus
from app.sell_land.schemas import BuyerOfferCreateRequest, ExploreSortType
from app.sell_land import admin_service, service as sell_land_service
from app.sell_land.repository import create_or_update_offer_for_buyer
from app.sell_land.property_booking_refunds import (
    cancel_property_booking,
    confirm_property_booking_refund,
    fail_property_booking_refund,
    get_accounting_property_booking_refund,
    get_buyer_booking_refund,
    list_property_booking_refunds,
    submit_buyer_refund_upi,
)
from app.sell_land.schemas import BuyerPropertyBookingRefundUpiRequest
from app.users.model import User


@pytest.fixture
def property_booking_case(admin_site_visit_api, monkeypatch):
    from app.sell_land import property_booking_refunds as service
    from app.sell_land import booking_refund_crypto

    monkeypatch.setattr(service, "notify_users", lambda **kwargs: None)
    monkeypatch.setattr(booking_refund_crypto, "_key", lambda: b"p" * 32)
    *_, Session = admin_site_visit_api
    db = Session()
    listing = db.query(SellLandRequest).filter_by(listing_code="LST-ADMIN-1").one()
    buyer = db.query(User).filter_by(role="CUSTOMER", fullname="Buyer").one()
    admin = db.query(User).filter_by(role="ADMIN").first()
    super_admin = db.query(User).filter_by(role="SUPER_ADMIN").one()
    accounting = db.query(User).filter_by(role="ACCOUNTING").one()
    listing.status = "booked"
    booking = SellLandBooking(
        request_id=listing.id, buyer_id=buyer.id, buyer_name=buyer.fullname,
        buyer_mobile=buyer.mobile, deal_amount=500000, booking_fee_amount=999,
        payment_transaction_id="pay_verified_1", payment_status="success",
        booking_status="booked", paid_at=datetime(2026, 11, 1),
    )
    db.add(booking)
    db.flush()
    payment = RazorpayPaymentOrder(
        user_id=buyer.id, property_id=listing.id, amount=999.0, amount_paise=99900,
        currency="INR", payment_context="buyer", site_visit_request_id=None,
        order_id="order_property_1", payment_id="pay_verified_1", status="SUCCESS",
        paid_at=datetime(2026, 11, 1),
    )
    db.add(payment)
    db.commit()
    ids = (booking.id, listing.id, buyer.id)
    actors = {
        key: SimpleNamespace(id=user.id, role=user.role, is_active=user.is_active)
        for key, user in (("buyer", buyer), ("admin", admin), ("super_admin", super_admin), ("accounting", accounting),
                          ("officer", db.query(User).filter_by(role="FIELD_OFFICER", fullname="Eligible Officer").one()))
    }
    db.close()
    yield Session, ids, actors


def test_cancel_uses_verified_captured_amount_and_restores_listing(property_booking_case):
    Session, (booking_id, listing_id, _), actors = property_booking_case
    db = Session()
    result = cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="REFUND", cancellation_reason="Booking review requires cancellation"
        ),
    )
    assert result.original_captured_amount == Decimal("999.00")
    assert result.approved_refund_amount == Decimal("999.00")
    assert result.refund_status == "AWAITING_BUYER_DETAILS"
    assert db.get(SellLandRequest, listing_id).status == "live"
    queue = list_property_booking_refunds(db, skip=0, limit=20)
    assert any(item.refund_id == result.refund_id for item in queue.items)
    assert db.query(PropertyBookingRefundEvent).filter_by(refund_id=result.refund_id).count() >= 3
    db.close()


def test_cancelled_listing_is_visible_in_buyer_explore(property_booking_case):
    Session, (booking_id, listing_id, buyer_id), actors = property_booking_case
    db = Session()
    cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="NO_REFUND", cancellation_reason="Cancellation without refund"
        ),
    )

    response = sell_land_service.list_explore_lands(
        db=db, user_id=buyer_id, search=None, min_price=None, max_price=None,
        min_area=None, max_area=None, sort_by=ExploreSortType.LATEST, skip=0, limit=20,
    )
    assert response.total == 1
    assert [item.id for item in response.items] == [listing_id]
    db.close()


def test_cancelled_booking_remains_available_to_super_admin_with_refund_audit(property_booking_case):
    Session, (booking_id, listing_id, _), actors = property_booking_case
    db = Session()
    cancelled = cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="NO_REFUND", cancellation_reason="Cancellation without refund"
        ),
    )

    detail, error = admin_service.get_booked_listing_detail(
        db, current_user=actors["super_admin"], request_id=listing_id
    )
    assert error is None
    assert detail.booking_id == booking_id
    assert detail.booking_status == "cancelled"
    assert detail.cancellation_reason == "Cancellation without refund"
    assert detail.refund_decision == "NO_REFUND"
    assert detail.refund_status == "NOT_REQUIRED"
    assert detail.approved_refund_amount == Decimal("0.00")
    assert detail.cancelled_at is not None
    assert cancelled.listing_status == "live"
    db.close()


def test_cancelled_accepted_offer_is_expired_but_history_and_new_offer_are_preserved(property_booking_case, monkeypatch):
    monkeypatch.setattr(sell_land_service, "notify_users", lambda **kwargs: None)
    Session, (booking_id, listing_id, buyer_id), actors = property_booking_case
    db = Session()
    listing = db.get(SellLandRequest, listing_id)
    old_offer = SellLandOffer(
        request_id=listing_id,
        buyer_id=buyer_id,
        offered_amount=500000,
        status=OfferStatus.ACCEPTED.value,
        seller_response_at=datetime(2026, 11, 1),
    )
    db.add(old_offer)
    db.flush()
    listing.accepted_offer_id = old_offer.id
    listing.offer_locked_by_buyer_id = buyer_id
    db.commit()
    old_offer_id = old_offer.id

    cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="NO_REFUND", cancellation_reason="Cancellation without refund"
        ),
    )
    db.refresh(old_offer)
    assert old_offer.status == OfferStatus.EXPIRED.value
    assert Decimal(old_offer.offered_amount) == Decimal("500000")
    assert db.get(SellLandRequest, listing_id).accepted_offer_id is None

    # Existing cancelled rows can predate the status transition; the seller API
    # still projects that offer as terminal from the cancelled booking ledger.
    old_offer.status = OfferStatus.ACCEPTED.value
    db.commit()

    seller_offers, error = sell_land_service.list_my_listing_offers(
        db, user_id=db.get(SellLandRequest, listing_id).user_id, request_id=listing_id
    )
    assert error is None
    assert next(item for item in seller_offers.items if item.id == old_offer_id).offer_status == OfferStatus.EXPIRED

    new_offer = create_or_update_offer_for_buyer(
        db, request_id=listing_id, buyer_id=buyer_id, offered_amount=650000
    )
    assert new_offer.id != old_offer_id
    assert new_offer.status == OfferStatus.PENDING.value
    assert Decimal(db.get(SellLandOffer, old_offer_id).offered_amount) == Decimal("500000")
    db.close()


def test_new_accepted_offer_price_is_separate_from_cancelled_booking_history(property_booking_case):
    Session, (booking_id, listing_id, buyer_id), actors = property_booking_case
    db = Session()
    cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="NO_REFUND", cancellation_reason="Old booking cancelled",
        ),
    )
    listing = db.get(SellLandRequest, listing_id)
    offer = SellLandOffer(
        request_id=listing_id, buyer_id=buyer_id, offered_amount=600000,
        status=OfferStatus.ACCEPTED.value, seller_response_at=datetime(2026, 11, 10),
    )
    db.add(offer)
    db.flush()
    listing.accepted_offer_id = offer.id
    listing.offer_locked_by_buyer_id = buyer_id
    listing.offer_lock_expires_at = datetime(2026, 11, 20)
    db.commit()

    buyer_detail, error = sell_land_service.get_buyer_land_detail_for_buyer(db, listing_id, buyer_id)
    assert error is None
    assert buyer_detail.deal_amount == 600000
    buyer_offers = sell_land_service.list_my_buyer_offers(db, buyer_id)
    new_offer_item = next(item for item in buyer_offers.items if item.offer_id == offer.id)
    old_booking_item = next(item for item in buyer_offers.items if item.booking_id == booking_id)
    assert new_offer_item.final_amount == 600000
    assert new_offer_item.booking_id is None
    assert old_booking_item.final_amount == 500000
    assert old_booking_item.booking_id == booking_id
    historical, error = admin_service.get_booked_listing_detail(
        db, current_user=actors["super_admin"], request_id=listing_id,
    )
    assert error is None
    assert historical.booking_id == booking_id
    assert historical.land.deal_price == 500000
    assert db.get(SellLandBooking, booking_id).deal_amount == 500000
    db.close()


def test_unresolved_refund_blocks_rebooking_and_failed_case_stays_in_accounting_queue(property_booking_case):
    Session, (booking_id, listing_id, buyer_id), actors = property_booking_case
    db = Session()
    cancelled = cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="REFUND", cancellation_reason="Refund still owed",
        ),
    )
    listing = db.get(SellLandRequest, listing_id)
    offer = SellLandOffer(
        request_id=listing_id, buyer_id=buyer_id, offered_amount=600000,
        status=OfferStatus.ACCEPTED.value, seller_response_at=datetime(2026, 11, 10),
    )
    db.add(offer)
    db.flush()
    listing.accepted_offer_id = offer.id
    listing.offer_locked_by_buyer_id = buyer_id
    listing.offer_lock_expires_at = datetime(2026, 11, 20)
    db.commit()

    booking, error = sell_land_service.create_booking_for_buyer(
        db, user_id=buyer_id, payload=SimpleNamespace(request_id=listing_id),
        aadhaar_doc=None, pan_doc=None, bank_doc=None,
    )
    assert booking is None
    assert "refund must be resolved" in error.lower()
    buyer = db.get(User, buyer_id)
    submit_buyer_refund_upi(
        db, booking_id=booking_id, buyer=buyer,
        payload=BuyerPropertyBookingRefundUpiRequest(upi_id="buyer.refund@okaxis"),
    )
    booking, error = sell_land_service.create_booking_for_buyer(
        db, user_id=buyer_id, payload=SimpleNamespace(request_id=listing_id),
        aadhaar_doc=None, pan_doc=None, bank_doc=None,
    )
    assert booking is None
    assert "refund must be resolved" in error.lower()
    fail_property_booking_refund(
        db, refund_id=cancelled.refund_id, actor=actors["accounting"],
        payload=AccountingPropertyBookingRefundFailRequest(reason="Transfer failed"),
    )
    queue = list_property_booking_refunds(db, skip=0, limit=20)
    assert any(item.refund_id == cancelled.refund_id and item.refund_status == "FAILED" for item in queue.items)
    db.close()


def test_other_buyer_cannot_create_parallel_unfinished_booking(property_booking_case):
    Session, (booking_id, listing_id, buyer_id), actors = property_booking_case
    db = Session()
    cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="NO_REFUND", cancellation_reason="Old booking cancelled",
        ),
    )
    buyer = db.get(User, buyer_id)
    other_buyer = User(fullname="Second buyer", mobile="9100000311", role="CUSTOMER", is_active=True)
    db.add(other_buyer)
    db.flush()
    db.add(SellLandBooking(
        request_id=listing_id, buyer_id=other_buyer.id, buyer_name=other_buyer.fullname,
        buyer_mobile=other_buyer.mobile, deal_amount=600000, booking_fee_amount=999,
        payment_status="initiated", booking_status="booked",
    ))
    db.commit()

    created, error = sell_land_service.create_booking_for_buyer(
        db, user_id=buyer.id, payload=SimpleNamespace(
            request_id=listing_id, buyer_name=buyer.fullname, buyer_mobile=buyer.mobile,
        ), aadhaar_doc=None, pan_doc=None, bank_doc=None,
    )
    assert created is None
    assert "another buyer" in error.lower()
    assert db.get(SellLandBooking, booking_id).deal_amount == Decimal("500000")
    db.close()


def test_seller_cannot_reject_an_already_accepted_offer(property_booking_case):
    Session, (_, listing_id, buyer_id), _ = property_booking_case
    db = Session()
    listing = db.get(SellLandRequest, listing_id)
    offer = SellLandOffer(
        request_id=listing_id, buyer_id=buyer_id, offered_amount=600000,
        status=OfferStatus.ACCEPTED.value, seller_response_at=datetime(2026, 11, 10),
    )
    db.add(offer)
    db.flush()
    listing.accepted_offer_id = offer.id
    listing.offer_locked_by_buyer_id = buyer_id
    db.commit()

    response, error = sell_land_service.reject_offer_for_my_listing(
        db, user_id=listing.user_id, request_id=listing_id, offer_id=offer.id,
    )
    assert response is None
    assert error == "Offer is already finalized"
    assert db.get(SellLandOffer, offer.id).status == OfferStatus.ACCEPTED.value
    db.close()


@pytest.mark.parametrize("actor", ["admin", "buyer", "officer"])
def test_only_super_admin_can_cancel_property_booking(property_booking_case, actor):
    Session, (booking_id, _, _), actors = property_booking_case
    db = Session()
    with pytest.raises(HTTPException) as error:
        cancel_property_booking(
            db, booking_id=booking_id, actor=actors[actor],
            payload=PropertyBookingCancellationRequest(
                refund_decision="REFUND", cancellation_reason="Booking review requires cancellation"
            ),
        )
    assert error.value.status_code == 403
    db.close()


def test_buyer_upi_is_owner_scoped_and_accounting_confirmation_is_idempotent(property_booking_case):
    Session, (booking_id, _, buyer_id), actors = property_booking_case
    db = Session()
    cancelled = cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="REFUND", refund_amount=Decimal("950.50"),
            cancellation_reason="Refund adjusted after review",
        ),
    )
    with pytest.raises(HTTPException) as error:
        get_buyer_booking_refund(db, booking_id=booking_id, buyer=SimpleNamespace(id=999))
    assert error.value.status_code == 404
    buyer = db.get(User, buyer_id)
    submitted = submit_buyer_refund_upi(
        db, booking_id=booking_id, buyer=buyer,
        payload=BuyerPropertyBookingRefundUpiRequest(upi_id="buyer.refund@okaxis"),
    )
    assert submitted.refund_status == "PENDING_ACCOUNTING"
    with pytest.raises(HTTPException) as duplicate_upi:
        submit_buyer_refund_upi(
            db, booking_id=booking_id, buyer=buyer,
            payload=BuyerPropertyBookingRefundUpiRequest(upi_id="buyer.refund@okaxis"),
        )
    assert duplicate_upi.value.status_code == 409
    refund = db.get(PropertyBookingRefund, cancelled.refund_id)
    assert "buyer.refund@okaxis" not in refund.buyer_upi_ciphertext
    accounting_detail = get_accounting_property_booking_refund(db, cancelled.refund_id)
    assert accounting_detail.buyer_upi_id == "buyer.refund@okaxis"
    queue = list_property_booking_refunds(db, skip=0, limit=20)
    assert next(item for item in queue.items if item.refund_id == cancelled.refund_id).buyer_upi_id == "buyer.refund@okaxis"

    with pytest.raises(HTTPException) as mismatch:
        confirm_property_booking_refund(
            db, refund_id=cancelled.refund_id, actor=actors["accounting"],
            payload=AccountingPropertyBookingRefundConfirmRequest(
                actual_refunded_amount=Decimal("950.49"), transaction_reference="UPI-REF-WRONG"
            ),
        )
    assert mismatch.value.status_code == 422
    with pytest.raises(ValueError):
        AccountingPropertyBookingRefundConfirmRequest(
            actual_refunded_amount=Decimal("950.50"), transaction_reference="  ",
        )

    payload = AccountingPropertyBookingRefundConfirmRequest(
        actual_refunded_amount=Decimal("950.50"), transaction_reference="UPI-REF-0001",
        confirmation_note="Sent through external UPI",
    )
    confirmed = confirm_property_booking_refund(
        db, refund_id=cancelled.refund_id, actor=actors["accounting"], payload=payload
    )
    event_count = db.query(PropertyBookingRefundEvent).filter_by(refund_id=cancelled.refund_id).count()
    again = confirm_property_booking_refund(
        db, refund_id=cancelled.refund_id, actor=actors["accounting"], payload=payload
    )
    assert confirmed.refund_status == again.refund_status == "CONFIRMED"
    assert again.transaction_reference == "UPI-REF-0001"
    assert refund.actual_refunded_amount == Decimal("950.50")
    assert refund.accounting_actor_id == actors["accounting"].id
    assert refund.accounting_confirmed_at is not None
    assert db.query(PropertyBookingRefundEvent).filter_by(refund_id=cancelled.refund_id).count() == event_count
    db.close()


def test_buyer_refund_upi_submission_encrypts_and_advances_status(property_booking_case):
    Session, (booking_id, _, buyer_id), actors = property_booking_case
    db = Session()
    cancelled = cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="REFUND", cancellation_reason="Refund UPI submission test",
        ),
    )

    response = submit_buyer_refund_upi(
        db, booking_id=booking_id, buyer=db.get(User, buyer_id),
        payload=BuyerPropertyBookingRefundUpiRequest(upi_id="focused.test@okaxis"),
    )

    refund = db.get(PropertyBookingRefund, cancelled.refund_id)
    assert response.refund_status == "PENDING_ACCOUNTING"
    assert refund.refund_status == "PENDING_ACCOUNTING"
    assert refund.buyer_upi_submitted_at is not None
    assert refund.buyer_upi_ciphertext.startswith("v1:")
    assert "focused.test@okaxis" not in refund.buyer_upi_ciphertext
    assert db.query(PropertyBookingRefundEvent).filter_by(
        refund_id=cancelled.refund_id, event_type="BUYER_UPI_SUBMITTED",
    ).count() == 1
    db.close()


def test_buyer_refund_upi_missing_encryption_key_returns_503_without_mutation(
    property_booking_case, monkeypatch,
):
    from app.sell_land import booking_refund_crypto
    from app.sell_land.booking_refund_crypto import BookingRefundEncryptionConfigurationError

    Session, (booking_id, _, buyer_id), actors = property_booking_case
    db = Session()
    cancelled = cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="REFUND", cancellation_reason="Missing encryption key test",
        ),
    )

    def missing_key():
        raise BookingRefundEncryptionConfigurationError("missing key")

    monkeypatch.setattr(booking_refund_crypto, "_key", missing_key)
    with pytest.raises(HTTPException) as error:
        submit_buyer_refund_upi(
            db, booking_id=booking_id, buyer=db.get(User, buyer_id),
            payload=BuyerPropertyBookingRefundUpiRequest(upi_id="focused.test@okaxis"),
        )

    assert error.value.status_code == 503
    refund = db.get(PropertyBookingRefund, cancelled.refund_id)
    assert refund.refund_status == "AWAITING_BUYER_DETAILS"
    assert refund.buyer_upi_ciphertext is None
    assert refund.buyer_upi_submitted_at is None
    assert db.query(PropertyBookingRefundEvent).filter_by(
        refund_id=cancelled.refund_id, event_type="BUYER_UPI_SUBMITTED",
    ).count() == 0
    db.close()


def test_no_refund_creates_no_accounting_case_and_completed_amount_is_not_refundable(property_booking_case):
    Session, (booking_id, listing_id, _), actors = property_booking_case
    db = Session()
    result = cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="NO_REFUND", refund_amount=Decimal("0.00"),
            cancellation_reason="Cancellation without a refund",
        ),
    )
    assert result.refund_status == "NOT_REQUIRED"
    assert result.approved_refund_amount == Decimal("0.00")
    assert db.get(SellLandRequest, listing_id).status == "live"
    assert get_buyer_booking_refund(db, booking_id=booking_id, buyer=db.get(User, actors["buyer"].id)).refund_decision == "NO_REFUND"
    db.close()


def test_failed_external_refund_stays_failed(property_booking_case):
    Session, (booking_id, _, _), actors = property_booking_case
    db = Session()
    cancelled = cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="REFUND", cancellation_reason="Booking review requires cancellation"
        ),
    )
    buyer = db.get(User, actors["buyer"].id)
    submit_buyer_refund_upi(db, booking_id=booking_id, buyer=buyer,
                            payload=BuyerPropertyBookingRefundUpiRequest(upi_id="buyer.refund@okaxis"))
    failed = fail_property_booking_refund(
        db, refund_id=cancelled.refund_id, actor=actors["accounting"],
        payload=AccountingPropertyBookingRefundFailRequest(reason="Beneficiary validation failed"),
    )
    assert failed.refund_status == "FAILED"
    db.close()


def test_accounting_can_resolve_failed_case_after_a_later_transfer(property_booking_case, monkeypatch):
    Session, (booking_id, _, _), actors = property_booking_case
    db = Session()
    cancelled = cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="REFUND", cancellation_reason="Refund transfer requires retry",
        ),
    )
    buyer = db.get(User, actors["buyer"].id)
    submit_buyer_refund_upi(
        db, booking_id=booking_id, buyer=buyer,
        payload=BuyerPropertyBookingRefundUpiRequest(upi_id="buyer.refund@okaxis"),
    )
    fail_property_booking_refund(
        db, refund_id=cancelled.refund_id, actor=actors["accounting"],
        payload=AccountingPropertyBookingRefundFailRequest(reason="Initial transfer failed"),
    )
    resolved = confirm_property_booking_refund(
        db, refund_id=cancelled.refund_id, actor=actors["accounting"],
        payload=AccountingPropertyBookingRefundConfirmRequest(
            actual_refunded_amount=Decimal("999.00"), transaction_reference="UPI-RETRY-0001",
        ),
    )
    assert resolved.refund_status == "CONFIRMED"
    assert resolved.actual_refunded_amount == Decimal("999.00")
    assert resolved.transaction_reference == "UPI-RETRY-0001"

    # A resolved refund permits a separate booking row at the new accepted price.
    listing = db.get(SellLandRequest, cancelled.listing_id)
    offer = SellLandOffer(
        request_id=listing.id, buyer_id=buyer.id, offered_amount=600000,
        status=OfferStatus.ACCEPTED.value, seller_response_at=datetime(2026, 11, 10),
    )
    db.add(offer)
    db.flush()
    listing.accepted_offer_id = offer.id
    listing.offer_locked_by_buyer_id = buyer.id
    listing.offer_lock_expires_at = datetime(2026, 11, 20)
    db.commit()
    monkeypatch.setattr(
        sell_land_service, "save_booking_doc_file",
        lambda **kwargs: (f"{kwargs['doc_label']}.pdf", f"/private/{kwargs['doc_label']}.pdf"),
    )
    new_booking, error = sell_land_service.create_booking_for_buyer(
        db, user_id=buyer.id, payload=SimpleNamespace(
            request_id=listing.id, buyer_name=buyer.fullname, buyer_mobile=buyer.mobile,
        ), aadhaar_doc=object(), pan_doc=object(), bank_doc=object(),
    )
    assert error is None
    assert new_booking.id != booking_id
    assert Decimal(new_booking.deal_amount) == Decimal("600000")
    assert db.get(SellLandBooking, booking_id).deal_amount == Decimal("500000")
    seller_tracking = sell_land_service.list_my_request_tracking(db, listing.user_id)
    current_card = next(card for card in seller_tracking if card.id == listing.id)
    assert Decimal(str(current_card.deal_amount)) == Decimal("600000")
    db.close()


@pytest.mark.parametrize("blocker", ["another_booking", "unrelated_lock", "completed_registry"])
def test_cancellation_does_not_republish_listing_when_another_deal_blocks_it(property_booking_case, blocker):
    Session, (booking_id, listing_id, buyer_id), actors = property_booking_case
    db = Session()
    listing = db.get(SellLandRequest, listing_id)
    if blocker == "another_booking":
        other_buyer = User(fullname="Other buyer", mobile="9100000211", role="CUSTOMER", is_active=True)
        db.add(other_buyer)
        db.flush()
        db.add(SellLandBooking(
            request_id=listing_id, buyer_id=other_buyer.id, buyer_name=other_buyer.fullname,
            buyer_mobile=other_buyer.mobile, deal_amount=500000, booking_fee_amount=999,
            payment_status="success", booking_status="booked",
        ))
    elif blocker == "unrelated_lock":
        other_buyer = User(fullname="Lock owner", mobile="9100000212", role="CUSTOMER", is_active=True)
        db.add(other_buyer)
        db.flush()
        listing.offer_locked_by_buyer_id = other_buyer.id
    else:
        db.get(SellLandBooking, booking_id).booking_status = "registry_done"
    db.commit()
    if blocker == "completed_registry":
        with pytest.raises(HTTPException) as error:
            cancel_property_booking(
                db, booking_id=booking_id, actor=actors["super_admin"],
                payload=PropertyBookingCancellationRequest(
                    refund_decision="NO_REFUND", cancellation_reason="Cancellation not allowed after registry"
                ),
            )
        assert error.value.status_code == 409
    else:
        cancel_property_booking(
            db, booking_id=booking_id, actor=actors["super_admin"],
            payload=PropertyBookingCancellationRequest(
                refund_decision="NO_REFUND", cancellation_reason="Cancellation without refund"
            ),
        )
        assert db.get(SellLandRequest, listing_id).status == "booked"
    db.close()


def test_duplicate_cancellation_request_is_rejected(property_booking_case):
    Session, (booking_id, _, _), actors = property_booking_case
    db = Session()
    payload = PropertyBookingCancellationRequest(
        refund_decision="NO_REFUND", cancellation_reason="Cancellation without refund"
    )
    cancel_property_booking(db, booking_id=booking_id, actor=actors["super_admin"], payload=payload)
    with pytest.raises(HTTPException) as error:
        cancel_property_booking(db, booking_id=booking_id, actor=actors["super_admin"], payload=payload)
    assert error.value.status_code == 409
    db.close()


def test_notification_failure_does_not_undo_cancellation(property_booking_case, monkeypatch):
    from app.sell_land import property_booking_refunds as service

    Session, (booking_id, listing_id, _), actors = property_booking_case
    monkeypatch.setattr(service, "notify_users", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    db = Session()
    result = cancel_property_booking(
        db, booking_id=booking_id, actor=actors["super_admin"],
        payload=PropertyBookingCancellationRequest(
            refund_decision="NO_REFUND", cancellation_reason="Cancellation without refund"
        ),
    )
    db.close()
    verify = Session()
    assert verify.get(SellLandBooking, booking_id).booking_status == "cancelled"
    assert verify.get(SellLandRequest, listing_id).status == "live"
    assert verify.get(PropertyBookingRefund, result.refund_id) is not None
    verify.close()
