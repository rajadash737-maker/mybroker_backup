"""add registry fields to booking

Revision ID: a67d159913e2
Revises: 2e6b8c73ace0
Create Date: 2026-03-20 19:55:13.005764
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a67d159913e2"
down_revision = "2e6b8c73ace0"
branch_labels = None
depends_on = None


def _ensure_column(name: str, column: sa.Column, expected_type: type, nullable: bool) -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("sell_land_bookings"):
        raise RuntimeError("sell_land_bookings must exist before registry fields can be migrated.")
    columns = {item["name"]: item for item in inspector.get_columns("sell_land_bookings")}
    if name not in columns:
        op.add_column("sell_land_bookings", column)
        return
    actual = columns[name]
    expected_length = getattr(column.type, "length", None)
    actual_length = getattr(actual["type"], "length", None)
    if (
        not isinstance(actual["type"], expected_type)
        or (expected_length is not None and actual_length != expected_length)
        or actual["nullable"] != nullable
    ):
        raise RuntimeError(
            f"Incompatible sell_land_bookings.{name}: got {actual['type']} "
            f"nullable={actual['nullable']}; expected {expected_type.__name__} nullable={nullable}."
        )
    if name == "booking_status":
        default = actual.get("default")
        normalized = str(default).strip().strip("()'\"").lower() if default is not None else None
        if normalized != "booked":
            raise RuntimeError("sell_land_bookings.booking_status must retain the 'booked' server default.")


def upgrade() -> None:
    _ensure_column(
        "booking_status",
        sa.Column("booking_status", sa.String(length=30), nullable=False, server_default="booked"),
        sa.String,
        False,
    )
    _ensure_column("registry_date", sa.Column("registry_date", sa.Date(), nullable=True), sa.Date, True)
    _ensure_column("registry_time", sa.Column("registry_time", sa.Time(), nullable=True), sa.Time, True)
    _ensure_column(
        "registry_location",
        sa.Column("registry_location", sa.String(length=255), nullable=True),
        sa.String,
        True,
    )
    _ensure_column(
        "registry_proof_url",
        sa.Column("registry_proof_url", sa.String(length=500), nullable=True),
        sa.String,
        True,
    )
    _ensure_column(
        "registry_proof_name",
        sa.Column("registry_proof_name", sa.String(length=255), nullable=True),
        sa.String,
        True,
    )
    _ensure_column("registry_notes", sa.Column("registry_notes", sa.Text(), nullable=True), sa.Text, True)


def downgrade() -> None:
    raise RuntimeError("Automatic downgrade is disabled to preserve registry booking data.")
