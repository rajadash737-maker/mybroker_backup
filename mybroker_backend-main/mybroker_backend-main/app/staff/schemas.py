from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.users.roles import UserRole


class CreateStaffRequest(BaseModel):
    fullname: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    username: str | None = Field(default=None, min_length=3, max_length=50)
    mobile: str | None = Field(default=None, min_length=10, max_length=15)

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


class StaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fullname: str
    email: EmailStr
    username: str | None = None
    mobile: str | None = None
    role: str
    is_active: bool
    created_at: datetime | None = None


class StaffCreateResponse(BaseModel):
    status: str
    staff: StaffResponse


class UpdateStaffRequest(BaseModel):
    fullname: str = Field(min_length=2, max_length=100)
    email: EmailStr
    role: UserRole


class ToggleStaffActiveRequest(BaseModel):
    is_active: bool


class StaffActionResponse(BaseModel):
    status: str
    staff: StaffResponse


class DeleteStaffResponse(BaseModel):
    status: str


class ResetStaffPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class ResetStaffPasswordResponse(BaseModel):
    status: str


class StaffAnalyticsSummary(BaseModel):
    total_staff: int
    total_visits: int
    total_verified_docs: int
    total_rejected_docs: int


class StaffAnalyticsItem(BaseModel):
    id: int
    name: str
    mobile: str | None = None
    role: str
    documents_verified: int | None = None
    documents_rejected: int | None = None
    listings_approved: int | None = None
    registry_approved: int | None = None
    sold_count: int | None = None
    site_visits: int | None = None
    registry_visits: int | None = None


class StaffAnalyticsResponse(BaseModel):
    summary: StaffAnalyticsSummary
    staff: list[StaffAnalyticsItem]


class BootstrapSuperAdminRequest(BaseModel):
    fullname: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: str | None = Field(default=None, min_length=3, max_length=50)
    mobile: str | None = Field(default=None, min_length=10, max_length=15)

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
