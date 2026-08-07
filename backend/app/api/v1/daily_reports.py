from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import DailyReport, User
from app.schemas.auth import EmptyData
from app.schemas.common import ApiResponse
from app.schemas.daily_report import (
    DailyCreateRequest,
    DailyReportCreateData,
    DailyReportData,
    DailyReportListData,
    DailyReportListItemData,
    DailyRevocationData,
    DailySaveRequest,
    DailyStatus,
    DailyVersionRequest,
)
from app.services.daily_report import (
    DailyReportService,
    parse_daily_content,
)
from app.services.template import parse_template_fields

router = APIRouter(prefix="/api/v1/daily-reports", tags=["daily-reports"])


async def _last_revocation(session: AsyncSession, report_id: str) -> DailyRevocationData | None:
    revocation = await DailyReportService(session).last_revocation(report_id)
    if revocation is None:
        return None
    return DailyRevocationData(
        reason=revocation.reason,
        revoked_at=revocation.created_at,
        actor_username=revocation.actor_username_snapshot,
    )


async def _report_data(session: AsyncSession, report: DailyReport) -> DailyReportData:
    return DailyReportData(
        id=report.id,
        day_id=report.day_id,
        work_date=report.work_date,
        status=cast(DailyStatus, report.status),
        template_version_id=report.template_version_id,
        template_snapshot=parse_template_fields(report.template_snapshot_json),
        content=parse_daily_content(report.content_json),
        version=report.version,
        submitted_at=report.submitted_at,
        archived_at=report.archived_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
        last_revocation=await _last_revocation(session, report.id),
    )


def _list_item(report: DailyReport) -> DailyReportListItemData:
    return DailyReportListItemData(
        id=report.id,
        day_id=report.day_id,
        work_date=report.work_date,
        status=cast(DailyStatus, report.status),
        version=report.version,
        updated_at=report.updated_at,
        submitted_at=report.submitted_at,
        archived_at=report.archived_at,
    )


@router.get("", response_model=ApiResponse[DailyReportListData])
async def list_daily_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    date_from: date | None = None,
    date_to: date | None = None,
    status: DailyStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[DailyReportListData]:
    items, total = await DailyReportService(session).list_reports(
        current_user.id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=DailyReportListData(
            items=[_list_item(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


@router.post("", response_model=ApiResponse[DailyReportCreateData])
async def create_daily_report(
    payload: DailyCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[DailyReportCreateData]:
    report, created = await DailyReportService(session).create(
        current_user.id,
        work_date=payload.work_date,
        client_request_id=payload.client_request_id,
    )
    data = await _report_data(session, report)
    # `.__dict__` (not `.model_dump()`) is used deliberately: `DailyReportData`'s
    # `field_serializer`s apply even to python-mode dumps, which would turn
    # every datetime field into an already-formatted string here.
    return ApiResponse(data=DailyReportCreateData(**data.__dict__, created=created))


@router.get("/{report_id}", response_model=ApiResponse[DailyReportData])
async def get_daily_report(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[DailyReportData]:
    report = await DailyReportService(session).get(current_user.id, report_id)
    return ApiResponse(data=await _report_data(session, report))


@router.patch("/{report_id}", response_model=ApiResponse[DailyReportData])
async def save_daily_report(
    report_id: str,
    payload: DailySaveRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[DailyReportData]:
    report = await DailyReportService(session).save(
        current_user.id,
        report_id,
        expected_version=payload.version,
        content=payload.content,
    )
    return ApiResponse(data=await _report_data(session, report))


@router.delete("/{report_id}", response_model=ApiResponse[EmptyData])
async def delete_daily_report(
    report_id: str,
    payload: DailyVersionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[EmptyData]:
    await DailyReportService(session).delete(
        current_user.id, report_id, expected_version=payload.version
    )
    return ApiResponse(data=EmptyData())


@router.post("/{report_id}/submit", response_model=ApiResponse[DailyReportData])
async def submit_daily_report(
    report_id: str,
    payload: DailyVersionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[DailyReportData]:
    report = await DailyReportService(session).submit(
        current_user.id, report_id, expected_version=payload.version
    )
    return ApiResponse(data=await _report_data(session, report))
