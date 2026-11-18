from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

from sqlalchemy import update
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
    "SITE_VISIT_ASSIGNED",
    "SITE_VISIT_ASSIGNMENT_REMOVED",
    "SITE_VISIT_COMPLETION_CODE_READY",
    "SITE_VISIT_COMPLETED",
}


def _clear_unregistered_fcm_token(db: Session, *, user_id: int, token: str) -> bool:
    """Clear only the exact token that failed for this exact user."""
    if not token:
        return False
    try:
        result = db.execute(
            update(User)
            .where(User.id == user_id, User.fcm_token == token)
            .values(fcm_token=None)
        )
        cleared = result.rowcount == 1
        if cleared:
            db.commit()
            logger.info("Cleared unregistered FCM token for user_id=%s", user_id)
        else:
            db.rollback()
        return cleared
    except Exception as exc:  # noqa: BLE001 - delivery cleanup must not fail notification flow
        db.rollback()
        logger.warning(
            "Could not clear unregistered FCM token for user_id=%s (%s)",
            user_id,
            type(exc).__name__,
        )
        return False


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
    recipient_users = list(users)
    users_by_id = {user.id: user for user in recipient_users}
    created: list[Notification] = []
    for user in recipient_users:
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
        user = users_by_id.get(item.user_id)
        if not user:
            continue
        token = (user.fcm_token or "").strip()
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
        if item.type.startswith("SITE_VISIT_") and item.reference_id:
            role = (item.role_target or "").lower()
            if role == "customer":
                destination = "my_site_visits"
            elif role == "field_officer":
                destination = "field_site_visits"
            elif role == "accounting":
                destination = "accounting_site_visit_refunds"
            elif role == "super_admin":
                destination = f"super_admin_site_visit_audit/{item.reference_id}"
            else:
                destination = f"site_visit_admin_detail/{item.reference_id}"
            data["deep_link"] = (extra_data or {}).get("deep_link") or destination
        send_result = send_notification(
            token=token,
            title=item.title,
            body=item.body,
            data=data,
        )
        if send_result.get("error") == "unregistered":
            _clear_unregistered_fcm_token(db, user_id=user.id, token=token)
    return created
