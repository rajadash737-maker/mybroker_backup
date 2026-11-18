"""Create an isolated Site Visit test database and migrate it through 0041.

On success, the baseline database is retained for the separate 0042 runner.
If this process creates the database but fails before baseline verification,
it drops only that database during cleanup.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import NoReturn


DATABASE_NAME = "mybroker_sitevisit_test_0174e41d408a4d31bdb3012ae84c2d51"
DATABASE_NAME_PATTERN = r"mybroker_sitevisit_test_[0-9a-f]{32}"
FORBIDDEN_DATABASE = "mybroker_db"
EXPECTED_HOST = "127.0.0.1"
EXPECTED_USER = "mybroker_sitevisit_test_admin"
TARGET_REVISION = "20261115_0041_unique_razorpay_webhook_event_key"
EXPECTED_PARENT_REVISION = "20261115_0040_site_visit_payment_attempt_link"
ENV_KEYS = (
    "SITE_VISIT_TEST_MYSQL_HOST",
    "SITE_VISIT_TEST_MYSQL_PORT",
    "SITE_VISIT_TEST_MYSQL_USER",
    "SITE_VISIT_TEST_MYSQL_PASSWORD",
)


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"Refusing to run: {message}")


def main() -> None:
    if DATABASE_NAME == FORBIDDEN_DATABASE:
        _fail("the application database is forbidden")
    if not re.fullmatch(DATABASE_NAME_PATTERN, DATABASE_NAME):
        _fail("the approved database name does not match the exact temporary format")

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

    # Set this before importing SQLAlchemy, project settings, or Alembic.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"

    from sqlalchemy import URL, create_engine, text

    admin_url = URL.create(
        "mysql+pymysql",
        username=username,
        password=os.environ["SITE_VISIT_TEST_MYSQL_PASSWORD"],
        host=host,
        port=port,
    )
    admin_engine = create_engine(admin_url, pool_pre_ping=True, pool_recycle=60)
    database_created = False
    baseline_verified = False
    test_engine = None

    try:
        # Verify the authenticated account and ensure no schema is selected
        # before creating anything. Also refuse to reuse an existing target.
        with admin_engine.connect() as connection:
            authenticated_user, selected_database, schema_count = connection.execute(
                text(
                    "SELECT CURRENT_USER(), DATABASE(), "
                    "(SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = :schema_name)"
                ),
                {"schema_name": DATABASE_NAME},
            ).one()
        if str(authenticated_user).split("@", 1)[0] != EXPECTED_USER:
            _fail("MySQL authenticated a different account")
        if selected_database is not None:
            _fail("the server connection unexpectedly selected a database")
        if int(schema_count) != 0:
            _fail("the approved temporary database already exists")

        with admin_engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE `{DATABASE_NAME}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
        database_created = True

        test_url = URL.create(
            "mysql+pymysql",
            username=username,
            password=os.environ["SITE_VISIT_TEST_MYSQL_PASSWORD"],
            host=host,
            port=port,
            database=DATABASE_NAME,
        )
        # Only this validated URL is exposed to application settings/Alembic.
        os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
        test_engine = create_engine(test_url, pool_pre_ping=True, pool_recycle=60)

        with test_engine.connect() as connection:
            authenticated_user, selected_database, table_count = connection.execute(
                text(
                    "SELECT CURRENT_USER(), DATABASE(), "
                    "(SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE())"
                )
            ).one()
        if str(authenticated_user).split("@", 1)[0] != EXPECTED_USER:
            _fail("MySQL authenticated a different account for the target database")
        if selected_database != DATABASE_NAME or selected_database == FORBIDDEN_DATABASE:
            _fail("MySQL selected a different or forbidden database")
        if int(table_count) != 0:
            _fail("the newly created target database is not empty")

        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        project_root = Path(__file__).resolve().parents[1]
        alembic_config = Config(str(project_root / "alembic.ini"))
        alembic_config.set_main_option(
            "sqlalchemy.url",
            test_url.render_as_string(hide_password=False).replace("%", "%%"),
        )
        target_script = ScriptDirectory.from_config(alembic_config).get_revision(TARGET_REVISION)
        if target_script is None or target_script.down_revision != EXPECTED_PARENT_REVISION:
            _fail("approved baseline revision has an unexpected parent")

        command.upgrade(alembic_config, TARGET_REVISION)

        with test_engine.connect() as connection:
            revisions = [
                str(row[0])
                for row in connection.execute(text("SELECT version_num FROM alembic_version")).all()
            ]
        if revisions != [TARGET_REVISION]:
            _fail("baseline verification did not find exactly the approved revision")

        baseline_verified = True
        print(f"Baseline verified for {DATABASE_NAME} at {TARGET_REVISION}.")
    except SystemExit:
        raise
    except Exception:
        _fail("baseline operation failed; details withheld")
    finally:
        try:
            if test_engine is not None:
                test_engine.dispose()
        finally:
            try:
                if database_created and not baseline_verified:
                    try:
                        if (
                            DATABASE_NAME == FORBIDDEN_DATABASE
                            or not re.fullmatch(DATABASE_NAME_PATTERN, DATABASE_NAME)
                        ):
                            _fail("cleanup target failed validation")
                        with admin_engine.begin() as connection:
                            connection.execute(text(f"DROP DATABASE `{DATABASE_NAME}`"))
                    except Exception:
                        _fail("temporary database cleanup failed; details withheld")
            finally:
                admin_engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("Baseline runner failed; details withheld.") from None
