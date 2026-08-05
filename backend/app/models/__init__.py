"""SQLAlchemy models.

Every model module must be imported here so `Base.metadata` is fully
populated before Alembic's `env.py` (and anything else) reads it.
"""

from app.models.base import Base
from app.models.daily_report import DailyReport
from app.models.export_job import ExportJob
from app.models.template import ReportTemplate, TemplateVersion
from app.models.user import User, UserSettings
from app.models.weekly_report import WeeklyReport, WeeklyReportSource

__all__ = [
    "Base",
    "DailyReport",
    "ExportJob",
    "ReportTemplate",
    "TemplateVersion",
    "User",
    "UserSettings",
    "WeeklyReport",
    "WeeklyReportSource",
]
