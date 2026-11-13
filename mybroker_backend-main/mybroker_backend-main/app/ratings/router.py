from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.ratings.schemas import (
    RatingCreateRequest,
    RatingResponse,
    RatingSummaryResponse,
    RatingRole,
    RatingListItem,
)
from app.ratings.service import (
    create_rating_for_user,
    get_my_rating,
    get_my_rating_summary,
    list_my_received_ratings,
    list_admin_ratings,
)
from app.users.model import User
from app.users.roles import UserRole

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("", response_model=RatingResponse)
def submit_rating(
    payload: RatingCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = create_rating_for_user(db, current_user.id, payload)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return response


@router.get("/me", response_model=RatingResponse)
def get_my_rating_endpoint(
    property_id: int = Query(ge=1),
    role: RatingRole = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rating = get_my_rating(db, current_user.id, property_id, role)
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    return rating


@router.get("/me/summary", response_model=RatingSummaryResponse)
def get_my_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_my_rating_summary(db, current_user.id)


@router.get("/me/list", response_model=list[RatingListItem])
def list_my_ratings_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_my_received_ratings(db, current_user.id, skip, limit)


@router.get("/admin/list", response_model=list[RatingListItem])
def list_admin_ratings_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    property_id: int | None = Query(default=None, ge=1),
    role: RatingRole | None = None,
    min_rating: int | None = Query(default=None, ge=1, le=5),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_admin_ratings(
        db,
        skip=skip,
        limit=limit,
        property_id=property_id,
        role=role,
        min_rating=min_rating,
    )
