from pydantic import BaseModel, Field


class TransactionItemResponse(BaseModel):
    transaction_id: str | None = None
    property_title: str = Field(default="")
    buyer_name: str = Field(default="")
    seller_name: str = Field(default="")
    location: str = Field(default="")
    deal_amount: int = Field(default=0)
    payment_status: str = Field(default="")
    deal_status: str = Field(default="")
    offer_status: str | None = None
    offer_status_at: str | None = None
    registry_date: str | None = None
    created_at: str | None = None


class TransactionsResponse(BaseModel):
    data: list[TransactionItemResponse] = Field(default_factory=list)
