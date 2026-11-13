"""create missing booking base table and assign field officers

Revision ID: 2e6b8c73ace0
Revises: 20260318_0001_offer_amount_numeric
Create Date: 2026-03-20 19:14:21.330190
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "2e6b8c73ace0"
down_revision = "20260318_0001_offer_amount_numeric"
branch_labels = None
depends_on = None


_BOOKING_BASE_COLUMNS = {
    "id": (sa.Integer, False, None),
    "request_id": (sa.Integer, False, None),
    "buyer_id": (sa.Integer, False, None),
    "buyer_name": (sa.String, False, 120),
    "buyer_mobile": (sa.String, False, 20),
    "aadhaar_number": (sa.String, True, 20),
    "pan_number": (sa.String, True, 20),
    "bank_account": (sa.String, True, 30),
    "aadhaar_doc_url": (sa.String, True, 500),
    "aadhaar_doc_name": (sa.String, True, 255),
    "pan_doc_url": (sa.String, True, 500),
    "pan_doc_name": (sa.String, True, 255),
    "bank_doc_url": (sa.String, True, 500),
    "bank_doc_name": (sa.String, True, 255),
    "deal_amount": (sa.Float, False, None),
    "booking_fee_amount": (sa.Float, False, None),
    "payment_status": (sa.String, False, 20),
    "paid_at": (sa.DateTime, True, None),
    "created_at": (sa.DateTime, False, None),
}
_BOOKING_COLUMN_DEFINITIONS = {
    "request_id": sa.Column("request_id", sa.Integer(), nullable=False),
    "buyer_id": sa.Column("buyer_id", sa.Integer(), nullable=False),
    "buyer_name": sa.Column("buyer_name", sa.String(length=120), nullable=False),
    "buyer_mobile": sa.Column("buyer_mobile", sa.String(length=20), nullable=False),
    "aadhaar_number": sa.Column("aadhaar_number", sa.String(length=20), nullable=True, server_default=""),
    "pan_number": sa.Column("pan_number", sa.String(length=20), nullable=True, server_default=""),
    "bank_account": sa.Column("bank_account", sa.String(length=30), nullable=True, server_default=""),
    "aadhaar_doc_url": sa.Column("aadhaar_doc_url", sa.String(length=500), nullable=True),
    "aadhaar_doc_name": sa.Column("aadhaar_doc_name", sa.String(length=255), nullable=True),
    "pan_doc_url": sa.Column("pan_doc_url", sa.String(length=500), nullable=True),
    "pan_doc_name": sa.Column("pan_doc_name", sa.String(length=255), nullable=True),
    "bank_doc_url": sa.Column("bank_doc_url", sa.String(length=500), nullable=True),
    "bank_doc_name": sa.Column("bank_doc_name", sa.String(length=255), nullable=True),
    "deal_amount": sa.Column("deal_amount", sa.Float(), nullable=False),
    "booking_fee_amount": sa.Column("booking_fee_amount", sa.Float(), nullable=False),
    "payment_status": sa.Column("payment_status", sa.String(length=20), nullable=False),
    "paid_at": sa.Column("paid_at", sa.DateTime(), nullable=True),
    "created_at": sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
}


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _column_type_matches(actual: sa.types.TypeEngine, expected: tuple[type, bool, int | None]) -> bool:
    type_class, _nullable, length = expected
    if not isinstance(actual, type_class):
        return False
    if length is not None and getattr(actual, "length", None) != length:
        return False
    return True


def _validate_base_table() -> None:
    inspector = _inspector()
    columns = {column["name"]: column for column in inspector.get_columns("sell_land_bookings")}
    missing = sorted(set(_BOOKING_BASE_COLUMNS) - set(columns))
    if missing:
        row_count = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM sell_land_bookings")).scalar_one()
        if row_count:
            raise RuntimeError(
                "Existing non-empty sell_land_bookings is missing base columns "
                f"{missing}; refusing to guess backfill values."
            )
        if "id" in missing:
            raise RuntimeError("Existing sell_land_bookings has no primary key; refusing structural repair.")
        for name in missing:
            op.add_column("sell_land_bookings", _BOOKING_COLUMN_DEFINITIONS[name])
        inspector = _inspector()
        columns = {column["name"]: column for column in inspector.get_columns("sell_land_bookings")}

    incompatible = []
    for name, expected in _BOOKING_BASE_COLUMNS.items():
        actual = columns[name]
        if not _column_type_matches(actual["type"], expected) or actual["nullable"] != expected[1]:
            incompatible.append(
                f"{name}: got {actual['type']} nullable={actual['nullable']}, "
                f"expected {expected[0].__name__} length={expected[2]} nullable={expected[1]}"
            )
    for name in ("aadhaar_number", "pan_number", "bank_account"):
        raw_default = columns[name].get("default")
        default = str(raw_default).strip().strip("()'\"").lower() if raw_default is not None else None
        if default is None or default != "":
            raise RuntimeError(f"sell_land_bookings.{name} must retain the empty-string server default.")
    raw_created_default = columns["created_at"].get("default")
    created_default = (
        str(raw_created_default).strip().strip("()'\"").lower()
        if raw_created_default is not None
        else ""
    )
    if created_default not in {"current_timestamp", "now"}:
        raise RuntimeError("sell_land_bookings.created_at must have its current-timestamp server default.")
    if incompatible:
        raise RuntimeError("Incompatible sell_land_bookings base schema: " + "; ".join(incompatible))
    primary_key = inspector.get_pk_constraint("sell_land_bookings").get("constrained_columns") or []
    if primary_key != ["id"]:
        raise RuntimeError("sell_land_bookings must have id as its sole primary key.")

    expected_fks = {
        "request_id": ("sell_land_requests", "id"),
        "buyer_id": ("users", "id"),
    }
    foreign_keys = inspector.get_foreign_keys("sell_land_bookings")
    for local_column, (target_table, target_column) in expected_fks.items():
        matching = [fk for fk in foreign_keys if fk.get("constrained_columns") == [local_column]]
        if len(matching) > 1:
            raise RuntimeError(f"Multiple foreign keys exist on sell_land_bookings.{local_column}.")
        if not any(
            fk.get("referred_table") == target_table
            and fk.get("referred_columns") == [target_column]
            for fk in matching
        ):
            raise RuntimeError(
                f"sell_land_bookings.{local_column} must reference {target_table}.{target_column}."
            )
        if any(
            fk.get("referred_table") != target_table
            or fk.get("referred_columns") != [target_column]
            for fk in matching
        ):
            raise RuntimeError(f"Incompatible foreign key on sell_land_bookings.{local_column}.")


def _ensure_index(name: str, columns: list[str]) -> None:
    indexes = _inspector().get_indexes("sell_land_bookings")
    same_name = next((index for index in indexes if index.get("name") == name), None)
    if same_name is not None and same_name.get("column_names") != columns:
        raise RuntimeError(f"Index {name} exists with incompatible columns {same_name.get('column_names')}.")
    matching = [index for index in indexes if index.get("column_names") == columns]
    if matching:
        if len(matching) > 1:
            raise RuntimeError(f"Duplicate indexes exist on sell_land_bookings{tuple(columns)}.")
        if any(index.get("unique", False) for index in matching):
            raise RuntimeError(f"Index on sell_land_bookings{tuple(columns)} must be non-unique.")
        return
    op.create_index(name, "sell_land_bookings", columns, unique=False)


def _ensure_base_foreign_keys() -> None:
    expected = {
        "request_id": ("sell_land_requests", "id", "fk_sell_land_bookings_request_id_sell_land_requests"),
        "buyer_id": ("users", "id", "fk_sell_land_bookings_buyer_id_users"),
    }
    foreign_keys = _inspector().get_foreign_keys("sell_land_bookings")
    for local_column, (target_table, target_column, name) in expected.items():
        matching = [fk for fk in foreign_keys if fk.get("constrained_columns") == [local_column]]
        if len(matching) > 1:
            raise RuntimeError(f"Multiple foreign keys exist on sell_land_bookings.{local_column}.")
        if matching:
            fk = matching[0]
            if fk.get("referred_table") != target_table or fk.get("referred_columns") != [target_column]:
                raise RuntimeError(f"Incompatible foreign key on sell_land_bookings.{local_column}.")
            continue
        op.create_foreign_key(
            name,
            "sell_land_bookings",
            target_table,
            [local_column],
            [target_column],
        )


def _ensure_assigned_officer() -> None:
    inspector = _inspector()
    columns = {column["name"]: column for column in inspector.get_columns("sell_land_bookings")}
    if "assigned_field_officer_id" not in columns:
        op.add_column(
            "sell_land_bookings",
            sa.Column("assigned_field_officer_id", sa.Integer(), nullable=True),
        )
    else:
        column = columns["assigned_field_officer_id"]
        if not isinstance(column["type"], sa.Integer) or not column["nullable"]:
            raise RuntimeError("Existing assigned_field_officer_id must be nullable Integer.")

    _ensure_index("ix_sell_land_bookings_assigned_field_officer_id", ["assigned_field_officer_id"])

    fks = _inspector().get_foreign_keys("sell_land_bookings")
    officer_fks = [fk for fk in fks if fk.get("constrained_columns") == ["assigned_field_officer_id"]]
    if len(officer_fks) > 1:
        raise RuntimeError("Multiple foreign keys exist on assigned_field_officer_id.")
    if any(
        fk.get("referred_table") != "users" or fk.get("referred_columns") != ["id"]
        for fk in officer_fks
    ):
        raise RuntimeError("Existing assigned_field_officer_id foreign key has an incompatible target.")
    if not officer_fks:
        op.create_foreign_key(
            "fk_sell_land_bookings_assigned_field_officer_id_users",
            "sell_land_bookings",
            "users",
            ["assigned_field_officer_id"],
            ["id"],
        )


def upgrade() -> None:
    inspector = _inspector()
    if not inspector.has_table("sell_land_bookings"):
        op.create_table(
            "sell_land_bookings",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("buyer_id", sa.Integer(), nullable=False),
            sa.Column("buyer_name", sa.String(length=120), nullable=False),
            sa.Column("buyer_mobile", sa.String(length=20), nullable=False),
            # Revisions 0017 and 0018 make these optional and provide empty defaults.
            sa.Column("aadhaar_number", sa.String(length=20), nullable=True, server_default=""),
            sa.Column("pan_number", sa.String(length=20), nullable=True, server_default=""),
            sa.Column("bank_account", sa.String(length=30), nullable=True, server_default=""),
            sa.Column("aadhaar_doc_url", sa.String(length=500), nullable=True),
            sa.Column("aadhaar_doc_name", sa.String(length=255), nullable=True),
            sa.Column("pan_doc_url", sa.String(length=500), nullable=True),
            sa.Column("pan_doc_name", sa.String(length=255), nullable=True),
            sa.Column("bank_doc_url", sa.String(length=500), nullable=True),
            sa.Column("bank_doc_name", sa.String(length=255), nullable=True),
            # Revision 0023 converts this migration-era Float to Numeric(18, 0).
            sa.Column("deal_amount", sa.Float(), nullable=False),
            sa.Column("booking_fee_amount", sa.Float(), nullable=False),
            sa.Column("payment_status", sa.String(length=20), nullable=False),
            sa.Column("paid_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )
        # Explicit indexes mirror index=True in SellLandBooking, even when a
        # MySQL version also creates supporting indexes for the foreign keys.

    _ensure_index("ix_sell_land_bookings_id", ["id"])
    _ensure_index("ix_sell_land_bookings_request_id", ["request_id"])
    _ensure_index("ix_sell_land_bookings_buyer_id", ["buyer_id"])
    _ensure_base_foreign_keys()
    _validate_base_table()
    _ensure_assigned_officer()


def downgrade() -> None:
    raise RuntimeError(
        "This repair is intentionally irreversible: dropping booking fields or table data is unsafe. "
        "Use a reviewed forward migration instead."
    )
