from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.sell_land.field_officer_schemas import (
    FieldOfficerAvailableCaseListResponse,
    FieldOfficerCaseActionResponse,
    FieldOfficerCaseDetailResponse,
    FieldOfficerDashboardResponse,
    FieldOfficerReviewActionRequest,
    FieldOfficerReviewActionResponse,
    FieldOfficerVisitPhotoUploadResponse,
    FieldOfficerRegistryCompleteResponse,
    FieldOfficerRegistryProofUploadResponse,
    FieldOfficerRegistryAssignmentListResponse,
    FieldOfficerRegistryAssignmentDetailResponse,
)
from app.sell_land.field_officer_service import (
    claim_case,
    get_case_review_detail,
    get_field_officer_dashboard,
    list_available_cases,
    review_case,
    release_case,
    upload_visit_photo,
    complete_registry,
    list_registry_assignments,
    get_registry_assignment_detail,
    start_registry_visit,
    upload_registry_proofs,
)
from app.users.model import User
from app.users.roles import UserRole

router = APIRouter(prefix="/field-officer/sell-land", tags=["Field Officer Sell Land"])


@router.get("/dashboard", response_model=FieldOfficerDashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    return get_field_officer_dashboard(db, current_user)


@router.get("/cases/available", response_model=FieldOfficerAvailableCaseListResponse)
def get_available_cases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    return list_available_cases(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.post("/cases/{request_id}/claim", response_model=FieldOfficerCaseActionResponse)
def claim_available_case(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    response, error = claim_case(
        db=db,
        current_user=current_user,
        request_id=request_id,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only approved listings can be claimed",
        "You already have an active locked case",
        "Case is already locked by another field officer",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/cases/{request_id}/release", response_model=FieldOfficerCaseActionResponse)
def release_claimed_case(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    response, error = release_case(
        db=db,
        current_user=current_user,
        request_id=request_id,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only approved listings can be released",
        "You can only release your own locked case",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/cases/{request_id}", response_model=FieldOfficerCaseDetailResponse)
def get_case_detail(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    response, error = get_case_review_detail(
        db=db,
        current_user=current_user,
        request_id=request_id,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only approved listings can be reviewed by field officer",
        "You can only review your own locked case",
        "Case lock has expired",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/cases/{request_id}/visit-photo", response_model=FieldOfficerVisitPhotoUploadResponse)
def upload_case_visit_photo(
    request_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    response, error = upload_visit_photo(
        db=db,
        current_user=current_user,
        request_id=request_id,
        file=file,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only approved listings can be reviewed by field officer",
        "You can only review your own locked case",
        "Case lock has expired",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.patch("/cases/{request_id}/review", response_model=FieldOfficerReviewActionResponse)
def review_claimed_case(
    request_id: int,
    payload: FieldOfficerReviewActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    response, error = review_case(
        db=db,
        current_user=current_user,
        request_id=request_id,
        payload=payload,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only approved listings can be reviewed by field officer",
        "You can only review your own locked case",
        "Case lock has expired",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error in {
        "Visit photo is required before review decision",
        "rejection_reason is required when decision is rejected",
    }:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/bookings/{booking_id}/registry-complete", response_model=FieldOfficerRegistryCompleteResponse)
def mark_registry_completed(
    booking_id: int,
    files: list[UploadFile] | None = File(default=None),
    file: UploadFile | None = File(default=None),
    notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    final_files = files or ([file] if file else None)
    response, error = complete_registry(
        db=db,
        current_user=current_user,
        booking_id=booking_id,
        files=final_files,
        notes=notes,
    )
    if error in {"Booking not found", "Sell land request not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "You can only complete registry for your assigned booking",
        "Registry is not scheduled",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.patch("/registry/assignments/{booking_id}/complete", response_model=FieldOfficerRegistryCompleteResponse)
def complete_registry_assignment_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    response, error = complete_registry(
        db=db,
        current_user=current_user,
        booking_id=booking_id,
        files=None,
        notes=None,
    )
    if error in {"Booking not found", "Sell land request not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "You can only complete registry for your assigned booking",
        "Registry is not scheduled",
        "Registry proof is required before completion",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/registry/assignments", response_model=FieldOfficerRegistryAssignmentListResponse)
def list_registry_assignments_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    return list_registry_assignments(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get("/registry/assignments/{booking_id}", response_model=FieldOfficerRegistryAssignmentDetailResponse)
def get_registry_assignment_detail_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    response, error = get_registry_assignment_detail(
        db=db,
        current_user=current_user,
        booking_id=booking_id,
    )
    if error == "Booking not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {"You can only view registry assigned to you"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.patch("/registry/assignments/{booking_id}/start", response_model=FieldOfficerRegistryAssignmentDetailResponse)
def start_registry_visit_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    response, error = start_registry_visit(
        db=db,
        current_user=current_user,
        booking_id=booking_id,
    )
    if error in {"Booking not found", "Sell land request not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "You can only start registry for your assigned booking",
        "Registry is not scheduled",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post(
    "/registry/assignments/{booking_id}/proofs",
    response_model=FieldOfficerRegistryProofUploadResponse,
)
def upload_registry_proofs_endpoint(
    booking_id: int,
    files: list[UploadFile] = File(...),
    notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.FIELD_OFFICER)),
):
    response, error = upload_registry_proofs(
        db=db,
        current_user=current_user,
        booking_id=booking_id,
        files=files,
        notes=notes,
    )
    if error in {"Booking not found", "Sell land request not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "You can only upload proof for your assigned booking",
        "Registry is not in progress",
        "No files uploaded",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response
