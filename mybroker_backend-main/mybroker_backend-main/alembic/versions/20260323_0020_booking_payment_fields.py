"""add booking payment method and transaction id

Revision ID: 20260323_0020
Revises: b9d3f2c1a0b1
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260323_0020"
down_revision = "b9d3f2c1a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("sell_land_bookings"):
        raise RuntimeError("sell_land_bookings must exist before payment fields can be migrated.")

    expected = {
        "payment_method": sa.String(length=30),
        "payment_transaction_id": sa.String(length=120),
    }
    for name, column_type in expected.items():
        columns = {column["name"]: column for column in sa.inspect(bind).get_columns("sell_land_bookings")}
        if name not in columns:
            op.add_column("sell_land_bookings", sa.Column(name, column_type, nullable=True))
        else:
            actual = columns[name]
            if (
                not isinstance(actual["type"], sa.String)
                or actual["type"].length != column_type.length
                or not actual["nullable"]
            ):
                raise RuntimeError(
                    f"Incompatible sell_land_bookings.{name}: expected nullable "
                    f"String({column_type.length}), got {actual['type']} nullable={actual['nullable']}."
                )


def downgrade() -> None:
    raise RuntimeError("Automatic downgrade is disabled to preserve booking payment details.")
