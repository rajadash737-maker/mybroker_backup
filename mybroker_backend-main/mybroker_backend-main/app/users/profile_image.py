from app.core.config import settings
from app.media.url_utils import to_public_url
from app.users.roles import UserRole


def resolve_profile_image_url(profile_image_url: str | None, role: str | None = None) -> str | None:
    if profile_image_url:
        return to_public_url(profile_image_url)

    if role == UserRole.FIELD_OFFICER.value:
        return to_public_url(settings.default_field_officer_profile_image_url)
    if role in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}:
        return to_public_url(settings.default_admin_profile_image_url)
    return to_public_url(settings.default_profile_image_url)
