"""Persist security state for OTP and Razorpay payment verification.

Revision ID: 20261106_0031_otp_security
Revises: 20261103_0030_request_fields
"""

from alembic import op
import sqlalchemy as sa


revision = "20261106_0031_otp_security"
down_revision = "20261103_0030_request_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().as_sql:
        op.add_column("otps", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
        op.add_column("otps", sa.Column("consumed_at", sa.DateTime(), nullable=True))
        op.add_column("otps", sa.Column("otp_hash", sa.String(length=64), nullable=True))
        op.create_index("ix_otps_mobile_purpose_created_at", "otps", ["mobile", "purpose", "created_at"])
        op.add_column("sell_land_payments", sa.Column("gateway_payment_id", sa.String(length=64), nullable=True))
        op.create_index(
            "ix_sell_land_payments_gateway_payment_id",
            "sell_land_payments",
            ["gateway_payment_id"],
            unique=True,
        )
        return
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("otps")}
    if "attempt_count" not in columns:
        op.add_column(
            "otps",
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        )
    if "consumed_at" not in columns:
        op.add_column("otps", sa.Column("consumed_at", sa.DateTime(), nullable=True))
    if "otp_hash" not in columns:
        op.add_column("otps", sa.Column("otp_hash", sa.String(length=64), nullable=True))

    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("otps")}
    index_name = "ix_otps_mobile_purpose_created_at"
    if index_name not in indexes:
        op.create_index(index_name, "otps", ["mobile", "purpose", "created_at"])

    payment_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("sell_land_payments")}
    if "gateway_payment_id" not in payment_columns:
        op.add_column("sell_land_payments", sa.Column("gateway_payment_id", sa.String(length=64), nullable=True))
    payment_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("sell_land_payments")}
    payment_index = "ix_sell_land_payments_gateway_payment_id"
    if payment_index not in payment_indexes:
        op.create_index(payment_index, "sell_land_payments", ["gateway_payment_id"], unique=True)


def downgrade() -> None:
    if op.get_context().as_sql:
        op.drop_index("ix_sell_land_payments_gateway_payment_id", table_name="sell_land_payments")
        op.drop_column("sell_land_payments", "gateway_payment_id")
        op.drop_index("ix_otps_mobile_purpose_created_at", table_name="otps")
        op.drop_column("otps", "otp_hash")
        op.drop_column("otps", "consumed_at")
        op.drop_column("otps", "attempt_count")
        return
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "otps" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("otps")}
        index_name = "ix_otps_mobile_purpose_created_at"
        if index_name in indexes:
            op.drop_index(index_name, table_name="otps")
        columns = {column["name"] for column in inspector.get_columns("otps")}
        if "consumed_at" in columns:
            op.drop_column("otps", "consumed_at")
        if "otp_hash" in columns:
            op.drop_column("otps", "otp_hash")
        if "attempt_count" in columns:
            op.drop_column("otps", "attempt_count")
    if "sell_land_payments" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("sell_land_payments")}
        payment_index = "ix_sell_land_payments_gateway_payment_id"
        if payment_index in indexes:
            op.drop_index(payment_index, table_name="sell_land_payments")
        columns = {column["name"] for column in inspector.get_columns("sell_land_payments")}
        if "gateway_payment_id" in columns:
            op.drop_column("sell_land_payments", "gateway_payment_id")
