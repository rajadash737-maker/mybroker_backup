from enum import StrEnum


class UserRole(StrEnum):
    CUSTOMER = "CUSTOMER"
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    FIELD_OFFICER = "FIELD_OFFICER"
    ACCOUNTING = "ACCOUNTING"


ROLE_DASHBOARD = {
    UserRole.SUPER_ADMIN: "super_admin_dashboard",
    UserRole.ADMIN: "admin_dashboard",
    UserRole.FIELD_OFFICER: "field_officer_dashboard",
    UserRole.ACCOUNTING: "accounting_dashboard",
    UserRole.CUSTOMER: "customer_dashboard",
}

