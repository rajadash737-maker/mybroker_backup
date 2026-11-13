from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_active_user, get_db
from app.sell_land.models import SellLandBooking, SellLandMedia, SellLandRegistryProof, SellLandRequest
from app.users.model import User
from app.users.roles import UserRole

router = APIRouter(prefix="/media", tags=["Private media"])
ADMIN_ROLES = {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}


def _stored_file_path(stored_url: str) -> Path | None:
    if stored_url.startswith("/media/private/"):
        root = settings.private_uploads_dir.resolve()
        path = (root / stored_url.removeprefix("/media/private/")).resolve()
    elif stored_url.startswith("/uploads/"):
        root = (Path(__file__).resolve().parents[1] / "uploads").resolve()
        path = (root / stored_url.removeprefix("/uploads/")).resolve()
    else:
        return None
    if path != root and root not in path.parents:
        return None
    return path


def _can_read_listing(user: User, listing: SellLandRequest) -> bool:
    if user.id == listing.user_id or user.role in ADMIN_ROLES:
        return True
    return user.role == UserRole.FIELD_OFFICER.value and user.id == listing.assigned_field_officer_id


def _can_read_booking(user: User, booking: SellLandBooking, listing: SellLandRequest) -> bool:
    if user.id in {booking.buyer_id, listing.user_id} or user.role in ADMIN_ROLES:
        return True
    assigned_officer_id = booking.assigned_field_officer_id or listing.field_officer_reviewed_by_id
    return user.role == UserRole.FIELD_OFFICER.value and user.id == assigned_officer_id


def _download(stored_url: str | None, filename: str | None):
    if not stored_url:
        raise HTTPException(status_code=404, detail="Private media not found")
    path = _stored_file_path(stored_url)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Private media file not found")
    return FileResponse(path, filename=filename or path.name, media_type="application/octet-stream")


@router.get("/private-legacy/listing/{media_id}")
def download_legacy_listing_document(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    media = db.query(SellLandMedia).filter(SellLandMedia.id == media_id).first()
    listing = db.query(SellLandRequest).filter(SellLandRequest.id == media.request_id).first() if media else None
    if media is None or listing is None or media.media_type != "document":
        raise HTTPException(status_code=404, detail="Private media not found")
    if not _can_read_listing(current_user, listing):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    return _download(media.file_url, media.file_name)


@router.get("/private-legacy/booking/{booking_id}/{document_type}")
def download_legacy_booking_document(
    booking_id: int,
    document_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    column_names = {
        "aadhaar": ("aadhaar_doc_url", "aadhaar_doc_name"),
        "pan": ("pan_doc_url", "pan_doc_name"),
        "bank": ("bank_doc_url", "bank_doc_name"),
    }
    if document_type not in column_names:
        raise HTTPException(status_code=404, detail="Private media not found")
    booking = db.query(SellLandBooking).filter(SellLandBooking.id == booking_id).first()
    listing = db.query(SellLandRequest).filter(SellLandRequest.id == booking.request_id).first() if booking else None
    if booking is None or listing is None:
        raise HTTPException(status_code=404, detail="Private media not found")
    if not _can_read_booking(current_user, booking, listing):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    url_column, name_column = column_names[document_type]
    return _download(getattr(booking, url_column), getattr(booking, name_column))


@router.get("/private-legacy/registry-proof/{proof_id}")
def download_legacy_registry_proof(
    proof_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    proof = db.query(SellLandRegistryProof).filter(SellLandRegistryProof.id == proof_id).first()
    booking = db.query(SellLandBooking).filter(SellLandBooking.id == proof.booking_id).first() if proof else None
    listing = db.query(SellLandRequest).filter(SellLandRequest.id == booking.request_id).first() if booking else None
    if proof is None or booking is None or listing is None:
        raise HTTPException(status_code=404, detail="Private media not found")
    if not _can_read_booking(current_user, booking, listing):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    return _download(proof.file_url, proof.file_name)


@router.get("/private-legacy/visit/{request_id}")
def download_legacy_visit_photo(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    listing = db.query(SellLandRequest).filter(SellLandRequest.id == request_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Private media not found")
    if not _can_read_listing(current_user, listing):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    return _download(listing.field_officer_visit_photo_url, listing.field_officer_visit_photo_name)


@router.get("/private/{media_path:path}")
def download_private_media(
    media_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stored_url = f"/media/private/{media_path}"
    media = db.query(SellLandMedia).filter(SellLandMedia.file_url == stored_url).first()
    filename = None
    allowed = False
    if media is not None:
        listing = db.query(SellLandRequest).filter(SellLandRequest.id == media.request_id).first()
        allowed = listing is not None and _can_read_listing(current_user, listing)
        filename = media.file_name
    else:
        booking = db.query(SellLandBooking).filter(
            (SellLandBooking.aadhaar_doc_url == stored_url)
            | (SellLandBooking.pan_doc_url == stored_url)
            | (SellLandBooking.bank_doc_url == stored_url)
            | (SellLandBooking.registry_proof_url == stored_url)
        ).first()
        if booking is not None:
            listing = db.query(SellLandRequest).filter(SellLandRequest.id == booking.request_id).first()
            allowed = listing is not None and _can_read_booking(current_user, booking, listing)
            if booking.aadhaar_doc_url == stored_url:
                filename = booking.aadhaar_doc_name
            elif booking.pan_doc_url == stored_url:
                filename = booking.pan_doc_name
            elif booking.bank_doc_url == stored_url:
                filename = booking.bank_doc_name
            else:
                filename = booking.registry_proof_name
        else:
            proof = db.query(SellLandRegistryProof).filter(SellLandRegistryProof.file_url == stored_url).first()
            if proof is not None:
                booking = db.query(SellLandBooking).filter(SellLandBooking.id == proof.booking_id).first()
                listing = db.query(SellLandRequest).filter(SellLandRequest.id == booking.request_id).first() if booking else None
                allowed = booking is not None and listing is not None and _can_read_booking(current_user, booking, listing)
                filename = proof.file_name
            else:
                listing = db.query(SellLandRequest).filter(
                    SellLandRequest.field_officer_visit_photo_url == stored_url
                ).first()
                if listing is None:
                    raise HTTPException(status_code=404, detail="Private media not found")
                allowed = _can_read_listing(current_user, listing)
                filename = listing.field_officer_visit_photo_name

    if not allowed:
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    return _download(stored_url, filename)
