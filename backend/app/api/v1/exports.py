import asyncio
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_app_settings, get_current_user
from app.core.config import Settings
from app.db.session import get_db_session
from app.models import ExportJob, User
from app.schemas.common import ApiResponse
from app.schemas.export import ExportCreateRequest, ExportJobData, ExportStatus
from app.services.export import EXPORT_MEDIA_TYPE, ExportService

router = APIRouter(prefix="/api/v1/daily-report-exports", tags=["daily-report-exports"])


def _job_data(job: ExportJob) -> ExportJobData:
    return ExportJobData(
        id=job.id,
        status=cast(ExportStatus, job.status),
        record_count=job.record_count,
        file_name=job.file_name,
        created_at=job.created_at,
        expires_at=job.expires_at,
    )


@router.post("", response_model=ApiResponse[ExportJobData])
async def create_export(
    payload: ExportCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ApiResponse[ExportJobData]:
    job = await ExportService(session, settings).create(
        current_user.id,
        daily_report_day_ids=payload.daily_report_day_ids,
        filter_=payload.filter,
    )
    return ApiResponse(data=_job_data(job))


@router.get("/{job_id}", response_model=ApiResponse[ExportJobData])
async def get_export(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ApiResponse[ExportJobData]:
    job = await ExportService(session, settings).get(current_user.id, job_id)
    return ApiResponse(data=_job_data(job))


@router.get("/{job_id}/file")
async def download_export(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> Response:
    file_name, path = await ExportService(session, settings).get_download(current_user.id, job_id)
    content = await asyncio.to_thread(path.read_bytes)
    return Response(
        content=content,
        media_type=EXPORT_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
