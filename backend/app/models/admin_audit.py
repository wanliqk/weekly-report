from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, desc
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ulid import generate_ulid
from app.models.base import Base


class AdminAuditEvent(Base):
    __tablename__ = "admin_audit_events"
    __table_args__ = (
        Index("ix_admin_audit_action_created", "action", desc("created_at")),
        Index("ix_admin_audit_target_created", "target_id", desc("created_at")),
        CheckConstraint(
            "action IN ('daily_submission_revoked', 'user_deleted')",
            name="ck_admin_audit_events_action",
        ),
        CheckConstraint(
            "length(trim(reason)) BETWEEN 1 AND 500",
            name="ck_admin_audit_events_reason_length",
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_username_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_owner_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
