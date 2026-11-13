"""add razorpay payments and webhook logs

Revision ID: 20260405_0025
Revises: 20260405_0024
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_0025"
down_revision = "20260405_0024"
branch_labels = None
depends_on = None


def _normalize_default(value):
    if value is None:
        return None
    return str(value).strip().strip("()'\"").lower()


def _validate_columns(table_name, expected):
    columns = {column["name"]: column for column in sa.inspect(op.get_bind()).get_columns(table_name)}
    missing = sorted(set(expected) - set(columns))
    if missing:
        raise RuntimeError(f"{table_name} is missing required columns {missing}; refusing repair.")
    for name, (type_class, length, nullable, defaults) in expected.items():
        actual = columns[name]
        if (
            not isinstance(actual["type"], type_class)
            or (length is not None and getattr(actual["type"], "length", None) != length)
            or actual["nullable"] != nullable
        ):
            raise RuntimeError(f"Incompatible {table_name}.{name}: {actual['type']} nullable={actual['nullable']}.")
        if defaults is not None and _normalize_default(actual.get("default")) not in defaults:
            raise RuntimeError(f"Incompatible server default on {table_name}.{name}.")


def _ensure_index(table_name, name, columns):
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
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
        raise RuntimeError(f"Duplicate non-unique indexes exist on {table_name}{tuple(columns)}.")
    if not equivalent:
        op.create_index(name, table_name, columns, unique=False)


def _validate_payment_orders():
    table = "razorpay_payment_orders"
    _validate_columns(table, {
        "id": (sa.Integer, None, False, None),
        "user_id": (sa.Integer, None, False, None),
        "property_id": (sa.Integer, None, False, None),
        "amount": (sa.Float, None, False, None),
        "amount_paise": (sa.Integer, None, False, None),
        "currency": (sa.String, 10, False, {"inr"}),
        "order_id": (sa.String, 64, False, None),
        "payment_id": (sa.String, 64, True, None),
        "signature": (sa.String, 256, True, None),
        "status": (sa.String, 20, False, {"created"}),
        "created_at": (sa.DateTime, None, False, {"current_timestamp", "now"}),
        "updated_at": (sa.DateTime, None, False, {"current_timestamp", "now"}),
        "paid_at": (sa.DateTime, None, True, None),
    })
    inspector = sa.inspect(op.get_bind())
    if (inspector.get_pk_constraint(table).get("constrained_columns") or []) != ["id"]:
        raise RuntimeError(f"{table} must use id as its sole primary key.")

    unique_constraints = inspector.get_unique_constraints(table)
    unique_order_constraints = [item for item in unique_constraints if item.get("column_names") == ["order_id"]]
    if len(unique_order_constraints) != 1:
        raise RuntimeError(f"{table}.order_id must have exactly one unique constraint.")

    foreign_keys = inspector.get_foreign_keys(table)
    for column, target_table in (("user_id", "users"), ("property_id", "sell_land_requests")):
        matches = [fk for fk in foreign_keys if fk.get("constrained_columns") == [column]]
        if (
            len(matches) != 1
            or matches[0].get("referred_table") != target_table
            or matches[0].get("referred_columns") != ["id"]
        ):
            raise RuntimeError(f"{table}.{column} has a missing or incompatible foreign key.")


def _ensure_payment_orders():
    table = "razorpay_payment_orders"
    if not sa.inspect(op.get_bind()).has_table(table):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("property_id", sa.Integer(), sa.ForeignKey("sell_land_requests.id"), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("amount_paise", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
            sa.Column("order_id", sa.String(length=64), nullable=False, unique=True),
            sa.Column("payment_id", sa.String(length=64), nullable=True),
            sa.Column("signature", sa.String(length=256), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="CREATED"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("paid_at", sa.DateTime(), nullable=True),
        )
    _validate_payment_orders()
    _ensure_index(table, "ix_razorpay_payment_orders_order_id", ["order_id"])
    _ensure_index(table, "ix_razorpay_payment_orders_user_id", ["user_id"])
    _ensure_index(table, "ix_razorpay_payment_orders_property_id", ["property_id"])


def _validate_webhook_logs():
    table = "razorpay_webhook_logs"
    _validate_columns(table, {
        "id": (sa.Integer, None, False, None),
        "event_id": (sa.String, 80, True, None),
        "event": (sa.String, 80, False, None),
        "order_id": (sa.String, 64, True, None),
        "payment_id": (sa.String, 64, True, None),
        "signature": (sa.String, 256, True, None),
        "status": (sa.String, 30, False, {"received"}),
        "error": (sa.String, 255, True, None),
        "payload": (sa.Text, None, False, None),
        "attempt_count": (sa.Integer, None, False, {"1"}),
        "last_attempt_at": (sa.DateTime, None, False, {"current_timestamp", "now"}),
        "created_at": (sa.DateTime, None, False, {"current_timestamp", "now"}),
    })
    if (sa.inspect(op.get_bind()).get_pk_constraint(table).get("constrained_columns") or []) != ["id"]:
        raise RuntimeError(f"{table} must use id as its sole primary key.")


def _ensure_webhook_logs():
    table = "razorpay_webhook_logs"
    if not sa.inspect(op.get_bind()).has_table(table):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.String(length=80), nullable=True),
            sa.Column("event", sa.String(length=80), nullable=False),
            sa.Column("order_id", sa.String(length=64), nullable=True),
            sa.Column("payment_id", sa.String(length=64), nullable=True),
            sa.Column("signature", sa.String(length=256), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="received"),
            sa.Column("error", sa.String(length=255), nullable=True),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("last_attempt_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        )
    _validate_webhook_logs()
    _ensure_index(table, "ix_razorpay_webhook_logs_event_id", ["event_id"])
    _ensure_index(table, "ix_razorpay_webhook_logs_order_id", ["order_id"])
    _ensure_index(table, "ix_razorpay_webhook_logs_payment_id", ["payment_id"])


def upgrade():
    _ensure_payment_orders()
    _ensure_webhook_logs()


def downgrade():
    op.drop_index("ix_razorpay_webhook_logs_payment_id", table_name="razorpay_webhook_logs")
    op.drop_index("ix_razorpay_webhook_logs_order_id", table_name="razorpay_webhook_logs")
    op.drop_index("ix_razorpay_webhook_logs_event_id", table_name="razorpay_webhook_logs")
    op.drop_table("razorpay_webhook_logs")

    op.drop_index("ix_razorpay_payment_orders_property_id", table_name="razorpay_payment_orders")
    op.drop_index("ix_razorpay_payment_orders_user_id", table_name="razorpay_payment_orders")
    op.drop_index("ix_razorpay_payment_orders_order_id", table_name="razorpay_payment_orders")
    op.drop_table("razorpay_payment_orders")
