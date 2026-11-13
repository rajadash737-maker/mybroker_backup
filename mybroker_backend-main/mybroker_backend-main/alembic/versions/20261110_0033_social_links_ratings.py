"""Create social_links and ratings tables.

Revision ID: 20261110_0033_social_links_ratings
Revises: 20261110_0032_banners
"""

from alembic import op
import sqlalchemy as sa


revision = "20261110_0033_social_links_ratings"
down_revision = "20261110_0032_banners"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "social_links",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("whatsapp", sa.String(length=255), nullable=True),
        sa.Column("instagram", sa.String(length=255), nullable=True),
        sa.Column("telegram", sa.String(length=255), nullable=True),
        sa.Column("youtube", sa.String(length=255), nullable=True),
        sa.Column("facebook", sa.String(length=255), nullable=True),
        sa.Column("linkedin", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("from_user_id", sa.Integer(), nullable=False),
        sa.Column("to_user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review", sa.Text(), nullable=True),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "from_user_id",
            "property_id",
            "role",
            name="uq_ratings_from_property_role",
        ),
    )
    op.create_index("ix_ratings_to_user_id", "ratings", ["to_user_id"], unique=False)
    op.create_index("ix_ratings_role", "ratings", ["role"], unique=False)
    op.create_index("ix_ratings_property_id", "ratings", ["property_id"], unique=False)
    op.create_foreign_key(
        "fk_ratings_from_user_id_users",
        "ratings",
        "users",
        ["from_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_ratings_to_user_id_users",
        "ratings",
        "users",
        ["to_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_ratings_property_id_sell_land_requests",
        "ratings",
        "sell_land_requests",
        ["property_id"],
        ["id"],
    )

def downgrade() -> None:
    op.drop_constraint("fk_ratings_property_id_sell_land_requests", "ratings", type_="foreignkey")
    op.drop_constraint("fk_ratings_to_user_id_users", "ratings", type_="foreignkey")
    op.drop_constraint("fk_ratings_from_user_id_users", "ratings", type_="foreignkey")
    op.drop_index("ix_ratings_property_id", table_name="ratings")
    op.drop_index("ix_ratings_role", table_name="ratings")
    op.drop_index("ix_ratings_to_user_id", table_name="ratings")
    op.drop_table("ratings")
    op.drop_table("social_links")
