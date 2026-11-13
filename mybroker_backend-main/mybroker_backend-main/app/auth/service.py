from datetime import datetime, timedelta
import logging
import os
import re
import secrets
import json
import hashlib
import hmac

import requests
from jwt import InvalidTokenError
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt_utils import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    refresh_token_expiry,
    JWT_SECRET_KEY,
)
from app.models.otp import Otp, RefreshToken
from app.auth.google_identity import verify_google_id_token
from app.users.model import User
from app.users.profile_image import resolve_profile_image_url
from app.users.roles import ROLE_DASHBOARD, UserRole

OTP_SEND_LIMIT = int(os.getenv("OTP_SEND_LIMIT", "3"))
OTP_RATE_WINDOW_SECONDS = int(os.getenv("OTP_RATE_WINDOW_SECONDS", "900"))
OTP_MAX_VERIFY_ATTEMPTS = int(os.getenv("OTP_MAX_VERIFY_ATTEMPTS", "5"))
PASSWORD_RESET_OTP_PURPOSE = "password_reset"


def _otp_digest(value: str) -> str:
    pepper = os.getenv("OTP_HASH_SECRET") or JWT_SECRET_KEY
    return hmac.new(pepper.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")
logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 5
MSG91_TEMPLATE_ID = os.getenv("MSG91_TEMPLATE_ID")
MSG91_AUTH_KEY = os.getenv("MSG91_AUTH_KEY")
MSG91_SENDER_ID = os.getenv("MSG91_SENDER_ID", "MYBROKER")
MSG91_OTP_ENDPOINT = "https://control.msg91.com/api/v5/otp"
MSG91_VERIFY_ENDPOINT = "https://control.msg91.com/api/v5/otp/verify"
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials
    except Exception:
        logger.exception("firebase-admin is not installed")
        return None

    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app

    cred = None
    if FIREBASE_CREDENTIALS_JSON:
        try:
            cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS_JSON))
        except Exception:
            logger.exception("Invalid FIREBASE_CREDENTIALS_JSON")
            return None
    elif FIREBASE_CREDENTIALS_PATH:
        try:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        except Exception:
            logger.exception("Invalid FIREBASE_CREDENTIALS_PATH")
            return None
    else:
        try:
            cred = credentials.ApplicationDefault()
        except Exception:
            logger.exception("Firebase application default credentials not available")
            return None

    _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def _utcnow() -> datetime:
    return datetime.utcnow()


def _generate_otp():
    return f"{secrets.randbelow(1000000):06d}"


def _msg91_is_success(resp):
    if resp is None:
        return False, "No response from MSG91"
    try:
        data = resp.json()
    except ValueError:
        if resp.status_code == 200:
            return True, None
        return False, "MSG91 request failed"

    msg = None
    if isinstance(data, dict):
        msg = data.get("message") or data.get("details") or data.get("errors")
        status = data.get("type") or data.get("status")
        if isinstance(status, str) and status.lower() in ("success", "ok"):
            return True, None
        if status is True or status == 200:
            return True, None

    if resp.status_code == 200:
        return True, None
    return False, str(msg) if msg else "MSG91 request failed"


def _normalize_mobile(mobile: str) -> str:
    m = mobile.strip().lstrip("+")
    if len(m) == 10:
        m = f"91{m}"
    return m


def _sanitize_username(value: str) -> str:
    username = re.sub(r"[^a-zA-Z0-9_.]", "", value.strip().lower())
    return username[:50]


def _username_exists(db: Session, username: str) -> bool:
    return db.query(User).filter(User.username == username).first() is not None


def _generate_unique_username(db: Session, fullname: str, email: str, preferred: str | None = None) -> str:
    candidate = _sanitize_username(preferred or "")
    if not candidate:
        candidate = _sanitize_username(email.split("@")[0]) or _sanitize_username(fullname.replace(" ", ".")) or "user"

    if not _username_exists(db, candidate):
        return candidate

    for i in range(1, 1000):
        option = f"{candidate}{i}"
        if not _username_exists(db, option):
            return option

    return f"user{secrets.randbelow(10_000_000):07d}"


