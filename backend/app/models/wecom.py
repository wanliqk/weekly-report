from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ulid import generate_ulid
from app.models.base import Base, TimestampMixin


class WeComUserBinding(TimestampMixin, Base):
    """One WeCom account connection per local user (`docs/方案设计.md` §6.2).

    Only holds an opaque `credential_slot` that Electron Main uses to locate
    its `safeStorage`-encrypted cookie jar file; never the cookie itself, its
    header name, or a local file path (`ai-docs/database.md` §9.4/§6.1).
    """

    __tablename__ = "wecom_user_bindings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_wecom_user_bindings_user_id"),
        UniqueConstraint("credential_slot", name="uq_wecom_user_bindings_credential_slot"),
        CheckConstraint(
            "status IN ('connected', 'expired', 'disconnected')",
            name="ck_wecom_user_bindings_status",
        ),
        CheckConstraint("version > 0", name="ck_wecom_user_bindings_version_positive"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    credential_slot: Mapped[str] = mapped_column(String(64), nullable=False)
    wecom_vid: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    corp_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    last_auth_error_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class WeComSyncProfile(TimestampMixin, Base):
    """The single active sync destination/mapping config per user (`docs/方案设计.md` §6.3).

    This *is* the "WeCom template/mapping config table" — there is no separate
    template config table to keep in sync with it.
    """

    __tablename__ = "wecom_sync_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_wecom_sync_profiles_user_id"),
        CheckConstraint(
            "length(destination_fingerprint) = 64",
            name="ck_wecom_sync_profiles_destination_fingerprint_length",
        ),
        CheckConstraint(
            "length(schema_fingerprint) = 64",
            name="ck_wecom_sync_profiles_schema_fingerprint_length",
        ),
        CheckConstraint("version > 0", name="ck_wecom_sync_profiles_version_positive"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    form_id: Mapped[str] = mapped_column(String(64), nullable=False)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    journal_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    destination_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    question_mapping_json: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_config_json: Mapped[str] = mapped_column(Text, nullable=False)
    field_mapping_json: Mapped[str] = mapped_column(Text, nullable=False)
    schema_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )


class WeComDailySyncRecord(TimestampMixin, Base):
    """Per-(date, destination) sync outcome (`docs/方案设计.md` §6.4).

    Never stores the request/response body — only fingerprints of the
    immutable formal snapshot plus non-sensitive remote IDs, so the row can
    always be explained/re-derived from `daily_report_days.archive_snapshot_json`.
    """

    __tablename__ = "wecom_daily_sync_records"
    __table_args__ = (
        UniqueConstraint(
            "daily_report_day_id",
            "destination_fingerprint",
            name="uq_wecom_daily_sync_records_day_destination",
        ),
        Index(
            "ix_wecom_daily_sync_records_user_status_updated",
            "user_id",
            "status",
            "updated_at",
        ),
        CheckConstraint(
            "status IN ('pending', 'syncing', 'succeeded', 'failed', 'auth_required', "
            "'schema_changed', 'duplicate_detected', 'uncertain')",
            name="ck_wecom_daily_sync_records_status",
        ),
        CheckConstraint(
            "length(destination_fingerprint) = 64",
            name="ck_wecom_daily_sync_records_destination_fingerprint_length",
        ),
        CheckConstraint(
            "length(payload_fingerprint) = 64",
            name="ck_wecom_daily_sync_records_payload_fingerprint_length",
        ),
        CheckConstraint("profile_version > 0", name="ck_wecom_daily_sync_records_profile_version"),
        CheckConstraint(
            "attempt_count >= 0", name="ck_wecom_daily_sync_records_attempt_count_non_negative"
        ),
        CheckConstraint(
            "last_error_message IS NULL OR length(trim(last_error_message)) BETWEEN 1 AND 500",
            name="ck_wecom_daily_sync_records_last_error_message_length",
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    daily_report_day_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("daily_report_days.id", ondelete="RESTRICT"), nullable=False
    )
    profile_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("wecom_sync_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    destination_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    attempt_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remote_answer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remote_reply_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remote_journal_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    succeeded_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
