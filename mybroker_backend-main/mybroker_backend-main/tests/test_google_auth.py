from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import google_identity
from app.auth import service as auth_service
from app.database import Base
from app.models.otp import RefreshToken
from app.users.model import User
from app.users.roles import UserRole


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _claims(email="google@example.test", **overrides):
    values = {
        "iss": "https://accounts.google.com",
        "aud": "test-client-id",
        "exp": datetime.now(timezone.utc).timestamp() + 300,
        "email": email,
        "email_verified": True,
        "name": "Google User",
        "sub": "google-subject",
        "role": "SUPER_ADMIN",
    }
    values.update(overrides)
    return values


def _mock_google_library(monkeypatch, verifier):
    google_pkg = ModuleType("google")
    auth_pkg = ModuleType("google.auth")
    transport_pkg = ModuleType("google.auth.transport")
    transport_requests = ModuleType("google.auth.transport.requests")
    transport_requests.Request = lambda: object()
    oauth2_pkg = ModuleType("google.oauth2")
    id_token_module = ModuleType("google.oauth2.id_token")
    id_token_module.verify_oauth2_token = verifier
    google_pkg.auth = auth_pkg
    google_pkg.oauth2 = oauth2_pkg
    auth_pkg.transport = transport_pkg
    transport_pkg.requests = transport_requests
    oauth2_pkg.id_token = id_token_module
    for name, module in {
        "google": google_pkg,
        "google.auth": auth_pkg,
        "google.auth.transport": transport_pkg,
        "google.auth.transport.requests": transport_requests,
        "google.oauth2": oauth2_pkg,
        "google.oauth2.id_token": id_token_module,
    }.items():
        monkeypatch.setitem(__import__("sys").modules, name, module)
    monkeypatch.setattr(google_identity, "settings", SimpleNamespace(google_oauth_client_ids=("test-client-id", "android-client-id")))


def test_valid_verified_google_token_creates_customer_and_persists_refresh_session(db, monkeypatch):
    monkeypatch.setattr(auth_service, "verify_google_id_token", lambda token: _claims())

    result = auth_service.google_login_user(db, "verified-token")

    user = db.query(User).filter_by(email="google@example.test").one()
    refresh = db.query(RefreshToken).filter_by(user_id=user.id).one()
    assert user.role == UserRole.CUSTOMER.value
    assert user.mobile is None
    assert user.password_hash is None
    assert result["user"]["role"] == UserRole.CUSTOMER.value
    assert result["tokens"]["access_token"]
    assert refresh.token_hash == auth_service.hash_token(result["tokens"]["refresh_token"])


def test_existing_verified_email_logs_in_once_and_preserves_role_and_password(db, monkeypatch):
    existing = User(
        fullname="Existing Staff", email="google@example.test", username="staff", mobile=None,
        password_hash="unchanged-hash", role=UserRole.ADMIN.value, is_active=True,
    )
    db.add(existing)
    db.commit()
    monkeypatch.setattr(auth_service, "verify_google_id_token", lambda token: _claims())

    result = auth_service.google_login_user(db, "verified-token")

    assert db.query(User).filter_by(email="google@example.test").count() == 1
    assert existing.role == UserRole.ADMIN.value
    assert existing.password_hash == "unchanged-hash"
    assert result["user"]["role"] == UserRole.ADMIN.value


def test_password_login_rejects_google_account_without_password_hash(db):
    from types import SimpleNamespace

    db.add(User(fullname="Google", email="google@example.test", username="google", password_hash=None))
    db.commit()
    result = auth_service.login_user(db, SimpleNamespace(identifier="google@example.test", email=None, mobile=None, password="any"))
    assert result["status"] == "Invalid credentials"


def test_inactive_google_account_is_rejected(db, monkeypatch):
    db.add(User(fullname="Inactive", email="google@example.test", username="inactive", password_hash=None, is_active=False))
    db.commit()
    monkeypatch.setattr(auth_service, "verify_google_id_token", lambda token: _claims())

    with pytest.raises(HTTPException) as exc:
        auth_service.google_login_user(db, "verified-token")
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    "claims,token_error",
    [
        (_claims(exp=1), None),
        (_claims(aud="wrong-client-id"), None),
        (_claims(email_verified=False), None),
        (_claims(email="not-an-email"), None),
        (_claims(email=None), None),
        (None, ValueError("invalid token")),
    ],
    ids=["expired", "wrong-audience", "unverified-email", "invalid-email", "missing-email", "invalid-token"],
)
def test_google_token_claims_are_rejected(claims, token_error, monkeypatch):
    def verifier(token, request, audience):
        if token_error:
            raise token_error
        return claims

    _mock_google_library(monkeypatch, verifier)
    with pytest.raises(HTTPException) as exc:
        google_identity.verify_google_id_token("test-token")
    assert exc.value.status_code == 401


def test_wrong_issuer_is_rejected(monkeypatch):
    _mock_google_library(monkeypatch, lambda token, request, audience: _claims(iss="attacker.example"))
    with pytest.raises(HTTPException):
        google_identity.verify_google_id_token("test-token")


def test_unconfigured_audience_fails_closed(monkeypatch):
    monkeypatch.setattr(google_identity, "settings", SimpleNamespace(google_oauth_client_ids=()))
    with pytest.raises(HTTPException) as exc:
        google_identity.verify_google_id_token("test-token")
    assert exc.value.status_code == 503


def test_client_role_is_ignored_and_google_user_is_always_customer(db, monkeypatch):
    from app.auth.schemas import GoogleAuthRequestSchema

    request = GoogleAuthRequestSchema.model_validate({"id_token": "valid", "role": "ADMIN"})
    monkeypatch.setattr(auth_service, "verify_google_id_token", lambda token: _claims(role="SUPER_ADMIN"))
    result = auth_service.google_login_user(db, request.id_token)

    user = db.query(User).one()
    assert user.role == UserRole.CUSTOMER.value
    assert result["user"]["role"] == UserRole.CUSTOMER.value


def test_concurrent_email_insert_is_reused_after_integrity_error(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'google-auth-race.db'}")
    Base.metadata.create_all(engine)
    competing_session = Session(engine)
    main_session = Session(engine)
    original_commit = main_session.commit
    inserted_competitor = False

    def commit_with_competing_signup():
        nonlocal inserted_competitor
        if not inserted_competitor:
            inserted_competitor = True
            competing_session.add(User(
                fullname="Racing Signup", email="google@example.test", username="winner", mobile=None,
                password_hash=None, role=UserRole.CUSTOMER.value, is_active=True,
            ))
            competing_session.commit()
        original_commit()

    main_session.commit = commit_with_competing_signup
    monkeypatch.setattr(auth_service, "verify_google_id_token", lambda token: _claims())
    try:
        result = auth_service.google_login_user(main_session, "verified-token")
        assert result["user"]["email"] == "google@example.test"
        assert main_session.query(func.count(User.id)).filter(User.email == "google@example.test").scalar() == 1
    finally:
        main_session.close()
        competing_session.close()
        engine.dispose()
