"""Create Site Visit requests and assignment history.

Revision ID: 20261115_0038_site_visit_foundation
Revises: 20261115_0037_site_visit_fee
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20261115_0038_site_visit_foundation"
down_revision = "20261115_0037_site_visit_fee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_visit_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("assigned_field_officer_id", sa.Integer(), nullable=True),
        sa.Column("property_name_snapshot", sa.String(length=150), nullable=False),
        sa.Column("listing_code_snapshot", sa.String(length=30), nullable=True),
        sa.Column("buyer_name_snapshot", sa.String(length=120), nullable=False),
        sa.Column("buyer_mobile_snapshot", sa.String(length=20), nullable=False),
        sa.Column("seller_name_snapshot", sa.String(length=120), nullable=False),
        sa.Column("seller_mobile_snapshot", sa.String(length=20), nullable=False),
        sa.Column("preferred_visit_date", sa.Date(), nullable=False),
        sa.Column("preferred_visit_time", sa.Time(), nullable=False),
        sa.Column("visitor_count", sa.Integer(), nullable=False),
        sa.Column("pickup_address", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("submission_key", sa.String(length=64), nullable=True),
        sa.Column("site_visit_fee_paise", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending_payment", nullable=False),
        sa.Column("payment_status", sa.String(length=20), server_default="initiated", nullable=False),
        sa.Column("payment_order_id", sa.String(length=64), nullable=True),
        sa.Column("payment_id", sa.String(length=64), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("site_visit_fee_paise >= 0", name="ck_site_visit_requests_fee_nonnegative"),
        sa.CheckConstraint("visitor_count BETWEEN 1 AND 20", name="ck_site_visit_requests_visitor_count"),
        sa.CheckConstraint(
            "status IN ('pending_payment', 'pending', 'assigned', 'scheduled', 'in_progress', "
            "'completed', 'cancelled', 'refund_pending', 'refunded', 'refund_failed')",
            name="ck_site_visit_requests_status",
        ),
        sa.CheckConstraint(
            "payment_status IN ('initiated', 'success', 'failed')",
            name="ck_site_visit_requests_payment_status",
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"], ["sell_land_requests.id"],
            name="fk_site_visit_requests_listing_id_sell_land_requests",
        ),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], name="fk_site_visit_requests_buyer_id_users"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], name="fk_site_visit_requests_seller_id_users"),
        sa.ForeignKeyConstraint(
            ["assigned_field_officer_id"], ["users.id"],
            name="fk_site_visit_requests_assigned_officer_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("buyer_id", "submission_key", name="uq_site_visit_requests_buyer_submission"),
        sa.UniqueConstraint("payment_order_id", name="uq_site_visit_requests_payment_order"),
        sa.UniqueConstraint("payment_id", name="uq_site_visit_requests_payment_id"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_site_visit_requests_id", "site_visit_requests", ["id"], unique=False)
    op.create_index("ix_site_visit_requests_listing_id", "site_visit_requests", ["listing_id"], unique=False)
    op.create_index("ix_site_visit_requests_buyer_id", "site_visit_requests", ["buyer_id"], unique=False)
    op.create_index("ix_site_visit_requests_seller_id", "site_visit_requests", ["seller_id"], unique=False)
    op.create_index(
        "ix_site_visit_requests_assigned_field_officer_id",
        "site_visit_requests",
        ["assigned_field_officer_id"],
        unique=False,
    )
    op.create_index("ix_site_visit_requests_status", "site_visit_requests", ["status"], unique=False)
    op.create_index("ix_site_visit_requests_payment_status", "site_visit_requests", ["payment_status"], unique=False)
    op.create_index(
        "ix_site_visit_requests_buyer_status_created",
        "site_visit_requests",
        ["buyer_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_site_visit_requests_listing_created",
        "site_visit_requests",
        ["listing_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_site_visit_requests_officer_status_date",
        "site_visit_requests",
        ["assigned_field_officer_id", "status", "preferred_visit_date"],
        unique=False,
    )

    op.create_table(
        "site_visit_assignment_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_visit_request_id", sa.Integer(), nullable=False),
        sa.Column("previous_field_officer_id", sa.Integer(), nullable=True),
        sa.Column("field_officer_id", sa.Integer(), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "action IN ('assigned', 'reassigned', 'unassigned')",
            name="ck_site_visit_assignment_history_action",
        ),
        sa.CheckConstraint(
            "actor_type IN ('system', 'admin', 'super_admin')",
            name="ck_site_visit_assignment_history_actor_type",
        ),
        sa.CheckConstraint(
            "(action = 'unassigned' AND field_officer_id IS NULL) OR "
            "(action IN ('assigned', 'reassigned') AND field_officer_id IS NOT NULL)",
            name="ck_site_visit_assignment_history_target",
        ),
        sa.ForeignKeyConstraint(
            ["site_visit_request_id"], ["site_visit_requests.id"],
            name="fk_site_visit_assignment_history_request_id_site_visit_requests",
        ),
        sa.ForeignKeyConstraint(
            ["previous_field_officer_id"], ["users.id"],
            name="fk_site_visit_assignment_history_previous_officer_users",
        ),
        sa.ForeignKeyConstraint(
            ["field_officer_id"], ["users.id"],
            name="fk_site_visit_assignment_history_field_officer_users",
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name="fk_site_visit_assignment_history_actor_users"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_site_visit_assignment_history_id", "site_visit_assignment_history", ["id"], unique=False)
    op.create_index(
        "ix_site_visit_assignment_history_site_visit_request_id",
        "site_visit_assignment_history",
        ["site_visit_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_site_visit_assignment_history_previous_field_officer_id",
        "site_visit_assignment_history",
        ["previous_field_officer_id"],
        unique=False,
    )
    op.create_index(
        "ix_site_visit_assignment_history_field_officer_id",
        "site_visit_assignment_history",
        ["field_officer_id"],
        unique=False,
    )
    op.create_index(
        "ix_site_visit_assignment_history_actor_id",
        "site_visit_assignment_history",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        "ix_site_visit_assignment_request_created",
        "site_visit_assignment_history",
        ["site_visit_request_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_site_visit_assignment_request_created", table_name="site_visit_assignment_history")
    op.drop_index("ix_site_visit_assignment_history_actor_id", table_name="site_visit_assignment_history")
    op.drop_index("ix_site_visit_assignment_history_field_officer_id", table_name="site_visit_assignment_history")
    op.drop_index(
        "ix_site_visit_assignment_history_previous_field_officer_id",
        table_name="site_visit_assignment_history",
    )
    op.drop_index(
        "ix_site_visit_assignment_history_site_visit_request_id",
        table_name="site_visit_assignment_history",
    )
    op.drop_index("ix_site_visit_assignment_history_id", table_name="site_visit_assignment_history")
    op.drop_table("site_visit_assignment_history")

    op.drop_index("ix_site_visit_requests_officer_status_date", table_name="site_visit_requests")
    op.drop_index("ix_site_visit_requests_listing_created", table_name="site_visit_requests")
    op.drop_index("ix_site_visit_requests_buyer_status_created", table_name="site_visit_requests")
    op.drop_index("ix_site_visit_requests_payment_status", table_name="site_visit_requests")
    op.drop_index("ix_site_visit_requests_status", table_name="site_visit_requests")
    op.drop_index("ix_site_visit_requests_assigned_field_officer_id", table_name="site_visit_requests")
    op.drop_index("ix_site_visit_requests_seller_id", table_name="site_visit_requests")
    op.drop_index("ix_site_visit_requests_buyer_id", table_name="site_visit_requests")
    op.drop_index("ix_site_visit_requests_listing_id", table_name="site_visit_requests")
    op.drop_index("ix_site_visit_requests_id", table_name="site_visit_requests")
    op.drop_table("site_visit_requests")
