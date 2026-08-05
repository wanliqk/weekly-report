from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User, WeeklyReport
from app.schemas.common import ApiResponse
from app.schemas.weekly_report import (
    WeeklyAvailabilityData,
    WeeklyGenerateRequest,
    WeeklyRegenerateRequest,
    WeeklyReportData,
    WeeklyReportListData,
    WeeklyReportListItemData,
    WeeklySaveRequest,
)
from app.services.weekly_report import WeeklyReportService, parse_weekly_content

router = APIRouter(prefix="/api/v1/weekly-reports", tags=["weekly-reports"])


def _report_data(report: WeeklyReport) -> WeeklyReportData:
    return WeeklyReportData(
        id=report.id,
        week_start=report.week_start,
        week_end=report.week_end,
        content=parse_weekly_content(report.content_json),
        generated_content=parse_weekly_content(report.generated_content_json),
        version=report.version,
        generated_at=report.generated_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def _list_item(report: WeeklyReport) -> WeeklyReportListItemData:
    return WeeklyReportListItemData(
        id=report.id,
        week_start=report.week_start,
        week_end=report.week_end,
        version=report.version,
        generated_at=report.generated_at,
        updated_at=report.updated_at,
    )


@router.get("/availability", response_model=ApiResponse[WeeklyAvailabilityData])
async def get_weekly_availability(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    week_start: date,
) -> ApiResponse[WeeklyAvailabilityData]:
    data = await WeeklyReportService(session).availability(current_user.id, week_start)
    return ApiResponse(data=data)


@router.get("", response_model=ApiResponse[WeeklyReportListData])
async def list_weekly_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    week_from: date | None = None,
    week_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[WeeklyReportListData]:
    items, total = await WeeklyReportService(session).list_reports(
        current_user.id, week_from=week_from, week_to=week_to, page=page, page_size=page_size
    )
    return ApiResponse(
        data=WeeklyReportListData(
            items=[_list_item(item) for item in items], page=page, page_size=page_size, total=total
        )
    )


@router.post("", response_model=ApiResponse[WeeklyReportData])
async def create_weekly_report(
    payload: WeeklyGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeeklyReportData]:
    report = await WeeklyReportService(session).generate(
        current_user.id, week_start=payload.week_start
    )
    return ApiResponse(data=_report_data(report))


@router.get("/{report_id}", response_model=ApiResponse[WeeklyReportData])
async def get_weekly_report(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeeklyReportData]:
    report = await WeeklyReportService(session).get(current_user.id, report_id)
    return ApiResponse(data=_report_data(report))


@router.put("/{report_id}", response_model=ApiResponse[WeeklyReportData])
async def save_weekly_report(
    report_id: str,
    payload: WeeklySaveRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeeklyReportData]:
    report = await WeeklyReportService(session).save(
        current_user.id,
        report_id,
        expected_version=payload.version,
        supplement=payload.supplement,
        next_week_plan=payload.next_week_plan,
        risks=payload.risks,
    )
    return ApiResponse(data=_report_data(report))


@router.post("/{report_id}/regenerate", response_model=ApiResponse[WeeklyReportData])
async def regenerate_weekly_report(
    report_id: str,
    payload: WeeklyRegenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeeklyReportData]:
    report = await WeeklyReportService(session).regenerate(
        current_user.id,
        report_id,
        expected_version=payload.version,
        confirm_overwrite=payload.confirm_overwrite,
    )
    return ApiResponse(data=_report_data(report))
