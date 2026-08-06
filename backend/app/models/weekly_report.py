from datetime import date, datetime

from sqlalchemy import (
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


class WeeklyReport(TimestampMixin, Base):
    __tablename__ = "weekly_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_reports_user_week"),
        Index("ix_weekly_reports_user_week", "user_id", desc("week_start"), desc("id")),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date(), nullable=False)
    week_end: Mapped[date] = mapped_column(Date(), nullable=False)
    generated_content_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class WeeklyReportSource(Base):
    __tablename__ = "weekly_report_sources"
    __table_args__ = (Index("ix_weekly_sources_daily_day", "daily_report_day_id"),)

    weekly_report_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("weekly_reports.id", ondelete="RESTRICT"), primary_key=True
    )
    daily_report_day_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("daily_report_days.id", ondelete="RESTRICT"), primary_key=True
    )
    work_date: Mapped[date] = mapped_column(Date(), nullable=False)
    included_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
