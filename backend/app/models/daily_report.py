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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ulid import generate_ulid
from app.models.base import Base, TimestampMixin


class DailyReportDay(TimestampMixin, Base):
    __tablename__ = "daily_report_days"
    __table_args__ = (
        UniqueConstraint("user_id", "work_date", name="uq_daily_report_days_user_work_date"),
        Index("ix_daily_report_days_user_date", "user_id", desc("work_date"), desc("id")),
        Index(
            "ix_daily_report_days_user_status_date",
            "user_id",
            "status",
            desc("work_date"),
        ),
        CheckConstraint("status IN ('open', 'archived')", name="ck_daily_report_days_status"),
        CheckConstraint(
            "(status = 'open' AND archive_snapshot_json IS NULL AND source_count = 0 "
            "AND archived_by IS NULL AND archived_at IS NULL) OR "
            "(status = 'archived' AND archive_snapshot_json IS NOT NULL AND source_count > 0 "
            "AND archived_by IS NOT NULL AND archived_at IS NOT NULL)",
            name="ck_daily_report_days_archive_state",
        ),
        CheckConstraint("version > 0", name="ck_daily_report_days_version_positive"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    work_date: Mapped[date] = mapped_column(Date(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    archive_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    archived_by: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class DailyReport(TimestampMixin, Base):
    __tablename__ = "daily_reports"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_daily_reports_client_request_id"),
        Index(
            "ix_daily_reports_day_status_submit",
            "day_id",
            "status",
            "submitted_at",
            "id",
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'archived')", name="ck_daily_reports_status"
        ),
        CheckConstraint(
            "(status = 'draft' AND submitted_at IS NULL AND archived_at IS NULL) OR "
            "(status = 'submitted' AND submitted_at IS NOT NULL AND archived_at IS NULL) OR "
            "(status = 'archived' AND submitted_at IS NOT NULL AND archived_at IS NOT NULL)",
            name="ck_daily_reports_status_timestamps",
        ),
        CheckConstraint("version > 0", name="ck_daily_reports_version_positive"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    day_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("daily_report_days.id", ondelete="RESTRICT"), nullable=False
    )
    client_request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    template_version_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("template_versions.id", ondelete="RESTRICT"), nullable=False
    )
    template_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    day: Mapped[DailyReportDay] = relationship(lazy="selectin")

    @property
    def user_id(self) -> str:
        """Compatibility accessor while V1 APIs are adapted in stages."""
        return self.day.user_id

    @property
    def work_date(self) -> date:
        """Compatibility accessor while V1 APIs are adapted in stages."""
        return self.day.work_date
