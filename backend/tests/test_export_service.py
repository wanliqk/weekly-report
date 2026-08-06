import json
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from pathlib import Path

import openpyxl
import pytest
from conftest import STAGE5_PASSWORD
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.models import DailyReport, DailyReportDay, ExportJob, User
from app.repositories.daily_report import DailyReportRepository
from app.repositories.template import TemplateRepository
from app.schemas.export import ExportFilter
from app.services.bootstrap import BootstrapService
from app.services.export import (
    EXPORT_MEDIA_TYPE,
    ExportFileNotAvailableError,
    ExportSelectionInvalidError,
    ExportService,
)

_FIXED_NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)


def _past_clock() -> datetime:
    """A fixed instant far enough in the past that `expires_at` (+24h) is
    already behind any real wall-clock `now`, regardless of when tests run.
    """
    return datetime(2000, 1, 1, tzinfo=UTC)


@pytest.fixture
def export_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        export_temp_dir=tmp_path / "exports",
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
async def export_engine(export_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(export_settings)
    try:
        yield engine
    finally:
        await engine.dispose()


def _fields(pairs: list[tuple[str, str]]) -> list[dict[str, object]]:
    return [
        {
            "field_key": key,
            "label": label,
            "description": "",
            "field_type": "text",
            "required": False,
            "enabled": True,
            "sort_order": index * 10,
            "options": [],
            "core_type": None,
        }
        for index, (key, label) in enumerate(pairs)
    ]


async def _default_template_version_id(session: AsyncSession, owner_id: str) -> str:
    repository = TemplateRepository(session)
    template = await repository.get_for_owner(owner_id)
    assert template is not None
    version = await repository.get_version(template.id, template.current_version_no)
    assert version is not None
    return version.id


async def _archived_report(
    session: AsyncSession,
    *,
    owner_id: str,
    work_date: date,
    fields: list[dict[str, object]],
    content: dict[str, str],
) -> DailyReport:
    report_id = generate_ulid()
    report = DailyReport(
        id=report_id,
        day_id=report_id,
        client_request_id=report_id,
        day=DailyReportDay(
            id=report_id,
            user_id=owner_id,
            work_date=work_date,
            status="archived",
            archive_snapshot_json="{}",
            source_count=1,
            archived_by=owner_id,
            archived_at=_FIXED_NOW,
        ),
        status="archived",
        template_version_id=await _default_template_version_id(session, owner_id),
        template_snapshot_json=json.dumps(fields, ensure_ascii=False),
        content_json=json.dumps(content, ensure_ascii=False),
        version=2,
        submitted_at=_FIXED_NOW,
        archived_at=_FIXED_NOW,
    )
    await DailyReportRepository(session).add(report)
    await session.commit()
    return report


async def _draft_report(session: AsyncSession, *, owner_id: str, work_date: date) -> DailyReport:
    report_id = generate_ulid()
    report = DailyReport(
        id=report_id,
        day_id=report_id,
        client_request_id=report_id,
        day=DailyReportDay(
            id=report_id,
            user_id=owner_id,
            work_date=work_date,
            status="open",
        ),
        status="draft",
        template_version_id=await _default_template_version_id(session, owner_id),
        template_snapshot_json="[]",
        content_json="{}",
        version=1,
    )
    await DailyReportRepository(session).add(report)
    await session.commit()
    return report


async def _bootstrap_user(session: AsyncSession) -> User:
    return await BootstrapService(session).bootstrap(
        username="owner", password=STAGE5_PASSWORD, display_name="Owner"
    )


def _workbook_path(job: ExportJob) -> Path:
    assert job.file_path is not None
    return Path(job.file_path)


async def test_create_from_ids_merges_columns_across_snapshots_and_marks_succeeded(
    export_engine: AsyncEngine, export_settings: Settings
) -> None:
    session_factory = create_session_factory(export_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
        older = await _archived_report(
            session,
            owner_id=user.id,
            work_date=date(2026, 8, 3),
            fields=_fields([("k1", "今日进展"), ("k2", "明日计划")]),
            content={"k1": "写文档", "k2": "写测试"},
        )
        newer = await _archived_report(
            session,
            owner_id=user.id,
            work_date=date(2026, 8, 4),
            fields=_fields([("k1", "今日工作内容"), ("k2", "明日计划"), ("k3", "风险")]),
            content={"k1": "评审代码", "k2": "发布", "k3": "无"},
        )

    async with session_factory() as session:
        job = await ExportService(session, export_settings).create(
            user.id, report_ids=[newer.id, older.id], filter_=None
        )

    assert job.status == "succeeded"
    assert job.record_count == 2
    assert job.file_name is not None and job.file_name.endswith(".xlsx")
    workbook_path = _workbook_path(job)
    assert workbook_path.parent == export_settings.export_temp_dir.resolve()

    workbook = openpyxl.load_workbook(workbook_path)
    sheet = workbook.active
    assert sheet is not None
    rows = list(sheet.iter_rows(values_only=True))
    assert rows[0] == ("工作日期", "提交时间", "归档时间", "今日工作内容", "明日计划", "风险")
    assert rows[1][0] == "2026-08-03"
    assert rows[1][3:] == ("写文档", "写测试", None)
    assert rows[2][0] == "2026-08-04"
    assert rows[2][3:] == ("评审代码", "发布", "无")


async def test_create_defuses_formula_like_content_but_preserves_bullet_dashes(
    export_engine: AsyncEngine, export_settings: Settings
) -> None:
    session_factory = create_session_factory(export_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
        await _archived_report(
            session,
            owner_id=user.id,
            work_date=date(2026, 8, 5),
            fields=_fields([("k1", "今日工作内容")]),
            content={"k1": '=HYPERLINK("http://evil.example","x")'},
        )
        await _archived_report(
            session,
            owner_id=user.id,
            work_date=date(2026, 8, 6),
            fields=_fields([("k1", "今日工作内容")]),
            content={"k1": "-完成需求分析\n-编写代码"},
        )

    async with session_factory() as session:
        job = await ExportService(session, export_settings).create(
            user.id, report_ids=None, filter_=ExportFilter()
        )

    workbook = openpyxl.load_workbook(_workbook_path(job))
    sheet = workbook.active
    assert sheet is not None
    rows = list(sheet.iter_rows(values_only=True))
    formula_cell, bullet_cell = rows[1][3], rows[2][3]
    assert formula_cell == '\'=HYPERLINK("http://evil.example","x")'
    assert bullet_cell == "-完成需求分析\n-编写代码"

    formula_row = next(row for row in sheet.iter_rows() if row[0].value == "2026-08-05")
    assert formula_row[3].data_type != "f"


async def test_create_rejects_selection_containing_foreign_or_non_archived_ids(
    export_engine: AsyncEngine, export_settings: Settings
) -> None:
    session_factory = create_session_factory(export_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
        archived = await _archived_report(
            session, owner_id=user.id, work_date=date(2026, 8, 5), fields=[], content={}
        )
        draft = await _draft_report(session, owner_id=user.id, work_date=date(2026, 8, 6))

    async with session_factory() as session:
        with pytest.raises(ExportSelectionInvalidError) as excinfo:
            await ExportService(session, export_settings).create(
                user.id,
                report_ids=[archived.id, draft.id, "01MISSINGMISSINGMISSINGMI"],
                filter_=None,
            )

    assert set(excinfo.value.data["invalid_report_ids"]) == {
        draft.id,
        "01MISSINGMISSINGMISSINGMI",
    }


async def test_create_from_filter_only_includes_archived_reports_in_range(
    export_engine: AsyncEngine, export_settings: Settings
) -> None:
    session_factory = create_session_factory(export_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
        await _archived_report(
            session,
            owner_id=user.id,
            work_date=date(2026, 7, 31),
            fields=[],
            content={},
        )
        in_range = await _archived_report(
            session, owner_id=user.id, work_date=date(2026, 8, 2), fields=[], content={}
        )
        await _draft_report(session, owner_id=user.id, work_date=date(2026, 8, 3))

    async with session_factory() as session:
        job = await ExportService(session, export_settings).create(
            user.id,
            report_ids=None,
            filter_=ExportFilter(date_from=date(2026, 8, 1), date_to=date(2026, 8, 31)),
        )

    assert job.status == "succeeded"
    assert job.record_count == 1
    workbook = openpyxl.load_workbook(_workbook_path(job))
    sheet = workbook.active
    assert sheet is not None
    rows = list(sheet.iter_rows(values_only=True))
    assert len(rows) == 2
    assert rows[1][0] == in_range.work_date.isoformat()


async def test_create_from_filter_with_no_matches_produces_header_only_workbook(
    export_engine: AsyncEngine, export_settings: Settings
) -> None:
    session_factory = create_session_factory(export_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)

    async with session_factory() as session:
        job = await ExportService(session, export_settings).create(
            user.id, report_ids=None, filter_=ExportFilter()
        )

    assert job.status == "succeeded"
    assert job.record_count == 0
    workbook = openpyxl.load_workbook(_workbook_path(job))
    sheet = workbook.active
    assert sheet is not None
    rows = list(sheet.iter_rows(values_only=True))
    assert rows == [("工作日期", "提交时间", "归档时间")]


async def test_create_marks_job_failed_without_raising_when_generation_fails(
    export_engine: AsyncEngine, export_settings: Settings
) -> None:
    broken_settings = export_settings.model_copy(
        update={"export_temp_dir": export_settings.export_temp_dir / "missing" / "nested"}
    )
    session_factory = create_session_factory(export_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)

    async with session_factory() as session:
        job = await ExportService(session, broken_settings).create(
            user.id, report_ids=None, filter_=ExportFilter()
        )

    assert job.status == "failed"
    assert job.error_message is not None
    assert job.file_path is None
    assert job.record_count == 0


async def test_get_download_expires_lazily_and_deletes_the_file(
    export_engine: AsyncEngine, export_settings: Settings
) -> None:
    session_factory = create_session_factory(export_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)

    async with session_factory() as session:
        job = await ExportService(session, export_settings, clock=_past_clock).create(
            user.id, report_ids=None, filter_=ExportFilter()
        )
    file_path = _workbook_path(job)
    assert file_path.exists()

    async with session_factory() as session:
        with pytest.raises(ExportFileNotAvailableError):
            await ExportService(session, export_settings).get_download(user.id, job.id)

    assert not file_path.exists()
    async with session_factory() as session:
        expired = await ExportService(session, export_settings).get(user.id, job.id)
    assert expired.status == "expired"
    assert expired.file_path is None


async def test_get_download_rejects_files_outside_the_export_directory(
    export_engine: AsyncEngine, export_settings: Settings, tmp_path: Path
) -> None:
    outside_file = tmp_path / "outside.xlsx"
    outside_file.write_bytes(b"not a real workbook")
    session_factory = create_session_factory(export_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)

    async with session_factory() as session:
        job = await ExportService(session, export_settings).create(
            user.id, report_ids=None, filter_=ExportFilter()
        )
        job.file_path = str(outside_file)
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(ExportFileNotAvailableError):
            await ExportService(session, export_settings).get_download(user.id, job.id)
    assert outside_file.exists()


async def test_cleanup_expired_sweeps_every_owner_and_leaves_fresh_jobs_alone(
    export_engine: AsyncEngine, export_settings: Settings
) -> None:
    session_factory = create_session_factory(export_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)

    async with session_factory() as session:
        stale_job = await ExportService(session, export_settings, clock=_past_clock).create(
            user.id, report_ids=None, filter_=ExportFilter()
        )
    async with session_factory() as session:
        fresh_job = await ExportService(session, export_settings).create(
            user.id, report_ids=None, filter_=ExportFilter()
        )

    stale_path = _workbook_path(stale_job)
    fresh_path = _workbook_path(fresh_job)
    assert stale_path.exists()
    assert fresh_path.exists()

    async with session_factory() as session:
        await ExportService(session, export_settings).cleanup_expired()

    assert not stale_path.exists()
    assert fresh_path.exists()
    async with session_factory() as session:
        refreshed_stale = await ExportService(session, export_settings).get(user.id, stale_job.id)
        refreshed_fresh = await ExportService(session, export_settings).get(user.id, fresh_job.id)
    assert refreshed_stale.status == "expired"
    assert refreshed_fresh.status == "succeeded"


def test_export_media_type_is_the_standard_xlsx_mime_type() -> None:
    assert EXPORT_MEDIA_TYPE == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
