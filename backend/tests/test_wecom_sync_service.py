from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from conftest import STAGE5_PASSWORD
from sqlalchemy.ext.asyncio import AsyncEngine
from wecom_service_support import (
    DEFAULT_FORM_ID,
    StubWeComClient,
    build_fork_item,
    build_form_detail,
)

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.integrations.wecom.client import WeComAuthExpired, WeComOutcomeUncertain
from app.integrations.wecom.schemas import WeComQuestionItem
from app.models import DailyReport, DailyReportDay, User
from app.repositories.daily_report_day import DailyReportDayRepository
from app.repositories.wecom import WeComDailySyncRecordRepository
from app.services.bootstrap import BootstrapService
from app.services.daily_report import DailyReportService
from app.services.daily_report_day import DailyReportDayService
from app.services.template import parse_template_fields
from app.services.user import UserService
from app.services.wecom_connection import WeComConnectionService
from app.services.wecom_sync import (
    WeComAlreadySucceededError,
    WeComDayNotArchivedError,
    WeComNotConnectedError,
    WeComSyncInProgressError,
    WeComSyncRecordNotFoundError,
    WeComSyncService,
    WeComUncertainRetryBlockedError,
)


@pytest.fixture
def wecom_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test", data_dir=tmp_path / "data", backup_dir=tmp_path / "backups"
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
async def wecom_engine(wecom_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(wecom_settings)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _bootstrap_user(session_factory: object, *, username: str = "owner") -> User:
    async with session_factory() as session:  # type: ignore[operator]
        return await BootstrapService(session).bootstrap(
            username=username, password=STAGE5_PASSWORD, display_name="Owner"
        )


async def _create_draft(session_factory: object, *, owner_id: str, work_date: date) -> DailyReport:
    async with session_factory() as session:  # type: ignore[operator]
        report, _created = await DailyReportService(session).create(
            owner_id, work_date=work_date, client_request_id=generate_ulid()
        )
        return report


async def _submit_with_core_content(
    session_factory: object,
    *,
    owner_id: str,
    report: DailyReport,
    today_work: str = "示例今日工作内容",
    tomorrow_plan: str = "示例明日计划内容",
) -> DailyReport:
    async with session_factory() as session:  # type: ignore[operator]
        fields = parse_template_fields(report.template_snapshot_json)
        content: dict[str, object] = {}
        for field in fields:
            if not field.enabled:
                continue
            if field.core_type == "today_work":
                content[field.field_key] = today_work
            elif field.core_type == "tomorrow_plan":
                content[field.field_key] = tomorrow_plan
        saved = await DailyReportService(session).save(
            owner_id, report.id, expected_version=report.version, content=content
        )
        return await DailyReportService(session).submit(
            owner_id, report.id, expected_version=saved.version
        )


async def _archive_day(
    session_factory: object, *, owner_id: str, work_date: date
) -> DailyReportDay:
    async with session_factory() as session:  # type: ignore[operator]
        return await DailyReportDayService(session).archive(
            owner_id, work_date, confirm_archive=True
        )


async def _prepare_archived_day(
    session_factory: object,
    *,
    owner_id: str,
    work_date: date,
    today_work: str = "示例今日工作内容",
    tomorrow_plan: str = "示例明日计划内容",
) -> DailyReportDay:
    entry = await _create_draft(session_factory, owner_id=owner_id, work_date=work_date)
    await _submit_with_core_content(
        session_factory,
        owner_id=owner_id,
        report=entry,
        today_work=today_work,
        tomorrow_plan=tomorrow_plan,
    )
    return await _archive_day(session_factory, owner_id=owner_id, work_date=work_date)


async def _connect(session_factory: object, *, owner_id: str) -> None:
    async with session_factory() as session:  # type: ignore[operator]
        await WeComConnectionService(session, client=StubWeComClient()).validate_connection(
            owner_id, cookie_jar=[], credential_slot=f"slot-{owner_id}", form_id="form-1"
        )


def _shanghai_noon_epoch(work_date: date) -> int:
    return int(
        datetime(work_date.year, work_date.month, work_date.day, 4, 0, 0, tzinfo=UTC).timestamp()
    )


async def test_preview_requires_an_archived_day(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _create_draft(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)

    async with session_factory() as session:
        day_row = await DailyReportDayRepository(session).get_for_owner_by_date(user.id, work_date)
        assert day_row is not None
        with pytest.raises(WeComDayNotArchivedError):
            await WeComSyncService(session).preview(user.id, day_row.id)


async def test_preview_requires_a_connection(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    day = await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)

    async with session_factory() as session:
        with pytest.raises(WeComNotConnectedError):
            await WeComSyncService(session).preview(user.id, day.id)


async def test_preview_returns_mapped_answers_for_an_archived_day(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    day = await _prepare_archived_day(
        session_factory,
        owner_id=user.id,
        work_date=work_date,
        today_work="完成示例模块开发",
        tomorrow_plan="继续编写单元测试",
    )
    await _connect(session_factory, owner_id=user.id)

    async with session_factory() as session:
        preview = await WeComSyncService(session).preview(user.id, day.id)

    assert preview.today_work_answer == "完成示例模块开发"
    assert preview.tomorrow_plan_answer == "继续编写单元测试"
    assert preview.source_count == 1
    assert preview.unmapped_field_keys == []
    assert preview.date_answer == "2026年08月05日"


async def test_get_or_create_record_is_idempotent(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    day = await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)

    async with session_factory() as session:
        first, first_created = await WeComSyncService(session).get_or_create_record(
            user.id, work_date
        )
    async with session_factory() as session:
        second, second_created = await WeComSyncService(session).get_or_create_record(
            user.id, work_date
        )

    assert first_created is True
    assert second_created is False
    assert first.id == second.id
    assert first.status == "pending"
    assert first.daily_report_day_id == day.id


async def test_get_or_create_record_requires_an_archived_day(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _create_draft(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)

    async with session_factory() as session:
        with pytest.raises(WeComDayNotArchivedError):
            await WeComSyncService(session).get_or_create_record(user.id, work_date)


async def test_get_or_create_record_requires_a_connection(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)

    async with session_factory() as session:
        with pytest.raises(WeComNotConnectedError):
            await WeComSyncService(session).get_or_create_record(user.id, work_date)


async def test_execute_succeeds_and_finalizes_the_record(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(user.id, work_date)

    stub = StubWeComClient()
    async with session_factory() as session:
        finished = await WeComSyncService(session, client=stub).execute(
            user.id, record.id, cookie_jar=[]
        )

    assert finished.status == "succeeded"
    assert finished.attempt_count == 1
    assert finished.attempt_token is None
    assert finished.remote_answer_id == "1"
    assert finished.succeeded_at is not None
    assert stub.get_form_detail_calls == 1
    assert stub.submit_daily_calls == 1


async def test_execute_maps_auth_expired_and_marks_the_binding_expired(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(user.id, work_date)

    stub = StubWeComClient(form_detail_error=WeComAuthExpired("login expired"))
    async with session_factory() as session:
        # `_perform_remote_sync`'s auth_required branch raises a plain
        # `AppError(code=40911, ...)` via `_app_error_for()` — not the
        # `WeComNotConnectedError` subclass `_require_connected_binding`/
        # `_require_active_profile` raise before any remote call is made.
        with pytest.raises(Exception) as excinfo:
            await WeComSyncService(session, client=stub).execute(user.id, record.id, cookie_jar=[])
    assert getattr(excinfo.value, "code", None) == 40911

    async with session_factory() as session:
        refreshed = await WeComDailySyncRecordRepository(session).get_for_owner(record.id, user.id)
        assert refreshed is not None
        assert refreshed.status == "auth_required"
        assert refreshed.last_error_kind == "auth_expired"
        binding = await WeComConnectionService(session).get_binding(user.id)
        assert binding is not None
        assert binding.status == "expired"
        assert binding.last_auth_error_at is not None


async def test_execute_maps_missing_target_question_to_schema_changed(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(user.id, work_date)

    drifted_questions = [
        WeComQuestionItem(
            question_id="1000000001", title="日期", reply_type=11, must_reply=False, pos=1
        ),
        # The "今日工作" question id has changed on the remote side.
        WeComQuestionItem(
            question_id="9999999999", title="今日工作", reply_type=1, must_reply=True, pos=2
        ),
        WeComQuestionItem(
            question_id="1000000003", title="明日计划", reply_type=1, must_reply=True, pos=3
        ),
    ]
    stub = StubWeComClient(form_detail=build_form_detail(questions=drifted_questions))
    async with session_factory() as session:
        with pytest.raises(Exception) as excinfo:  # AppError, code 40912
            await WeComSyncService(session, client=stub).execute(user.id, record.id, cookie_jar=[])
    assert getattr(excinfo.value, "code", None) == 40912
    assert stub.submit_daily_calls == 0

    async with session_factory() as session:
        refreshed = await WeComDailySyncRecordRepository(session).get_for_owner(record.id, user.id)
        assert refreshed is not None
        assert refreshed.status == "schema_changed"


async def test_execute_submits_even_when_a_fork_exists_on_the_matching_date(
    wecom_engine: AsyncEngine,
) -> None:
    """`ISS-040` second revision: a `fork_items` entry on `work_date` used to
    block the sync as `duplicate_detected`. That check was removed after real
    usage showed it false-positives on every attempt — `fork_items` lists
    form *instances that exist* (and `get_form_detail()` itself appears to
    cause today's fork to exist), not ones that were actually submitted to.
    This is the regression guard: a same-date fork must never block
    submission again."""
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(user.id, work_date)

    candidate = build_fork_item(form_id=DEFAULT_FORM_ID, ctime=_shanghai_noon_epoch(work_date))
    stub = StubWeComClient(form_detail=build_form_detail(fork_items=[candidate]))
    async with session_factory() as session:
        finished = await WeComSyncService(session, client=stub).execute(
            user.id, record.id, cookie_jar=[]
        )

    assert finished.status == "succeeded"
    assert stub.submit_daily_calls == 1


async def test_execute_maps_an_uncertain_outcome_and_blocks_direct_retry(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(user.id, work_date)

    stub = StubWeComClient(submit_error=WeComOutcomeUncertain("write timed out"))
    async with session_factory() as session:
        with pytest.raises(Exception) as excinfo:
            await WeComSyncService(session, client=stub).execute(user.id, record.id, cookie_jar=[])
    assert getattr(excinfo.value, "code", None) == 50302

    async with session_factory() as session:
        refreshed = await WeComDailySyncRecordRepository(session).get_for_owner(record.id, user.id)
        assert refreshed is not None
        assert refreshed.status == "uncertain"

        with pytest.raises(WeComUncertainRetryBlockedError):
            await WeComSyncService(session).retry(user.id, record.id)


async def test_execute_already_succeeded_short_circuits_without_calling_the_client(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(user.id, work_date)

    stub = StubWeComClient()
    async with session_factory() as session:
        await WeComSyncService(session, client=stub).execute(user.id, record.id, cookie_jar=[])
    assert stub.get_form_detail_calls == 1

    async with session_factory() as session:
        with pytest.raises(WeComAlreadySucceededError):
            await WeComSyncService(session, client=stub).execute(user.id, record.id, cookie_jar=[])
    # No new remote calls were made for the already-succeeded record.
    assert stub.get_form_detail_calls == 1


async def test_execute_rejects_a_concurrent_call_while_already_syncing(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(user.id, work_date)
        claimed = await WeComDailySyncRecordRepository(session).transition_to_syncing(
            record_id=record.id,
            owner_id=user.id,
            allowed_statuses=("pending",),
            attempt_token="already-in-flight",
            now=datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC),
        )
        assert claimed is True
        await session.commit()

    stub = StubWeComClient()
    async with session_factory() as session:
        with pytest.raises(WeComSyncInProgressError):
            await WeComSyncService(session, client=stub).execute(user.id, record.id, cookie_jar=[])
    assert stub.get_form_detail_calls == 0


async def test_retry_moves_a_recoverable_failure_back_to_pending(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(user.id, work_date)

    stub = StubWeComClient(form_detail_error=WeComAuthExpired("login expired"))
    async with session_factory() as session:
        with pytest.raises(Exception) as excinfo:
            await WeComSyncService(session, client=stub).execute(user.id, record.id, cookie_jar=[])
    assert getattr(excinfo.value, "code", None) == 40911

    async with session_factory() as session:
        retried = await WeComSyncService(session).retry(user.id, record.id)
    assert retried.status == "pending"
    assert retried.attempt_token is None


async def test_retry_is_a_noop_while_pending_or_syncing(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(user.id, work_date)

    async with session_factory() as session:
        retried = await WeComSyncService(session).retry(user.id, record.id)
    assert retried.status == "pending"
    assert retried.attempt_count == 0


async def test_list_records_filters_by_status_and_date_range(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    await _connect(session_factory, owner_id=user.id)
    early = date(2026, 8, 1)
    late = date(2026, 8, 10)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=early)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=late)
    async with session_factory() as session:
        await WeComSyncService(session).get_or_create_record(user.id, early)
    async with session_factory() as session:
        await WeComSyncService(session).get_or_create_record(user.id, late)

    async with session_factory() as session:
        items, total = await WeComSyncService(session).list_records(
            user.id, status="pending", date_from=None, date_to=None, page=1, page_size=20
        )
    assert total == 2
    assert {work_date for _record, work_date in items} == {early, late}

    async with session_factory() as session:
        items, total = await WeComSyncService(session).list_records(
            user.id, status=None, date_from=late, date_to=late, page=1, page_size=20
        )
    assert total == 1
    assert items[0][1] == late

    async with session_factory() as session:
        items, total = await WeComSyncService(session).list_records(
            user.id, status="succeeded", date_from=None, date_to=None, page=1, page_size=20
        )
    assert total == 0


async def test_get_record_hides_a_record_owned_by_another_user(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    owner = await _bootstrap_user(session_factory, username="owner")
    async with session_factory() as session:
        stranger = await UserService(session).create_user(
            username="stranger",
            password=STAGE5_PASSWORD,
            display_name="Stranger",
            role="user",
        )
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=owner.id, work_date=work_date)
    await _connect(session_factory, owner_id=owner.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(owner.id, work_date)

    async with session_factory() as session:
        with pytest.raises(WeComSyncRecordNotFoundError):
            await WeComSyncService(session).get_record(stranger.id, record.id)


async def test_finalize_attempt_discards_a_late_response_from_a_superseded_attempt(
    wecom_engine: AsyncEngine,
) -> None:
    """Direct repository-level test of the safety property `execute()`
    relies on (`docs/方案设计.md` §3.2 point 3): a finalize whose
    `attempt_token` no longer matches the row (because a newer attempt has
    since claimed it) must be silently discarded rather than overwriting the
    newer attempt's state.
    """
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=work_date)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        record, _created = await WeComSyncService(session).get_or_create_record(user.id, work_date)

    async with session_factory() as session:
        repo = WeComDailySyncRecordRepository(session)
        now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
        claimed = await repo.transition_to_syncing(
            record_id=record.id,
            owner_id=user.id,
            allowed_statuses=("pending",),
            attempt_token="token-current",
            now=now,
        )
        assert claimed is True

        stale_result = await repo.finalize_attempt(
            record_id=record.id,
            owner_id=user.id,
            attempt_token="token-stale",
            status="succeeded",
            now=now,
            profile_id=record.profile_id,
            profile_version=record.profile_version,
            payload_fingerprint=record.payload_fingerprint,
            remote_answer_id="stale-answer",
            remote_reply_id=None,
            remote_journal_uuid=None,
            last_error_kind=None,
            last_error_message=None,
            succeeded_at=now,
        )
        assert stale_result is False
        await session.commit()

    async with session_factory() as session:
        still_syncing = await WeComDailySyncRecordRepository(session).get_for_owner(
            record.id, user.id
        )
        assert still_syncing is not None
        assert still_syncing.status == "syncing"
        assert still_syncing.remote_answer_id is None

    async with session_factory() as session:
        repo = WeComDailySyncRecordRepository(session)
        now = datetime(2026, 8, 5, 12, 5, 0, tzinfo=UTC)
        current_result = await repo.finalize_attempt(
            record_id=record.id,
            owner_id=user.id,
            attempt_token="token-current",
            status="succeeded",
            now=now,
            profile_id=record.profile_id,
            profile_version=record.profile_version,
            payload_fingerprint=record.payload_fingerprint,
            remote_answer_id="current-answer",
            remote_reply_id=None,
            remote_journal_uuid=None,
            last_error_kind=None,
            last_error_message=None,
            succeeded_at=now,
        )
        assert current_result is True
        await session.commit()

    async with session_factory() as session:
        finished = await WeComDailySyncRecordRepository(session).get_for_owner(record.id, user.id)
        assert finished is not None
        assert finished.status == "succeeded"
        assert finished.remote_answer_id == "current-answer"


async def test_recover_stale_syncing_records_moves_expired_attempts_to_uncertain(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    early = date(2026, 8, 1)
    late = date(2026, 8, 2)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=early)
    await _prepare_archived_day(session_factory, owner_id=user.id, work_date=late)
    await _connect(session_factory, owner_id=user.id)
    async with session_factory() as session:
        stale_record, _created = await WeComSyncService(session).get_or_create_record(
            user.id, early
        )
    async with session_factory() as session:
        fresh_record, _created = await WeComSyncService(session).get_or_create_record(user.id, late)

    async with session_factory() as session:
        repo = WeComDailySyncRecordRepository(session)
        await repo.transition_to_syncing(
            record_id=stale_record.id,
            owner_id=user.id,
            allowed_statuses=("pending",),
            attempt_token="stale-token",
            now=datetime(2026, 8, 1, 0, 0, 0, tzinfo=UTC),
        )
        await repo.transition_to_syncing(
            record_id=fresh_record.id,
            owner_id=user.id,
            allowed_statuses=("pending",),
            attempt_token="fresh-token",
            now=datetime(2026, 8, 9, 23, 59, 0, tzinfo=UTC),
        )
        await session.commit()

    async with session_factory() as session:
        recovered_count = await WeComSyncService(
            session, clock=lambda: datetime(2026, 8, 10, 0, 0, 0, tzinfo=UTC)
        ).recover_stale_syncing_records()
    assert recovered_count == 1

    async with session_factory() as session:
        repo = WeComDailySyncRecordRepository(session)
        recovered = await repo.get_for_owner(stale_record.id, user.id)
        assert recovered is not None
        assert recovered.status == "uncertain"
        assert recovered.attempt_token is None
        still_syncing = await repo.get_for_owner(fresh_record.id, user.id)
        assert still_syncing is not None
        assert still_syncing.status == "syncing"
        assert still_syncing.attempt_token == "fresh-token"
