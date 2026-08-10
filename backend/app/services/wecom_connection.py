"""`WeComConnectionService`: connect/disconnect and profile management
(`docs/方案设计.md` §4.2/§5.1).

Owns the *connect* half of the WeCom integration: turning a Main-supplied
Cookie jar into a validated `wecom_user_bindings` row plus an initial
`wecom_sync_profiles` row, and the read/update paths for that profile.
Executing an actual sync is `WeComSyncService` (`app/services/wecom_sync.py`)
— the two are split because they're invoked from different Routers (public
vs Main-only) with different lifecycles, even though both sit behind the
same `WeComInternalClient` and the same two tables.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Protocol

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.config import Settings
from app.core.errors import AppError
from app.core.ulid import generate_ulid
from app.core.wecom_logging import log_wecom_event
from app.integrations.wecom.client import (
    WeComAuthExpired,
    WeComBusinessRejected,
    WeComClientError,
    WeComOutcomeUncertain,
    WeComProtocolChanged,
    WeComSchemaChanged,
    WeComTransportFailed,
)
from app.integrations.wecom.schemas import WeComCookieIn, WeComQuestionItem, WeComTemplateInfo
from app.models import WeComSyncProfile, WeComUserBinding
from app.repositories.wecom import WeComSyncProfileRepository, WeComUserBindingRepository
from app.schemas.wecom import (
    WeComFieldMappingConfig,
    WeComQuestionMappingConfig,
    WeComQuestionSpec,
    WeComRecipientConfig,
    WeComReplyType,
)
from app.services.wecom_mapper import compute_schema_fingerprint

logger = logging.getLogger("app.integrations.wecom.connection")


class WeComClientLike(Protocol):
    """Duck-typed subset of `WeComInternalClient` this Service depends on —
    lets tests inject a hand-written stub instead of a real HTTP client
    (`docs/方案设计.md` never requires network access in unit tests)."""

    async def get_template_info(
        self, cookie_jar: Sequence[WeComCookieIn], form_id: str
    ) -> WeComTemplateInfo: ...

    async def aclose(self) -> None: ...


class WeComNotConnectedError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40911, http_status=409, message="企业微信未连接或登录已失效,请先连接")


class WeComProfileVersionConflictError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40904, http_status=409, message="配置已被更新。请重新加载。")


class WeComTemplateStructureUnresolvedError(AppError):
    """`docs/方案设计.md` §7.1: only a first-connect heuristic is allowed to
    pick the three target questions; if it can't find all three (or one
    resolves to an unrecognized `reply_type`), the connection attempt fails
    cleanly instead of persisting a guessed-at, possibly-invalid config."""

    def __init__(self) -> None:
        super().__init__(
            code=50201,
            http_status=502,
            message="无法从企业微信模板中识别出日期/今日工作/明日计划三个目标题目",
        )


# `docs/方案设计.md` §8 point 5 classifies Client failures into six exception
# types; §11's table maps each *sync execution* scenario to a state-machine
# outcome. Connection validation isn't a state-machine transition (there is
# no `wecom_daily_sync_records` row yet), so failures here are reported as
# plain `AppError`s instead — this mapping keeps the same *spirit* (auth
# failures are distinguishable from "the remote's response doesn't make
# sense" from "the remote is temporarily unreachable") without inventing
# sync-record states that don't apply to this flow.
def _map_connection_client_error(exc: WeComClientError) -> AppError:
    if isinstance(exc, WeComAuthExpired):
        return WeComNotConnectedError()
    if isinstance(exc, WeComTransportFailed | WeComOutcomeUncertain):
        # "连接建立前失败" / a read timeout mid-connect: nothing was ever
        # committed (the whole flow is one local transaction that only
        # writes at the very end), so this is safely reported as a
        # confirmed-not-accepted temporary failure, matching 50302's
        # "可确认未受理" semantics even though 50302 is written with sync
        # execution in mind.
        return AppError(code=50302, http_status=503, message="企业微信暂时不可用,请稍后重试")
    if isinstance(exc, WeComSchemaChanged | WeComProtocolChanged | WeComBusinessRejected):
        return AppError(code=50201, http_status=502, message="企业微信返回内容不符合已知协议")
    return AppError(code=50201, http_status=502, message="企业微信返回内容不符合已知协议")


# Only the `reply_type` codes actually observed for date/text questions are
# mapped: legacy fixture text=1/date=11, live 2026-08 response text=24/date=11.
# A question whose `reply_type` isn't one of these is never a valid
# date/today/tomorrow candidate for this integration; encountering one just
# means "this isn't the question we're looking for", not a crash.
_REPLY_TYPE_MAP: dict[int, WeComReplyType] = {1: "text", 11: "date", 24: "text"}


def build_question_spec(item: WeComQuestionItem, *, submit_order: int) -> WeComQuestionSpec | None:
    """Turns one live `WeComQuestionItem` into a `WeComQuestionSpec`, or
    `None` if its `reply_type` isn't one this integration recognizes.

    Shared by connect-time discovery (this module) and `WeComSyncService`'s
    execute-time drift detection — the latter looks the question up *by the
    `question_id` already saved in `wecom_sync_profiles`*, never by title
    (`docs/方案设计.md` §7.1: title matching is first-connect only).
    """
    reply_type = _REPLY_TYPE_MAP.get(item.reply_type)
    if reply_type is None:
        return None
    sub_type: str | None = None
    if item.ext is not None:
        raw_sub_type = item.ext.get("qdata_sub_type")
        if isinstance(raw_sub_type, str):
            sub_type = raw_sub_type
    return WeComQuestionSpec(
        question_id=item.question_id,
        reply_type=reply_type,
        sub_type=sub_type,
        submit_order=submit_order,
    )


# First-connect-only candidate heuristic (`docs/方案设计.md` §7.1: "标签匹配只用于
# 首次配置时给出候选"). Matches the fixed template copy observed in
# `tests/fixtures/wecom/get_template_combine_info_response.json` ("日期"/
# "今日工作"/"明日计划"); a template using different wording would fail to
# resolve all three candidates and surface
# `WeComTemplateStructureUnresolvedError` rather than silently guessing.
_DATE_HINTS = ("日期",)
_TODAY_HINTS = ("今日",)
_TOMORROW_HINTS = ("明日",)


def _pop_first_matching(
    pool: list[WeComQuestionItem], hints: tuple[str, ...]
) -> WeComQuestionItem | None:
    for index, item in enumerate(pool):
        if any(hint in item.title for hint in hints):
            return pool.pop(index)
    return None


def _select_target_question_specs(
    questions: list[WeComQuestionItem],
) -> tuple[WeComQuestionSpec, WeComQuestionSpec, WeComQuestionSpec]:
    pool = list(questions)
    date_item = _pop_first_matching(pool, _DATE_HINTS)
    today_item = _pop_first_matching(pool, _TODAY_HINTS)
    tomorrow_item = _pop_first_matching(pool, _TOMORROW_HINTS)
    if date_item is None or today_item is None or tomorrow_item is None:
        raise WeComTemplateStructureUnresolvedError()

    date_spec = build_question_spec(date_item, submit_order=date_item.pos or 0)
    today_spec = build_question_spec(today_item, submit_order=today_item.pos or 1)
    tomorrow_spec = build_question_spec(tomorrow_item, submit_order=tomorrow_item.pos or 2)
    if date_spec is None or today_spec is None or tomorrow_spec is None:
        raise WeComTemplateStructureUnresolvedError()
    if len({date_spec.submit_order, today_spec.submit_order, tomorrow_spec.submit_order}) != 3:
        raise WeComTemplateStructureUnresolvedError()
    return date_spec, today_spec, tomorrow_spec


def _template_resolution_diagnostics(
    questions: list[WeComQuestionItem],
) -> dict[str, str | int | bool | None]:
    def single_candidate_reply_type(hints: tuple[str, ...]) -> int | None:
        candidates = [item for item in questions if any(hint in item.title for hint in hints)]
        return candidates[0].reply_type if len(candidates) == 1 else None

    return {
        "question_count": len(questions),
        "recognized_question_count": sum(item.reply_type in _REPLY_TYPE_MAP for item in questions),
        "date_candidate_count": sum(
            any(hint in item.title for hint in _DATE_HINTS) for item in questions
        ),
        "today_candidate_count": sum(
            any(hint in item.title for hint in _TODAY_HINTS) for item in questions
        ),
        "tomorrow_candidate_count": sum(
            any(hint in item.title for hint in _TOMORROW_HINTS) for item in questions
        ),
        "date_reply_type": single_candidate_reply_type(_DATE_HINTS),
        "today_reply_type": single_candidate_reply_type(_TODAY_HINTS),
        "tomorrow_reply_type": single_candidate_reply_type(_TOMORROW_HINTS),
        "unique_submit_order_count": len({item.pos for item in questions if item.pos is not None}),
    }


def compute_destination_fingerprint(form_id: str, template_id: str) -> str:
    """SHA-256 of the normalized `(form_id, template_id)` pair
    (`docs/方案设计.md` §6.3: "对 form_id + template_id 的规范化 SHA-256")."""
    normalized = json.dumps(
        {"form_id": form_id, "template_id": template_id},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class WeComConnectionService:
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
        # Threaded in via `Depends(get_app_settings)` at the API layer (same
        # pattern as `ExportService`) rather than read from the global
        # `get_settings()` singleton here — a low-level Service reaching for
        # process-global settings on its own bypasses whatever `Settings`
        # instance a test (or a future second app instance) actually wired up.
        self._settings = settings
        self._bindings = WeComUserBindingRepository(session)
        self._profiles = WeComSyncProfileRepository(session)

    def _new_client(self) -> WeComClientLike:
        if self._client_factory is not None:
            return self._client_factory()
        from app.integrations.wecom.client import WeComInternalClient

        debug_raw_body = (
            self._settings.wecom_debug_raw_body if self._settings is not None else False
        )
        return WeComInternalClient(debug_raw_body=debug_raw_body)

    async def validate_connection(
        self,
        owner_id: str,
        *,
        cookie_jar: Sequence[WeComCookieIn],
        credential_slot: str,
        form_id: str,
    ) -> None:
        """`docs/方案设计.md` §5.1 steps 4-6. Fully atomic: either both
        `wecom_user_bindings` and `wecom_sync_profiles` end up saved, or
        neither does — every failure path raises before either repository
        write happens, and the one place that writes commits both together.
        """
        validation_started = time.monotonic()
        client = self._injected_client if self._injected_client is not None else self._new_client()
        owns_client = self._injected_client is None
        try:
            try:
                template_info = await client.get_template_info(cookie_jar, form_id)
            except WeComClientError as exc:
                log_wecom_event(
                    logger,
                    event="connection_validation",
                    path_template="/journal/get_template_combine_info",
                    outcome="client_error",
                    duration_ms=int((time.monotonic() - validation_started) * 1000),
                    diagnostics={
                        "error_type": type(exc).__name__,
                        "error_message": exc.message,
                        **({"schema_paths": exc.detail} if exc.detail is not None else {}),
                        **(
                            {
                                "business_code": exc.biz_code,
                                **(
                                    {"business_message": exc.biz_message}
                                    if exc.biz_message is not None
                                    else {}
                                ),
                            }
                            if isinstance(exc, WeComBusinessRejected)
                            else {}
                        ),
                    },
                )
                raise _map_connection_client_error(exc) from exc

            try:
                date_spec, today_spec, tomorrow_spec = _select_target_question_specs(
                    template_info.questions
                )
            except WeComTemplateStructureUnresolvedError as exc:
                log_wecom_event(
                    logger,
                    event="connection_validation",
                    path_template="/journal/get_template_combine_info",
                    outcome="template_unresolved",
                    duration_ms=int((time.monotonic() - validation_started) * 1000),
                    diagnostics={
                        "error_type": type(exc).__name__,
                        "error_message": exc.message,
                        **_template_resolution_diagnostics(template_info.questions),
                    },
                )
                raise
            question_mapping = WeComQuestionMappingConfig(
                schema_version=1,
                date_question=date_spec,
                today_question=today_spec,
                tomorrow_question=tomorrow_spec,
            )
            schema_fingerprint = compute_schema_fingerprint(date_spec, today_spec, tomorrow_spec)
            destination_fingerprint = compute_destination_fingerprint(
                template_info.form_id, template_info.template_id
            )
            # `docs/方案设计.md` §5.1 step 5 + `wecom_vid`'s own honest caveat
            # (see the task brief / `WECOM-06` report): none of the three
            # verified endpoints identify "who am I" directly at connect
            # time. `entries[0]` (`body.entrys[0]`) is a best-guess
            # placeholder for display purposes only; a real `submit_daily`
            # success later self-heals it via `WeComSyncService`.
            best_guess_entry = template_info.entries[0] if template_info.entries else None
            wecom_vid = best_guess_entry.reply_id if best_guess_entry is not None else ""
            display_name = best_guess_entry.reply_name if best_guess_entry is not None else ""
            # §5.1 step 6 / §6.3, 2026-08-11 revision (`ISS-052`/`ISS-054`,
            # `PROD-032`): recipients are entirely system-resolved — a user
            # is never asked to hand-type a vid. Three-tier fallback, most
            # to least specific:
            #   1. `entries[0].reportvids` — WeCom's own already-resolved
            #      recipient list for a real past submission (previously
            #      parsed and silently discarded by `WeComTemplateEntry`'s
            #      `extra="ignore"`); real captures confirm it is the
            #      template's configured approvers, never the submitter.
            #   2. `template_info.appro[]` — the template's own configured
            #      approver list, template-scoped so it's available even
            #      before this user has ever submitted anything.
            #   3. The connecting user's own `wecom_vid` (`ISS-042`) — kept
            #      only as a last resort when neither of the above exists;
            #      real usage proved this self-targeted default itself gets
            #      rejected (`business_code=-1000888`) once real approvers
            #      exist, so it must never be preferred over either tier
            #      above.
            if best_guess_entry is not None and best_guess_entry.reportvids:
                default_reporter_vids = list(best_guess_entry.reportvids)
            elif template_info.appro:
                default_reporter_vids = [approver.vid for approver in template_info.appro]
            else:
                default_reporter_vids = [wecom_vid] if wecom_vid else []
            recipient_config = WeComRecipientConfig(
                schema_version=1,
                mngreporter_vids=[],
                reporter_vids=default_reporter_vids,
                remote_version=0,
            )
            field_mapping = WeComFieldMappingConfig(
                schema_version=1, rules=[], unmapped_policy="block"
            )

            now = self._clock()
            await self._upsert_binding(
                owner_id=owner_id,
                credential_slot=credential_slot,
                wecom_vid=wecom_vid,
                display_name=display_name,
                now=now,
            )
            await self._upsert_profile(
                owner_id=owner_id,
                form_id=template_info.form_id,
                template_id=template_info.template_id,
                destination_fingerprint=destination_fingerprint,
                question_mapping=question_mapping,
                recipient_config=recipient_config,
                field_mapping=field_mapping,
                schema_fingerprint=schema_fingerprint,
            )
            await self._session.commit()
            log_wecom_event(
                logger,
                event="connection_validation",
                path_template="/journal/get_template_combine_info",
                outcome="ok",
                duration_ms=int((time.monotonic() - validation_started) * 1000),
                diagnostics=_template_resolution_diagnostics(template_info.questions),
            )
        except BaseException:
            await self._session.rollback()
            raise
        finally:
            if owns_client:
                await client.aclose()

    async def _upsert_binding(
        self,
        *,
        owner_id: str,
        credential_slot: str,
        wecom_vid: str,
        display_name: str,
        now: datetime,
    ) -> None:
        existing = await self._bindings.get_for_owner(owner_id)
        if existing is not None:
            existing.credential_slot = credential_slot
            existing.wecom_vid = wecom_vid
            existing.display_name = display_name
            existing.status = "connected"
            existing.last_validated_at = now
            existing.version += 1
            await self._session.flush()
            return
        binding = WeComUserBinding(
            id=generate_ulid(),
            user_id=owner_id,
            credential_slot=credential_slot,
            wecom_vid=wecom_vid,
            display_name=display_name,
            corp_id=None,
            status="connected",
            last_validated_at=now,
            last_auth_error_at=None,
            version=1,
        )
        try:
            # A plain `try/except IntegrityError` around a flush leaves the
            # *entire* session transaction in SQLAlchemy's DEACTIVE state
            # (not just this one insert) — any query issued afterwards raises
            # `PendingRollbackError` instead of running, and a bare
            # `session.rollback()` here would also discard `validate_connection`'s
            # earlier, already-flushed changes in the same atomic transaction.
            # A SAVEPOINT (`begin_nested()`) scopes the rollback to just this
            # insert attempt, leaving everything else in the transaction intact.
            async with self._session.begin_nested():
                await self._bindings.add(binding)
        except IntegrityError:
            # A concurrent connect() from the same user raced us and won;
            # fall back to updating its row instead of failing outright.
            existing = await self._bindings.get_for_owner(owner_id)
            if existing is None:
                raise
            existing.credential_slot = credential_slot
            existing.wecom_vid = wecom_vid
            existing.display_name = display_name
            existing.status = "connected"
            existing.last_validated_at = now
            existing.version += 1
            await self._session.flush()

    async def _upsert_profile(
        self,
        *,
        owner_id: str,
        form_id: str,
        template_id: str,
        destination_fingerprint: str,
        question_mapping: WeComQuestionMappingConfig,
        recipient_config: WeComRecipientConfig,
        field_mapping: WeComFieldMappingConfig,
        schema_fingerprint: str,
    ) -> None:
        question_mapping_json = question_mapping.model_dump_json()
        recipient_config_json = recipient_config.model_dump_json()

        # `field_mapping` is this method's caller-computed *first-connect*
        # default (empty rules). A reconnect (this user already has a
        # profile row, whatever its form_id) must not apply it:
        # `field_mapping.rules` is keyed by this app's own template
        # `field_key` and has no relationship to which WeCom form is
        # connected — overwriting it on every reconnect silently erased a
        # user's already-working sync setup even when reconnecting to a form
        # with identical field labels (reported by a real user; see
        # `ai-docs/issues.md` ISS-042's trailing note and `PROD-030`).
        #
        # `recipient_config` is the opposite: it is *never* user-edited
        # (`PROD-032` — the caller always computes it fresh from WeCom's own
        # template/submission data, never from user input), so there is no
        # user customization to protect here. A reconnect refreshing it to
        # whatever the template's approvers currently resolve to is exactly
        # the desired behavior, not a regression — it is overwritten on
        # every connect, first or not.
        existing = await self._profiles.get_for_owner(owner_id)
        if existing is not None:
            existing.form_id = form_id
            existing.template_id = template_id
            existing.destination_fingerprint = destination_fingerprint
            existing.question_mapping_json = question_mapping_json
            existing.recipient_config_json = recipient_config_json
            existing.schema_fingerprint = schema_fingerprint
            existing.is_active = True
            existing.version += 1
            await self._session.flush()
            return
        field_mapping_json = field_mapping.model_dump_json()
        profile = WeComSyncProfile(
            id=generate_ulid(),
            user_id=owner_id,
            form_id=form_id,
            template_id=template_id,
            journal_uuid=None,
            destination_fingerprint=destination_fingerprint,
            question_mapping_json=question_mapping_json,
            recipient_config_json=recipient_config_json,
            field_mapping_json=field_mapping_json,
            schema_fingerprint=schema_fingerprint,
            version=1,
            is_active=True,
        )
        try:
            # See `_upsert_binding`'s matching comment: a SAVEPOINT keeps a
            # failed insert here from rolling back `_upsert_binding`'s
            # already-flushed changes earlier in the same transaction.
            async with self._session.begin_nested():
                await self._profiles.add(profile)
        except IntegrityError:
            # A concurrent connect() from the same user raced us and won: the
            # row that now exists is a real "existing profile" case, so the
            # same field_mapping-preserved/recipient_config-refreshed rule
            # applies here too.
            existing = await self._profiles.get_for_owner(owner_id)
            if existing is None:
                raise
            existing.form_id = form_id
            existing.template_id = template_id
            existing.destination_fingerprint = destination_fingerprint
            existing.question_mapping_json = question_mapping_json
            existing.recipient_config_json = recipient_config_json
            existing.schema_fingerprint = schema_fingerprint
            existing.is_active = True
            existing.version += 1
            await self._session.flush()

    async def disconnect(self, owner_id: str) -> None:
        """`docs/方案设计.md` §5's disconnect flow / `POST
        /api/v1/internal/wecom/connections/disconnect`: only *marks* the
        binding disconnected — the credential file itself is deleted by
        Electron Main before this call ever reaches the backend (`WECOM-03`,
        already implemented). No binding row at all is treated as an
        already-satisfied no-op, not an error."""
        binding = await self._bindings.get_for_owner(owner_id)
        if binding is None:
            return
        binding.status = "disconnected"
        binding.version += 1
        await self._session.commit()

    async def get_binding(self, owner_id: str) -> WeComUserBinding | None:
        return await self._bindings.get_for_owner(owner_id)

    async def get_profile(self, owner_id: str) -> WeComSyncProfile:
        profile = await self._profiles.get_for_owner(owner_id)
        if profile is None:
            raise WeComNotConnectedError()
        return profile

    async def update_profile(
        self,
        owner_id: str,
        *,
        expected_version: int,
        field_mapping: WeComFieldMappingConfig,
    ) -> WeComSyncProfile:
        profile = await self._profiles.get_for_owner(owner_id)
        if profile is None:
            raise WeComNotConnectedError()

        updated = await self._profiles.update_field_mapping_if_version(
            owner_id=owner_id,
            expected_version=expected_version,
            field_mapping_json=field_mapping.model_dump_json(),
            updated_at=self._clock(),
        )
        if not updated:
            await self._session.rollback()
            current = await self._profiles.get_for_owner(owner_id)
            if current is None:
                raise WeComNotConnectedError()
            raise WeComProfileVersionConflictError()
        await self._session.commit()
        refreshed = await self._profiles.get_for_owner(owner_id)
        assert refreshed is not None
        return refreshed
