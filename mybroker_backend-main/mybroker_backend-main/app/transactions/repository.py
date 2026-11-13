from sqlalchemy import exists, or_
from sqlalchemy.orm import aliased
from sqlalchemy.orm import Session

from app.sell_land.models import SellLandBooking, SellLandOffer, SellLandRequest
from app.users.model import User


def list_user_transactions(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
):
    return (
        db.query(SellLandBooking, SellLandRequest, User)
        .join(SellLandRequest, SellLandRequest.id == SellLandBooking.request_id)
        .join(User, User.id == SellLandRequest.user_id)
        .filter(
            or_(
                SellLandBooking.buyer_id == user_id,
                SellLandRequest.user_id == user_id,
            )
        )
        .order_by(SellLandBooking.created_at.desc(), SellLandBooking.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_user_offer_transactions(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
):
    buyer_user = aliased(User)
    seller_user = aliased(User)

    booking_exists_for_buyer = (
        db.query(SellLandBooking.id)
        .filter(
            SellLandBooking.request_id == SellLandOffer.request_id,
            SellLandBooking.buyer_id == SellLandOffer.buyer_id,
        )
        .exists()
    )

    booking_exists_for_listing = (
        db.query(SellLandBooking.id)
        .filter(SellLandBooking.request_id == SellLandOffer.request_id)
        .exists()
    )

    return (
        db.query(SellLandOffer, SellLandRequest, seller_user, buyer_user)
        .join(SellLandRequest, SellLandRequest.id == SellLandOffer.request_id)
        .join(seller_user, seller_user.id == SellLandRequest.user_id)
        .join(buyer_user, buyer_user.id == SellLandOffer.buyer_id)
        .filter(
            or_(
                SellLandOffer.buyer_id == user_id,
                SellLandRequest.user_id == user_id,
            )
        )
        .filter(
            or_(
                (SellLandOffer.buyer_id == user_id) & (~booking_exists_for_buyer),
                (SellLandRequest.user_id == user_id) & (~booking_exists_for_listing),
            )
        )
        .order_by(SellLandOffer.created_at.desc(), SellLandOffer.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_booking_by_transaction_id(
    db: Session,
    user_id: int,
    transaction_id: str,
):
    return (
        db.query(SellLandBooking, SellLandRequest, User)
        .join(SellLandRequest, SellLandRequest.id == SellLandBooking.request_id)
        .join(User, User.id == SellLandRequest.user_id)
        .filter(
            SellLandBooking.payment_transaction_id == transaction_id,
            or_(
                SellLandBooking.buyer_id == user_id,
                SellLandRequest.user_id == user_id,
            ),
        )
        .first()
    )


def get_booking_by_id_for_user(
    db: Session,
    user_id: int,
    booking_id: int,
):
    return (
        db.query(SellLandBooking, SellLandRequest, User)
        .join(SellLandRequest, SellLandRequest.id == SellLandBooking.request_id)
        .join(User, User.id == SellLandRequest.user_id)
        .filter(
            SellLandBooking.id == booking_id,
            or_(
                SellLandBooking.buyer_id == user_id,
                SellLandRequest.user_id == user_id,
            ),
        )
        .first()
    )


def get_offer_by_id(
    db: Session,
    user_id: int,
    offer_id: int,
):
    buyer_user = aliased(User)
    seller_user = aliased(User)
    return (
        db.query(SellLandOffer, SellLandRequest, seller_user, buyer_user)
        .join(SellLandRequest, SellLandRequest.id == SellLandOffer.request_id)
        .join(seller_user, seller_user.id == SellLandRequest.user_id)
        .join(buyer_user, buyer_user.id == SellLandOffer.buyer_id)
        .filter(
            SellLandOffer.id == offer_id,
            or_(
                SellLandOffer.buyer_id == user_id,
                SellLandRequest.user_id == user_id,
            ),
        )
        .first()
    )
