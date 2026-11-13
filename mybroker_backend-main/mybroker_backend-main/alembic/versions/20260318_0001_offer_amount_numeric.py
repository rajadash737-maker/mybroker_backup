"""Use numeric for offer amounts to avoid rounding"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260318_0001_offer_amount_numeric"
down_revision = "20260316_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "sell_land_offers",
        "offered_amount",
        existing_type=sa.Float(),
        type_=sa.Numeric(18, 0),
        existing_nullable=False,
    )
    op.alter_column(
        "sell_land_offers",
        "counter_amount",
        existing_type=sa.Float(),
        type_=sa.Numeric(18, 0),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "sell_land_offers",
        "counter_amount",
        existing_type=sa.Numeric(18, 0),
        type_=sa.Float(),
        existing_nullable=True,
    )
    op.alter_column(
        "sell_land_offers",
        "offered_amount",
        existing_type=sa.Numeric(18, 0),
        type_=sa.Float(),
        existing_nullable=False,
    )
