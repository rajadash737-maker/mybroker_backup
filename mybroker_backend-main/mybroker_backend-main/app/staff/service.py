import re
import secrets
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.service import pwd_context
from app.models.otp import RefreshToken
from app.sell_land.constants import BookingStatus, SellLandStatus
from app.sell_land.models import SellLandBooking, SellLandRequest
from app.users.model import User
from app.users.roles import UserRole


def _sanitize_username(value: str) -> str:
    username = re.sub(r"[^a-zA-Z0-9_.]", "", value.strip().lower())
    return username[:50]


def _username_exists(db: Session, username: str) -> bool:
    return db.query(User).filter(User.username == username).first() is not None


def _generate_unique_username(db: Session, fullname: str, email: str, preferred: str | None = None) -> str:
    candidate = _sanitize_username(preferred or "")
    if not candidate:
        candidate = _sanitize_username(email.split("@")[0]) or _sanitize_username(fullname.replace(" ", ".")) or "staff"

    if not _username_exists(db, candidate):
        return candidate

    for i in range(1, 1000):
        option = f"{candidate}{i}"
        if not _username_exists(db, option):
            return option

    return f"staff{secrets.randbelow(10_000_000):07d}"


def can_assign_role(actor_role: str, requested_role: UserRole) -> bool:
    if actor_role == UserRole.SUPER_ADMIN.value:
        return True
    if actor_role == UserRole.ADMIN.value:
        return requested_role in {UserRole.FIELD_OFFICER, UserRole.ACCOUNTING}
    return False


def create_staff(db: Session, actor: User, payload) -> tuple[User | None, str | None]:
    if payload.role == UserRole.CUSTOMER:
        return None, "CUSTOMER role cannot be created from admin panel"

    if not can_assign_role(actor.role, payload.role):
        return None, "You are not allowed to assign this role"

    desired_username = _generate_unique_username(db, payload.fullname, payload.email, payload.username)
    checks = [User.email == payload.email, User.username == desired_username]
    if payload.mobile is not None:
        checks.append(User.mobile == payload.mobile)

    existing = db.query(User).filter(or_(*checks)).first()
    if existing:
        return None, "Email, username, or mobile already in use"

    user = User(
        fullname=payload.fullname.strip(),
        email=payload.email,
        username=desired_username,
        mobile=payload.mobile,
        password_hash=pwd_context.hash(payload.password),
        role=payload.role.value,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None, "Email, username, or mobile already in use"
    db.refresh(user)
    return user, None


def list_staff(db: Session):
    return (
        db.query(User)
        .filter(User.role != UserRole.CUSTOMER.value)
        .order_by(User.id.desc())
        .all()
    )


def get_staff_by_id(db: Session, staff_id: int) -> User | None:
    return (
        db.query(User)
        .filter(User.id == staff_id, User.role != UserRole.CUSTOMER.value)
        .first()
    )


def _can_manage_target(actor: User, target: User) -> bool:
    actor_role = actor.role
    if actor_role == UserRole.SUPER_ADMIN.value:
        return True
    if actor_role == UserRole.ADMIN.value:
        return target.role in {UserRole.FIELD_OFFICER.value, UserRole.ACCOUNTING.value}
    return False


def update_staff(db: Session, actor: User, staff_id: int, payload) -> tuple[User | None, str | None]:
    target = get_staff_by_id(db, staff_id)
    if not target:
        return None, "Staff not found"

    if not _can_manage_target(actor, target):
        return None, "You are not allowed to update this staff"

    if not can_assign_role(actor.role, payload.role):
        return None, "You are not allowed to assign this role"

    updated_email = str(payload.email).strip().lower()
    email_in_use = (
        db.query(User)
        .filter(User.email == updated_email, User.id != target.id)
        .first()
    )
    if email_in_use:
        return None, "Email already in use"

    target.fullname = payload.fullname.strip()
    target.email = updated_email
    target.role = payload.role.value

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None, "Failed to update staff"
    db.refresh(target)
    return target, None


def toggle_staff_active(db: Session, actor: User, staff_id: int, is_active: bool) -> tuple[User | None, str | None]:
    target = get_staff_by_id(db, staff_id)
    if not target:
        return None, "Staff not found"

    if actor.id == target.id:
        return None, "You cannot change your own active status"

    if not _can_manage_target(actor, target):
        return None, "You are not allowed to update this staff"

    target.is_active = is_active
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None, "Failed to update staff"
    db.refresh(target)
    return target, None


def delete_staff(db: Session, actor: User, staff_id: int) -> str | None:
    target = get_staff_by_id(db, staff_id)
    if not target:
        return "Staff not found"

    if actor.id == target.id:
        return "You cannot delete your own account"

    if not _can_manage_target(actor, target):
        return "You are not allowed to delete this staff"

    linked_requests = db.query(SellLandRequest.id).filter(SellLandRequest.user_id == target.id).first()
    if linked_requests:
        return "Cannot delete this staff because related records exist"

    db.query(RefreshToken).filter(RefreshToken.user_id == target.id).delete(synchronize_session=False)
    db.delete(target)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return "Cannot delete this staff because related records exist"
    return None


def reset_staff_password(db: Session, actor: User, staff_id: int, new_password: str) -> str | None:
    target = get_staff_by_id(db, staff_id)
    if not target:
        return "Staff not found"

    if actor.role != UserRole.SUPER_ADMIN.value:
        return "Only super admin can reset staff passwords"

    target.password_hash = pwd_context.hash(new_password)
    db.commit()
    return None


def has_any_admin_staff(db: Session) -> bool:
    return (
        db.query(User)
        .filter(User.role.in_([UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]))
        .first()
        is not None
    )


def _normalize_role_filter(role: str | None) -> str | None:
    if role is None:
        return None
    normalized = role.strip().lower()
    if normalized in {"admin", "field_officer"}:
        return normalized
    return None


def _resolve_date_range(
    range_key: str | None,
    start_date: date | None,
    end_date: date | None,
) -> tuple[datetime | None, datetime | None, date | None, date | None]:
    if range_key is None:
        range_key = "today"
    key = range_key.strip().lower()
    if key in {"all", ""}:
        return None, None, None, None

    today = datetime.utcnow().date()

    if key == "today":
        start = today
        end = today
    elif key == "week":
        start = today - timedelta(days=6)
        end = today
    elif key == "month":
        start = today.replace(day=1)
        end = today
    elif key == "custom":
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required for custom range")
        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")
        start = start_date
        end = end_date
    else:
        raise ValueError("Invalid range value")

    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end + timedelta(days=1), time.min)
    return start_dt, end_dt, start, end


