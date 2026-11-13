from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.schemas import (
    AuthResponseSchema,
    ChangePasswordResponseSchema,
    ChangePasswordSchema,
    LoginSchema,
    LogoutRequestSchema,
    RefreshTokenRequestSchema,
    ResetPasswordSchema,
    SendOtpSchema,
    SignupSchema,
    FirebaseTokenSchema,
    GoogleAuthRequestSchema,
    VerifyOtpSchema,
)
from app.auth.service import (
    build_auth_identity,
    change_password_user,
    login_user,
    logout_user,
    refresh_tokens,
    reset_password_user,
    send_otp,
    signup_user,
    firebase_health_check,
    verify_firebase_token,
    verify_otp,
    google_login_user,
)
from app.core.dependencies import get_current_active_user, get_db
from app.users.model import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup")
def signup(data: SignupSchema, db: Session = Depends(get_db)):
    return signup_user(db, data)


@router.post("/send-otp")
def send_otp_route(data: SendOtpSchema, db: Session = Depends(get_db)):
    return send_otp(db, data.mobile, data.purpose)


@router.post("/verify-otp")
def verify_otp_route(data: VerifyOtpSchema, db: Session = Depends(get_db)):
    return verify_otp(db, data.mobile, data.otp, data.purpose)

@router.post("/firebase/verify")
def verify_firebase_route(data: FirebaseTokenSchema, db: Session = Depends(get_db)):
    return verify_firebase_token(db, data.id_token, data.mobile, data.purpose)

@router.get("/firebase/health")
def firebase_health():
    return firebase_health_check()


@router.post("/login", response_model=AuthResponseSchema)
def login(data: LoginSchema, request: Request, db: Session = Depends(get_db)):
    return login_user(db, data, request.client.host if request.client else None, request.headers.get("user-agent"))


@router.post("/google", response_model=AuthResponseSchema)
def google_login(data: GoogleAuthRequestSchema, request: Request, db: Session = Depends(get_db)):
    return google_login_user(
        db,
        data.id_token,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@router.post("/refresh", response_model=AuthResponseSchema)
def refresh(data: RefreshTokenRequestSchema, request: Request, db: Session = Depends(get_db)):
    return refresh_tokens(
        db,
        data.refresh_token,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@router.post("/logout")
def logout(data: LogoutRequestSchema, db: Session = Depends(get_db)):
    return logout_user(db, data.refresh_token)


@router.post("/reset-password")
def reset_password(data: ResetPasswordSchema, db: Session = Depends(get_db)):
    return reset_password_user(db, data.mobile, data.password, data.confirm)


@router.post("/change-password", response_model=ChangePasswordResponseSchema)
def change_password(
    data: ChangePasswordSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return change_password_user(
        db=db,
        user=current_user,
        role=data.role,
        email=data.email,
        old_password=data.old_password,
        new_password=data.new_password,
    )


@router.get("/me", response_model=AuthResponseSchema)
def auth_me(current_user: User = Depends(get_current_active_user)):
    return build_auth_identity(current_user)
