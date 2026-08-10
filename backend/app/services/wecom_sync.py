"""`WeComSyncService`: preview, idempotent record creation, and the
execute/retry state machine (`docs/方案设计.md` §4.2/§5.2/§5.3/§10/§11).

`docs/方案设计.md` §3.2 requires the external HTTP call to never happen while
a SQLite write transaction is open: `execute()` is split into three phases —
a short transaction that atomically claims the record (`pending/.../uncertain
-> syncing`), an out-of-transaction phase that talks to `WeComInternalClient`
and never touches the session's write path, and a second short transaction
that writes the final outcome conditioned on `attempt_token` still matching
(so a late response from a superseded attempt is silently discarded).
"""

from __future__ import annotations

import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.config import Settings
from app.core.errors import AppError
from app.core.ulid import generate_ulid
from app.integrations.wecom.client import (
    WeComAuthExpired,
    WeComBusinessRejected,
    WeComClientError,
    WeComProtocolChanged,
    WeComSchemaChanged,
    WeComTransportFailed,
)
from app.integrations.wecom.schemas import (
    WeComAnswerItem,
    WeComCookieIn,
    WeComFormDetail,
    WeComQuestionItem,
    WeComSubmissionResult,
    WeComSubmitDailyPayload,
)
from app.models import WeComDailySyncRecord, WeComSyncProfile, WeComUserBinding
from app.repositories.daily_report_day import DailyReportDayRepository
from app.repositories.wecom import (
    WeComDailySyncRecordRepository,
    WeComSyncProfileRepository,
    WeComUserBindingRepository,
)
from app.schemas.wecom import (
    WeComFieldMappingConfig,
    WeComQuestionMappingConfig,
    WeComQuestionSpec,
    WeComRecipientConfig,
)
from app.services.daily_report_day import (
    DailyReportDayNotFoundError,
    parse_day_archive_snapshot,
)
from app.services.wecom_connection import build_question_spec, compute_destination_fingerprint
from app.services.wecom_mapper import (
    WeComMappedPreview,
    build_wecom_preview,
    compute_schema_fingerprint,
)


class WeComClientLike(Protocol):
    """Duck-typed subset of `WeComInternalClient` — see
    `app/services/wecom_connection.py`'s identically-named Protocol for why
    tests inject a stub instead of a real HTTP client. `execute()` uses both
    protocol methods below: `get_form_detail()` (structure re-check; its
    `fork_items` are fetched but no longer used for duplicate detection —
    `docs/方案设计.md` §10.2's second revision) replaces the old
    `get_template_info()` + `list_journals()` pair."""

    async def get_form_detail(
        self, cookie_jar: Sequence[WeComCookieIn], form_id: str
    ) -> WeComFormDetail: ...

    async def submit_daily(
        self, cookie_jar: Sequence[WeComCookieIn], payload: WeComSubmitDailyPayload
    ) -> WeComSubmissionResult: ...

    async def aclose(self) -> None: ...


class WeComNotConnectedError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40911, http_status=409, message="企业微信未连接或登录已失效,请先连接")


class WeComDayNotArchivedError(AppError):
    """`docs/方案设计.md` §9.4: "日报未归档继续复用现有状态不允许错误,不新建同义错误码" —
    reuses the existing generic "illegal status transition" code (`40902`,
    already used by `DailyReportStateError` for entry-level violations) for
    this day-container-level precondition instead of minting a new one."""

    def __init__(self) -> None:
        super().__init__(code=40902, http_status=409, message="日期尚未归档,无法与企业微信同步")


class WeComSyncRecordNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="同步记录不存在")


class WeComAlreadySucceededError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40913, http_status=409, message="该正式日报已成功同步")


class WeComSyncInProgressError(AppError):
    """Distinguishable from a "real" failure via `data.status` — callers
    (Main, then eventually the renderer polling `GET /sync-records/{id}`)
    can branch on this without a dedicated numeric code, since `docs/方案设计.md`
    §9.4's frozen error table doesn't define one for "already in flight"."""

    def __init__(self) -> None:
        super().__init__(
            code=40902,
            http_status=409,
            message="同步正在处理中,请稍后查询结果",
            data={"status": "syncing"},
        )


class WeComUncertainRetryBlockedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code=40914, http_status=409, message="上次同步结果不确定,禁止直接重试,请先对账"
        )


