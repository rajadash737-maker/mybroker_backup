import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.notifications.service import notify_users
from app.users.model import User
from app.users.roles import UserRole

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_users_by_roles(self, roles: list[str]) -> list[User]:
        if not roles:
            return []
        role_values = [r.strip().lower() for r in roles if r and r.strip()]
        if not role_values:
            return []
        return (
            self.db.query(User)
            .filter(func.lower(User.role).in_(role_values))
            .filter(User.is_active.is_(True))
            .all()
        )

    def notify_property_uploaded(self, property_id: int) -> dict[str, Any]:
        recipients = self._get_users_by_roles(
            [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value, UserRole.ACCOUNTING.value]
        )

        logger.info(
            "Property upload notification triggered for property_id=%s, recipients=%s",
            property_id,
            [u.id for u in recipients],
        )

        created = notify_users(
            db=self.db,
            users=recipients,
            title="New Property Uploaded",
            body="A new property needs verification",
            notif_type="LAND_SUBMITTED",
            role_target=None,
            reference_id=str(property_id),
        )

        return {"requested": len(recipients), "created": len(created)}
