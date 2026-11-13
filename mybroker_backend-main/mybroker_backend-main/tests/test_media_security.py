from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.datastructures import UploadFile

from app.media import router as private_media_router
from app.media import utils as media_utils


def _upload(filename: str, content_type: str, data: bytes) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(data),
        headers=Headers({"content-type": content_type}),
    )


def test_upload_validation_rejects_extension_mime_content_mismatch():
    fake_pdf = _upload("identity.pdf", "application/pdf", b"this is not a PDF")

    with pytest.raises(ValueError, match="content does not match"):
        media_utils.validate_upload(fake_pdf, {".pdf"})


def test_upload_validation_enforces_configured_size_limit(monkeypatch):
    monkeypatch.setattr(media_utils, "_max_upload_bytes", lambda: 8)
    large_pdf = _upload("identity.pdf", "application/pdf", b"%PDF-" + b"x" * 20)

    with pytest.raises(ValueError, match="size limit"):
        media_utils.validate_upload(large_pdf, {".pdf"})


def test_private_file_resolution_rejects_path_traversal(monkeypatch):
    monkeypatch.setattr(
        private_media_router,
        "settings",
        SimpleNamespace(private_uploads_dir=Path("C:/private_uploads")),
    )

    assert private_media_router._stored_file_path("/media/private/../secret.pdf") is None


def test_unregistered_private_document_is_not_served_from_public_uploads(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "uploads_dir", Path(__file__).resolve().parent)
    monkeypatch.setattr(Path, "is_file", lambda _self: True)

    class Query:
        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return None

    class FakeDb:
        def query(self, *_args, **_kwargs):
            return Query()

    with pytest.raises(HTTPException) as error:
        main.get_public_upload("sell-land/booking-docs/booking_1/identity.pdf", db=FakeDb())

    assert error.value.status_code == 404


def test_booking_document_access_requires_a_related_party_or_assigned_officer():
    booking = SimpleNamespace(buyer_id=11, assigned_field_officer_id=33)
    listing = SimpleNamespace(user_id=22)

    assert private_media_router._can_read_booking(SimpleNamespace(id=11, role="customer"), booking, listing)
    assert private_media_router._can_read_booking(SimpleNamespace(id=22, role="customer"), booking, listing)
    assert private_media_router._can_read_booking(SimpleNamespace(id=33, role="FIELD_OFFICER"), booking, listing)
    assert not private_media_router._can_read_booking(SimpleNamespace(id=44, role="customer"), booking, listing)


def test_deprecated_property_prototype_uses_authenticated_seller(monkeypatch):
    from datetime import datetime
    from fastapi import Response
    import app.api.property as property_api

    created = {}

    class Store:
        def create(self, *, seller_id, title, document_url):
            created["seller_id"] = seller_id
            return SimpleNamespace(id=1, created_at=datetime.utcnow())

    class Notifications:
        def __init__(self, db):
            pass

        def notify_property_uploaded(self, property_id):
            return {"ok": True}

    monkeypatch.setattr(property_api, "_property_store", Store())
    monkeypatch.setattr(property_api, "NotificationService", Notifications)
    response = Response()
    result = property_api.upload_property(
        property_api.PropertyUploadRequest(title="prototype"),
        response=response,
        db=object(),
        current_user=SimpleNamespace(id=77),
    )

    assert created["seller_id"] == 77
    assert result["property_id"] == 1
    assert response.headers["Deprecation"] == "true"


def test_deprecated_property_prototype_rejects_forged_seller_id():
    from fastapi import HTTPException, Response
    import app.api.property as property_api

    with pytest.raises(HTTPException) as error:
        property_api.upload_property(
            property_api.PropertyUploadRequest(seller_id=99),
            response=Response(),
            db=object(),
            current_user=SimpleNamespace(id=77),
        )
    assert error.value.status_code == 403