# Every status a record can hold *except* `succeeded`/`syncing`, which are
# always checked and rejected explicitly before this set is consulted.
# `uncertain` is deliberately included: see the module-level note on
# `execute()` and this task's report for why (`SEC-015`/§10.3 says a record
# can only leave `uncertain` via remote reconciliation; nothing in this
# codebase currently *triggers* `execute()` against an `uncertain` record —
# `retry()` explicitly refuses it — but if some future reconciliation flow
# ever calls `execute()` directly, the state machine must not reject it here
# purely because of that unrelated gap).
_EXECUTABLE_SOURCE_STATUSES = (
    "pending",
    "failed",
    "auth_required",
    "schema_changed",
    "duplicate_detected",
    "uncertain",
)
_RETRY_ALLOWED_SOURCE_STATUSES = ("failed", "auth_required", "schema_changed", "duplicate_detected")

# `docs/方案设计.md` §10.3: how long a record may sit in `syncing` before a
# startup recovery sweep treats it as crash-interrupted. Generous relative to
# the Client's own connect/write/read timeouts (`WECOM-04`) so a merely-slow
# in-flight request is never misclassified while the process is still alive
# — this sweep only ever runs once, at the next startup.
STALE_SYNCING_LEASE_SECONDS = 300


def _app_error_for(status: str, kind: str | None = None, *, message: str | None = None) -> AppError:
    if status == "auth_required":
        return AppError(
            code=40911, http_status=409, message="企业微信未连接或登录已失效,请先重新登录"
        )
    if status == "schema_changed":
        return AppError(code=40912, http_status=409, message="企业微信模板结构已变化")
    if status == "duplicate_detected":
        return AppError(code=40915, http_status=409, message="检测到可能的企业微信重复日报")
    if status == "uncertain":
        return AppError(
            code=50302, http_status=503, message="企业微信暂时不可用,结果不确定,请稍后重试"
        )
    # status == "failed"
    if kind == "transport_failed":
        return AppError(code=50302, http_status=503, message="企业微信暂时不可用,请稍后重试")
    if kind in ("unmapped_fields", "payload_invalid"):
        return AppError(
            code=40001, http_status=400, message="同步内容未完成映射或超出限制,请检查同步设置"
        )
    if kind == "business_rejected":
        # `message` is `_classify_read_client_error`/`_classify_write_client_error`'s
        # already-built `_business_rejection_message()` text (includes
        # `biz_code`) — reused here instead of a second, independently
        # hardcoded generic sentence so the synchronous error response the
        # caller sees immediately matches what gets persisted to
        # `last_error_message`.
        return AppError(code=50201, http_status=502, message=message or "企业微信拒绝了本次操作")
    return AppError(code=50201, http_status=502, message="企业微信返回内容不符合已知协议")


def _business_rejection_message(exc: WeComBusinessRejected, *, action: str) -> str:
    """`action` is "请求"(读取模板结构) or "提交"(写入日报答案).

    WeCom frequently rejects with a non-zero business code and no `head.msg`
    text at all (`ai-docs/issues.md` `ISS-042`: `business_code=-120000035`,
    no文案) — the business code is the only diagnostic ever actually
    available, so it's always surfaced directly instead of being hidden
    behind one fixed generic sentence regardless of the real reason.
    `exc.biz_message` (verbatim text from WeCom's own response body, when it
    does provide one) is deliberately never forwarded to the user —
    `docs/方案设计.md` §9.4: "响应只给出用户可行动建议和本地 record_id,不透传企业微信
    原始响应"; `biz_code` is the documented safe exception (`WeComClientError`'s
    own docstring lists "a business code" alongside an HTTP status as
    safe-to-surface classification context, unlike a raw body)."""
    return f"企业微信拒绝了本次{action}(业务码 {exc.biz_code})"


def _classify_read_client_error(exc: WeComClientError) -> tuple[str, str, str, str | None]:
    """`(status, last_error_kind, last_error_message, binding_status)` for a
    read-only Client call (`get_form_detail`)."""
    if isinstance(exc, WeComAuthExpired):
        return "auth_required", "auth_expired", "登录状态已失效,请重新连接企业微信", "expired"
    if isinstance(exc, WeComSchemaChanged | WeComProtocolChanged):
        return "schema_changed", "schema_changed", "企业微信模板结构已变化,请重新连接", None
    if isinstance(exc, WeComBusinessRejected):
        return "failed", "business_rejected", _business_rejection_message(exc, action="请求"), None
    if isinstance(exc, WeComTransportFailed):
        return "failed", "transport_failed", "无法连接企业微信服务,请稍后重试", None
    # WeComOutcomeUncertain: a read timed out mid-request.
    return "uncertain", "uncertain", "请求超时,结果不确定,请稍后重试", None


