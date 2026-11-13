"""Add processing fee settings

Revision ID: 20260405_0024
Revises: 20260404_0023
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260405_0024"
down_revision = "20260404_0023"
branch_labels = None
depends_on = None


def _normalize_default(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip().strip("()'\"").lower()


def _ensure_id_index() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = inspector.get_indexes("processing_fee_settings")
    named = next((index for index in indexes if index.get("name") == "ix_processing_fee_settings_id"), None)
    if named is not None:
        if named.get("column_names") != ["id"] or named.get("unique", False):
            raise RuntimeError("ix_processing_fee_settings_id exists with an incompatible definition.")
        return

    equivalent = [index for index in indexes if index.get("column_names") == ["id"]]
    if len(equivalent) > 1 or any(index.get("unique", False) for index in equivalent):
        raise RuntimeError("Incompatible or duplicate indexes exist on processing_fee_settings.id.")
    if not equivalent:
        op.create_index("ix_processing_fee_settings_id", "processing_fee_settings", ["id"], unique=False)


def _validate_table() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"]: column for column in inspector.get_columns("processing_fee_settings")}
    expected = {
        "id": (sa.Integer, False),
        "seller_processing_fee": (sa.Float, False),
        "buyer_processing_fee": (sa.Float, False),
        "updated_at": (sa.DateTime, False),
    }
    missing = sorted(set(expected) - set(columns))
    if missing:
        raise RuntimeError(f"processing_fee_settings is missing required columns {missing}; refusing repair.")
    incompatible = [
        name for name, (type_class, nullable) in expected.items()
        if not isinstance(columns[name]["type"], type_class) or columns[name]["nullable"] != nullable
    ]
    if incompatible:
        raise RuntimeError(f"processing_fee_settings has incompatible columns {incompatible}.")

    defaults = {
        "seller_processing_fee": {"999", "999.0"},
        "buyer_processing_fee": {"1000", "1000.0"},
    }
    for name, allowed in defaults.items():
        if _normalize_default(columns[name].get("default")) not in allowed:
            raise RuntimeError(f"processing_fee_settings.{name} has an incompatible server default.")
    if _normalize_default(columns["updated_at"].get("default")) not in {"current_timestamp", "now"}:
        raise RuntimeError("processing_fee_settings.updated_at must default to the current timestamp.")
    if (inspector.get_pk_constraint("processing_fee_settings").get("constrained_columns") or []) != ["id"]:
        raise RuntimeError("processing_fee_settings must use id as its sole primary key.")


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("processing_fee_settings"):
        op.create_table(
            "processing_fee_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("seller_processing_fee", sa.Float(), nullable=False, server_default="999.0"),
            sa.Column("buyer_processing_fee", sa.Float(), nullable=False, server_default="1000.0"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    _validate_table()
    _ensure_id_index()


def downgrade() -> None:
    op.drop_index(op.f("ix_processing_fee_settings_id"), table_name="processing_fee_settings")
    op.drop_table("processing_fee_settings")
