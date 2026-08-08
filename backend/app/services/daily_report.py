import json
import math
from collections.abc import Mapping
from datetime import date

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.core.ulid import generate_ulid
from app.models import AdminAuditEvent, DailyReport, DailyReportDay
from app.repositories.admin_audit import AdminAuditRepository
from app.repositories.daily_report import DailyReportRepository
from app.repositories.daily_report_day import DailyReportDayRepository
from app.schemas.daily_report import DailyContent, DailyInputContent, ProjectListEntry
from app.schemas.template import TemplateFieldData
from app.services.template import TemplateService, parse_template_fields

_CONTENT_ADAPTER: TypeAdapter[DailyContent] = TypeAdapter(DailyContent)
_MAX_CREATE_ATTEMPTS = 3
_REVOCATION_ACTION = "daily_submission_revoked"
_PROJECT_LIST_STATUSES = {"TODO", "DOING", "DONE"}
_PROJECT_LIST_KEYS = {"project", "content", "status"}


class DailyReportNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="日报不存在")


class DailyReportDayArchivedError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40905, http_status=409, message="日期已归档")


class DailyReportIdempotencyConflictError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40908, http_status=409, message="创建幂等键已被用于另一个日期")


class DailyReportStateError(AppError):
    def __init__(self, message: str = "当前日报状态不允许此操作") -> None:
        super().__init__(code=40902, http_status=409, message=message)


class DailyReportVersionConflictError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40904, http_status=409, message="日报已被更新。请重新加载。")


class DailyContentValidationError(AppError):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__(
            code=42201,
            http_status=422,
            message="日报内容校验失败",
            data={"errors": errors},
        )


def parse_daily_content(content_json: str) -> DailyContent:
    try:
        return _CONTENT_ADAPTER.validate_json(content_json)
    except ValidationError as error:
        raise RuntimeError("stored daily content is invalid") from error


def _value_error(field: TemplateFieldData, value: object) -> str | None:
    if value is None:
        return None
    if field.field_type in {"text", "textarea"}:
        return None if isinstance(value, str) else "必须是文本"
    if field.field_type == "number":
        if not isinstance(value, int | float) or isinstance(value, bool):
            return "必须是数字"
        try:
            return None if math.isfinite(value) else "必须是数字"
        except OverflowError:
            return "必须是数字"
    if field.field_type == "date":
        if not isinstance(value, str):
            return "必须是 YYYY-MM-DD 日期"
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return "必须是有效的 YYYY-MM-DD 日期"
        return None if parsed.isoformat() == value else "必须是有效的 YYYY-MM-DD 日期"
    if field.field_type == "select":
        return None if isinstance(value, str) and value in field.options else "必须选择有效选项"
    if field.field_type == "multiselect":
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            return "必须是选项数组"
        if len(set(value)) != len(value) or any(item not in field.options for item in value):
            return "包含重复或无效选项"
        return None
    if field.field_type == "PROJECT_LIST":
        return _project_list_error(value)
    return "字段类型不受支持"


def _project_list_error(value: object) -> str | None:
    """Validates a `PROJECT_LIST` value in either of its two shapes.

    `save()` passes the raw dict straight from the request JSON, but
    `submit()` re-validates content re-read via `parse_daily_content()`,
    which has already coerced matching list items into `ProjectListEntry`
    model instances (see `DailyFieldValue`'s `list[ProjectListEntry]`
    branch) — so both forms must be accepted here.
    """
    if not isinstance(value, list):
        return "必须是项目列表"
    for item in value:
        if isinstance(item, ProjectListEntry):
            project, content, status = item.project, item.content, item.status
        elif isinstance(item, dict) and item.keys() == _PROJECT_LIST_KEYS:
            project, content, status = item["project"], item["content"], item["status"]
        else:
            return "项目条目字段不完整或包含未知字段"
        if not isinstance(project, str) or not project.strip():
            return "项目名称不能为空"
        if not isinstance(content, str) or not content.strip():
            return "工作内容不能为空"
        if status not in _PROJECT_LIST_STATUSES:
            return "完成状态无效"
    return None


