"""add notification_reads table

Revision ID: 20260414_0028
Revises: 20260413_0027
Create Date: 2026-04-14 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260414_0028"
down_revision = "20260413_0027"
branch_labels = None
depends_on = None


def _normalize_default(value):
    if value is None:
        return None
    return str(value).strip().strip("()'\"").lower()


def _validate_table():
    table = "notification_reads"
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"]: column for column in inspector.get_columns(table)}
    expected = {
        "id": (sa.Integer, None, False, None),
        "user_id": (sa.Integer, None, False, None),
        "property_id": (sa.String, 64, False, None),
        "read_at": (sa.DateTime, None, False, {"current_timestamp", "now"}),
    }
    missing = sorted(set(expected) - set(columns))
    if missing:
        raise RuntimeError(f"{table} is missing required columns {missing}; refusing repair.")
    for name, (type_class, length, nullable, defaults) in expected.items():
        actual = columns[name]
        if (
            not isinstance(actual["type"], type_class)
            or (length is not None and getattr(actual["type"], "length", None) != length)
            or actual["nullable"] != nullable
        ):
            raise RuntimeError(f"Incompatible {table}.{name}: {actual['type']} nullable={actual['nullable']}.")
        if defaults is not None and _normalize_default(actual.get("default")) not in defaults:
            raise RuntimeError(f"Incompatible server default on {table}.{name}.")

    if (inspector.get_pk_constraint(table).get("constrained_columns") or []) != ["id"]:
        raise RuntimeError(f"{table} must use id as its sole primary key.")
    unique_constraints = inspector.get_unique_constraints(table)
    if len([item for item in unique_constraints if item.get("column_names") == ["user_id", "property_id"]]) != 1:
        raise RuntimeError(f"{table} must have exactly one unique (user_id, property_id) constraint.")
    foreign_keys = inspector.get_foreign_keys(table)
    user_fks = [fk for fk in foreign_keys if fk.get("constrained_columns") == ["user_id"]]
    if len(user_fks) != 1 or user_fks[0].get("referred_table") != "users" or user_fks[0].get("referred_columns") != ["id"]:
        raise RuntimeError(f"{table}.user_id has a missing or incompatible foreign key.")


def _ensure_index(name, columns):
    indexes = sa.inspect(op.get_bind()).get_indexes("notification_reads")
    named = next((index for index in indexes if index.get("name") == name), None)
    if named is not None:
        if named.get("column_names") != columns or named.get("unique", False):
            raise RuntimeError(f"Index {name} exists with an incompatible definition.")
        return
    equivalent = [
        index for index in indexes
        if index.get("column_names") == columns and not index.get("unique", False)
    ]
    if len(equivalent) > 1:
        raise RuntimeError(f"Duplicate non-unique indexes exist on notification_reads{tuple(columns)}.")
    if not equivalent:
        op.create_index(name, "notification_reads", columns, unique=False)


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("notification_reads"):
        op.create_table(
            "notification_reads",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("property_id", sa.String(length=64), nullable=False),
            sa.Column("read_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.UniqueConstraint("user_id", "property_id", name="uq_notification_read_user_property"),
        )
    _validate_table()
    _ensure_index("ix_notification_reads_user_id", ["user_id"])
    _ensure_index("ix_notification_reads_property_id", ["property_id"])


def downgrade():
    op.drop_index("ix_notification_reads_property_id", table_name="notification_reads")
    op.drop_index("ix_notification_reads_user_id", table_name="notification_reads")
    op.drop_table("notification_reads")
