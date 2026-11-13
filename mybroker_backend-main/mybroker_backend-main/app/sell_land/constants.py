from enum import Enum


class SellLandStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    FIELD_VERIFIED = "field_verified"
    LIVE = "live"
    REJECTED = "rejected"
    BOOKED = "booked"
    SOLD = "sold"
    PROCESSING_REFUND = "processing_refund"
    REFUND_SUCCESSFUL = "refund_successful"


class LandType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    AGRICULTURAL = "agricultural"
    INDUSTRIAL = "industrial"
    OTHER = "other"


class AreaUnit(str, Enum):
    SQFT = "sqft"
    SQM = "sqm"
    DECIMAL = "decimal"
    ACRE = "acre"
    HECTARE = "hectare"
    BIGHA = "bigha"


class OwnershipType(str, Enum):
    SINGLE_OWNER = "single_owner"
    MULTI_OWNER = "multi_owner"
    INHERITED_LAND = "inherited_land"
    # Legacy values kept for backward compatibility with older drafts.
    OWNER = "owner"
    BROKER = "broker"
    POWER_OF_ATTORNEY = "power_of_attorney"
    OTHER = "other"


class SellerCategory(str, Enum):
    GENERAL = "general"
    OBC = "obc"
    SC = "sc"
    ST = "st"


class PriceType(str, Enum):
    TOTAL_PRICE = "total_price"
    PRICE_PER_UNIT = "price_per_unit"


class Availability(str, Enum):
    IMMEDIATE = "immediate"
    WITHIN_3_MONTHS = "within_3_months"


class MediaType(str, Enum):
    PHOTO = "photo"
    DOCUMENT = "document"


class DocumentType(str, Enum):
    SALE_DEED = "sale_deed"
    ORIGINAL_SALE_DEED = "original_sale_deed"
    KHATA_PATTA = "khata_patta"
    ENCUMBRANCE_CERTIFICATE = "encumbrance_certificate"
    LATEST_TAX_RECEIPT = "latest_tax_receipt"
    DEATH_CERTIFICATE = "death_certificate"
    LEGAL_HEIR_CERTIFICATE = "legal_heir_certificate"
    ALL_HEIRS_AADHAAR = "all_heirs_aadhaar"
    CONSENT_AFFIDAVIT_ALL_HEIRS = "consent_affidavit_all_heirs"
    ALL_CO_OWNER_AADHAAR = "all_co_owner_aadhaar"
    JOINT_AFFIDAVIT = "joint_affidavit"
    AADHAAR_PAN = "aadhaar_pan"
    SELLER_IDENTITY_PROOF = "seller_identity_proof"
    OTHER = "other"


class PaymentMethod(str, Enum):
    UPI = "upi"
    DEBIT_CREDIT_CARD = "debit_credit_card"
    NET_BANKING = "net_banking"


class PaymentStatus(str, Enum):
    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"


class OfferStatus(str, Enum):
    PENDING = "pending"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class BookingStatus(str, Enum):
    BOOKED = "booked"
    CONFIRMED = "confirmed"
    IN_PROCESS = "in_process"
    REGISTRY_SCHEDULED = "registry_scheduled"
    REGISTRY_DONE = "registry_done"
    SOLD = "sold"


DEFAULT_SELL_LAND_STATUS = SellLandStatus.PENDING.value


SELLER_TYPE_REQUIRED_DOCUMENTS: dict[OwnershipType, tuple[DocumentType, ...]] = {
    OwnershipType.SINGLE_OWNER: (
        DocumentType.SALE_DEED,
        DocumentType.KHATA_PATTA,
        DocumentType.ENCUMBRANCE_CERTIFICATE,
        DocumentType.LATEST_TAX_RECEIPT,
        DocumentType.AADHAAR_PAN,
    ),
    OwnershipType.MULTI_OWNER: (
        DocumentType.SALE_DEED,
        DocumentType.ALL_CO_OWNER_AADHAAR,
        DocumentType.JOINT_AFFIDAVIT,
        DocumentType.ENCUMBRANCE_CERTIFICATE,
        DocumentType.LATEST_TAX_RECEIPT,
    ),
    OwnershipType.INHERITED_LAND: (
        DocumentType.ORIGINAL_SALE_DEED,
        DocumentType.DEATH_CERTIFICATE,
        DocumentType.LEGAL_HEIR_CERTIFICATE,
        DocumentType.ALL_HEIRS_AADHAAR,
        DocumentType.CONSENT_AFFIDAVIT_ALL_HEIRS,
        DocumentType.ENCUMBRANCE_CERTIFICATE,
        DocumentType.LATEST_TAX_RECEIPT,
    ),
    # Legacy mapping to avoid breaking older saved records.
    OwnershipType.OWNER: (
        DocumentType.SALE_DEED,
        DocumentType.KHATA_PATTA,
        DocumentType.ENCUMBRANCE_CERTIFICATE,
        DocumentType.SELLER_IDENTITY_PROOF,
    ),
    OwnershipType.BROKER: (
        DocumentType.SALE_DEED,
        DocumentType.KHATA_PATTA,
        DocumentType.ENCUMBRANCE_CERTIFICATE,
        DocumentType.SELLER_IDENTITY_PROOF,
    ),
    OwnershipType.POWER_OF_ATTORNEY: (
        DocumentType.SALE_DEED,
        DocumentType.KHATA_PATTA,
        DocumentType.ENCUMBRANCE_CERTIFICATE,
        DocumentType.SELLER_IDENTITY_PROOF,
    ),
    OwnershipType.OTHER: (
        DocumentType.SALE_DEED,
        DocumentType.KHATA_PATTA,
        DocumentType.ENCUMBRANCE_CERTIFICATE,
        DocumentType.SELLER_IDENTITY_PROOF,
    ),
}


def get_required_documents_for_ownership(ownership_type: OwnershipType) -> tuple[DocumentType, ...]:
    return SELLER_TYPE_REQUIRED_DOCUMENTS.get(ownership_type, SELLER_TYPE_REQUIRED_DOCUMENTS[OwnershipType.SINGLE_OWNER])


def get_allowed_documents_for_ownership(ownership_type: OwnershipType) -> tuple[DocumentType, ...]:
    required = get_required_documents_for_ownership(ownership_type)
    if DocumentType.OTHER in required:
        return required
    return (*required, DocumentType.OTHER)
