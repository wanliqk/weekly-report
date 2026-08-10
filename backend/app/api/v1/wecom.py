"""Public WeCom REST surface (`docs/方案设计.md` §9.1).

Everything here runs behind the ordinary business-API gate: `get_current_user`
(JWT + forced-password-change check) plus the existing global
`RuntimeSecretMiddleware`. None of it ever accepts a Cookie, a Cookie header,
a credential file path, or a `credential_slot` — those only ever cross the
Main-only surface in `app/api/v1/internal_wecom.py`.
"""

from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User, WeComDailySyncRecord, WeComSyncProfile, WeComUserBinding
from app.schemas.common import ApiResponse
from app.schemas.wecom import (
    WeComBindingStatus,
    WeComConnectionData,
    WeComFieldMappingConfig,
    WeComPreviewData,
    WeComPreviewRequest,
    WeComProfileData,
    WeComProfileUpdateRequest,
    WeComQuestionMappingConfig,
    WeComRecipientConfig,
    WeComSyncRecordCreateData,
    WeComSyncRecordData,
    WeComSyncRecordListData,
    WeComSyncStatus,
)
from app.services.wecom_connection import WeComConnectionService
from app.services.wecom_mapper import WeComMappedPreview
from app.services.wecom_sync import WeComSyncService

router = APIRouter(prefix="/api/v1/wecom", tags=["wecom"])
# `docs/方案设计.md` §9.1's idempotent create endpoint is scoped under
# `/api/v1/daily-report-days/{work_date}/wecom-syncs`, not `/api/v1/wecom/**`
# — kept in this file (not `daily_report_days.py`) because it's owned by
# `WeComSyncService`, not `DailyReportDayService`, and every other WeCom
# route lives here.
day_sync_router = APIRouter(prefix="/api/v1/daily-report-days", tags=["wecom"])


def _connection_data(binding: WeComUserBinding | None) -> WeComConnectionData:
    if binding is None:
        return WeComConnectionData(
            connected=False,
            status=None,
            wecom_vid=None,
            display_name=None,
            corp_id=None,
            last_validated_at=None,
            last_auth_error_at=None,
        )
    return WeComConnectionData(
        connected=binding.status == "connected",
        status=cast(WeComBindingStatus, binding.status),
        wecom_vid=binding.wecom_vid,
        display_name=binding.display_name,
        corp_id=binding.corp_id,
        last_validated_at=binding.last_validated_at,
        last_auth_error_at=binding.last_auth_error_at,
    )


def _profile_data(profile: WeComSyncProfile) -> WeComProfileData:
    return WeComProfileData(
        form_id=profile.form_id,
        template_id=profile.template_id,
        destination_fingerprint=profile.destination_fingerprint,
        schema_fingerprint=profile.schema_fingerprint,
        question_mapping=WeComQuestionMappingConfig.model_validate_json(
            profile.question_mapping_json
        ),
        recipient_config=WeComRecipientConfig.model_validate_json(profile.recipient_config_json),
        field_mapping=WeComFieldMappingConfig.model_validate_json(profile.field_mapping_json),
        version=profile.version,
        is_active=profile.is_active,
    )


def _preview_data(preview: WeComMappedPreview) -> WeComPreviewData:
    return WeComPreviewData(
        date_answer=preview.date_answer,
        today_work_answer=preview.today_work_answer,
        tomorrow_plan_answer=preview.tomorrow_plan_answer,
        source_count=preview.source_count,
        today_work_char_count=preview.today_work_char_count,
        tomorrow_plan_char_count=preview.tomorrow_plan_char_count,
        unmapped_field_keys=preview.unmapped_field_keys,
    )


def _sync_record_fields(record: WeComDailySyncRecord, work_date: date) -> dict[str, object]:
    return {
        "id": record.id,
        "daily_report_day_id": record.daily_report_day_id,
        "work_date": work_date,
        "destination_fingerprint": record.destination_fingerprint,
        "status": record.status,
        "attempt_count": record.attempt_count,
        "remote_answer_id": record.remote_answer_id,
        "remote_reply_id": record.remote_reply_id,
        "remote_journal_uuid": record.remote_journal_uuid,
        "last_error_kind": record.last_error_kind,
        "last_error_message": record.last_error_message,
        "last_attempt_at": record.last_attempt_at,
        "succeeded_at": record.succeeded_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _sync_record_data(record: WeComDailySyncRecord, work_date: date) -> WeComSyncRecordData:
    return WeComSyncRecordData.model_validate(_sync_record_fields(record, work_date))


@router.get("/connection", response_model=ApiResponse[WeComConnectionData])
async def get_connection(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComConnectionData]:
    binding = await WeComConnectionService(session).get_binding(current_user.id)
    return ApiResponse(data=_connection_data(binding))


@router.get("/profile", response_model=ApiResponse[WeComProfileData])
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComProfileData]:
    profile = await WeComConnectionService(session).get_profile(current_user.id)
    return ApiResponse(data=_profile_data(profile))


@router.put("/profile", response_model=ApiResponse[WeComProfileData])
async def update_profile(
    payload: WeComProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComProfileData]:
    profile = await WeComConnectionService(session).update_profile(
        current_user.id,
        expected_version=payload.expected_version,
        field_mapping=payload.field_mapping,
    )
    return ApiResponse(data=_profile_data(profile))


@router.post("/previews", response_model=ApiResponse[WeComPreviewData])
async def create_preview(
    payload: WeComPreviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComPreviewData]:
    preview = await WeComSyncService(session).preview(current_user.id, payload.daily_report_day_id)
    return ApiResponse(data=_preview_data(preview))


@router.get("/sync-records", response_model=ApiResponse[WeComSyncRecordListData])
async def list_sync_records(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: WeComSyncStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[WeComSyncRecordListData]:
    items, total = await WeComSyncService(session).list_records(
        current_user.id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=WeComSyncRecordListData(
            items=[_sync_record_data(record, work_date) for record, work_date in items],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


@router.get("/sync-records/{record_id}", response_model=ApiResponse[WeComSyncRecordData])
async def get_sync_record(
    record_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComSyncRecordData]:
    record, work_date = await WeComSyncService(session).get_record(current_user.id, record_id)
    return ApiResponse(data=_sync_record_data(record, work_date))


@router.post("/sync-records/{record_id}/retry", response_model=ApiResponse[WeComSyncRecordData])
async def retry_sync_record(
    record_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComSyncRecordData]:
    await WeComSyncService(session).retry(current_user.id, record_id)
    record, work_date = await WeComSyncService(session).get_record(current_user.id, record_id)
    return ApiResponse(data=_sync_record_data(record, work_date))


@day_sync_router.post(
    "/{work_date}/wecom-syncs", response_model=ApiResponse[WeComSyncRecordCreateData]
)
async def create_or_get_sync_record(
    work_date: date,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[WeComSyncRecordCreateData]:
    record, created = await WeComSyncService(session).get_or_create_record(
        current_user.id, work_date
    )
    fields = _sync_record_fields(record, work_date)
    created_data = WeComSyncRecordCreateData.model_validate({**fields, "created": created})
    return ApiResponse(data=created_data)
