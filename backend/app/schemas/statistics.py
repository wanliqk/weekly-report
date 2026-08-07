from datetime import date

from pydantic import BaseModel

from app.schemas.daily_report_day import DailyReportDayMonthItemData


class StatisticsMonthlyData(BaseModel):
    month: str
    effective_date_from: date
    effective_date_to: date
    denominator_days: int
    completed_days: int
    completion_rate: float | None
    daily_report_count: int
    weekly_report_count: int
    current_streak_days: int
    days: list[DailyReportDayMonthItemData]
