from sqlalchemy.orm import Session

from app.ratings.repository import (
    create_rating,
    get_existing_rating,
    get_rating_summary,
    list_ratings_for_user,
    list_ratings_admin,
)
from app.ratings.schemas import (
    RatingCreateRequest,
    RatingResponse,
    RatingSummaryResponse,
    RatingRole,
    RatingListItem,
    RatingUserSummary,
)
from app.sell_land.constants import SellLandStatus
from app.sell_land.models import SellLandBooking, SellLandRequest
from app.sell_land.repository import get_booking_for_listing_buyer, get_sell_land_request_by_id


def create_rating_for_user(
    db: Session,
    current_user_id: int,
    payload: RatingCreateRequest,
) -> tuple[RatingResponse | None, str | None]:
    listing = get_sell_land_request_by_id(db, payload.property_id)
    if not listing:
        return None, "Property not found"
    if listing.status != SellLandStatus.SOLD.value:
        return None, "Ratings are allowed only after sale is completed"

    if get_existing_rating(db, payload.property_id, current_user_id, payload.role.value):
        return None, "Rating already submitted"

    to_user_id: int | None = None

    if payload.role == RatingRole.BUYER_TO_SELLER:
        booking = get_booking_for_listing_buyer(db, payload.property_id, current_user_id)
        if not booking:
            return None, "Only the booked buyer can rate the seller"
        to_user_id = listing.user_id
    elif payload.role == RatingRole.SELLER_TO_BUYER:
        if listing.user_id != current_user_id:
            return None, "Only the seller can rate the buyer"
        booking = (
            db.query(SellLandBooking)
            .filter(SellLandBooking.request_id == payload.property_id)
            .order_by(SellLandBooking.created_at.desc(), SellLandBooking.id.desc())
            .first()
        )
        if not booking:
            return None, "Buyer not found for this property"
        to_user_id = booking.buyer_id

    if to_user_id is None:
        return None, "Invalid rating target"

    entity = create_rating(
        db,
        property_id=payload.property_id,
        from_user_id=current_user_id,
        to_user_id=to_user_id,
        role=payload.role.value,
        rating=payload.rating,
        review=payload.review,
    )
    return RatingResponse.model_validate(entity), None


def get_my_rating(
    db: Session,
    current_user_id: int,
    property_id: int,
    role: RatingRole,
) -> RatingResponse | None:
    entity = get_existing_rating(db, property_id, current_user_id, role.value)
    if not entity:
        return None
    return RatingResponse.model_validate(entity)


def get_my_rating_summary(
    db: Session,
    current_user_id: int,
) -> RatingSummaryResponse:
    average, total_reviews = get_rating_summary(db, current_user_id)
    return RatingSummaryResponse(average=average, total_reviews=total_reviews)


def list_my_received_ratings(
    db: Session,
    current_user_id: int,
    skip: int,
    limit: int,
) -> list[RatingListItem]:
    rows = list_ratings_for_user(db, current_user_id, skip, limit)
    items: list[RatingListItem] = []
    for rating, from_user, to_user, listing in rows:
        items.append(
            RatingListItem(
                id=rating.id,
                rating=rating.rating,
                review=rating.review,
                role=RatingRole(rating.role),
                property_id=rating.property_id,
                property_title=listing.title if listing else None,
                listing_code=listing.listing_code if listing else None,
                from_user=RatingUserSummary(
                    id=from_user.id,
                    fullname=from_user.fullname,
                    mobile=from_user.mobile,
                )
                if from_user
                else None,
                to_user=RatingUserSummary(
                    id=to_user.id,
                    fullname=to_user.fullname,
                    mobile=to_user.mobile,
                )
                if to_user
                else None,
                created_at=rating.created_at,
            )
        )
    return items


def list_admin_ratings(
    db: Session,
    skip: int,
    limit: int,
    property_id: int | None = None,
    role: RatingRole | None = None,
    min_rating: int | None = None,
) -> list[RatingListItem]:
    rows = list_ratings_admin(
        db,
        skip=skip,
        limit=limit,
        property_id=property_id,
        role=role.value if role else None,
        min_rating=min_rating,
    )
    items: list[RatingListItem] = []
    for rating, from_user, to_user, listing in rows:
        items.append(
            RatingListItem(
                id=rating.id,
                rating=rating.rating,
                review=rating.review,
                role=RatingRole(rating.role),
                property_id=rating.property_id,
                property_title=listing.title if listing else None,
                listing_code=listing.listing_code if listing else None,
                from_user=RatingUserSummary(
                    id=from_user.id,
                    fullname=from_user.fullname,
                    mobile=from_user.mobile,
                )
                if from_user
                else None,
                to_user=RatingUserSummary(
                    id=to_user.id,
                    fullname=to_user.fullname,
                    mobile=to_user.mobile,
                )
                if to_user
                else None,
                created_at=rating.created_at,
            )
        )
    return items