def _issue_token_pair(db: Session, user: User, client_ip: str | None, user_agent: str | None):
    access_token = create_access_token(user.id)
    refresh_token, refresh_jti = create_refresh_token(user.id)

    refresh_row = RefreshToken(
        user_id=user.id,
        jti=refresh_jti,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_token_expiry(),
        created_ip=client_ip,
        user_agent=(user_agent or "")[:255] or None,
    )
    db.add(refresh_row)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "access_expires_in_seconds": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_expires_in_seconds": REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    }


def _revoke_all_active_refresh_tokens(db: Session, user_id: int):
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).update({RefreshToken.revoked_at: _utcnow()}, synchronize_session=False)
    db.commit()


def _auth_user_payload(user: User) -> dict:
    role_value = user.role or UserRole.CUSTOMER.value
    return {
        "id": user.id,
        "fullname": user.fullname,
        "username": user.username,
        "email": user.email,
        "mobile": user.mobile,
        "role": role_value,
        "is_active": bool(user.is_active),
        "profile_image_url": resolve_profile_image_url(user.profile_image_url, role_value),
    }


def _dashboard_key_for_role(role_value: str) -> str:
    try:
        role = UserRole(role_value)
    except ValueError:
        role = UserRole.CUSTOMER
    return ROLE_DASHBOARD[role]


def build_auth_identity(user: User) -> dict:
    auth_user = _auth_user_payload(user)
    return {
        "status": "OK",
        "user_id": user.id,
        "profile_image_url": resolve_profile_image_url(user.profile_image_url, auth_user["role"]),
        "dashboard_key": _dashboard_key_for_role(auth_user["role"]),
        "user": auth_user,
    }


def send_otp(db: Session, mobile: str, purpose: str = "signup"):
    now = _utcnow()
    mobile = _normalize_mobile(mobile)
    if purpose not in {"signup", PASSWORD_RESET_OTP_PURPOSE}:
        return {"status": "Invalid OTP purpose"}
    if OTP_SEND_LIMIT <= 0 or OTP_RATE_WINDOW_SECONDS <= 0 or OTP_MAX_VERIFY_ATTEMPTS <= 0:
        raise RuntimeError("OTP rate-limit settings must be positive integers")

    window_start = now - timedelta(seconds=OTP_RATE_WINDOW_SECONDS)
    recent_count = db.query(Otp).filter(
        Otp.mobile == mobile,
        Otp.purpose == purpose,
        Otp.created_at >= window_start,
    ).count()
    if recent_count >= OTP_SEND_LIMIT:
        return {"status": "OTP rate limit exceeded"}

    # Expire any previous unverified OTPs for this mobile/purpose
    db.query(Otp).filter(
        Otp.mobile == mobile,
        Otp.purpose == purpose,
        Otp.verified == False,
    ).update({Otp.expires_at: now})

    code = _generate_otp()
    otp = Otp(
        mobile=mobile,
        otp_code=None,
        otp_hash=_otp_digest(code),
        purpose=purpose,
        verified=False,
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)

    if not MSG91_AUTH_KEY or not MSG91_SENDER_ID or not MSG91_TEMPLATE_ID:
        return {"status": "MSG91 not configured"}
    if len(MSG91_SENDER_ID) != 6:
        return {"status": "MSG91 sender id must be 6 characters"}

    payload = {
        "template_id": MSG91_TEMPLATE_ID,
        "mobile": mobile,
        "sender": MSG91_SENDER_ID,
        "otp": code,
        "otp_expiry": OTP_EXPIRY_MINUTES,
    }
    try:
        resp = requests.post(
            MSG91_OTP_ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "authkey": MSG91_AUTH_KEY,
            },
            timeout=10,
        )
        ok, err = _msg91_is_success(resp)
        if not ok:
            logger.warning("MSG91 send OTP failed: status=%s body=%s", resp.status_code, resp.text[:500])
            return {"status": err or "OTP send failed"}
    except requests.RequestException:
        logger.exception("MSG91 send OTP request exception")
        return {"status": "OTP send failed"}

    return {"status": "OTP sent"}


