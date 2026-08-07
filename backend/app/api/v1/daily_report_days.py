from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.errors import AppError
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiResponse
from app.schemas.daily_report import DailyReportListItemData, DailyStatus
from app.schemas.daily_report_day import (
    DailyReportDayArchiveRequest,
    DailyReportDayDetailData,
    DailyReportDayMonthData,
    DailyReportDayMonthItemData,
)
from app.services.daily_report_day import DailyReportDayService, DayDetail

router = APIRouter(prefix="/api/v1/daily-report-days", tags=["daily-report-days"])


class InvalidMonthError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40001, http_status=400, message="month 必须是 YYYY-MM 格式")


def _parse_month(month: str) -> tuple[date, date]:
    year_text, month_text = month.split("-")
    try:
        year, month_no = int(year_text), int(month_text)
        month_start = date(year, month_no, 1)
    except ValueError as error:
        raise InvalidMonthError() from error
    next_month_start = date(year + 1, 1, 1) if month_no == 12 else date(year, month_no + 1, 1)
    month_end = date.fromordinal(next_month_start.toordinal() - 1)
    return month_start, month_end


def _detail_response(detail: DayDetail) -> DailyReportDayDetailData:
    return DailyReportDayDetailData(
        work_date=detail.work_date,
        status=detail.status,
        draft_count=detail.draft_count,
        submitted_count=detail.submitted_count,
        archived_count=detail.archived_count,
        can_archive=detail.can_archive,
        disabled_reason=detail.disabled_reason,
        entries=[
            DailyReportListItemData(
                id=entry.id,
                work_date=entry.work_date,
                status=cast(DailyStatus, entry.status),
                version=entry.version,
                updated_at=entry.updated_at,
                submitted_at=entry.submitted_at,
                archived_at=entry.archived_at,
            )
            for entry in detail.entries
        ],
        archive_snapshot=detail.archive_snapshot,
        archived_at=detail.archived_at,
    )


@router.get("", response_model=ApiResponse[DailyReportDayMonthData])
async def month_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")],
) -> ApiResponse[DailyReportDayMonthData]:
    month_start, month_end = _parse_month(month)
    items = await DailyReportDayService(session).month_summary(
        current_user.id, month_start=month_start, month_end=month_end
    )
    return ApiResponse(
        data=DailyReportDayMonthData(
            month=month,
            items=[
                DailyReportDayMonthItemData(
                    work_date=item.work_date,
                    status=item.status,
                    draft_count=item.draft_count,
                    submitted_count=item.submitted_count,
                    archived_count=item.archived_count,
                    total_count=item.total_count,
                    can_create=item.can_create,
                    can_archive=item.can_archive,
                    disabled_reason=item.disabled_reason,
                )
                for item in items
            ],
        )
    )


@router.get("/{work_date}", response_model=ApiResponse[DailyReportDayDetailData])
async def day_detail(
    work_date: date,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[DailyReportDayDetailData]:
    detail = await DailyReportDayService(session).get_detail(current_user.id, work_date)
    return ApiResponse(data=_detail_response(detail))


@router.post("/{work_date}/archive", response_model=ApiResponse[DailyReportDayDetailData])
async def archive_day(
    work_date: date,
    payload: DailyReportDayArchiveRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[DailyReportDayDetailData]:
    service = DailyReportDayService(session)
    await service.archive(current_user.id, work_date, confirm_archive=payload.confirm_archive)
    detail = await service.get_detail(current_user.id, work_date)
    return ApiResponse(data=_detail_response(detail))
