"""Main-only WeCom REST surface (`docs/方案设计.md` §9.2).

Only Electron Main's `WeComBridgeClient` ever calls these routes: they
accept a structured Cookie jar directly in the request body (never a raw
`Cookie` header or an arbitrary target URL) and are gated by both the
ordinary JWT (`get_current_user`) and the separate `X-Main-Bridge-Secret`
(`require_main_bridge_secret`, applied at router level so it runs before any
handler body). `include_in_schema=False` keeps this surface out of the
public `/docs`/`/openapi.json` (`docs/方案设计.md` §12: "Main-only 端点默认不
出现在公开 OpenAPI").
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_main_bridge_secret
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiResponse
from app.schemas.wecom import (
    WeComConnectionValidateRequest,
    WeComCredentialSlotData,
    WeComInternalAckData,
    WeComSyncExecuteRequest,
)
from app.services.wecom_connection import WeComConnectionService
from app.services.wecom_sync import WeComSyncService

router = APIRouter(
    prefix="/api/v1/internal/wecom",
    tags=["wecom-internal"],
    dependencies=[Depends(require_main_bridge_secret)],
    include_in_schema=False,
)


@router.post("/connections/validate", response_model=ApiResponse[WeComInternalAckData])
async def validate_connection(
    payload: WeComConnectionValidateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComInternalAckData]:
    await WeComConnectionService(session).validate_connection(
        current_user.id,
        cookie_jar=payload.cookie_jar,
        credential_slot=payload.credential_slot,
        form_id=payload.form_id,
    )
    return ApiResponse(data=WeComInternalAckData(status="connected"))


@router.get("/connections/credential-slot", response_model=ApiResponse[WeComCredentialSlotData])
async def get_connection_credential_slot(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComCredentialSlotData]:
    """Return only the current user's opaque slot to Electron Main.

    This hidden, double-authenticated endpoint is the restart-safe bridge
    between the database's non-sensitive binding metadata and Main's encrypted
    credential files. The slot never crosses preload or renderer.
    """

    binding = await WeComConnectionService(session).get_binding(current_user.id)
    return ApiResponse(
        data=WeComCredentialSlotData(
            credential_slot=binding.credential_slot if binding is not None else None,
            connection_status=binding.status if binding is not None else None,
        )
    )


@router.post("/connections/disconnect", response_model=ApiResponse[WeComInternalAckData])
async def disconnect_connection(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComInternalAckData]:
    await WeComConnectionService(session).disconnect(current_user.id)
    return ApiResponse(data=WeComInternalAckData(status="disconnected"))


@router.post("/sync-records/{record_id}/execute", response_model=ApiResponse[WeComInternalAckData])
async def execute_sync(
    record_id: str,
    payload: WeComSyncExecuteRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComInternalAckData]:
    record = await WeComSyncService(session).execute(
        current_user.id, record_id, cookie_jar=payload.cookie_jar
    )
    return ApiResponse(data=WeComInternalAckData(status=record.status))
