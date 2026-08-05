from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.common import ApiResponse
from app.schemas.system import BootstrapAdminData, BootstrapAdminRequest, BootstrapStatusData
from app.services.bootstrap import BootstrapService

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/bootstrap-status", response_model=ApiResponse[BootstrapStatusData])
async def get_bootstrap_status(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[BootstrapStatusData]:
    service = BootstrapService(session)
    initialized = await service.is_initialized()
    return ApiResponse(data=BootstrapStatusData(initialized=initialized))


@router.post("/bootstrap-admin", response_model=ApiResponse[BootstrapAdminData])
async def bootstrap_admin(
    payload: BootstrapAdminRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[BootstrapAdminData]:
    service = BootstrapService(session)
    user = await service.bootstrap_admin(
        username=payload.username,
        password=payload.password,
        display_name=payload.display_name,
    )
    return ApiResponse(data=BootstrapAdminData.model_validate(user))
