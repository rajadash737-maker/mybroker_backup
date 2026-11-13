"""Change sell_land_bookings.deal_amount to numeric

Revision ID: 20260404_0023
Revises: 20260404_0022
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260404_0023"
down_revision = "20260404_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("sell_land_bookings"):
        raise RuntimeError("sell_land_bookings must exist before deal_amount can be converted.")
    columns = {column["name"]: column for column in inspector.get_columns("sell_land_bookings")}
    if "deal_amount" not in columns:
        raise RuntimeError("sell_land_bookings.deal_amount is missing; refusing to invent booking amounts.")

    amount = columns["deal_amount"]
    if amount["nullable"]:
        raise RuntimeError("sell_land_bookings.deal_amount must be non-nullable before precision conversion.")

    # SQLAlchemy's Float subclasses Numeric. Check Float first: MySQL reflects
    # FLOAT(M) as Float(precision=M), and the old Numeric-first branch treated
    # that source FLOAT as an already-converted decimal with missing precision.
    if isinstance(amount["type"], sa.Float):
        invalid_values = op.get_bind().execute(
            sa.text(
                "SELECT COUNT(*) FROM sell_land_bookings "
                "WHERE deal_amount <> ROUND(deal_amount, 0) "
                "OR deal_amount > 999999999999999999 "
                "OR deal_amount < -999999999999999999"
            )
        ).scalar_one()
        if invalid_values:
            raise RuntimeError(
                "Cannot convert sell_land_bookings.deal_amount to Numeric(18, 0): "
                f"{invalid_values} value(s) have fractional rupees or exceed the target range. "
                "Resolve these values explicitly before retrying."
            )
        op.alter_column(
            "sell_land_bookings",
            "deal_amount",
            existing_type=amount["type"],
            type_=sa.Numeric(18, 0),
            existing_nullable=False,
        )
    elif isinstance(amount["type"], sa.Numeric):
        precision = getattr(amount["type"], "precision", None)
        scale = getattr(amount["type"], "scale", None)
        if precision != 18 or scale != 0:
            raise RuntimeError(
                f"Existing sell_land_bookings.deal_amount is Numeric({precision}, {scale}), "
                "expected Numeric(18, 0)."
            )
    else:
        raise RuntimeError(
            f"Cannot safely convert sell_land_bookings.deal_amount from {amount['type']} to Numeric(18, 0)."
        )


def downgrade() -> None:
    raise RuntimeError("Automatic downgrade is disabled to avoid precision loss in booking amounts.")
