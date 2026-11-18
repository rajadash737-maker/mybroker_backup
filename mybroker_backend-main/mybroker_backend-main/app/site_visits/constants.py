from enum import Enum
from datetime import datetime, timedelta, timezone


SITE_VISIT_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


def site_visit_today():
    return datetime.now(SITE_VISIT_TIMEZONE).date()


class SiteVisitStatus(str, Enum):
    PENDING_PAYMENT = "pending_payment"
    PENDING = "pending"
    ASSIGNED = "assigned"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CORRECTION_REQUIRED = "correction_required"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    REFUND_FAILED = "refund_failed"


class AssignmentAction(str, Enum):
    ASSIGNED = "assigned"
    REASSIGNED = "reassigned"
    UNASSIGNED = "unassigned"


class AssignmentActorType(str, Enum):
    SYSTEM = "system"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
