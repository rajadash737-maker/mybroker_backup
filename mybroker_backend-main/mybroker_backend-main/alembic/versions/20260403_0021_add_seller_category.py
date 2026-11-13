from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260403_0021_add_seller_category"
down_revision = "20260323_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sell_land_requests",
        sa.Column("owner_category", sa.String(length=20), nullable=True, server_default="general"),
    )


def downgrade() -> None:
    op.drop_column("sell_land_requests", "owner_category")
