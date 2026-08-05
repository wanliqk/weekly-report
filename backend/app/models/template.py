from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ulid import generate_ulid
from app.models.base import Base, TimestampMixin


class ReportTemplate(TimestampMixin, Base):
    __tablename__ = "report_templates"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_report_templates_user_id"),
        CheckConstraint(
            "current_version_no > 0", name="ck_report_templates_current_version_positive"
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="日报模板", server_default="日报模板"
    )
    current_version_no: Mapped[int] = mapped_column(Integer, nullable=False)


class TemplateVersion(Base):
    """Immutable version snapshot: rows are insert-only, never updated or deleted."""

    __tablename__ = "template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version_no", name="uq_template_versions_template_version"),
        CheckConstraint("version_no > 0", name="ck_template_versions_version_no_positive"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    template_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("report_templates.id", ondelete="RESTRICT"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, server_default=func.now()
    )
