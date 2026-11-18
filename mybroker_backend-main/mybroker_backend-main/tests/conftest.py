from datetime import date, datetime, time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.notifications.models  # noqa: F401
import app.sell_land.models  # noqa: F401
import app.settings.models  # noqa: F401
import app.site_visits.models  # noqa: F401
import app.users.model  # noqa: F401
from app.core.dependencies import get_current_user, get_db
from app.database import Base
from app.sell_land.models import SellLandRequest
from app.site_visits.models import SiteVisitAssignment, SiteVisitRequest
from app.users.model import User


@pytest.fixture
def admin_site_visit_api():
    """Shared isolated SQLite API fixture for Admin Site Visit endpoint tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestSession()

    admin = User(fullname="Admin", mobile="9100000001", role="ADMIN", is_active=True)
    other_admin = User(fullname="Other Admin", mobile="9100000008", role="ADMIN", is_active=True)
    super_admin = User(fullname="Super Admin", mobile="9100000002", role="SUPER_ADMIN", is_active=True)
    buyer = User(fullname="Buyer", mobile="9100000003", role="CUSTOMER", is_active=True)
    officer = User(fullname="Eligible Officer", mobile="9100000004", role="FIELD_OFFICER", is_active=True)
    inactive_officer = User(fullname="Inactive Officer", mobile="9100000005", role="FIELD_OFFICER", is_active=False)
    accounting = User(fullname="Accounting", mobile="9100000006", role="ACCOUNTING", is_active=True)
    seller = User(fullname="Seller", mobile="9100000007", role="CUSTOMER", is_active=True)
    db.add_all([admin, other_admin, super_admin, buyer, officer, inactive_officer, accounting, seller])
    db.flush()

    listing = SellLandRequest(
        user_id=seller.id,
        listing_code="LST-ADMIN-1",
        title="Admin Test Property",
        status="live",
        reviewed_by_id=admin.id,
        city="Test City",
        state="Test State",
        field_officer_reviewed_by_id=officer.id,
        field_officer_reviewed_at=datetime(2026, 1, 1),
        field_officer_decision="approved",
    )
    db.add(listing)
    db.flush()

    def create_request(*, payment_status, request_status, suffix):
        request = SiteVisitRequest(
            listing_id=listing.id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            property_name_snapshot=f"Admin Test Property {suffix}",
            listing_code_snapshot=f"LST-ADMIN-{suffix}",
            buyer_name_snapshot="Buyer Snapshot",
            buyer_mobile_snapshot="9100000003",
            seller_name_snapshot="Seller Snapshot",
            seller_mobile_snapshot="9100000007",
            preferred_visit_date=date(2026, 12, 1),
            preferred_visit_time=time(10, 30),
            visitor_count=2,
            pickup_address="Test pickup address, Test City",
            site_visit_fee_paise=12550,
            payment_status=payment_status,
            status=request_status,
        )
        db.add(request)
        db.flush()
        return request

    paid_one = create_request(payment_status="success", request_status="pending", suffix="1")
    paid_two = create_request(payment_status="success", request_status="assigned", suffix="2")
    unpaid = create_request(payment_status="initiated", request_status="pending_payment", suffix="3")
    paid_two.assigned_field_officer_id = officer.id
    db.add(
        SiteVisitAssignment(
            site_visit_request_id=paid_two.id,
            previous_field_officer_id=None,
            field_officer_id=officer.id,
            actor_id=admin.id,
            action="assigned",
            actor_type="admin",
            note="Initial assignment",
        )
    )
    db.commit()

    paid_one_id, paid_two_id, unpaid_id = paid_one.id, paid_two.id, unpaid.id
    actors = {
        key: SimpleNamespace(id=user.id, role=user.role, is_active=user.is_active)
        for key, user in [
            ("admin", admin),
            ("other_admin", other_admin),
            ("super_admin", super_admin),
            ("buyer", buyer),
            ("officer", officer),
            ("inactive_officer", inactive_officer),
            ("accounting", accounting),
        ]
    }
    auth_state = {"user": actors["admin"]}
    db.close()

    app = FastAPI()
    from app.site_visits.router import router

    app.include_router(router)

    def override_db():
        request_db = TestSession()
        try:
            yield request_db
        finally:
            request_db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: auth_state["user"]
    client = TestClient(app)
    try:
        yield client, auth_state, actors, paid_one_id, paid_two_id, unpaid_id, TestSession
    finally:
        client.close()
        engine.dispose()
