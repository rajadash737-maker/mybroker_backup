from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import service as auth_service
from app.database import Base
from app.models.otp import Otp
from app.users.model import User


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _add_otp(db, *, purpose="password_reset", expires_at=None, verified=True):
    user = db.query(User).filter_by(mobile="911234567890").first()
    if user is None:
        user = User(
            fullname="OTP Test",
            email="otp@example.test",
            mobile="911234567890",
            password_hash="old-hash",
        )
        db.add(user)
    otp = Otp(
        mobile="911234567890",
        otp_code="123456",
        purpose=purpose,
        verified=verified,
        expires_at=expires_at or datetime.utcnow() + timedelta(minutes=5),
    )
    db.add(otp)
    db.commit()
    return user, otp


def test_expired_otp_cannot_verify_or_reset_password(db):
    _, otp = _add_otp(db, expires_at=datetime.utcnow() - timedelta(seconds=1), verified=False)

    assert auth_service.verify_otp(db, otp.mobile, otp.otp_code, "password_reset")["status"] == "Invalid or expired OTP"
    assert auth_service.reset_password_user(db, otp.mobile, "new-password") ["status"] == "Please verify OTP before reset password"


def test_password_reset_rejects_signup_otp(db):
    user, _ = _add_otp(db, purpose="signup")
    old_hash = user.password_hash

    result = auth_service.reset_password_user(db, user.mobile, "new-password")

    assert result["status"] == "Please verify OTP before reset password"
    assert user.password_hash == old_hash


def test_password_reset_otp_is_consumed_and_cannot_be_reused(db):
    user, otp = _add_otp(db)

    first = auth_service.reset_password_user(db, user.mobile, "new-password")
    db.refresh(otp)
    updated_hash = user.password_hash
    second = auth_service.reset_password_user(db, user.mobile, "another-password")

    assert first["status"] == "Password reset successful"
    assert otp.consumed_at is not None
    assert second["status"] == "Please verify OTP before reset password"
    assert user.password_hash == updated_hash


def test_wrong_otp_attempts_expire_the_code(db, monkeypatch):
    monkeypatch.setattr(auth_service, "OTP_MAX_VERIFY_ATTEMPTS", 2)
    _, otp = _add_otp(db, verified=False)

    assert auth_service.verify_otp(db, otp.mobile, "000000", "password_reset")["status"] == "Invalid or expired OTP"
    assert auth_service.verify_otp(db, otp.mobile, "000000", "password_reset")["status"] == "Invalid or expired OTP"
    db.refresh(otp)
    assert otp.attempt_count == 2
    assert otp.expires_at <= datetime.utcnow()


def test_otp_sending_is_rate_limited_per_mobile_and_purpose(db, monkeypatch):
    monkeypatch.setattr(auth_service, "OTP_SEND_LIMIT", 1)
    monkeypatch.setattr(auth_service, "OTP_RATE_WINDOW_SECONDS", 900)
    monkeypatch.setattr(auth_service, "MSG91_AUTH_KEY", None)
    monkeypatch.setattr(auth_service, "MSG91_TEMPLATE_ID", None)
    monkeypatch.setattr(auth_service, "_generate_otp", lambda: "123456")

    first = auth_service.send_otp(db, "1234567890", "password_reset")
    second = auth_service.send_otp(db, "1234567890", "password_reset")

    assert first["status"] == "MSG91 not configured"
    assert second["status"] == "OTP rate limit exceeded"
    record = db.query(Otp).filter_by(mobile="911234567890", purpose="password_reset").one()
    assert record.otp_code is None
    assert record.otp_hash is not None and record.otp_hash != "123456"
