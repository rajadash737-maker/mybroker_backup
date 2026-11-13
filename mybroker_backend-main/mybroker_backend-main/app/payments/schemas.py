from pydantic import BaseModel, Field, field_validator


class CreateOrderRequest(BaseModel):
    amount: float = Field(gt=0)
    user_id: int = Field(gt=0)
    property_id: int = Field(gt=0)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("amount must be greater than 0")
        return value


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str = Field(min_length=5, max_length=64)
    razorpay_payment_id: str = Field(min_length=5, max_length=64)
    razorpay_signature: str = Field(min_length=5, max_length=256)

    @field_validator(
        "razorpay_order_id",
        "razorpay_payment_id",
        "razorpay_signature",
        mode="before",
    )
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned


class VerifyPaymentResponse(BaseModel):
    status: str
    order_id: str
    payment_id: str


class PaymentItemResponse(BaseModel):
    id: int
    user_id: int
    property_id: int
    order_id: str
    payment_id: str | None = None
    amount: float
    status: str
    created_at: str
    updated_at: str


class PaymentListResponse(BaseModel):
    total: int
    items: list[PaymentItemResponse]


class WebhookLogItemResponse(BaseModel):
    id: int
    event_id: str | None = None
    event: str
    order_id: str | None = None
    payment_id: str | None = None
    status: str
    payment_context: str
    error: str | None = None
    payload: str
    created_at: str


class WebhookLogListResponse(BaseModel):
    total: int
    items: list[WebhookLogItemResponse]
