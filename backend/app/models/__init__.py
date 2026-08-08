"""SQLAlchemy models.

Every model module must be imported here so `Base.metadata` is fully
populated before Alembic's `env.py` (and anything else) reads it.
"""

from app.models.admin_audit import AdminAuditEvent
from app.models.base import Base
from app.models.daily_report import DailyReport, DailyReportDay
from app.models.export_job import ExportJob
from app.models.template import ReportTemplate, TemplateVersion
from app.models.user import User, UserSettings
from app.models.wecom import WeComDailySyncRecord, WeComSyncProfile, WeComUserBinding
from app.models.weekly_report import WeeklyReport, WeeklyReportSource

__all__ = [
    "AdminAuditEvent",
    "Base",
    "DailyReport",
    "DailyReportDay",
    "ExportJob",
    "ReportTemplate",
    "TemplateVersion",
    "User",
    "UserSettings",
    "WeComDailySyncRecord",
    "WeComSyncProfile",
    "WeComUserBinding",
    "WeeklyReport",
    "WeeklyReportSource",
]
