from datetime import date, datetime
from enum import Enum

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, ValidationInfo, field_validator

from app.media.url_utils import to_public_url
from app.users.profile_image import resolve_profile_image_url

class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fullname: str
    username: str | None = None
    email: EmailStr
    mobile: str | None = None
    role: str
    is_active: bool
    profile_image_url: str | None = None
    address: str | None = None
    date_of_birth: date | None = None
    gender: GenderEnum | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("profile_image_url", mode="before")
    @classmethod
    def normalize_profile_image_url(cls, value: str | None, info: ValidationInfo) -> str | None:
        role = info.data.get("role") if info.data else None
        return resolve_profile_image_url(value, role)


class UpdateProfileRequest(BaseModel):
    fullname: str | None = Field(default=None, min_length=2, max_length=100)
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    mobile: str | None = Field(default=None, min_length=10, max_length=15)
    address: str | None = Field(default=None, max_length=255)
    date_of_birth: date | None = None
    gender: GenderEnum | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()

    @field_validator("mobile")
    @classmethod
    def normalize_mobile(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = value.strip().lstrip("+")
        if len(digits) == 10:
            digits = f"91{digits}"
        if not digits.isdigit():
            raise ValueError("mobile must be numeric")
        return digits

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def parse_date_of_birth(cls, value):
        if value is None or isinstance(value, date):
            return value
        if isinstance(value, str):
            raw = value.strip()
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(raw, fmt).date()
                except ValueError:
                    continue
        raise ValueError("date_of_birth must be DD/MM/YYYY or YYYY-MM-DD")


class ProfilePhotoResponse(BaseModel):
    status: str
    profile_image_url: str

    @field_validator("profile_image_url", mode="before")
    @classmethod
    def normalize_profile_image_url(cls, value: str) -> str:
        return to_public_url(value) or value


class FcmTokenRequest(BaseModel):
    token: str = Field(
        min_length=10,
        max_length=4096,
        validation_alias=AliasChoices("token", "fcm_token"),
        serialization_alias="token",
    )
