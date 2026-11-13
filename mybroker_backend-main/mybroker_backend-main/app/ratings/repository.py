from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.ratings.models import Rating
from app.sell_land.models import SellLandRequest
from app.users.model import User


def get_existing_rating(
    db: Session,
    property_id: int,
    from_user_id: int,
    role: str,
) -> Rating | None:
    return (
        db.query(Rating)
        .filter(
            Rating.property_id == property_id,
            Rating.from_user_id == from_user_id,
            Rating.role == role,
        )
        .first()
    )


def create_rating(
    db: Session,
    *,
    property_id: int,
    from_user_id: int,
    to_user_id: int,
    role: str,
    rating: int,
    review: str | None,
) -> Rating:
    entity = Rating(
        property_id=property_id,
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        role=role,
        rating=rating,
        review=review,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def get_rating_summary(db: Session, to_user_id: int) -> tuple[float, int]:
    avg, total = (
        db.query(func.avg(Rating.rating), func.count(Rating.id))
        .filter(Rating.to_user_id == to_user_id)
        .one()
    )
    average = float(avg or 0.0)
    total_reviews = int(total or 0)
    return average, total_reviews


def list_ratings_for_user(
    db: Session,
    to_user_id: int,
    skip: int,
    limit: int,
) -> list[tuple[Rating, User | None, User | None, SellLandRequest | None]]:
    from_user = aliased(User)
    to_user = aliased(User)
    return (
        db.query(Rating, from_user, to_user, SellLandRequest)
        .outerjoin(from_user, Rating.from_user_id == from_user.id)
        .outerjoin(to_user, Rating.to_user_id == to_user.id)
        .outerjoin(SellLandRequest, Rating.property_id == SellLandRequest.id)
        .filter(Rating.to_user_id == to_user_id)
        .order_by(Rating.created_at.desc(), Rating.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_ratings_admin(
    db: Session,
    skip: int,
    limit: int,
    property_id: int | None = None,
    role: str | None = None,
    min_rating: int | None = None,
) -> list[tuple[Rating, User | None, User | None, SellLandRequest | None]]:
    from_user = aliased(User)
    to_user = aliased(User)
    query = (
        db.query(Rating, from_user, to_user, SellLandRequest)
        .outerjoin(from_user, Rating.from_user_id == from_user.id)
        .outerjoin(to_user, Rating.to_user_id == to_user.id)
        .outerjoin(SellLandRequest, Rating.property_id == SellLandRequest.id)
    )
    if property_id:
        query = query.filter(Rating.property_id == property_id)
    if role:
        query = query.filter(Rating.role == role)
    if min_rating:
        query = query.filter(Rating.rating >= min_rating)

    return (
        query.order_by(Rating.created_at.desc(), Rating.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
