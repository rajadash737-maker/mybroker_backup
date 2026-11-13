"""Integration tests for the booking repair.

Set MIGRATION_TEST_ADMIN_URL to a local MySQL administrative URL for a
disposable server. Tests create uniquely named `mybroker_migration_test_*`
databases and intentionally never connect to the configured application DB or
drop test databases. The server must permit CREATE DATABASE.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[1]
REVISION_18 = "20260318_0001_offer_amount_numeric"
REVISION_29 = "20260414_0029"
NEW_HEAD = "20261103_0030_request_fields"
SECURITY_HEAD = "20261106_0031_otp_security"
REVISION_22 = "20260404_0022"
REVISION_23 = "20260404_0023"


class BookingMigrationMySQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        admin_url = os.getenv("MIGRATION_TEST_ADMIN_URL")
        if not admin_url:
            raise unittest.SkipTest("Set MIGRATION_TEST_ADMIN_URL to a local disposable MySQL server.")
        cls.admin_url = make_url(admin_url)
        if cls.admin_url.drivername not in {"mysql+pymysql", "mysql+mysqldb", "mysql"}:
            raise unittest.SkipTest("Migration integration tests require MySQL.")
        if cls.admin_url.host not in {"localhost", "127.0.0.1", "::1"}:
            raise unittest.SkipTest("Tests refuse non-local MySQL hosts to prevent production access.")
        if (cls.admin_url.database or "").lower() == "mybroker_db":
            raise unittest.SkipTest("Tests refuse the configured mybroker_db database.")
        cls.admin_engine = create_engine(cls.admin_url, pool_pre_ping=True)

    @classmethod
    def tearDownClass(cls) -> None:
        engine = getattr(cls, "admin_engine", None)
        if engine is not None:
            engine.dispose()

    def setUp(self) -> None:
        self.database = f"mybroker_migration_test_{uuid.uuid4().hex[:12]}"
        with self.admin_engine.begin() as connection:
            exists = connection.execute(
                text("SELECT SCHEMA_NAME FROM information_schema.schemata WHERE SCHEMA_NAME = :name"),
                {"name": self.database},
            ).scalar_one_or_none()
            if exists:
                self.fail("Generated disposable schema unexpectedly already exists.")
            connection.exec_driver_sql(
                f"CREATE DATABASE `{self.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        self.database_url = self.admin_url.set(database=self.database)
        self.engine = create_engine(self.database_url, pool_pre_ping=True)

    def tearDown(self) -> None:
        if hasattr(self, "engine"):
            self.engine.dispose()

    def _alembic(self, revision: str) -> None:
        env = os.environ.copy()
        env["DATABASE_URL"] = self.database_url.render_as_string(hide_password=False)
        env["DATABASE_ECHO"] = "0"
        run = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if run.returncode:
            # Do not include the DB URL in assertion output.
            self.fail(f"Alembic upgrade to {revision} failed (exit {run.returncode}).\n{run.stdout}")

        if revision == REVISION_18:
            version_column = next(
                column for column in inspect(self.engine).get_columns("alembic_version")
                if column["name"] == "version_num"
            )
            self.assertEqual(version_column["type"].length, 128)
            with self.engine.connect() as connection:
                stored_revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
            self.assertEqual(stored_revision, REVISION_18)

    def _base_revision(self) -> None:
        self._alembic(REVISION_18)

    def _set_revision_marker(self, revision: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text("UPDATE alembic_version SET version_num=:revision"),
                {"revision": revision},
            )

    def test_long_revision_id_and_existing_revision_link(self) -> None:
        self._base_revision()
        self.assertEqual(REVISION_18, "20260318_0001_offer_amount_numeric")
        revision_file = (ROOT / "alembic" / "versions" / f"{REVISION_18}.py").read_text()
        self.assertIn(f'revision = "{REVISION_18}"', revision_file)
        self.assertIn('down_revision = "20260316_0018"', revision_file)

    def test_revisions_24_through_29_retry_when_ddl_is_complete_but_marker_is_old(self) -> None:
        self._base_revision()
        self._alembic(NEW_HEAD)

        retry_pairs = (
            ("20260405_0024", "20260404_0023"),
            ("20260405_0025", "20260405_0024"),
            ("20260405_0026", "20260405_0025"),
            ("20260413_0027", "20260405_0026"),
            ("20260414_0028", "20260413_0027"),
            ("20260414_0029", "20260414_0028"),
        )
        for revision, parent in retry_pairs:
            with self.subTest(revision=revision):
                self._set_revision_marker(parent)
                self._alembic(revision)
                with self.engine.connect() as connection:
                    self.assertEqual(
                        connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
                        revision,
                    )
        self._alembic(NEW_HEAD)

    def test_processing_fee_retry_completes_missing_post_create_index(self) -> None:
        self._base_revision()
        self._alembic(REVISION_23)
        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                """CREATE TABLE processing_fee_settings (
                    id INT NOT NULL AUTO_INCREMENT,
                    seller_processing_fee FLOAT NOT NULL DEFAULT 999.0,
                    buyer_processing_fee FLOAT NOT NULL DEFAULT 1000.0,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB"""
            )

        # Model the committed CREATE TABLE followed by interruption before
        # Alembic's separate CREATE INDEX operation.
        self._alembic("20260405_0024")
        indexes = {index["name"] for index in inspect(self.engine).get_indexes("processing_fee_settings")}
        self.assertIn("ix_processing_fee_settings_id", indexes)

    def test_security_revision_adds_otp_and_payment_verification_state(self) -> None:
        self._base_revision()
        self._alembic(SECURITY_HEAD)
        otp_columns = {column["name"]: column for column in inspect(self.engine).get_columns("otps")}
        payment_columns = {
            column["name"]: column for column in inspect(self.engine).get_columns("sell_land_payments")
        }
        self.assertEqual(otp_columns["attempt_count"]["nullable"], False)
        self.assertIn("consumed_at", otp_columns)
        self.assertIn("otp_hash", otp_columns)
        self.assertIn("gateway_payment_id", payment_columns)
        payment_indexes = {
            index["name"]: index for index in inspect(self.engine).get_indexes("sell_land_payments")
        }
        self.assertTrue(payment_indexes["ix_sell_land_payments_gateway_payment_id"]["unique"])

    def _seed_parent_rows(self) -> tuple[int, int]:
        with self.engine.begin() as connection:
            user_id = connection.execute(
                text("INSERT INTO users (fullname) VALUES ('migration-test')")
            ).lastrowid
            request_id = connection.execute(
                text(
                    "INSERT INTO sell_land_requests (user_id, land_type, ownership_type, area_unit) "
                    "VALUES (:user_id, 'residential', 'single_owner', 'sqft')"
                ),
                {"user_id": user_id},
            ).lastrowid
        return int(user_id), int(request_id)

    def _insert_booking_amount(self, value: int) -> int:
        user_id, request_id = self._seed_parent_rows()
        with self.engine.begin() as connection:
            result = connection.execute(
                text(
                    "INSERT INTO sell_land_bookings "
                    "(request_id, buyer_id, buyer_name, buyer_mobile, deal_amount, "
                    "booking_fee_amount, payment_status) "
                    "VALUES (:request_id, :buyer_id, 'Numeric migration test', '9000000000', "
                    ":amount, 1000, 'initiated')"
                ),
                {"request_id": request_id, "buyer_id": user_id, "amount": value},
            )
            return int(result.lastrowid)

    def _upgrade_to_22(self) -> None:
        self._alembic(REVISION_22)

    def _create_base_booking(self, *, partial_officer: bool = False, with_indexes: bool = True) -> int:
        user_id, request_id = self._seed_parent_rows()
        ddl = """
            CREATE TABLE sell_land_bookings (
                id INT NOT NULL AUTO_INCREMENT,
                request_id INT NOT NULL,
                buyer_id INT NOT NULL,
                buyer_name VARCHAR(120) NOT NULL,
                buyer_mobile VARCHAR(20) NOT NULL,
                aadhaar_number VARCHAR(20) NULL DEFAULT '',
                pan_number VARCHAR(20) NULL DEFAULT '',
                bank_account VARCHAR(30) NULL DEFAULT '',
                aadhaar_doc_url VARCHAR(500) NULL,
                aadhaar_doc_name VARCHAR(255) NULL,
                pan_doc_url VARCHAR(500) NULL,
                pan_doc_name VARCHAR(255) NULL,
                bank_doc_url VARCHAR(500) NULL,
                bank_doc_name VARCHAR(255) NULL,
                deal_amount FLOAT NOT NULL,
                booking_fee_amount FLOAT NOT NULL,
                payment_status VARCHAR(20) NOT NULL,
                paid_at DATETIME NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                CONSTRAINT fk_test_booking_request FOREIGN KEY (request_id) REFERENCES sell_land_requests (id),
                CONSTRAINT fk_test_booking_buyer FOREIGN KEY (buyer_id) REFERENCES users (id)
                __INDEXES__
            ) ENGINE=InnoDB
        """
        if partial_officer:
            ddl = ddl.replace(
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,",
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,\n"
                "                assigned_field_officer_id INT NULL,",
            )
        if with_indexes:
            ddl = ddl.replace(
                "__INDEXES__",
                ",\n                INDEX ix_sell_land_bookings_id (id),"
                "\n                INDEX ix_sell_land_bookings_request_id (request_id),"
                "\n                INDEX ix_sell_land_bookings_buyer_id (buyer_id)",
            )
        else:
            ddl = ddl.replace("__INDEXES__", "")
        with self.engine.begin() as connection:
            connection.exec_driver_sql(ddl)
            result = connection.execute(
                text(
                    "INSERT INTO sell_land_bookings "
                    "(request_id, buyer_id, buyer_name, buyer_mobile, deal_amount, "
                    "booking_fee_amount, payment_status) "
                    "VALUES (:request_id, :buyer_id, 'Existing buyer', '9000000000', 123456.0, 1000, 'initiated')"
                ),
                {"request_id": request_id, "buyer_id": user_id},
            )
            booking_id = int(result.lastrowid)
        return booking_id

    def _assert_booking_fk_and_indexes(self) -> None:
        inspector = inspect(self.engine)
        fks = inspector.get_foreign_keys("sell_land_bookings")
        references = {
            (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
            for fk in fks
        }
        self.assertIn((("request_id",), "sell_land_requests", ("id",)), references)
        self.assertIn((("buyer_id",), "users", ("id",)), references)
        self.assertIn((("assigned_field_officer_id",), "users", ("id",)), references)
        indexed = {tuple(index["column_names"]) for index in inspector.get_indexes("sell_land_bookings")}
        for column in ("id", "request_id", "buyer_id", "assigned_field_officer_id"):
            self.assertIn((column,), indexed)

    def test_missing_booking_table_upgrades_through_head_and_request_repair(self) -> None:
        self._base_revision()
        self.assertFalse(inspect(self.engine).has_table("sell_land_bookings"))
        self._alembic(REVISION_29)
        self._alembic(NEW_HEAD)
        self._assert_booking_fk_and_indexes()
        reflected = {column["name"]: column for column in inspect(self.engine).get_columns("sell_land_bookings")}
        columns = set(reflected)
        self.assertTrue({"booking_status", "payment_method", "payment_transaction_id", "registry_notes"}.issubset(columns))
        self.assertTrue(all(reflected[name]["nullable"] for name in ("aadhaar_number", "pan_number", "bank_account")))
        deal_type = reflected["deal_amount"]["type"]
        self.assertEqual((deal_type.precision, deal_type.scale), (18, 0))
        request_columns = {column["name"] for column in inspect(self.engine).get_columns("sell_land_requests")}
        self.assertTrue({"assigned_field_officer_id", "lock_started_at", "lock_expires_at"}.issubset(request_columns))

    def test_existing_booking_rows_survive_full_upgrade(self) -> None:
        self._base_revision()
        booking_id = self._create_base_booking()
        self._alembic(REVISION_29)
        self._alembic(NEW_HEAD)
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT buyer_name, deal_amount FROM sell_land_bookings WHERE id=:id"),
                {"id": booking_id},
            ).one()
        self.assertEqual(row.buyer_name, "Existing buyer")
        self.assertEqual(str(row.deal_amount), "123456")
        self._assert_booking_fk_and_indexes()

    def test_partial_assigned_officer_ddl_is_completed_without_duplicate_objects(self) -> None:
        self._base_revision()
        booking_id = self._create_base_booking(partial_officer=True)
        self._alembic(REVISION_29)
        self._alembic(NEW_HEAD)
        self._assert_booking_fk_and_indexes()
        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(
                    text("SELECT COUNT(*) FROM sell_land_bookings WHERE id=:id"), {"id": booking_id}
                ).scalar_one(),
                1,
            )

    def test_existing_registry_proof_table_and_rows_are_preserved(self) -> None:
        self._base_revision()
        booking_id = self._create_base_booking()
        self._alembic("a67d159913e2")
        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                """CREATE TABLE sell_land_registry_proofs (
                    id INT NOT NULL AUTO_INCREMENT,
                    booking_id INT NOT NULL,
                    file_url VARCHAR(500) NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    CONSTRAINT fk_test_proof_booking FOREIGN KEY (booking_id) REFERENCES sell_land_bookings (id)
                ) ENGINE=InnoDB"""
            )
            connection.execute(
                text("INSERT INTO sell_land_registry_proofs (booking_id, file_url, file_name) VALUES (:id, 'u', 'f')"),
                {"id": booking_id},
            )
        self._alembic("b9d3f2c1a0b1")
        self._alembic(NEW_HEAD)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM sell_land_registry_proofs")).scalar_one(), 1)
        proof_indexes = {tuple(index["column_names"]) for index in inspect(self.engine).get_indexes("sell_land_registry_proofs")}
        self.assertIn(("id",), proof_indexes)
        self.assertIn(("booking_id",), proof_indexes)

    def test_float_12_deal_amount_converts_to_decimal_and_preserves_data(self) -> None:
        self._upgrade_to_22()
        # Keep within exact single-precision integer range for FLOAT(12).
        booking_id = self._insert_booking_amount(1234567)
        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE sell_land_bookings MODIFY deal_amount FLOAT(12) NOT NULL"
            )

        self._alembic(REVISION_23)

        amount = next(
            column for column in inspect(self.engine).get_columns("sell_land_bookings")
            if column["name"] == "deal_amount"
        )
        self.assertEqual((amount["type"].precision, amount["type"].scale), (18, 0))
        self.assertFalse(amount["nullable"])
        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(
                    text("SELECT deal_amount FROM sell_land_bookings WHERE id=:id"),
                    {"id": booking_id},
                ).scalar_one(),
                1234567,
            )

    def test_already_correct_decimal_column_is_accepted(self) -> None:
        self._upgrade_to_22()
        booking_id = self._insert_booking_amount(250000)
        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE sell_land_bookings MODIFY deal_amount DECIMAL(18, 0) NOT NULL"
            )

        self._alembic(REVISION_23)

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(
                    text("SELECT deal_amount FROM sell_land_bookings WHERE id=:id"),
                    {"id": booking_id},
                ).scalar_one(),
                250000,
            )

    def test_retry_after_float_to_decimal_ddl_before_revision_record(self) -> None:
        self._upgrade_to_22()
        booking_id = self._insert_booking_amount(7654321)
        # First run performs the DDL. Move only this disposable test schema's
        # version marker back to model interruption before Alembic records 0023.
        self._alembic(REVISION_23)
        with self.engine.begin() as connection:
            connection.execute(
                text("UPDATE alembic_version SET version_num=:revision"),
                {"revision": REVISION_22},
            )

        # Retrying must recognize the committed DECIMAL DDL and safely advance.
        self._alembic(REVISION_23)

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(
                    text("SELECT deal_amount FROM sell_land_bookings WHERE id=:id"),
                    {"id": booking_id},
                ).scalar_one(),
                7654321,
            )


if __name__ == "__main__":
    unittest.main()

