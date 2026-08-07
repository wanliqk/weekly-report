from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.month_range import parse_month_range
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiResponse
from app.schemas.daily_report_day import DailyReportDayMonthItemData
from app.schemas.statistics import StatisticsMonthlyData
from app.services.statistics import StatisticsService

router = APIRouter(prefix="/api/v1/statistics", tags=["statistics"])


@router.get("/monthly", response_model=ApiResponse[StatisticsMonthlyData])
async def get_monthly_statistics(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")],
) -> ApiResponse[StatisticsMonthlyData]:
    month_start, month_end = parse_month_range(month)
    result = await StatisticsService(session).monthly(
        current_user.id, month=month, month_start=month_start, month_end=month_end
    )
    return ApiResponse(
        data=StatisticsMonthlyData(
            month=result.month,
            effective_date_from=result.effective_date_from,
            effective_date_to=result.effective_date_to,
            denominator_days=result.denominator_days,
            completed_days=result.completed_days,
            completion_rate=result.completion_rate,
            daily_report_count=result.daily_report_count,
            weekly_report_count=result.weekly_report_count,
            current_streak_days=result.current_streak_days,
            days=[
                DailyReportDayMonthItemData(
                    work_date=item.work_date,
                    day_id=item.day_id,
                    status=item.status,
                    draft_count=item.draft_count,
                    submitted_count=item.submitted_count,
                    archived_count=item.archived_count,
                    total_count=item.total_count,
                    can_create=item.can_create,
                    can_archive=item.can_archive,
                    archive_disabled_reason=item.archive_disabled_reason,
                )
                for item in result.days
            ],
        )
    )