def _classify_write_client_error(exc: WeComClientError) -> tuple[str, str, str, str | None]:
    """Same shape for `submit_daily`. Per `WECOM-04`, this call only ever
    raises `WeComAuthExpired`/`WeComBusinessRejected`/`WeComTransportFailed`/
    `WeComOutcomeUncertain` — never `WeComSchemaChanged`/`WeComProtocolChanged`
    (those are read-call-only); the fallback branch below is defensive."""
    if isinstance(exc, WeComAuthExpired):
        return "auth_required", "auth_expired", "登录状态已失效,请重新连接企业微信", "expired"
    if isinstance(exc, WeComBusinessRejected):
        return "failed", "business_rejected", _business_rejection_message(exc, action="提交"), None
    if isinstance(exc, WeComTransportFailed):
        return "failed", "transport_failed", "无法连接企业微信服务,请稍后重试", None
    return "uncertain", "uncertain", "提交结果不确定,请勿重复提交,需先对账", None


def _rebuild_current_specs(
    questions: list[WeComQuestionItem], question_mapping: WeComQuestionMappingConfig
) -> tuple[WeComQuestionSpec, WeComQuestionSpec, WeComQuestionSpec] | None:
    """Re-derives the three target questions' *current* specs by looking
    each one up **by the `question_id` already saved** in `wecom_sync_profiles`
    — never by re-running the title heuristic (`docs/方案设计.md` §7.1: "标签匹配
    只用于首次配置时给出候选,不得把'名称包含计划'作为运行时规则"). Returns `None` if any
    of the three questions is now missing or has an unrecognized `reply_type`
    — both are treated as "the structure changed" by the caller."""
    by_id = {item.question_id: item for item in questions}
    specs: list[WeComQuestionSpec] = []
    for configured in (
        question_mapping.date_question,
        question_mapping.today_question,
        question_mapping.tomorrow_question,
    ):
        item = by_id.get(configured.question_id)
        if item is None:
            return None
        spec = build_question_spec(item, submit_order=configured.submit_order)
        if spec is None:
            return None
        specs.append(spec)
    return specs[0], specs[1], specs[2]


@dataclass
class _SyncAttemptOutcome:
    status: str
    profile_id: str
    profile_version: int
    payload_fingerprint: str
    remote_answer_id: str | None = None
    remote_reply_id: str | None = None
    remote_journal_uuid: str | None = None
    last_error_kind: str | None = None
    last_error_message: str | None = None
    binding_status: str | None = None
    remote_user_vid: str | None = None
    app_error: AppError | None = None


