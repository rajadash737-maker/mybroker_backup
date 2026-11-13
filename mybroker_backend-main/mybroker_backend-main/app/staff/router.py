import os
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.staff.schemas import (
    BootstrapSuperAdminRequest,
    CreateStaffRequest,
    DeleteStaffResponse,
    ResetStaffPasswordRequest,
    ResetStaffPasswordResponse,
    StaffActionResponse,
    StaffCreateResponse,
    StaffResponse,
    StaffAnalyticsResponse,
    ToggleStaffActiveRequest,
    UpdateStaffRequest,
)
from app.staff.service import (
    bootstrap_super_admin,
    create_staff,
    get_staff_analytics,
    delete_staff,
    list_staff,
    reset_staff_password,
    toggle_staff_active,
    update_staff,
)
from app.users.model import User
from app.users.roles import UserRole

router = APIRouter(prefix="/admin/staff", tags=["Admin Staff"])


@router.post("", response_model=StaffCreateResponse, status_code=status.HTTP_201_CREATED)
def create_staff_user(
    payload: CreateStaffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    staff, error = create_staff(db, current_user, payload)
    if error == "You are not allowed to assign this role":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
    if error == "CUSTOMER role cannot be created from admin panel":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return {"status": "Staff created successfully", "staff": staff}


@router.get("", response_model=list[StaffResponse])
def list_staff_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return list_staff(db)


@router.get("/analytics", response_model=StaffAnalyticsResponse)
def staff_analytics(
    role: str | None = Query(default=None),
    range: str | None = Query(default="today"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    try:
        return get_staff_analytics(
            db=db,
            role=role,
            range_key=range,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{staff_id}", response_model=StaffActionResponse)
def update_staff_user(
    staff_id: int,
    payload: UpdateStaffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    staff, error = update_staff(db, current_user, staff_id, payload)
    if error == "Staff not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "You are not allowed to assign this role":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
    if error == "You are not allowed to update this staff":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return {"status": "Staff updated successfully", "staff": staff}


@router.patch("/{staff_id}/active", response_model=StaffActionResponse)
def toggle_staff_user_active(
    staff_id: int,
    payload: ToggleStaffActiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    staff, error = toggle_staff_active(db, current_user, staff_id, payload.is_active)
    if error == "Staff not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {"You cannot change your own active status", "You are not allowed to update this staff"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return {"status": "Staff active status updated", "staff": staff}


@router.delete("/{staff_id}", response_model=DeleteStaffResponse)
def delete_staff_user(
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    error = delete_staff(db, current_user, staff_id)
    if error == "Staff not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {"You cannot delete your own account", "You are not allowed to delete this staff"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return {"status": "Staff deleted successfully"}


@router.put("/{staff_id}/reset-password", response_model=ResetStaffPasswordResponse)
def reset_staff_user_password(
    staff_id: int,
    payload: ResetStaffPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    error = reset_staff_password(db, current_user, staff_id, payload.new_password)
    if error == "Staff not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Only super admin can reset staff passwords":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return {"status": "Password reset successfully"}


@router.post("/bootstrap-super-admin", response_model=StaffCreateResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_first_super_admin(
    payload: BootstrapSuperAdminRequest,
    setup_key: str | None = Header(default=None, alias="X-Setup-Key"),
    db: Session = Depends(get_db),
):
    expected = os.getenv("ADMIN_SETUP_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ADMIN_SETUP_KEY is not configured")
    if setup_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid setup key")

    staff, error = bootstrap_super_admin(db, payload)
    if error == "Super admin already exists":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return {"status": "Super admin bootstrapped successfully", "staff": staff}
