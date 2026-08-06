from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiResponse
from app.schemas.settings import CapabilitiesData, SettingsData
from app.services.settings import SettingsService

router = APIRouter(tags=["settings"])


@router.get("/api/v1/settings/me", response_model=ApiResponse[SettingsData])
async def get_my_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SettingsData]:
    settings = await SettingsService(session).get(current_user.id)
    return ApiResponse(data=SettingsData(timezone=settings.timezone))


@router.get("/api/v1/capabilities", response_model=ApiResponse[CapabilitiesData])
async def get_capabilities(
    _current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[CapabilitiesData]:
    return ApiResponse(data=CapabilitiesData())
