"""add registry proofs table

Revision ID: b9d3f2c1a0b1
Revises: a67d159913e2
Create Date: 2026-03-21 22:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b9d3f2c1a0b1"
down_revision = "a67d159913e2"
branch_labels = None
depends_on = None


_TABLE = "sell_land_registry_proofs"


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _ensure_index(name: str, columns: list[str]) -> None:
    indexes = _inspector().get_indexes(_TABLE)
    conflict = next((index for index in indexes if index.get("name") == name), None)
    if conflict is not None and conflict.get("column_names") != columns:
        raise RuntimeError(f"Index {name} exists with incompatible columns {conflict.get('column_names')}.")
    matching = [index for index in indexes if index.get("column_names") == columns]
    if matching:
        if len(matching) > 1:
            raise RuntimeError(f"Duplicate indexes exist on {_TABLE}{tuple(columns)}.")
        if any(index.get("unique", False) for index in matching):
            raise RuntimeError(f"Index on {_TABLE}{tuple(columns)} must be non-unique.")
        return
    op.create_index(name, _TABLE, columns, unique=False)


def _validate_columns() -> None:
    inspector = _inspector()
    columns = {column["name"]: column for column in inspector.get_columns(_TABLE)}
    expected = {
        "id": (sa.Integer, None, False),
        "booking_id": (sa.Integer, None, False),
        "file_url": (sa.String, 500, False),
        "file_name": (sa.String, 255, False),
        "created_at": (sa.DateTime, None, False),
    }
    missing = sorted(set(expected) - set(columns))
    if missing:
        raise RuntimeError(f"Existing {_TABLE} is missing required columns {missing}; refusing to guess values.")
    incompatible = []
    for name, (type_class, length, nullable) in expected.items():
        actual = columns[name]
        if (
            not isinstance(actual["type"], type_class)
            or (length is not None and getattr(actual["type"], "length", None) != length)
            or actual["nullable"] != nullable
        ):
            incompatible.append(name)
    if incompatible:
        raise RuntimeError(f"Existing {_TABLE} has incompatible column definitions: {incompatible}.")
    created_default = columns["created_at"].get("default")
    normalized_default = (
        str(created_default).strip().strip("()'\"").lower() if created_default is not None else ""
    )
    if normalized_default not in {"now", "current_timestamp"}:
        raise RuntimeError(f"{_TABLE}.created_at must have a current-timestamp server default.")
    primary_key = inspector.get_pk_constraint(_TABLE).get("constrained_columns") or []
    if primary_key != ["id"]:
        raise RuntimeError(f"Existing {_TABLE} must have id as its sole primary key.")


def _complete_empty_partial_table() -> None:
    inspector = _inspector()
    if not inspector.has_table(_TABLE):
        return
    columns = {column["name"] for column in inspector.get_columns(_TABLE)}
    expected = {
        "booking_id": sa.Column("booking_id", sa.Integer(), nullable=False),
        "file_url": sa.Column("file_url", sa.String(length=500), nullable=False),
        "file_name": sa.Column("file_name", sa.String(length=255), nullable=False),
        "created_at": sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    }
    missing = [name for name in expected if name not in columns]
    if not missing:
        return
    if "id" not in columns:
        raise RuntimeError(f"Existing {_TABLE} has no id column; refusing structural repair.")
    count = op.get_bind().execute(sa.text(f"SELECT COUNT(*) FROM {_TABLE}")).scalar_one()
    if count:
        raise RuntimeError(
            f"Existing non-empty {_TABLE} is missing columns {missing}; refusing to invent proof data."
        )
    for name in missing:
        op.add_column(_TABLE, expected[name])


def _ensure_booking_fk() -> None:
    foreign_keys = _inspector().get_foreign_keys(_TABLE)
    matching = [fk for fk in foreign_keys if fk.get("constrained_columns") == ["booking_id"]]
    if len(matching) > 1:
        raise RuntimeError(f"Multiple foreign keys exist on {_TABLE}.booking_id.")
    if any(
        fk.get("referred_table") != "sell_land_bookings" or fk.get("referred_columns") != ["id"]
        for fk in matching
    ):
        raise RuntimeError(f"Existing {_TABLE}.booking_id FK has an incompatible target.")
    if not matching:
        op.create_foreign_key(
            "fk_sell_land_registry_proofs_booking_id_sell_land_bookings",
            _TABLE,
            "sell_land_bookings",
            ["booking_id"],
            ["id"],
        )


def upgrade() -> None:
    if not _inspector().has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False, autoincrement=True),
            sa.Column("booking_id", sa.Integer(), nullable=False),
            sa.Column("file_url", sa.String(length=500), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    _complete_empty_partial_table()
    _validate_columns()
    # id is indexed in the SQLAlchemy model as well as being the primary key.
    _ensure_index("ix_sell_land_registry_proofs_id", ["id"])
    _ensure_index("ix_sell_land_registry_proofs_booking_id", ["booking_id"])
    _ensure_booking_fk()


def downgrade() -> None:
    raise RuntimeError("Automatic downgrade is disabled to preserve registry proof records.")
