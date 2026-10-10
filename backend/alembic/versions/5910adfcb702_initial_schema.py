"""initial_schema

Revision ID: 5910adfcb702
Revises: None
Create Date: 2026-10-10 11:36:10.471889

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5910adfcb702"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. services
    op.create_table(
        "services",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. appointments
    op.create_table(
        "appointments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("customer_name", sa.String(length=100), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=False),
        sa.Column("customer_phone", sa.String(length=50), nullable=False),
        sa.Column("service_id", sa.String(length=36), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=35), nullable=False, server_default="scheduled"),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_recovery", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. waitlist_entries
    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("customer_name", sa.String(length=100), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=False),
        sa.Column("customer_phone", sa.String(length=50), nullable=False),
        sa.Column("service_id", sa.String(length=36), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("preferred_start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("preferred_end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=35), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. recovery_offers
    op.create_table(
        "recovery_offers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("appointment_id", sa.String(length=36), sa.ForeignKey("appointments.id"), nullable=False),
        sa.Column("waitlist_id", sa.String(length=36), sa.ForeignKey("waitlist_entries.id"), nullable=False),
        sa.Column("token", sa.String(length=64), unique=True, nullable=False),
        sa.Column("status", sa.String(length=35), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. notification_logs
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("offer_id", sa.String(length=36), sa.ForeignKey("recovery_offers.id"), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="email"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="delivered"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 6. business_settings
    op.create_table(
        "business_settings",
        sa.Column("id", sa.Integer(), primary_key=True, server_default="1"),
        sa.Column("business_name", sa.String(length=100), nullable=False, server_default="SlotBack Wellness Spa"),
        sa.Column("default_offer_expiry_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("notification_email", sa.String(length=255), nullable=False, server_default="staff@slotback.com"),
        sa.Column("auto_match_waitlist", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("business_id", sa.String(length=36), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. users (staff authentication & authorization)
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="staff"),
        sa.Column("business_id", sa.String(length=36), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("business_settings")
    op.drop_table("notification_logs")
    op.drop_table("recovery_offers")
    op.drop_table("waitlist_entries")
    op.drop_table("appointments")
    op.drop_table("services")
