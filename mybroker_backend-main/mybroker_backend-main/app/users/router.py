import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user, get_db
from app.users.model import User
from app.users.schemas import FcmTokenRequest, ProfilePhotoResponse, UpdateProfileRequest, UserProfileResponse
from app.users.service import (
    get_profile_by_user_id,
    update_fcm_token,
    update_profile_by_user_id,
    update_profile_photo_by_user_id,
)

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)


@router.get("/me/profile", response_model=UserProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    user = get_profile_by_user_id(db, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/me/profile", response_model=UserProfileResponse)
def update_my_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    user, error = update_profile_by_user_id(db, current_user.id, payload)
    if error == "Email, username, or mobile already in use":
        raise HTTPException(status_code=409, detail=error)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/me/profile-photo", response_model=ProfilePhotoResponse)
def upload_my_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    user, error = update_profile_photo_by_user_id(db, current_user.id, file)
    if error == "User not found":
        raise HTTPException(status_code=404, detail=error)
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "status": "Profile photo updated",
        "profile_image_url": user.profile_image_url,
    }


@router.post("/me/fcm-token")
def register_fcm_token(
    payload: FcmTokenRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    token = payload.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="FCM token is required")

    logger.info("Saving FCM token for user_id=%s", current_user.id)
    _, error = update_fcm_token(db, current_user.id, token)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return {"status": "ok"}
