from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RatingRole(str, Enum):
    BUYER_TO_SELLER = "buyer_to_seller"
    SELLER_TO_BUYER = "seller_to_buyer"


class RatingCreateRequest(BaseModel):
    property_id: int = Field(ge=1)
    role: RatingRole
    rating: int = Field(ge=1, le=5)
    review: str | None = Field(default=None, max_length=1000)


class RatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_user_id: int
    to_user_id: int
    role: RatingRole
    rating: int
    review: str | None = None
    property_id: int
    created_at: datetime


class RatingSummaryResponse(BaseModel):
    average: float
    total_reviews: int


class RatingUserSummary(BaseModel):
    id: int
    fullname: str | None = None
    mobile: str | None = None


class RatingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rating: int
    review: str | None = None
    role: RatingRole
    property_id: int
    property_title: str | None = None
    listing_code: str | None = None
    from_user: RatingUserSummary | None = None
    to_user: RatingUserSummary | None = None
    created_at: datetime
