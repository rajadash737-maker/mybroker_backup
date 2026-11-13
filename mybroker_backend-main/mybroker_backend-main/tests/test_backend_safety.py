import importlib
import logging
from types import SimpleNamespace

import pytest

from app.auth import jwt_utils
from app.database import Base
from app.users import router as users_router
from app.users.schemas import FcmTokenRequest


def test_production_rejects_short_jwt_signing_secret():
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        jwt_utils._validate_signing_secret("short", "production")


def test_production_accepts_long_jwt_signing_secret():
    jwt_utils._validate_signing_secret("test-only-secret-value-long-enough-123", "production")


def test_importing_main_does_not_create_database_schema(monkeypatch):
    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("application import must not create database tables")

    monkeypatch.setattr(Base.metadata, "create_all", fail_if_called)
    import app.main as main

    importlib.reload(main)
    assert not called


def test_fcm_registration_does_not_log_token(monkeypatch, caplog):
    token = "synthetic-test-fcm-token"
    monkeypatch.setattr(users_router, "update_fcm_token", lambda db, user_id, value: (None, None))
    caplog.set_level(logging.DEBUG, logger=users_router.__name__)

    result = users_router.register_fcm_token(
        FcmTokenRequest(token=token),
        current_user=SimpleNamespace(id=123),
        db=object(),
    )

    assert result == {"status": "ok"}
    assert token not in caplog.text
