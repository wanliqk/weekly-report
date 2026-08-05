from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiResponse
from app.schemas.template import (
    TemplateCurrentData,
    TemplatePublishRequest,
    TemplateVersionsData,
    TemplateVersionSummaryData,
)
from app.services.template import TemplateService

router = APIRouter(prefix="/api/v1/report-templates", tags=["report-templates"])


@router.get("/current", response_model=ApiResponse[TemplateCurrentData])
async def get_current_template(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[TemplateCurrentData]:
    template, _version, fields = await TemplateService(session).get_current(current_user.id)
    return ApiResponse(
        data=TemplateCurrentData(
            id=template.id,
            name=template.name,
            version_no=template.current_version_no,
            fields=fields,
        )
    )


@router.put("/current", response_model=ApiResponse[TemplateCurrentData])
async def publish_template(
    payload: TemplatePublishRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[TemplateCurrentData]:
    template, version, fields = await TemplateService(session).publish(
        current_user.id, fields=payload.fields
    )
    return ApiResponse(
        data=TemplateCurrentData(
            id=template.id,
            name=template.name,
            version_no=version.version_no,
            fields=fields,
        )
    )


@router.get("/versions", response_model=ApiResponse[TemplateVersionsData])
async def list_template_versions(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[TemplateVersionsData]:
    versions = await TemplateService(session).list_versions(current_user.id)
    return ApiResponse(
        data=TemplateVersionsData(
            items=[
                TemplateVersionSummaryData(
                    id=version.id,
                    version_no=version.version_no,
                    created_at=version.created_at,
                )
                for version in versions
            ]
        )
    )
