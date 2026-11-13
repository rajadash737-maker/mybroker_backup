"""add notifications table

Revision ID: 20260414_0029
Revises: 20260414_0028
Create Date: 2026-04-14 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260414_0029"
down_revision = "20260414_0028"
branch_labels = None
depends_on = None


def _normalize_default(value):
    if value is None:
        return None
    return str(value).strip().strip("()'\"").lower()


def _validate_table():
    table = "notifications"
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"]: column for column in inspector.get_columns(table)}
    expected = {
        "id": (sa.Integer, None, False, None),
        "user_id": (sa.Integer, None, False, None),
        "title": (sa.String, 200, False, None),
        "body": (sa.String, 500, False, None),
        "type": (sa.String, 50, False, None),
        "role_target": (sa.String, 50, True, None),
        "reference_id": (sa.String, 50, True, None),
        "is_read": (None, None, False, {"0", "false"}),
        "created_at": (sa.DateTime, None, False, {"current_timestamp", "now"}),
    }
    missing = sorted(set(expected) - set(columns))
    if missing:
        raise RuntimeError(f"{table} is missing required columns {missing}; refusing repair.")
    for name, (type_class, length, nullable, defaults) in expected.items():
        actual = columns[name]
        if name == "is_read":
            from sqlalchemy.dialects.mysql import TINYINT

            valid_type = isinstance(actual["type"], sa.Boolean) or (
                isinstance(actual["type"], TINYINT)
                and getattr(actual["type"], "display_width", None) in {None, 1}
            )
        else:
            valid_type = isinstance(actual["type"], type_class)
        if (
            not valid_type
            or (length is not None and getattr(actual["type"], "length", None) != length)
            or actual["nullable"] != nullable
        ):
            raise RuntimeError(f"Incompatible {table}.{name}: {actual['type']} nullable={actual['nullable']}.")
        if defaults is not None and _normalize_default(actual.get("default")) not in defaults:
            raise RuntimeError(f"Incompatible server default on {table}.{name}.")

    if (inspector.get_pk_constraint(table).get("constrained_columns") or []) != ["id"]:
        raise RuntimeError(f"{table} must use id as its sole primary key.")
    unique_constraints = inspector.get_unique_constraints(table)
    if len([
        item for item in unique_constraints
        if item.get("column_names") == ["user_id", "reference_id", "type"]
    ]) != 1:
        raise RuntimeError(f"{table} must have exactly one unique (user_id, reference_id, type) constraint.")
    foreign_keys = inspector.get_foreign_keys(table)
    user_fks = [fk for fk in foreign_keys if fk.get("constrained_columns") == ["user_id"]]
    if len(user_fks) != 1 or user_fks[0].get("referred_table") != "users" or user_fks[0].get("referred_columns") != ["id"]:
        raise RuntimeError(f"{table}.user_id has a missing or incompatible foreign key.")


def _ensure_index(name, columns):
    indexes = sa.inspect(op.get_bind()).get_indexes("notifications")
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
        raise RuntimeError(f"Duplicate non-unique indexes exist on notifications{tuple(columns)}.")
    if not equivalent:
        op.create_index(name, "notifications", columns, unique=False)


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("body", sa.String(length=500), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False),
            sa.Column("role_target", sa.String(length=50), nullable=True),
            sa.Column("reference_id", sa.String(length=50), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.UniqueConstraint("user_id", "reference_id", "type", name="uq_notification_user_reference_type"),
        )
    _validate_table()
    _ensure_index("ix_notifications_user_id", ["user_id"])
    _ensure_index("ix_notifications_type", ["type"])
    _ensure_index("ix_notifications_role_target", ["role_target"])
    _ensure_index("ix_notifications_reference_id", ["reference_id"])


def downgrade():
    op.drop_index("ix_notifications_reference_id", table_name="notifications")
    op.drop_index("ix_notifications_role_target", table_name="notifications")
    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
