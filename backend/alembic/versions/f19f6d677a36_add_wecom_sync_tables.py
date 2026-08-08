"""add wecom sync tables

Revision ID: f19f6d677a36
Revises: 8b1d4e6f2a90
Create Date: 2026-08-08 22:07:55.422730

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f19f6d677a36"
down_revision: str | Sequence[str] | None = "8b1d4e6f2a90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Three brand-new, always-empty tables (`docs/方案设计.md` §6, `ai-docs/database.md`
    §9): no existing data is touched or migrated by this revision.
    """
    op.create_table(
        "wecom_user_bindings",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("credential_slot", sa.String(length=64), nullable=False),
        sa.Column("wecom_vid", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("corp_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(), nullable=True),
        sa.Column("last_auth_error_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('connected', 'expired', 'disconnected')",
            name="ck_wecom_user_bindings_status",
        ),
        sa.CheckConstraint("version > 0", name="ck_wecom_user_bindings_version_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_wecom_user_bindings_user_id"),
        sa.UniqueConstraint("credential_slot", name="uq_wecom_user_bindings_credential_slot"),
    )

    op.create_table(
        "wecom_sync_profiles",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("form_id", sa.String(length=64), nullable=False),
        sa.Column("template_id", sa.String(length=64), nullable=False),
        sa.Column("journal_uuid", sa.String(length=64), nullable=True),
        sa.Column("destination_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("question_mapping_json", sa.Text(), nullable=False),
        sa.Column("recipient_config_json", sa.Text(), nullable=False),
        sa.Column("field_mapping_json", sa.Text(), nullable=False),
        sa.Column("schema_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(destination_fingerprint) = 64",
            name="ck_wecom_sync_profiles_destination_fingerprint_length",
        ),
        sa.CheckConstraint(
            "length(schema_fingerprint) = 64",
            name="ck_wecom_sync_profiles_schema_fingerprint_length",
        ),
        sa.CheckConstraint("version > 0", name="ck_wecom_sync_profiles_version_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_wecom_sync_profiles_user_id"),
    )

    op.create_table(
        "wecom_daily_sync_records",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("daily_report_day_id", sa.String(length=26), nullable=False),
        sa.Column("profile_id", sa.String(length=26), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("destination_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("payload_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("attempt_token", sa.String(length=64), nullable=True),
        sa.Column("remote_answer_id", sa.String(length=64), nullable=True),
        sa.Column("remote_reply_id", sa.String(length=64), nullable=True),
        sa.Column("remote_journal_uuid", sa.String(length=64), nullable=True),
        sa.Column("last_error_kind", sa.String(length=64), nullable=True),
        sa.Column("last_error_message", sa.String(length=500), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("succeeded_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'syncing', 'succeeded', 'failed', 'auth_required', "
            "'schema_changed', 'duplicate_detected', 'uncertain')",
            name="ck_wecom_daily_sync_records_status",
        ),
        sa.CheckConstraint(
            "length(destination_fingerprint) = 64",
            name="ck_wecom_daily_sync_records_destination_fingerprint_length",
        ),
        sa.CheckConstraint(
            "length(payload_fingerprint) = 64",
            name="ck_wecom_daily_sync_records_payload_fingerprint_length",
        ),
        sa.CheckConstraint(
            "profile_version > 0", name="ck_wecom_daily_sync_records_profile_version"
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name="ck_wecom_daily_sync_records_attempt_count_non_negative"
        ),
        sa.CheckConstraint(
            "last_error_message IS NULL OR length(trim(last_error_message)) BETWEEN 1 AND 500",
            name="ck_wecom_daily_sync_records_last_error_message_length",
        ),
        sa.ForeignKeyConstraint(
            ["daily_report_day_id"], ["daily_report_days.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["wecom_sync_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "daily_report_day_id",
            "destination_fingerprint",
            name="uq_wecom_daily_sync_records_day_destination",
        ),
    )
    with op.batch_alter_table("wecom_daily_sync_records", schema=None) as batch_op:
        batch_op.create_index(
            "ix_wecom_daily_sync_records_user_status_updated",
            ["user_id", "status", "updated_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema.

    Straight table drops: these three tables were created empty by this
    revision's `upgrade()` and have no prior-version data shape to preserve.
    """
    with op.batch_alter_table("wecom_daily_sync_records", schema=None) as batch_op:
        batch_op.drop_index("ix_wecom_daily_sync_records_user_status_updated")

    op.drop_table("wecom_daily_sync_records")
    op.drop_table("wecom_sync_profiles")
    op.drop_table("wecom_user_bindings")
