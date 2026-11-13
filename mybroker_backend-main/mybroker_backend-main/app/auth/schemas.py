from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from app.media.url_utils import to_public_url
from app.users.profile_image import resolve_profile_image_url

class SignupSchema(BaseModel):
    fullname: str = Field(min_length=2, max_length=100)
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr
    mobile: str
    password: str = Field(min_length=8, max_length=128)
    confirm: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()

class LoginSchema(BaseModel):
    email: str | None = None
    mobile: str | None = None
    identifier: str | None = None
    password: str

    @model_validator(mode="after")
    def validate_identifier(self):
        if not (self.identifier or self.email or self.mobile):
            raise ValueError("identifier or email or mobile is required")
        return self


class GoogleAuthRequestSchema(BaseModel):
    id_token: str = Field(min_length=1)

class SendOtpSchema(BaseModel):
    mobile: str
    purpose: Literal["signup", "password_reset"] = "signup"

class VerifyOtpSchema(BaseModel):
    mobile: str
    otp: str
    purpose: Literal["signup", "password_reset"] = "signup"

class FirebaseTokenSchema(BaseModel):
    id_token: str
    mobile: str
    purpose: Literal["signup", "password_reset"] = "signup"

class ResetPasswordSchema(BaseModel):
    mobile: str
    password: str = Field(min_length=8, max_length=128)
    confirm: str | None = Field(default=None, min_length=8, max_length=128)


class ChangePasswordSchema(BaseModel):
    role: str = Field(min_length=3, max_length=50)
    email: EmailStr
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordResponseSchema(BaseModel):
    status: str
    message: str | None = None


class TokenPairSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_in_seconds: int
    refresh_expires_in_seconds: int


class AuthUserSchema(BaseModel):
    id: int
    fullname: str
    username: str | None = None
    email: EmailStr
    mobile: str | None = None
    role: str
    is_active: bool
    profile_image_url: str | None = None

    @field_validator("profile_image_url", mode="before")
    @classmethod
    def normalize_profile_image_url(cls, value: str | None) -> str | None:
        return resolve_profile_image_url(value)


class AuthResponseSchema(BaseModel):
    status: str
    user_id: int | None = None
    profile_image_url: str | None = None
    dashboard_key: str | None = None
    user: AuthUserSchema | None = None
    tokens: TokenPairSchema | None = None

    @field_validator("profile_image_url", mode="before")
    @classmethod
    def normalize_profile_image_url(cls, value: str | None) -> str | None:
        return resolve_profile_image_url(value)


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequestSchema(BaseModel):
    refresh_token: str = Field(min_length=20)
