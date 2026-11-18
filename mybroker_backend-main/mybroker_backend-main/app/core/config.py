import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=False)


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_values(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "local")
    database_url: str = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root@localhost:3306/mybroker_db"
)
    database_echo: bool = _to_bool(os.getenv("DATABASE_ECHO"), default=False)
    max_upload_size_bytes: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024)))
    private_uploads_dir: Path = Path(
        os.getenv("PRIVATE_UPLOADS_DIR", str(Path(__file__).resolve().parents[1] / "private_uploads"))
    )
    frontend_origins: str = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "")
    default_profile_image_url: str = os.getenv(
        "DEFAULT_PROFILE_IMAGE_URL",
        "https://ui-avatars.com/api/?name=User&background=e5e7eb&color=111827",
    )
    default_admin_profile_image_url: str = os.getenv(
        "DEFAULT_ADMIN_PROFILE_IMAGE_URL",
        "https://ui-avatars.com/api/?name=Admin&background=1f2937&color=f9fafb",
    )
    default_field_officer_profile_image_url: str = os.getenv(
        "DEFAULT_FIELD_OFFICER_PROFILE_IMAGE_URL",
        "https://ui-avatars.com/api/?name=Officer&background=334155&color=f8fafc",
    )
    firebase_credentials_path: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
    firebase_credentials_json: str = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
    google_oauth_client_ids: tuple[str, ...] = _csv_values(os.getenv("GOOGLE_OAUTH_CLIENT_IDS"))
    site_visit_otp_encryption_key: str = os.getenv("SITE_VISIT_OTP_ENCRYPTION_KEY", "")
    site_visit_otp_hmac_key: str = os.getenv("SITE_VISIT_OTP_HMAC_KEY", "")
    site_visit_refund_encryption_key: str = os.getenv("SITE_VISIT_REFUND_ENCRYPTION_KEY", "")
    land_booking_refund_encryption_key: str = os.getenv("LAND_BOOKING_REFUND_ENCRYPTION_KEY", "")


settings = Settings()
