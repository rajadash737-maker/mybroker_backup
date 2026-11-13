import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user, get_db
from app.notifications.models import Notification
from app.notifications.schemas import (
    NotificationCreateRequest,
    NotificationListResponse,
    NotificationReadRequest,
    NotificationResponse,
)
from app.notifications.service import notify_users
from app.users.model import User
from app.users.roles import UserRole
from app.core.dependencies import require_roles

router = APIRouter(prefix="/notifications", tags=["Notifications"])
logger = logging.getLogger(__name__)


def _clean_reference_ids(values: list[str]) -> list[str]:
    cleaned = []
    for value in values or []:
        item = (value or "").strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


@router.post(
    "",
    response_model=list[NotificationResponse],
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_notification_endpoint(
    payload: NotificationCreateRequest,
    db: Session = Depends(get_db),
):
    users: list[User] = []
    if payload.user_ids:
        users = db.query(User).filter(User.id.in_(payload.user_ids)).all()
    elif payload.role_target:
        users = db.query(User).filter(User.role == payload.role_target).all()

    created = notify_users(
        db=db,
        users=users,
        title=payload.title,
        body=payload.body,
        notif_type=payload.type,
        role_target=payload.role_target,
        reference_id=payload.reference_id,
    )
    return [
        NotificationResponse(
            id=item.id,
            title=item.title,
            body=item.body,
            type=item.type,
            role_target=item.role_target,
            reference_id=item.reference_id,
            is_read=item.is_read,
            created_at=item.created_at,
        )
        for item in created
    ]


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    only_unread: bool = Query(default=False),
    reference_id: str | None = Query(default=None),
    notif_type: str | None = Query(default=None, alias="type"),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if only_unread:
        query = query.filter(Notification.is_read.is_(False))
    if reference_id:
        query = query.filter(Notification.reference_id == reference_id)
    if notif_type:
        query = query.filter(Notification.type == notif_type)

    total = query.count()
    items = (
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "items": [
            NotificationResponse(
                id=item.id,
                title=item.title,
                body=item.body,
                type=item.type,
                role_target=item.role_target,
                reference_id=item.reference_id,
                is_read=item.is_read,
                created_at=item.created_at,
            )
            for item in items
        ],
    }


@router.post("/read", response_model=NotificationListResponse)
def mark_notifications_read(
    payload: NotificationReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    reference_ids = _clean_reference_ids(payload.reference_ids)
    ids = [i for i in payload.notification_ids if i]

    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if payload.mark_all:
        query.update({Notification.is_read: True}, synchronize_session=False)
    else:
        if ids:
            query = query.filter(Notification.id.in_(ids))
        if reference_ids:
            query = query.filter(Notification.reference_id.in_(reference_ids))
        query.update({Notification.is_read: True}, synchronize_session=False)

    db.commit()

    refreshed = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(50)
        .all()
    )
    return {
        "total": len(refreshed),
        "items": [
            NotificationResponse(
                id=item.id,
                title=item.title,
                body=item.body,
                type=item.type,
                role_target=item.role_target,
                reference_id=item.reference_id,
                is_read=item.is_read,
                created_at=item.created_at,
            )
            for item in refreshed
        ],
    }
