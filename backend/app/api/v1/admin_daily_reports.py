from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.db.session import get_db_session
from app.models import User
from app.repositories.daily_report import AdminSubmittedEntry
from app.schemas.admin_daily_report import (
    AdminAuditEventData,
    AdminAuditEventListData,
    AdminDailyReportRevokeRequest,
    AdminDailyReportSubmittedItemData,
    AdminDailyReportSubmittedListData,
)
from app.schemas.common import ApiResponse
from app.services.admin_daily_report import AdminDailyReportService

router = APIRouter(prefix="/api/v1/admin", tags=["admin-daily-reports"])

AuditAction = Literal["daily_submission_revoked", "user_deleted"]


def _submitted_item(entry: AdminSubmittedEntry) -> AdminDailyReportSubmittedItemData:
    return AdminDailyReportSubmittedItemData(
        id=entry.id,
        owner_id=entry.owner_id,
        owner_username=entry.owner_username,
        owner_display_name=entry.owner_display_name,
        work_date=entry.work_date,
        submitted_at=entry.submitted_at,
        version=entry.version,
    )


@router.get(
    "/daily-reports/submitted", response_model=ApiResponse[AdminDailyReportSubmittedListData]
)
async def list_submitted_daily_reports(
    _admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[AdminDailyReportSubmittedListData]:
    items, total = await AdminDailyReportService(session).list_submitted(
        page=page, page_size=page_size
    )
    return ApiResponse(
        data=AdminDailyReportSubmittedListData(
            items=[_submitted_item(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


@router.post(
    "/daily-reports/{report_id}/revoke-submission",
    response_model=ApiResponse[AdminDailyReportSubmittedItemData],
)
async def revoke_daily_report_submission(
    report_id: str,
    payload: AdminDailyReportRevokeRequest,
    admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[AdminDailyReportSubmittedItemData]:
    entry = await AdminDailyReportService(session).revoke_submission(
        admin,
        report_id,
        expected_version=payload.version,
        reason=payload.reason,
    )
    return ApiResponse(data=_submitted_item(entry))


@router.get("/audit-events", response_model=ApiResponse[AdminAuditEventListData])
async def list_audit_events(
    _admin: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    action: AuditAction | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[AdminAuditEventListData]:
    items, total = await AdminDailyReportService(session).list_audit_events(
        action=action,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=AdminAuditEventListData(
            items=[
                AdminAuditEventData(
                    id=event.id,
                    action=event.action,
                    actor_username_snapshot=event.actor_username_snapshot,
                    target_type=event.target_type,
                    target_id=event.target_id,
                    target_owner_id=event.target_owner_id,
                    reason=event.reason,
                    created_at=event.created_at,
                )
                for event in items
            ],
            page=page,
            page_size=page_size,
            total=total,
        )
    )
