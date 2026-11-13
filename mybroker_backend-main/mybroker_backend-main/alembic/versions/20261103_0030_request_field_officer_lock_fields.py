"""add missing sell-land request assignment and lock fields

Revision ID: 20261103_0030_request_fields
Revises: 20260414_0029
Create Date: 2026-11-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20261103_0030_request_fields"
down_revision = "20260414_0029"
branch_labels = None
depends_on = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _ensure_column(name: str, column: sa.Column, expected_type: type) -> None:
    inspector = _inspector()
    if not inspector.has_table("sell_land_requests"):
        raise RuntimeError("sell_land_requests must exist before request fields can be migrated.")
    columns = {item["name"]: item for item in inspector.get_columns("sell_land_requests")}
    if name not in columns:
        op.add_column("sell_land_requests", column)
        return
    actual = columns[name]
    if not isinstance(actual["type"], expected_type) or not actual["nullable"]:
        raise RuntimeError(
            f"Incompatible sell_land_requests.{name}: expected nullable {expected_type.__name__}, "
            f"got {actual['type']} nullable={actual['nullable']}."
        )


def _ensure_officer_index() -> None:
    indexes = _inspector().get_indexes("sell_land_requests")
    index_name = "ix_sell_land_requests_assigned_field_officer_id"
    conflict = next((index for index in indexes if index.get("name") == index_name), None)
    if conflict is not None and conflict.get("column_names") != ["assigned_field_officer_id"]:
        raise RuntimeError(f"{index_name} has incompatible columns.")
    matching = [index for index in indexes if index.get("column_names") == ["assigned_field_officer_id"]]
    if matching:
        if len(matching) > 1:
            raise RuntimeError("Duplicate assigned_field_officer_id indexes exist.")
        if any(index.get("unique", False) for index in matching):
            raise RuntimeError("assigned_field_officer_id index must be non-unique.")
        return
    op.create_index(
        index_name,
        "sell_land_requests",
        ["assigned_field_officer_id"],
        unique=False,
    )


def _ensure_officer_fk() -> None:
    foreign_keys = _inspector().get_foreign_keys("sell_land_requests")
    matching = [fk for fk in foreign_keys if fk.get("constrained_columns") == ["assigned_field_officer_id"]]
    if len(matching) > 1:
        raise RuntimeError("Multiple foreign keys exist on request assigned_field_officer_id.")
    if any(fk.get("referred_table") != "users" or fk.get("referred_columns") != ["id"] for fk in matching):
        raise RuntimeError("Existing request assigned-field-officer FK has an incompatible target.")
    if not matching:
        op.create_foreign_key(
            "fk_sell_land_requests_assigned_field_officer_id_users",
            "sell_land_requests",
            "users",
            ["assigned_field_officer_id"],
            ["id"],
        )


def upgrade() -> None:
    _ensure_column(
        "assigned_field_officer_id",
        sa.Column("assigned_field_officer_id", sa.Integer(), nullable=True),
        sa.Integer,
    )
    _ensure_officer_index()
    _ensure_officer_fk()
    _ensure_column("lock_started_at", sa.Column("lock_started_at", sa.DateTime(), nullable=True), sa.DateTime)
    _ensure_column("lock_expires_at", sa.Column("lock_expires_at", sa.DateTime(), nullable=True), sa.DateTime)


def downgrade() -> None:
    raise RuntimeError(
        "This migration is intentionally irreversible because downgrading would remove request workflow data."
    )
