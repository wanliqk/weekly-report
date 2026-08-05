from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    desc,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ulid import generate_ulid
from app.models.base import Base, TimestampMixin


class DailyReport(TimestampMixin, Base):
    __tablename__ = "daily_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "work_date", name="uq_daily_reports_user_work_date"),
        Index("ix_daily_reports_user_status_date", "user_id", "status", desc("work_date")),
        Index("ix_daily_reports_user_date", "user_id", desc("work_date"), desc("id")),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'archived')", name="ck_daily_reports_status"
        ),
        # Base timing sanity check only; full status-transition timing rules are
        # enforced by the Service layer, not by this constraint (see database.md §3.5).
        CheckConstraint(
            "(status != 'draft' OR archived_at IS NULL) AND "
            "(status != 'archived' OR (submitted_at IS NOT NULL AND archived_at IS NOT NULL))",
            name="ck_daily_reports_status_timestamps",
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    work_date: Mapped[date] = mapped_column(Date(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    template_version_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("template_versions.id", ondelete="RESTRICT"), nullable=False
    )
    template_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