def verify_otp(db: Session, mobile: str, otp: str, purpose: str = "signup"):
    now = _utcnow()
    mobile = _normalize_mobile(mobile)
    if purpose not in {"signup", PASSWORD_RESET_OTP_PURPOSE}:
        return {"status": "Invalid OTP purpose"}
    if OTP_MAX_VERIFY_ATTEMPTS <= 0:
        raise RuntimeError("OTP_MAX_VERIFY_ATTEMPTS must be a positive integer")
    record = (
        db.query(Otp)
        .filter(
            Otp.mobile == mobile,
            Otp.purpose == purpose,
            Otp.verified == False,
            Otp.expires_at > now,
            Otp.consumed_at.is_(None),
        )
        .order_by(Otp.id.desc())
        .first()
    )

    if not record:
        return {"status": "Invalid or expired OTP"}

    stored_digest = record.otp_hash
    is_valid_code = (
        hmac.compare_digest(stored_digest, _otp_digest(otp))
        if stored_digest
        else record.otp_code == otp
    )
    if not is_valid_code:
        record.attempt_count = (record.attempt_count or 0) + 1
        if record.attempt_count >= OTP_MAX_VERIFY_ATTEMPTS:
            record.expires_at = now
        db.commit()
        return {"status": "Invalid or expired OTP"}

    if not MSG91_AUTH_KEY:
        return {"status": "MSG91 not configured"}

    params = {"mobile": mobile, "otp": otp}
    try:
        resp = requests.get(
            MSG91_VERIFY_ENDPOINT,
            params=params,
            headers={"authkey": MSG91_AUTH_KEY},
            timeout=10,
        )
        ok, err = _msg91_is_success(resp)
        if not ok:
            logger.warning("MSG91 verify OTP failed: status=%s body=%s", resp.status_code, resp.text[:500])
            return {"status": err or "Invalid or expired OTP"}
    except requests.RequestException:
        logger.exception("MSG91 verify OTP request exception")
        return {"status": "Invalid or expired OTP"}

    record.verified = True
    db.commit()

    return {"status": "OTP verified"}


def verify_firebase_token(db: Session, id_token: str, mobile: str, purpose: str = "signup"):
    app = _get_firebase_app()
    if app is None:
        logger.warning("Firebase not configured: missing credentials or firebase-admin")
        return {"status": "Firebase not configured"}

    try:
        from firebase_admin import auth as firebase_auth
    except Exception:
        logger.exception("firebase-admin auth import failed")
        return {"status": "Firebase not configured"}

    try:
        decoded = firebase_auth.verify_id_token(id_token)
    except Exception:
        logger.exception("Firebase token verification failed")
        return {"status": "Invalid Firebase token"}

    token_phone = decoded.get("phone_number")
    if not token_phone:
        logger.warning("Firebase token missing phone_number claim")
        return {"status": "Phone number not found in token"}

    mobile_norm = _normalize_mobile(mobile)
    token_digits = re.sub(r"\D", "", token_phone or "")

    if not (token_digits == mobile_norm or token_digits.endswith(mobile_norm)):
        logger.warning(
            "Firebase mobile mismatch: token_phone=%s mobile=%s",
            token_phone,
            mobile_norm,
        )
        return {"status": "Mobile mismatch"}

    now = _utcnow()
    db.query(Otp).filter(
        Otp.mobile == mobile_norm,
        Otp.purpose == purpose,
        Otp.verified == False,
    ).update({Otp.expires_at: now})

    otp = Otp(
        mobile=mobile_norm,
        otp_code="firebase",
        purpose=purpose,
        verified=True,
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)

    return {"status": "OTP verified"}


