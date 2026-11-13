from datetime import datetime
from pydantic import BaseModel, Field


class NotificationCreateRequest(BaseModel):
    title: str
    body: str
    type: str
    role_target: str | None = None
    reference_id: str | None = None
    user_ids: list[int] = Field(default_factory=list)


class NotificationReadRequest(BaseModel):
    notification_ids: list[int] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    mark_all: bool = False


class NotificationResponse(BaseModel):
    id: int
    title: str
    body: str
    type: str
    role_target: str | None = None
    reference_id: str | None = None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    total: int
    items: list[NotificationResponse]
