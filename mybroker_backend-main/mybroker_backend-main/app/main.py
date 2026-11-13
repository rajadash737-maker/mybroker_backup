from dotenv import load_dotenv

load_dotenv()

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.router import router as auth_router
from app.core.request_context import set_request_base_url
from app.sell_land.admin_router import router as sell_land_admin_router
from app.sell_land.field_officer_router import router as sell_land_field_officer_router
from app.sell_land.router import router as sell_land_router
from app.staff.router import router as staff_router
from app.users.router import router as users_router
from app.ratings.router import router as ratings_router
from app.settings.router import router as settings_router
from app.transactions.router import router as transactions_router
from app.payments.router import router as payments_router
from app.api.property import router as property_router
from app.notifications.router import router as notifications_router
from app.media.router import router as media_router
from app.core.dependencies import get_db
from app.sell_land.models import SellLandBooking, SellLandMedia, SellLandRegistryProof, SellLandRequest
import app.models.otp  # VERY IMPORTANT
import app.sell_land.models  # VERY IMPORTANT
import app.users.model  # VERY IMPORTANT
import app.ratings.models  # VERY IMPORTANT
import app.settings.models  # VERY IMPORTANT
import app.payments.models  # VERY IMPORTANT
import app.notifications.models  # VERY IMPORTANT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server is starting up...")
    yield
    logger.info("Server is shutting down...")

app = FastAPI(lifespan=lifespan)


@app.get("/up")
def health_up():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.middleware("http")
async def request_base_url_middleware(request, call_next):
    set_request_base_url(str(request.base_url))
    try:
        response = await call_next(request)
        return response
    finally:
        set_request_base_url(None)

frontend_origins = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
)
allowed_origins = [origin.strip() for origin in frontend_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_dir = Path(__file__).resolve().parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)


@app.get("/uploads/{file_path:path}", include_in_schema=False)
def get_public_upload(file_path: str, db: Session = Depends(get_db)):
    relative_path = Path(file_path)
    root = uploads_dir.resolve()
    path = (root / relative_path).resolve()
    if path == root or root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    normalized = relative_path.as_posix()
    if normalized.startswith(("banners/", "profiles/")):
        return FileResponse(path)

    public_photo = db.query(SellLandMedia.id).filter(
        SellLandMedia.file_url == f"/uploads/{normalized}",
        SellLandMedia.media_type == "photo",
    ).first()
    if not public_photo:
        document = db.query(SellLandMedia).filter(
            SellLandMedia.file_url == f"/uploads/{normalized}",
            SellLandMedia.media_type == "document",
        ).first()
        if document:
            return RedirectResponse(f"/media/private-legacy/listing/{document.id}", status_code=307)
        booking = db.query(SellLandBooking).filter(
            (SellLandBooking.aadhaar_doc_url == f"/uploads/{normalized}")
            | (SellLandBooking.pan_doc_url == f"/uploads/{normalized}")
            | (SellLandBooking.bank_doc_url == f"/uploads/{normalized}")
        ).first()
        if booking:
            for kind, url in (
                ("aadhaar", booking.aadhaar_doc_url),
                ("pan", booking.pan_doc_url),
                ("bank", booking.bank_doc_url),
            ):
                if url == f"/uploads/{normalized}":
                    return RedirectResponse(f"/media/private-legacy/booking/{booking.id}/{kind}", status_code=307)
        proof = db.query(SellLandRegistryProof).filter(
            SellLandRegistryProof.file_url == f"/uploads/{normalized}"
        ).first()
        if proof:
            return RedirectResponse(f"/media/private-legacy/registry-proof/{proof.id}", status_code=307)
        visit = db.query(SellLandRequest).filter(
            SellLandRequest.field_officer_visit_photo_url == f"/uploads/{normalized}"
        ).first()
        if visit:
            return RedirectResponse(f"/media/private-legacy/visit/{visit.id}", status_code=307)
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(sell_land_router)
app.include_router(sell_land_admin_router)
app.include_router(sell_land_field_officer_router)
app.include_router(staff_router)
app.include_router(ratings_router)
app.include_router(settings_router)
app.include_router(transactions_router)
app.include_router(payments_router)
app.include_router(property_router)
app.include_router(notifications_router)
app.include_router(media_router)
