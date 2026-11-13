from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SocialLinksBase(BaseModel):
    whatsapp: str | None = Field(default=None, max_length=255)
    instagram: str | None = Field(default=None, max_length=255)
    telegram: str | None = Field(default=None, max_length=255)
    youtube: str | None = Field(default=None, max_length=255)
    facebook: str | None = Field(default=None, max_length=255)
    linkedin: str | None = Field(default=None, max_length=255)


class SocialLinksUpdateRequest(SocialLinksBase):
    pass


class SocialLinksResponse(SocialLinksBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class BannerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    sort_order: int
    is_active: bool


class BannerDeleteResponse(BaseModel):
    status: str


class ProcessingFeeSettingsUpdateRequest(BaseModel):
    seller_processing_fee: float = Field(ge=0)
    buyer_processing_fee: float = Field(ge=0)


class ProcessingFeeSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_processing_fee: float
    buyer_processing_fee: float
    updated_at: datetime