def _is_empty(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or value == []


def validate_daily_content(
    fields: list[TemplateFieldData],
    content: Mapping[str, object],
    *,
    require_required: bool,
) -> None:
    enabled_by_key = {field.field_key: field for field in fields if field.enabled}
    errors: list[dict[str, str]] = []
    for key in content:
        if key not in enabled_by_key:
            errors.append({"field": key, "message": "字段不存在或未启用"})
    for field in enabled_by_key.values():
        value = content.get(field.field_key)
        if require_required and field.required and _is_empty(value):
            errors.append({"field": field.field_key, "message": "必填字段不能为空"})
            continue
        if _is_empty(value):
            continue
        message = _value_error(field, value)
        if message is not None:
            errors.append({"field": field.field_key, "message": message})
    if errors:
        raise DailyContentValidationError(errors)


class DailyReportService:
    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._reports = DailyReportRepository(session)
        self._days = DailyReportDayRepository(session)
        self._audit = AdminAuditRepository(session)

    async def get(self, owner_id: str, report_id: str) -> DailyReport:
        report = await self._reports.get_for_owner(report_id, owner_id)
        if report is None:
            raise DailyReportNotFoundError()
        return report

    async def last_revocation(self, report_id: str) -> AdminAuditEvent | None:
        return await self._audit.get_latest_for_target(
            action=_REVOCATION_ACTION, target_id=report_id
        )

    async def list_reports(
        self,
        owner_id: str,
        *,
        date_from: date | None,
        date_to: date | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[DailyReport], int]:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise AppError(code=40001, http_status=400, message="开始日期不能晚于结束日期")
        return await self._reports.list_page(
            owner_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
            page=page,
            page_size=page_size,
        )

    async def create(
        self, owner_id: str, *, work_date: date, client_request_id: str
    ) -> tuple[DailyReport, bool]:
        """Returns `(entry, created)`; `created` is `False` for an idempotent replay.

        `docs/方案设计.md` §6.2 requires the create response to flag whether
        this call produced a brand-new entry or returned an existing one
        matched by `client_request_id`.
        """
        existing_by_key = await self._reports.get_by_client_request_id(client_request_id)
        if existing_by_key is not None:
            return (
                self._resolve_idempotent_create(
                    existing_by_key, owner_id=owner_id, work_date=work_date
                ),
                False,
            )

        _template, version, fields = await TemplateService(self._session).get_current(owner_id)
        template_snapshot_json = json.dumps(
            [field.model_dump(mode="json") for field in fields],
            ensure_ascii=False,
            separators=(",", ":"),
        )

        for _attempt in range(_MAX_CREATE_ATTEMPTS):
            day = await self._days.get_for_owner_by_date(owner_id, work_date)
            if day is None:
                day = DailyReportDay(
                    id=generate_ulid(),
                    user_id=owner_id,
                    work_date=work_date,
                    status="open",
                    source_count=0,
                    version=1,
                )
                try:
                    await self._days.add(day)
                except IntegrityError:
                    await self._session.rollback()
                    continue
            elif day.status == "archived":
                raise DailyReportDayArchivedError()

            report = DailyReport(
                id=generate_ulid(),
                day_id=day.id,
                client_request_id=client_request_id,
                status="draft",
                template_version_id=version.id,
                template_snapshot_json=template_snapshot_json,
                content_json="{}",
                version=1,
            )
            try:
                inserted = await self._reports.insert_entry_if_day_open(report)
            except IntegrityError as error:
                await self._session.rollback()
                existing_by_key = await self._reports.get_by_client_request_id(client_request_id)
                if existing_by_key is not None:
                    return (
                        self._resolve_idempotent_create(
                            existing_by_key, owner_id=owner_id, work_date=work_date
                        ),
                        False,
                    )
                raise RuntimeError("daily report insert failed") from error
            if inserted:
                await self._session.commit()
                created_report = await self._reports.get_for_owner(report.id, owner_id)
                assert created_report is not None
                return created_report, True
            await self._session.rollback()
        raise RuntimeError("daily report creation failed after retrying the open-day race")

    @staticmethod
    def _resolve_idempotent_create(
        existing: DailyReport, *, owner_id: str, work_date: date
    ) -> DailyReport:
        if existing.day.user_id == owner_id and existing.work_date == work_date:
            return existing
        raise DailyReportIdempotencyConflictError()

    async def save(
        self,
        owner_id: str,
        report_id: str,
        *,
        expected_version: int,
        content: DailyInputContent,
    ) -> DailyReport:
        report = await self.get(owner_id, report_id)
        self._require_state_and_version(report, state="draft", expected_version=expected_version)
        validate_daily_content(
            parse_template_fields(report.template_snapshot_json),
            content,
            require_required=False,
        )
        updated = await self._reports.save_draft(
            report_id=report_id,
            owner_id=owner_id,
            expected_version=expected_version,
            content_json=json.dumps(content, ensure_ascii=False, separators=(",", ":")),
            updated_at=self._clock(),
        )
        if not updated:
            await self._raise_after_failed_update(owner_id, report_id, required_state="draft")
        await self._session.commit()
        return await self.get(owner_id, report_id)

    async def delete(self, owner_id: str, report_id: str, *, expected_version: int) -> None:
        report = await self.get(owner_id, report_id)
        self._require_state_and_version(report, state="draft", expected_version=expected_version)
        day_id = report.day_id
        deleted = await self._reports.delete_draft(
            report_id=report_id,
            owner_id=owner_id,
            expected_version=expected_version,
        )
        if not deleted:
            await self._raise_after_failed_update(owner_id, report_id, required_state="draft")
        remaining = await self._reports.count_by_day(day_id)
        if remaining == 0:
            await self._days.delete_if_empty_open(day_id=day_id, owner_id=owner_id)
        await self._session.commit()

    async def submit(self, owner_id: str, report_id: str, *, expected_version: int) -> DailyReport:
        report = await self.get(owner_id, report_id)
        self._require_state_and_version(report, state="draft", expected_version=expected_version)
        validate_daily_content(
            parse_template_fields(report.template_snapshot_json),
            parse_daily_content(report.content_json),
            require_required=True,
        )
        now = self._clock()
        updated = await self._reports.submit_draft(
            report_id=report_id,
            owner_id=owner_id,
            expected_version=expected_version,
            submitted_at=now,
        )
        if not updated:
            await self._raise_after_failed_update(owner_id, report_id, required_state="draft")
        await self._session.commit()
        return await self.get(owner_id, report_id)

    @staticmethod
    def _require_state_and_version(
        report: DailyReport, *, state: str, expected_version: int
    ) -> None:
        if report.status != state:
            raise DailyReportStateError()
        if report.version != expected_version:
            raise DailyReportVersionConflictError()

    async def _raise_after_failed_update(
        self, owner_id: str, report_id: str, *, required_state: str
    ) -> None:
        await self._session.rollback()
        current = await self.get(owner_id, report_id)
        if current.status != required_state:
            raise DailyReportStateError()
        raise DailyReportVersionConflictError()
