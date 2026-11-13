from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.settings.schemas import (
    BannerDeleteResponse,
    BannerResponse,
    ProcessingFeeSettingsResponse,
    ProcessingFeeSettingsUpdateRequest,
    SocialLinksResponse,
    SocialLinksUpdateRequest,
)
from app.settings.service import (
    create_banner_from_upload,
    get_banners,
    get_or_create_links,
    get_or_create_processing_fees,
    remove_banner,
    update_links,
    update_processing_fees,
)
from app.users.model import User
from app.users.roles import UserRole

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/social-links", response_model=SocialLinksResponse)
def get_social_links_endpoint(
    db: Session = Depends(get_db),
):
    return get_or_create_links(db)


@router.put("/social-links", response_model=SocialLinksResponse)
def update_social_links_endpoint(
    payload: SocialLinksUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    return update_links(db, payload)


@router.get("/banners", response_model=list[BannerResponse])
def list_banners_endpoint(
    db: Session = Depends(get_db),
):
    return get_banners(db)


@router.post("/banners", response_model=BannerResponse)
def upload_banner_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    try:
        return create_banner_from_upload(db, file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/banners/{banner_id}", response_model=BannerDeleteResponse)
def delete_banner_endpoint(
    banner_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    if not remove_banner(db, banner_id):
        raise HTTPException(status_code=404, detail="Banner not found")
    return BannerDeleteResponse(status="deleted")


@router.get("/processing-fees", response_model=ProcessingFeeSettingsResponse)
def get_processing_fees_endpoint(
    db: Session = Depends(get_db),
):
    return get_or_create_processing_fees(db)


@router.put("/processing-fees", response_model=ProcessingFeeSettingsResponse)
def update_processing_fees_endpoint(
    payload: ProcessingFeeSettingsUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    return update_processing_fees(db, payload)
