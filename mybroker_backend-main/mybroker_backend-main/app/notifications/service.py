from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.notifications.models import Notification
from app.services.fcm_service import send_notification
from app.users.model import User

logger = logging.getLogger(__name__)
NON_UNIQUE_NOTIFICATION_TYPES = {
    "OFFER_RECEIVED",
    "BUYER_OFFER_ACCEPTED",
    "BUYER_OFFER_REJECTED",
    "BUYER_COUNTER_RECEIVED",
    "BUYER_COUNTER_REJECTED",
    "LISTING_LOCKED_FOR_ADMIN",
    "SELLER_COUNTER_ACCEPTED",
    "REGISTRY_SCHEDULED",
    "REGISTRY_IN_PROCESS",
    "REGISTRY_DONE",
    "REGISTRY_SOLD",
}


def _unique_notification_exists(
    db: Session,
    user_id: int,
    reference_id: str | None,
    notif_type: str,
) -> bool:
    if notif_type in NON_UNIQUE_NOTIFICATION_TYPES:
        return False
    return (
        db.query(Notification.id)
        .filter(
            Notification.user_id == user_id,
            Notification.reference_id == reference_id,
            Notification.type == notif_type,
        )
        .first()
        is not None
    )


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    body: str,
    notif_type: str,
    role_target: str | None = None,
    reference_id: str | None = None,
) -> Notification | None:
    if notif_type in NON_UNIQUE_NOTIFICATION_TYPES:
        existing = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.reference_id == reference_id,
                Notification.type == notif_type,
            )
            .first()
        )
        if existing is not None:
            existing.title = title
            existing.body = body
            existing.role_target = role_target
            existing.is_read = False
            existing.created_at = datetime.utcnow()
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                return None
            return existing

    if _unique_notification_exists(db, user_id, reference_id, notif_type):
        return None

    item = Notification(
        user_id=user_id,
        title=title,
        body=body,
        type=notif_type,
        role_target=role_target,
        reference_id=reference_id,
        is_read=False,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return None
    return item


def notify_users(
    db: Session,
    users: Iterable[User],
    title: str,
    body: str,
    notif_type: str,
    role_target: str | None = None,
    reference_id: str | None = None,
    extra_data: dict[str, str] | None = None,
) -> list[Notification]:
    created: list[Notification] = []
    for user in users:
        item = create_notification(
            db=db,
            user_id=user.id,
            title=title,
            body=body,
            notif_type=notif_type,
            role_target=role_target or user.role,
            reference_id=reference_id,
        )
        if item is None:
            continue
        created.append(item)
    if created:
        db.commit()
    else:
        return created

    for item in created:
        user = next((u for u in users if u.id == item.user_id), None)
        if not user:
            continue
        data = {
            "notification_id": str(item.id),
            "type": item.type,
            "role_target": item.role_target or "",
            "reference_id": item.reference_id or "",
            "title": item.title,
            "body": item.body,
        }
        if extra_data:
            data.update(extra_data)
        send_notification(
            token=(user.fcm_token or "").strip(),
            title=item.title,
            body=item.body,
            data=data,
        )
    return created
