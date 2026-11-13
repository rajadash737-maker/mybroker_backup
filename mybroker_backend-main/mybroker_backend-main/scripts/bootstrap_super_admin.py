"""Create the initial MyBrokerr Super Admin and verify its existing auth path.

Run from the backend project root with:
    python scripts/bootstrap_super_admin.py
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.auth.schemas import LoginSchema
from app.auth.service import login_user, pwd_context
from app.database import SessionLocal
from app.main import app
from app.users.model import User
from app.users.roles import UserRole


EMAIL = "rajadash737@gmail.com"


def main() -> int:
    password = getpass.getpass("Password for rajadash737@gmail.com: ")
    if not 8 <= len(password) <= 128:
        print("Password must be between 8 and 128 characters.", file=sys.stderr)
        return 2

    db = SessionLocal()
    created = False
    try:
        existing = db.query(User).filter(User.email == EMAIL).with_for_update().first()
        if existing is not None:
            print("Account already exists; it was not changed.")
            if existing.role != UserRole.SUPER_ADMIN.value:
                print("Existing account is not SUPER_ADMIN; no changes were made.", file=sys.stderr)
                return 3
            if not pwd_context.verify(password, existing.password_hash):
                print("Existing SUPER_ADMIN credentials did not authenticate.", file=sys.stderr)
                return 4
            user_id = existing.id
        else:
            user = User(
                fullname="Super Admin",
                email=EMAIL,
                password_hash=pwd_context.hash(password),
                role=UserRole.SUPER_ADMIN.value,
                is_active=True,
            )
            db.add(user)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                # Another process may have inserted the unique email meanwhile.
                existing = db.query(User).filter(User.email == EMAIL).first()
                if existing is None:
                    raise
                print("Account already exists; it was not changed.")
                if existing.role != UserRole.SUPER_ADMIN.value:
                    print("Existing account is not SUPER_ADMIN; no changes were made.", file=sys.stderr)
                    return 3
                if not pwd_context.verify(password, existing.password_hash):
                    print("Existing SUPER_ADMIN credentials did not authenticate.", file=sys.stderr)
                    return 4
                user_id = existing.id
            else:
                db.refresh(user)
                user_id = user.id
                created = True
    finally:
        db.close()

    # Exercise the production login service, then make a real authenticated API
    # request through FastAPI's normal dependency and role checks.
    auth_db = SessionLocal()
    try:
        login_result = login_user(
            auth_db,
            LoginSchema(identifier=EMAIL, password=password),
        )
        if login_result.get("status") != "Login successful":
            print("Login service verification failed.", file=sys.stderr)
            return 5
        if login_result.get("user_id") != user_id:
            print("Login service returned an unexpected user.", file=sys.stderr)
            return 5
        access_token = login_result["tokens"]["access_token"]
    finally:
        auth_db.close()

    response = TestClient(app).get(
        "/admin/staff",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code != 200:
        print(
            f"Protected admin API verification failed (HTTP {response.status_code}).",
            file=sys.stderr,
        )
        return 6

    print("Login verification: passed.")
    print("SUPER_ADMIN protected API verification (/admin/staff): passed.")
    print("Account creation: " + ("created." if created else "existing account verified; unchanged."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
