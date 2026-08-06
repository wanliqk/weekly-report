import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_app_settings, get_backup_registry, get_current_admin
from app.core.backup_registry import BackupRegistry
from app.core.config import Settings
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiResponse
from app.schemas.system import (
    BackupCreateData,
    BootstrapData,
    BootstrapRequest,
    BootstrapStatusData,
)
from app.services.backup import BACKUP_MEDIA_TYPE, BackupService
from app.services.bootstrap import BootstrapService

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/bootstrap-status", response_model=ApiResponse[BootstrapStatusData])
async def get_bootstrap_status(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[BootstrapStatusData]:
    service = BootstrapService(session)
    initialized = await service.is_initialized()
    return ApiResponse(data=BootstrapStatusData(initialized=initialized))


@router.post("/bootstrap", response_model=ApiResponse[BootstrapData])
async def bootstrap(
    payload: BootstrapRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[BootstrapData]:
    service = BootstrapService(session)
    user = await service.bootstrap(
        username=payload.username,
        password=payload.password,
        display_name=payload.display_name,
    )
    return ApiResponse(data=BootstrapData.model_validate(user))


@router.post("/backups", response_model=ApiResponse[BackupCreateData])
async def create_backup(
    current_admin: Annotated[User, Depends(get_current_admin)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    registry: Annotated[BackupRegistry, Depends(get_backup_registry)],
) -> ApiResponse[BackupCreateData]:
    record = await BackupService(registry, settings).create(current_admin.id)
    return ApiResponse(
        data=BackupCreateData(
            id=record.id, file_name=record.file_name, expires_at=record.expires_at
        )
    )


@router.get("/backups/{backup_id}/file")
async def download_backup(
    backup_id: str,
    current_admin: Annotated[User, Depends(get_current_admin)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    registry: Annotated[BackupRegistry, Depends(get_backup_registry)],
) -> Response:
    file_name, path = await BackupService(registry, settings).get_download(
        current_admin.id, backup_id
    )
    content = await asyncio.to_thread(path.read_bytes)
    return Response(
        content=content,
        media_type=BACKUP_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