def firebase_health_check():
    app = _get_firebase_app()
    if app is None:
        return {"status": "Firebase not configured"}
    return {"status": "OK"}


def signup_user(db: Session, data):
    mobile = _normalize_mobile(data.mobile)

    if data.password != data.confirm:
        return {"status": "Passwords do not match"}

    now = _utcnow()
    verified = (
        db.query(Otp)
        .filter(
            Otp.mobile == mobile,
            Otp.purpose == "signup",
            Otp.verified == True,
            Otp.expires_at > now,
            Otp.consumed_at.is_(None),
        )
        .order_by(Otp.id.desc())
        .first()
    )
    if not verified:
        return {"status": "Please verify OTP before signup"}

    desired_username = _generate_unique_username(db, data.fullname, data.email, data.username)

    existing = db.query(User).filter(
        (User.email == data.email) | (User.mobile == mobile) | (User.username == desired_username)
    ).first()
    if existing:
        return {"status": "User with this email, mobile, or username already exists"}

    hashed_pw = pwd_context.hash(data.password)

    user = User(
        fullname=data.fullname,
        username=desired_username,
        email=data.email,
        mobile=mobile,
        password_hash=hashed_pw,
        role=UserRole.CUSTOMER.value,
        is_active=True,
    )

    db.add(user)
    verified.consumed_at = now
    verified.expires_at = now
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"status": "User with this email, mobile, or username already exists"}
    db.refresh(user)

    return {"status": "Signup successful"}


def login_user(db: Session, data, client_ip: str | None = None, user_agent: str | None = None):
    identifier = (data.identifier or data.email or data.mobile or "").strip()
    if not identifier:
        return {"status": "Email or mobile is required"}

    if "@" in identifier:
        user = db.query(User).filter(User.email == identifier).first()
    elif identifier.isdigit() or (identifier.startswith("+") and identifier[1:].isdigit()):
        user = db.query(User).filter(User.mobile == _normalize_mobile(identifier)).first()
    else:
        user = db.query(User).filter(User.username == _sanitize_username(identifier)).first()

    if not user or not user.password_hash or not pwd_context.verify(data.password, user.password_hash):
        return {"status": "Invalid credentials"}
    if not user.is_active:
        return {"status": "Account is deactivated"}

    token_pair = _issue_token_pair(db, user, client_ip, user_agent)
    response = build_auth_identity(user)
    response["status"] = "Login successful"
    response["tokens"] = token_pair
    return response


