from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user, get_db
from app.models.property import PropertyStore
from app.services.notification_service import NotificationService
from app.users.model import User

router = APIRouter(prefix="/property", tags=["property"])

_property_store = PropertyStore()


class PropertyUploadRequest(BaseModel):
    seller_id: int | None = None
    title: str | None = None
    document_url: str | None = None


@router.post("/upload", deprecated=True)
def upload_property(
    payload: PropertyUploadRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if payload.seller_id is not None and payload.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Seller ID must match the authenticated user")
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</sell-land/>; rel="successor-version"'
    prop = _property_store.create(
        seller_id=current_user.id,
        title=payload.title,
        document_url=payload.document_url,
    )

    notify_result = NotificationService(db=db).notify_property_uploaded(prop.id)

    return {
        "property_id": prop.id,
        "notified_roles": ["super_admin", "admin", "accounting"],
        "notification_result": notify_result,
    }