def get_staff_analytics(
    db: Session,
    role: str | None,
    range_key: str | None,
    start_date: date | None,
    end_date: date | None,
) -> dict:
    role_filter = _normalize_role_filter(role)
    start_dt, end_dt, start_day, end_day = _resolve_date_range(range_key, start_date, end_date)

    if role_filter == "admin":
        roles = [UserRole.ADMIN.value]
    elif role_filter == "field_officer":
        roles = [UserRole.FIELD_OFFICER.value]
    else:
        roles = [UserRole.ADMIN.value, UserRole.FIELD_OFFICER.value]

    staff = (
        db.query(User)
        .filter(User.role.in_(roles))
        .order_by(User.fullname.asc(), User.id.asc())
        .all()
    )

    admin_ids = [user.id for user in staff if user.role == UserRole.ADMIN.value]
    officer_ids = [user.id for user in staff if user.role == UserRole.FIELD_OFFICER.value]

    def _apply_datetime_range(query, column):
        if start_dt is None or end_dt is None:
            return query
        return query.filter(column.is_not(None), column >= start_dt, column < end_dt)

    def _apply_date_range(query, column):
        if start_day is None or end_day is None:
            return query
        return query.filter(column.is_not(None), column >= start_day, column <= end_day)

    admin_verified: dict[int, int] = {}
    admin_rejected: dict[int, int] = {}
    admin_live: dict[int, int] = {}
    admin_registry: dict[int, int] = {}
    admin_sold: dict[int, int] = {}

    if admin_ids:
        query = db.query(
            SellLandRequest.reviewed_by_id,
            func.count(SellLandRequest.id),
        ).filter(
            SellLandRequest.reviewed_by_id.in_(admin_ids),
            SellLandRequest.status != SellLandStatus.REJECTED.value,
        )
        query = _apply_datetime_range(query, SellLandRequest.reviewed_at)
        admin_verified = {int(row[0]): int(row[1]) for row in query.group_by(SellLandRequest.reviewed_by_id).all()}

        query = db.query(
            SellLandRequest.reviewed_by_id,
            func.count(SellLandRequest.id),
        ).filter(
            SellLandRequest.reviewed_by_id.in_(admin_ids),
            SellLandRequest.status == SellLandStatus.REJECTED.value,
        )
        query = _apply_datetime_range(query, SellLandRequest.reviewed_at)
        admin_rejected = {int(row[0]): int(row[1]) for row in query.group_by(SellLandRequest.reviewed_by_id).all()}

        query = db.query(
            SellLandRequest.reviewed_by_id,
            func.count(SellLandRequest.id),
        ).filter(
            SellLandRequest.reviewed_by_id.in_(admin_ids),
            SellLandRequest.status == SellLandStatus.LIVE.value,
        )
        query = _apply_datetime_range(query, SellLandRequest.updated_at)
        admin_live = {int(row[0]): int(row[1]) for row in query.group_by(SellLandRequest.reviewed_by_id).all()}

        query = (
            db.query(
                SellLandRequest.reviewed_by_id,
                func.count(SellLandBooking.id),
            )
            .join(SellLandRequest, SellLandRequest.id == SellLandBooking.request_id)
            .filter(
                SellLandRequest.reviewed_by_id.in_(admin_ids),
                SellLandBooking.booking_status == BookingStatus.SOLD.value,
            )
        )
        query = _apply_date_range(query, SellLandBooking.registry_date)
        admin_registry = {int(row[0]): int(row[1]) for row in query.group_by(SellLandRequest.reviewed_by_id).all()}

        query = db.query(
            SellLandRequest.reviewed_by_id,
            func.count(SellLandRequest.id),
        ).filter(
            SellLandRequest.reviewed_by_id.in_(admin_ids),
            SellLandRequest.status == SellLandStatus.SOLD.value,
        )
        query = _apply_datetime_range(query, SellLandRequest.updated_at)
        admin_sold = {int(row[0]): int(row[1]) for row in query.group_by(SellLandRequest.reviewed_by_id).all()}

    officer_visits: dict[int, int] = {}
    officer_registry: dict[int, int] = {}
    if officer_ids:
        query = db.query(
            SellLandRequest.field_officer_reviewed_by_id,
            func.count(SellLandRequest.id),
        ).filter(
            SellLandRequest.field_officer_reviewed_by_id.in_(officer_ids),
            SellLandRequest.field_officer_reviewed_at.is_not(None),
        )
        query = _apply_datetime_range(query, SellLandRequest.field_officer_reviewed_at)
        officer_visits = {
            int(row[0]): int(row[1])
            for row in query.group_by(SellLandRequest.field_officer_reviewed_by_id).all()
        }

        query = db.query(
            SellLandBooking.assigned_field_officer_id,
            func.count(SellLandBooking.id),
        ).filter(
            SellLandBooking.assigned_field_officer_id.in_(officer_ids),
            SellLandBooking.booking_status.in_(
                [BookingStatus.REGISTRY_DONE.value, BookingStatus.SOLD.value]
            ),
        )
        query = _apply_date_range(query, SellLandBooking.registry_date)
        officer_registry = {
            int(row[0]): int(row[1])
            for row in query.group_by(SellLandBooking.assigned_field_officer_id).all()
        }

    staff_items = []
    for user in staff:
        if user.role == UserRole.ADMIN.value:
            staff_items.append(
                {
                    "id": user.id,
                    "name": user.fullname,
                    "mobile": user.mobile,
                    "role": user.role.lower(),
                    "documents_verified": admin_verified.get(user.id, 0),
                    "documents_rejected": admin_rejected.get(user.id, 0),
                    "listings_approved": admin_live.get(user.id, 0),
                    "registry_approved": admin_registry.get(user.id, 0),
                    "sold_count": admin_sold.get(user.id, 0),
                }
            )
        elif user.role == UserRole.FIELD_OFFICER.value:
            staff_items.append(
                {
                    "id": user.id,
                    "name": user.fullname,
                    "mobile": user.mobile,
                    "role": user.role.lower(),
                    "site_visits": officer_visits.get(user.id, 0),
                    "registry_visits": officer_registry.get(user.id, 0),
                }
            )

    summary = {
        "total_staff": len(staff),
        "total_visits": sum(officer_visits.values()),
        "total_verified_docs": sum(admin_verified.values()),
        "total_rejected_docs": sum(admin_rejected.values()),
    }

    return {
        "summary": summary,
        "staff": staff_items,
    }


def bootstrap_super_admin(db: Session, payload) -> tuple[User | None, str | None]:
    if has_any_admin_staff(db):
        return None, "Super admin already exists"

    desired_username = _generate_unique_username(db, payload.fullname, payload.email, payload.username)
    checks = [User.email == payload.email, User.username == desired_username]
    if payload.mobile is not None:
        checks.append(User.mobile == payload.mobile)

    existing = db.query(User).filter(or_(*checks)).first()
    if existing:
        return None, "Email, username, or mobile already in use"

    user = User(
        fullname=payload.fullname.strip(),
        email=payload.email,
        username=desired_username,
        mobile=payload.mobile,
        password_hash=pwd_context.hash(payload.password),
        role=UserRole.SUPER_ADMIN.value,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None, "Email, username, or mobile already in use"
    db.refresh(user)
    return user, None