def google_login_user(db: Session, raw_id_token: str, client_ip: str | None = None, user_agent: str | None = None):
    claims = verify_google_id_token(raw_id_token)
    email = claims["email"].strip().lower()

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None:
        display_name = claims.get("name")
        if not isinstance(display_name, str) or not display_name.strip():
            display_name = email.split("@", 1)[0]
        username = _generate_unique_username(db, display_name, email)
        user = User(
            fullname=display_name.strip()[:100],
            email=email,
            username=username,
            mobile=None,
            password_hash=None,
            role=UserRole.CUSTOMER.value,
            is_active=True,
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            # A concurrent request may have inserted this verified email.
            user = db.query(User).filter(func.lower(User.email) == email).first()
            if user is None:
                raise

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    token_pair = _issue_token_pair(db, user, client_ip, user_agent)
    response = build_auth_identity(user)
    response["status"] = "Login successful"
    response["tokens"] = token_pair
    return response


def refresh_tokens(db: Session, raw_refresh_token: str, client_ip: str | None = None, user_agent: str | None = None):
    try:
        payload = decode_token(raw_refresh_token, expected_type="refresh")
    except InvalidTokenError:
        return {"status": "Invalid refresh token"}

    jti = payload.get("jti")
    sub = payload.get("sub")
    if not jti or not sub:
        return {"status": "Invalid refresh token"}

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return {"status": "Invalid refresh token"}

    token_row = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not token_row:
        return {"status": "Invalid refresh token"}

    if token_row.user_id != user_id or token_row.token_hash != hash_token(raw_refresh_token):
        _revoke_all_active_refresh_tokens(db, token_row.user_id)
        return {"status": "Refresh token reuse detected. Please login again"}

    now = _utcnow()
    if token_row.revoked_at is not None:
        _revoke_all_active_refresh_tokens(db, token_row.user_id)
        return {"status": "Refresh token reuse detected. Please login again"}

    if token_row.expires_at <= now:
        token_row.revoked_at = now
        db.commit()
        return {"status": "Refresh token expired. Please login again"}

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"status": "User not found"}
    if not user.is_active:
        _revoke_all_active_refresh_tokens(db, user.id)
        return {"status": "Account is deactivated"}

    new_token, new_jti = create_refresh_token(user.id)

    token_row.revoked_at = now
    token_row.replaced_by_jti = new_jti

    db.add(
        RefreshToken(
            user_id=user.id,
            jti=new_jti,
            token_hash=hash_token(new_token),
            expires_at=refresh_token_expiry(),
            created_ip=client_ip,
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    db.commit()
    response = build_auth_identity(user)
    response["status"] = "Token refreshed"
    response["tokens"] = {
        "access_token": create_access_token(user.id),
        "refresh_token": new_token,
        "token_type": "bearer",
        "access_expires_in_seconds": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_expires_in_seconds": REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    }
    return response


def logout_user(db: Session, raw_refresh_token: str):
    try:
        payload = decode_token(raw_refresh_token, expected_type="refresh")
    except InvalidTokenError:
        return {"status": "Logout successful"}

    jti = payload.get("jti")
    if not jti:
        return {"status": "Logout successful"}

    token_row = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if token_row and token_row.revoked_at is None:
        token_row.revoked_at = _utcnow()
        db.commit()

    return {"status": "Logout successful"}


def reset_password_user(db: Session, mobile: str, password: str, confirm: str | None = None):
    if confirm is not None and password != confirm:
        return {"status": "Passwords do not match"}
    if len(password) < 8 or len(password) > 128:
        return {"status": "Password must be between 8 and 128 characters"}

    mobile = _normalize_mobile(mobile)
    now = _utcnow()

    verified = (
        db.query(Otp)
        .filter(
            Otp.mobile == mobile,
            Otp.purpose == PASSWORD_RESET_OTP_PURPOSE,
            Otp.verified == True,
            Otp.expires_at > now,
            Otp.consumed_at.is_(None),
        )
        .order_by(Otp.id.desc())
        .first()
    )
    if not verified:
        return {"status": "Please verify OTP before reset password"}

    user = db.query(User).filter(User.mobile == mobile).first()
    if not user:
        return {"status": "User not found"}

    verified.consumed_at = now
    verified.expires_at = now
    user.password_hash = pwd_context.hash(password)
    _revoke_all_active_refresh_tokens(db, user.id)

    return {"status": "Password reset successful"}


def change_password_user(db: Session, user: User, role: str, email: str, old_password: str, new_password: str):
    requested_role = (role or "").strip().lower()
    current_role = (user.role or "").strip().lower()
    normalized_role_map = {
        "super_admin": "admin",
        "admin": "admin",
        "field_officer": "field_officer",
        "accounting": "accountant",
        "accountant": "accountant",
    }
    expected_role = normalized_role_map.get(current_role, current_role)
    incoming_role = normalized_role_map.get(requested_role, requested_role)

    if incoming_role != expected_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role does not match the logged-in account",
        )

    if (user.email or "").strip().lower() != (email or "").strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email does not match the logged-in account",
        )

    if not pwd_context.verify(old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if old_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    user.password_hash = pwd_context.hash(new_password)
    db.add(user)
    db.commit()
    _revoke_all_active_refresh_tokens(db, user.id)

    return {
        "status": "success",
        "message": "Password changed successfully",
    }