class WeComSyncService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        client: WeComClientLike | None = None,
        client_factory: Callable[[], WeComClientLike] | None = None,
        clock: Clock = utc_now,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._injected_client = client
        self._client_factory = client_factory
        self._clock = clock
        # See `WeComConnectionService`'s matching comment: threaded in via
        # `Depends(get_app_settings)`, never read from the global
        # `get_settings()` singleton inside this Service.
        self._settings = settings
        self._records = WeComDailySyncRecordRepository(session)
        self._profiles = WeComSyncProfileRepository(session)
        self._bindings = WeComUserBindingRepository(session)
        self._days = DailyReportDayRepository(session)

    def _new_client(self) -> WeComClientLike:
        if self._client_factory is not None:
            return self._client_factory()
        from app.integrations.wecom.client import WeComInternalClient

        debug_raw_body = (
            self._settings.wecom_debug_raw_body if self._settings is not None else False
        )
        return WeComInternalClient(debug_raw_body=debug_raw_body)

    async def _require_connected_binding(self, owner_id: str) -> WeComUserBinding:
        binding = await self._bindings.get_for_owner(owner_id)
        if binding is None or binding.status != "connected":
            raise WeComNotConnectedError()
        return binding

    async def _require_active_profile(self, owner_id: str) -> WeComSyncProfile:
        profile = await self._profiles.get_for_owner(owner_id)
        if profile is None or not profile.is_active:
            raise WeComNotConnectedError()
        return profile

    # -- preview --------------------------------------------------------------

    async def preview(self, owner_id: str, daily_report_day_id: str) -> WeComMappedPreview:
        """`docs/方案设计.md` §5.2: never persisted, never logged — this
        method's return value is handed straight back to the API layer."""
        day = await self._days.get_for_owner_by_id(owner_id, daily_report_day_id)
        if day is None:
            raise DailyReportDayNotFoundError()
        if day.status != "archived":
            raise WeComDayNotArchivedError()
        await self._require_connected_binding(owner_id)
        profile = await self._require_active_profile(owner_id)
        assert day.archive_snapshot_json is not None
        snapshot = parse_day_archive_snapshot(day.archive_snapshot_json)
        field_mapping = WeComFieldMappingConfig.model_validate_json(profile.field_mapping_json)
        return build_wecom_preview(snapshot, field_mapping)

    # -- create/get (idempotent) -----------------------------------------------

    async def get_or_create_record(
        self, owner_id: str, work_date: date
    ) -> tuple[WeComDailySyncRecord, bool]:
        """`docs/方案设计.md` §10.1: creation itself is always idempotent —
        an existing record for `(day, destination)` is returned as-is
        regardless of its status; whether it can be *acted on again* is the
        execute/retry state machine's job, not creation's."""
        day = await self._days.get_for_owner_by_date(owner_id, work_date)
        if day is None:
            raise DailyReportDayNotFoundError()
        if day.status != "archived":
            raise WeComDayNotArchivedError()
        await self._require_connected_binding(owner_id)
        profile = await self._require_active_profile(owner_id)
        destination_fingerprint = compute_destination_fingerprint(
            profile.form_id, profile.template_id
        )

        existing = await self._records.get_for_owner_by_day_and_destination(
            owner_id=owner_id,
            daily_report_day_id=day.id,
            destination_fingerprint=destination_fingerprint,
        )
        if existing is not None:
            return existing, False

        # A real (not blocking-enforced) payload fingerprint is computed even
        # at creation time purely to satisfy `wecom_daily_sync_records`'
        # existing `length(payload_fingerprint) = 64` CHECK constraint
        # (WECOM-02, not something this task may alter) — `build_wecom_preview`
        # is a pure function that never raises/blocks on unmapped fields by
        # itself, so calling it here doesn't smuggle in the "block on
        # unmapped fields" precheck that belongs at execute time instead.
        assert day.archive_snapshot_json is not None
        snapshot = parse_day_archive_snapshot(day.archive_snapshot_json)
        field_mapping = WeComFieldMappingConfig.model_validate_json(profile.field_mapping_json)
        preview = build_wecom_preview(snapshot, field_mapping)

        record = WeComDailySyncRecord(
            id=generate_ulid(),
            user_id=owner_id,
            daily_report_day_id=day.id,
            profile_id=profile.id,
            profile_version=profile.version,
            destination_fingerprint=destination_fingerprint,
            payload_fingerprint=preview.payload_fingerprint,
            status="pending",
            attempt_count=0,
            attempt_token=None,
        )
        try:
            await self._records.add(record)
        except IntegrityError:
            await self._session.rollback()
            existing = await self._records.get_for_owner_by_day_and_destination(
                owner_id=owner_id,
                daily_report_day_id=day.id,
                destination_fingerprint=destination_fingerprint,
            )
            if existing is not None:
                return existing, False
            raise
        await self._session.commit()
        created = await self._records.get_for_owner(record.id, owner_id)
        assert created is not None
        return created, True

    # -- query ------------------------------------------------------------------

    async def list_records(
        self,
        owner_id: str,
        *,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[WeComDailySyncRecord, date]], int]:
        return await self._records.list_page_for_owner(
            owner_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

    async def get_record(self, owner_id: str, record_id: str) -> tuple[WeComDailySyncRecord, date]:
        record = await self._records.get_for_owner(record_id, owner_id)
        if record is None:
            raise WeComSyncRecordNotFoundError()
        day = await self._days.get_for_owner_by_id(owner_id, record.daily_report_day_id)
        assert day is not None
        return record, day.work_date

    # -- retry --------------------------------------------------------------

    async def retry(self, owner_id: str, record_id: str) -> WeComDailySyncRecord:
        record = await self._records.get_for_owner(record_id, owner_id)
        if record is None:
            raise WeComSyncRecordNotFoundError()
        if record.status == "succeeded":
            raise WeComAlreadySucceededError()
        if record.status == "uncertain":
            # SEC-015 / §10.3: never automatically re-enter the state
            # machine from `uncertain` — only remote reconciliation may
            # resolve it, and nothing in this task wires that trigger up
            # (see `_EXECUTABLE_SOURCE_STATUSES`'s docstring and this
            # task's final report for the honest, documented gap).
            raise WeComUncertainRetryBlockedError()
        if record.status in ("pending", "syncing"):
            # Already queued or in flight; retry is a no-op, not an error.
            return record

        now = self._clock()
        transitioned = await self._records.transition_to_pending_for_retry(
            record_id=record_id,
            owner_id=owner_id,
            allowed_statuses=_RETRY_ALLOWED_SOURCE_STATUSES,
            now=now,
        )
        if not transitioned:
            await self._session.rollback()
            current = await self._records.get_for_owner(record_id, owner_id)
            if current is None:
                raise WeComSyncRecordNotFoundError()
            if current.status == "succeeded":
                raise WeComAlreadySucceededError()
            if current.status == "uncertain":
                raise WeComUncertainRetryBlockedError()
            return current
        await self._session.commit()
        refreshed = await self._records.get_for_owner(record_id, owner_id)
        assert refreshed is not None
        return refreshed

    # -- crash recovery -------------------------------------------------------

    async def recover_stale_syncing_records(self) -> int:
        """`docs/方案设计.md` §10.3's startup sweep. Called once from
        `app/__main__.py::main()`, before the app starts serving requests —
        never from a request handler. Not owner-scoped (see the repository
        method's docstring); returns the number of records recovered, purely
        for startup logging/observability.
        """
        now = self._clock()
        cutoff = now - timedelta(seconds=STALE_SYNCING_LEASE_SECONDS)
        recovered = await self._records.recover_stale_syncing(cutoff=cutoff, now=now)
        if recovered:
            await self._session.commit()
        return recovered

    # -- execute (the state machine core) ----------------------------------

    async def execute(
        self, owner_id: str, record_id: str, *, cookie_jar: Sequence[WeComCookieIn]
    ) -> WeComDailySyncRecord:
        record = await self._records.get_for_owner(record_id, owner_id)
        if record is None:
            raise WeComSyncRecordNotFoundError()
        if record.status == "succeeded":
            raise WeComAlreadySucceededError()

        attempt_token = secrets.token_hex(16)
        claim_time = self._clock()
        transitioned = await self._records.transition_to_syncing(
            record_id=record_id,
            owner_id=owner_id,
            allowed_statuses=_EXECUTABLE_SOURCE_STATUSES,
            attempt_token=attempt_token,
            now=claim_time,
        )
        if not transitioned:
            await self._session.rollback()
            current = await self._records.get_for_owner(record_id, owner_id)
            if current is None:
                raise WeComSyncRecordNotFoundError()
            if current.status == "succeeded":
                raise WeComAlreadySucceededError()
            if current.status == "syncing":
                raise WeComSyncInProgressError()
            raise AppError(code=40902, http_status=409, message="当前状态不允许执行同步")
        await self._session.commit()  # short transaction A ends here

        # -- everything below runs with no open SQLite write transaction ----
        outcome = await self._perform_remote_sync(
            owner_id=owner_id, record=record, cookie_jar=cookie_jar
        )

        # short transaction B: binding side effect + conditional finalize,
        # committed/rolled back together.
        if outcome.binding_status is not None:
            await self._apply_binding_status(owner_id, status=outcome.binding_status)
        if outcome.status == "succeeded" and outcome.remote_user_vid is not None:
            await self._heal_wecom_vid(owner_id, remote_user_vid=outcome.remote_user_vid)

        finalize_time = self._clock()
        finalized = await self._records.finalize_attempt(
            record_id=record_id,
            owner_id=owner_id,
            attempt_token=attempt_token,
            status=outcome.status,
            now=finalize_time,
            profile_id=outcome.profile_id,
            profile_version=outcome.profile_version,
            payload_fingerprint=outcome.payload_fingerprint,
            remote_answer_id=outcome.remote_answer_id,
            remote_reply_id=outcome.remote_reply_id,
            remote_journal_uuid=outcome.remote_journal_uuid,
            last_error_kind=outcome.last_error_kind,
            last_error_message=outcome.last_error_message,
            succeeded_at=finalize_time if outcome.status == "succeeded" else None,
        )
        if not finalized:
            # A newer attempt already superseded this one (its token no
            # longer matches) — discard this result entirely, including the
            # binding side effect just staged above (`docs/方案设计.md` §3.2
            # point 3).
            await self._session.rollback()
        else:
            await self._session.commit()

        refreshed = await self._records.get_for_owner(record_id, owner_id)
        assert refreshed is not None
        if finalized and outcome.app_error is not None:
            raise outcome.app_error
        return refreshed

    async def _apply_binding_status(self, owner_id: str, *, status: str) -> None:
        binding = await self._bindings.get_for_owner(owner_id)
        if binding is None:
            return
        binding.status = status
        if status == "expired":
            binding.last_auth_error_at = self._clock()
        binding.version += 1
        await self._session.flush()

    async def _heal_wecom_vid(self, owner_id: str, *, remote_user_vid: str) -> None:
        """`docs/方案设计.md` §5.1 step 5's honest caveat: the connect-time
        `wecom_vid` is only ever a best-guess placeholder. The first time a
        `submit_daily` call genuinely succeeds, its authoritative
        `WeComSubmissionResult.user_vid` is used to self-heal the saved
        value if it turns out to have been wrong."""
        binding = await self._bindings.get_for_owner(owner_id)
        if binding is None or binding.wecom_vid == remote_user_vid:
            return
        binding.wecom_vid = remote_user_vid
        binding.version += 1
        await self._session.flush()

    async def _perform_remote_sync(
        self, *, owner_id: str, record: WeComDailySyncRecord, cookie_jar: Sequence[WeComCookieIn]
    ) -> _SyncAttemptOutcome:
        """Never raises — every path returns a `_SyncAttemptOutcome` so
        `execute()` can unconditionally reach its finalize step and the
        record never gets stuck in `syncing` because of an exception
        escaping this method."""
        fallback_profile_id = record.profile_id
        fallback_profile_version = record.profile_version
        fallback_payload_fingerprint = record.payload_fingerprint

        binding = await self._bindings.get_for_owner(owner_id)
        profile = await self._profiles.get_for_owner(owner_id)
        day = await self._days.get_for_owner_by_id(owner_id, record.daily_report_day_id)
        if (
            binding is None
            or binding.status != "connected"
            or profile is None
            or not profile.is_active
            or day is None
            or day.archive_snapshot_json is None
        ):
            # The connection (or even the day itself) was torn down by a
            # concurrent request mid-flight. The record still must reach a
            # terminal state rather than being stuck in `syncing` forever.
            return _SyncAttemptOutcome(
                status="auth_required",
                profile_id=fallback_profile_id,
                profile_version=fallback_profile_version,
                payload_fingerprint=fallback_payload_fingerprint,
                last_error_kind="not_connected",
                last_error_message="企业微信连接已失效,请重新连接",
                app_error=_app_error_for("auth_required"),
            )

        client = self._injected_client if self._injected_client is not None else self._new_client()
        owns_client = self._injected_client is None
        try:
            try:
                form_detail = await client.get_form_detail(cookie_jar, profile.form_id)
            except WeComClientError as exc:
                status, kind, message, binding_status = _classify_read_client_error(exc)
                return _SyncAttemptOutcome(
                    status=status,
                    profile_id=profile.id,
                    profile_version=profile.version,
                    payload_fingerprint=fallback_payload_fingerprint,
                    last_error_kind=kind,
                    last_error_message=message,
                    binding_status=binding_status,
                    app_error=_app_error_for(status, kind, message=message),
                )

            question_mapping = WeComQuestionMappingConfig.model_validate_json(
                profile.question_mapping_json
            )
            fresh_specs = _rebuild_current_specs(form_detail.questions, question_mapping)
            if fresh_specs is None or (
                compute_schema_fingerprint(*fresh_specs) != profile.schema_fingerprint
            ):
                return _SyncAttemptOutcome(
                    status="schema_changed",
                    profile_id=profile.id,
                    profile_version=profile.version,
                    payload_fingerprint=fallback_payload_fingerprint,
                    last_error_kind="schema_changed",
                    last_error_message="企业微信模板结构已变化,与已保存配置不一致",
                    app_error=_app_error_for("schema_changed"),
                )

            # `docs/方案设计.md` §10.2 (2026-08-09 second revision): the
            # `fork_items`-based duplicate check has been removed entirely.
            # It produced false positives on every attempt — `fork_items`
            # lists form *instances that exist*, not ones that were actually
            # submitted to, and this same `get_form_detail()` call appears to
            # cause today's fork to exist as a side effect of merely being
            # asked about it, so "does today's fork exist" was never a valid
            # proxy for "did I already submit today". No field on
            # `fork_items` (`form_id`/`ctime`/`mtime`/`status`) reliably
            # distinguishes an empty placeholder from a real submission, so
            # there is currently no reliable duplicate signal available from
            # any verified endpoint; `submit_again=true` is trusted to be
            # WeCom's own accepted behavior for this integration, matching
            # the real working capture this flow is based on.

            raw_reply_type_by_question_id = {
                question.question_id: question.reply_type for question in form_detail.questions
            }

            def _is_rich_text(question_id: str) -> bool:
                # `24` is WeCom's own raw "rich text" question type — the one
                # value confirmed (`docs/方案设计.md` §2.4) to require the
                # `rich_text_reply` wire shape instead of bare `text_reply`.
                return raw_reply_type_by_question_id.get(question_id) == 24

            snapshot = parse_day_archive_snapshot(day.archive_snapshot_json)
            field_mapping = WeComFieldMappingConfig.model_validate_json(profile.field_mapping_json)
            preview = build_wecom_preview(snapshot, field_mapping)
            if preview.unmapped_field_keys and field_mapping.unmapped_policy == "block":
                # §7.3's precheck: never submit while non-empty custom
                # fields remain unmapped. Caught here, before any write call.
                return _SyncAttemptOutcome(
                    status="failed",
                    profile_id=profile.id,
                    profile_version=profile.version,
                    payload_fingerprint=preview.payload_fingerprint,
                    last_error_kind="unmapped_fields",
                    last_error_message="存在未映射的自定义字段,请先在同步设置中完成映射",
                    app_error=_app_error_for("failed", "unmapped_fields"),
                )

            recipient_config = WeComRecipientConfig.model_validate_json(
                profile.recipient_config_json
            )
            try:
                payload = WeComSubmitDailyPayload(
                    form_id=profile.form_id,
                    template_id=profile.template_id,
                    items=[
                        WeComAnswerItem(
                            question_id=question_mapping.date_question.question_id,
                            text_reply=preview.date_answer,
                            rich_text=_is_rich_text(question_mapping.date_question.question_id),
                        ),
                        WeComAnswerItem(
                            question_id=question_mapping.today_question.question_id,
                            text_reply=preview.today_work_answer,
                            rich_text=_is_rich_text(question_mapping.today_question.question_id),
                        ),
                        WeComAnswerItem(
                            question_id=question_mapping.tomorrow_question.question_id,
                            text_reply=preview.tomorrow_plan_answer,
                            rich_text=_is_rich_text(question_mapping.tomorrow_question.question_id),
                        ),
                    ],
                    mngreporter_vids=recipient_config.mngreporter_vids,
                    reporter_vids=recipient_config.reporter_vids,
                )
            except ValidationError:
                # §7.3: "文本未超过远端元数据限制;不静默截断" — an oversized answer
                # fails the precheck cleanly instead of being truncated.
                return _SyncAttemptOutcome(
                    status="failed",
                    profile_id=profile.id,
                    profile_version=profile.version,
                    payload_fingerprint=preview.payload_fingerprint,
                    last_error_kind="payload_invalid",
                    last_error_message="生成的同步内容超出企业微信限制",
                    app_error=_app_error_for("failed", "payload_invalid"),
                )

            try:
                result = await client.submit_daily(cookie_jar, payload)
            except WeComClientError as exc:
                status, kind, message, binding_status = _classify_write_client_error(exc)
                return _SyncAttemptOutcome(
                    status=status,
                    profile_id=profile.id,
                    profile_version=profile.version,
                    payload_fingerprint=preview.payload_fingerprint,
                    last_error_kind=kind,
                    last_error_message=message,
                    binding_status=binding_status,
                    app_error=_app_error_for(status, kind, message=message),
                )

            return _SyncAttemptOutcome(
                status="succeeded",
                profile_id=profile.id,
                profile_version=profile.version,
                payload_fingerprint=preview.payload_fingerprint,
                remote_answer_id=result.answer_id,
                remote_reply_id=result.reply_id,
                remote_journal_uuid=result.journal_uuid,
                remote_user_vid=result.user_vid,
            )
        finally:
            if owns_client:
                await client.aclose()
