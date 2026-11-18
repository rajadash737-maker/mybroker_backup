"""Fail-closed runner for the isolated Site Visit MySQL migration test.

This runner targets an already-created disposable database. It does not create
or drop databases. Run it with the dedicated Site Visit test credentials.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import NoReturn


EXPECTED_HOST = "127.0.0.1"
EXPECTED_USER = "mybroker_sitevisit_test_admin"
FORBIDDEN_DATABASE = "mybroker_db"
TARGET_REVISION = "20261115_0042_site_visit_completion_code"
PARENT_REVISION = "20261115_0041_unique_razorpay_webhook_event_key"
DATABASE_NAME_PATTERN = r"mybroker_sitevisit_test_[0-9a-f]{32}"
ENV_KEYS = (
    "SITE_VISIT_TEST_MYSQL_HOST",
    "SITE_VISIT_TEST_MYSQL_PORT",
    "SITE_VISIT_TEST_MYSQL_USER",
    "SITE_VISIT_TEST_MYSQL_PASSWORD",
)


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"Refusing to run: {message}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "database",
        help="Exact disposable database name, beginning with the Site Visit test prefix",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    database_name = args.database

    if database_name == FORBIDDEN_DATABASE:
        _fail("the application database is forbidden")
    if not re.fullmatch(DATABASE_NAME_PATTERN, database_name):
        _fail("database name must match the exact temporary Site Visit format")

    missing = [key for key in ENV_KEYS if not os.environ.get(key)]
    if missing:
        _fail("one or more dedicated Site Visit test connection variables are missing")

    host = os.environ["SITE_VISIT_TEST_MYSQL_HOST"].strip()
    username = os.environ["SITE_VISIT_TEST_MYSQL_USER"].strip()
    if host != EXPECTED_HOST:
        _fail("the test host must be 127.0.0.1")
    if username != EXPECTED_USER:
        _fail("the dedicated Site Visit test account is required")

    try:
        port = int(os.environ["SITE_VISIT_TEST_MYSQL_PORT"])
    except ValueError:
        _fail("the test port must be an integer")
    if not 1 <= port <= 65535:
        _fail("the test port is outside the valid range")

    # This is set before importing SQLAlchemy, project settings, or Alembic.
    # It prevents python-dotenv from loading a .env DATABASE_URL.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"

    from sqlalchemy import URL, create_engine, text

    test_url = URL.create(
        "mysql+pymysql",
        username=username,
        password=os.environ["SITE_VISIT_TEST_MYSQL_PASSWORD"],
        host=host,
        port=port,
        database=database_name,
    )
    # Both the project settings and Alembic env.py consume this process-local
    # value. Set it before importing Alembic so the ini fallback is never used.
    os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)

    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    # Verify server-side identity and selected schema before Alembic can run.
    preflight_engine = create_engine(test_url, pool_pre_ping=True)
    try:
        with preflight_engine.connect() as connection:
            authenticated_user, selected_database = connection.execute(
                text("SELECT CURRENT_USER(), DATABASE()")
            ).one()
    except Exception:
        _fail("database identity check failed; details withheld")
    finally:
        preflight_engine.dispose()

    if str(authenticated_user).split("@", 1)[0] != EXPECTED_USER:
        _fail("MySQL authenticated a different account")
    if selected_database != database_name or selected_database == FORBIDDEN_DATABASE:
        _fail("MySQL selected a different or forbidden database")

    project_root = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(project_root / "alembic.ini"))
    alembic_config.set_main_option(
        "sqlalchemy.url",
        test_url.render_as_string(hide_password=False).replace("%", "%%"),
    )

    def read_revisions() -> list[str]:
        revision_engine = create_engine(test_url, pool_pre_ping=True)
        try:
            with revision_engine.connect() as connection:
                return [
                    str(row[0])
                    for row in connection.execute(text("SELECT version_num FROM alembic_version")).all()
                ]
        finally:
            revision_engine.dispose()

    try:
        script = ScriptDirectory.from_config(alembic_config)
        target_script = script.get_revision(TARGET_REVISION)
        if target_script is None or target_script.down_revision != PARENT_REVISION:
            _fail("approved migration does not have the required parent revision")
        current_revisions = read_revisions()
    except SystemExit:
        raise
    except Exception:
        _fail("database revision precondition failed; details withheld")

    if len(current_revisions) != 1:
        _fail("database must have exactly one Alembic revision")
    if current_revisions[0] != PARENT_REVISION:
        _fail("database is not at the required parent revision")

    try:
        command.upgrade(alembic_config, TARGET_REVISION)
    except Exception:
        _fail("Alembic upgrade failed; details withheld")

    try:
        final_revisions = read_revisions()
    except Exception:
        _fail("final database revision verification failed; details withheld")
    if final_revisions != [TARGET_REVISION]:
        _fail("final database revision does not match the approved revision")
    print(f"Alembic upgrade completed for isolated database {database_name} at {TARGET_REVISION}.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never echo third-party exception text: it may contain connection data.
        raise SystemExit("Runner failed; details withheld.") from None
