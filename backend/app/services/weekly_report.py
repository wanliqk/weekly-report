import json
from datetime import UTC, date, datetime, timedelta
from typing import cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.core.ulid import generate_ulid
from app.models import DailyReport, WeeklyReport
from app.repositories.daily_report import DailyReportRepository
from app.repositories.weekly_report import WeeklyReportRepository, WeeklySource
from app.schemas.daily_report import DailyContent, DailyStatus
from app.schemas.weekly_report import (
    WeeklyAvailabilityData,
    WeeklyAvailabilityDay,
    WeeklyContent,
    WeeklyDay,
    WeeklyDayField,
)
from app.services.daily_report import parse_daily_content
from app.services.template import parse_template_fields

WEEK_LENGTH = timedelta(days=6)
_ACTIVE_STATUSES = {"draft", "submitted"}


class WeeklyWeekStartInvalidError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40001, http_status=400, message="week_start 必须是周一")


class WeeklyRegenerateNotConfirmedError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40001, http_status=400, message="重新生成必须显式确认")


class WeeklyReportNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="周报不存在")


class WeeklyReportAlreadyExistsError(AppError):
    def __init__(self, existing_weekly_report_id: str) -> None:
        super().__init__(
            code=40903,
            http_status=409,
            message="该自然周周报已存在",
            data={"existing_weekly_report_id": existing_weekly_report_id},
        )


class WeeklyReportVersionConflictError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40904, http_status=409, message="周报已被更新。请重新加载。")


def week_end_for(week_start: date) -> date:
    if week_start.weekday() != 0:
        raise WeeklyWeekStartInvalidError()
    return week_start + WEEK_LENGTH


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def parse_weekly_content(content_json: str) -> WeeklyContent:
    raw = json.loads(content_json)
    if not isinstance(raw, dict):
        raise RuntimeError("stored weekly content is invalid")
    schema_version = raw.get("schema_version")
    if schema_version is None:
        return WeeklyContent.model_validate(raw)
    if schema_version != 2 or not isinstance(raw.get("days"), list):
        raise RuntimeError("stored weekly content has an unsupported schema version")

    days: list[WeeklyDay] = []
    for day in raw["days"]:
        if not isinstance(day, dict) or not isinstance(day.get("entries"), list):
            raise RuntimeError("stored weekly content contains an invalid day")
        entries = day["entries"]
        if day.get("source_count") != len(entries):
            raise RuntimeError("stored weekly content source count does not match entries")
        for entry in entries:
            if not isinstance(entry, dict):
                raise RuntimeError("stored weekly content contains an invalid entry")
            days.append(
                WeeklyDay(
                    work_date=day.get("work_date"),
                    daily_report_id=entry.get("daily_report_id"),
                    fields=entry.get("fields"),
                )
            )
    return WeeklyContent(
        days=days,
        supplement=raw.get("supplement", ""),
        next_week_plan=raw.get("next_week_plan", ""),
        risks=raw.get("risks", ""),
    )


def _serialize_weekly_content_v2(content: WeeklyContent, reports: list[DailyReport]) -> str:
    report_by_id = {report.id: report for report in reports}
    days: list[dict[str, object]] = []
    for day in content.days:
        report = report_by_id.get(day.daily_report_id)
        if report is None or report.submitted_at is None:
            raise RuntimeError("weekly content source report is missing")
        days.append(
            {
                "work_date": day.work_date.isoformat(),
                "daily_report_day_id": report.day_id,
                "source_count": 1,
                "entries": [
                    {
                        "daily_report_id": report.id,
                        "submitted_at": _utc_iso(report.submitted_at),
                        "fields": [field.model_dump(mode="json") for field in day.fields],
                    }
                ],
            }
        )
    return json.dumps(
        {
            "schema_version": 2,
            "days": days,
            "supplement": content.supplement,
            "next_week_plan": content.next_week_plan,
            "risks": content.risks,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _serialize_weekly_source_snapshot_v2(reports: list[DailyReport]) -> str:
    days: list[dict[str, object]] = []
    for report in reports:
        if report.submitted_at is None:
            raise RuntimeError("weekly source report is missing submitted_at")
        days.append(
            {
                "work_date": report.work_date.isoformat(),
                "daily_report_day_id": report.day_id,
                "source_count": 1,
                "entries": [
                    {
                        "daily_report_id": report.id,
                        "submitted_at": _utc_iso(report.submitted_at),
                    }
                ],
            }
        )
    return json.dumps(
        {"schema_version": 2, "days": days},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _replace_weekly_free_text(
    content_json: str, *, supplement: str, next_week_plan: str, risks: str
) -> str:
    raw = json.loads(content_json)
    if isinstance(raw, dict) and raw.get("schema_version") == 2:
        raw["supplement"] = supplement
        raw["next_week_plan"] = next_week_plan
        raw["risks"] = risks
        serialized = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
        parse_weekly_content(serialized)
        return serialized
    current = parse_weekly_content(content_json)
    return current.model_copy(
        update={
            "supplement": supplement,
            "next_week_plan": next_week_plan,
            "risks": risks,
        }
    ).model_dump_json()


def build_weekly_content(
    reports: list[DailyReport], *, supplement: str = "", next_week_plan: str = "", risks: str = ""
) -> WeeklyContent:
    """Pure function: summarizes archived daily reports into a weekly snapshot.

    Only enabled fields (in each report's own template snapshot) are carried
    over, matching how the daily UI itself only ever showed those fields at
    archive time; disabled fields are dropped rather than shown as stale.
    """
    days: list[WeeklyDay] = []
    for report in reports:
        fields = parse_template_fields(report.template_snapshot_json)
        content: DailyContent = parse_daily_content(report.content_json)
        enabled = sorted((f for f in fields if f.enabled), key=lambda f: f.sort_order)
        days.append(
            WeeklyDay(
                work_date=report.work_date,
                daily_report_id=report.id,
                fields=[
                    WeeklyDayField(
                        field_key=field.field_key,
                        label=field.label,
                        value=content.get(field.field_key),
                    )
                    for field in enabled
                ],
            )
        )
    return WeeklyContent(
        days=days, supplement=supplement, next_week_plan=next_week_plan, risks=risks
    )


class WeeklyReportService:
    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._reports = WeeklyReportRepository(session)
        self._daily_reports = DailyReportRepository(session)

    async def availability(self, owner_id: str, week_start: date) -> WeeklyAvailabilityData:
        week_end = week_end_for(week_start)
        reports = await self._daily_reports.list_owned_in_range(
            owner_id, date_from=week_start, date_to=week_end
        )
        by_date = {report.work_date: report for report in reports}
        days = [
            WeeklyAvailabilityDay(
                work_date=day,
                status=cast(DailyStatus, by_date[day].status) if day in by_date else None,
            )
            for day in _each_day(week_start, week_end)
        ]
        archived_count = sum(1 for report in reports if report.status == "archived")
        non_archived_dates = [
            report.work_date for report in reports if report.status in _ACTIVE_STATUSES
        ]
        existing = await self._reports.get_by_owner_week(owner_id, week_start)
        return WeeklyAvailabilityData(
            week_start=week_start,
            week_end=week_end,
            days=days,
            archived_count=archived_count,
            non_archived_dates=non_archived_dates,
            existing_weekly_report_id=existing.id if existing else None,
        )

    async def list_reports(
        self,
        owner_id: str,
        *,
        week_from: date | None,
        week_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[WeeklyReport], int]:
        if week_from is not None and week_to is not None and week_from > week_to:
            raise AppError(code=40001, http_status=400, message="开始周不能晚于结束周")
        return await self._reports.list_page(
            owner_id, week_from=week_from, week_to=week_to, page=page, page_size=page_size
        )

    async def get(self, owner_id: str, report_id: str) -> WeeklyReport:
        report = await self._reports.get_for_owner(report_id, owner_id)
        if report is None:
            raise WeeklyReportNotFoundError()
        return report

    async def generate(self, owner_id: str, *, week_start: date) -> WeeklyReport:
        week_end = week_end_for(week_start)
        archived = await self._daily_reports.list_owned_archived_by_range(
            owner_id, date_from=week_start, date_to=week_end
        )
        now = self._clock()
        content = build_weekly_content(archived)
        content_json = _serialize_weekly_content_v2(content, archived)
        report = WeeklyReport(
            id=generate_ulid(),
            user_id=owner_id,
            week_start=week_start,
            week_end=week_end,
            generated_content_json=content_json,
            content_json=content_json,
            source_snapshot_json=_serialize_weekly_source_snapshot_v2(archived),
            generated_at=now,
            version=1,
        )
        try:
            await self._reports.add(report)
            await self._reports.replace_sources(report.id, _sources_for(archived, now))
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            existing = await self._reports.get_by_owner_week(owner_id, week_start)
            if existing is not None:
                raise WeeklyReportAlreadyExistsError(existing.id) from error
            raise RuntimeError("weekly report insert failed") from error
        return report

    async def save(
        self,
        owner_id: str,
        report_id: str,
        *,
        expected_version: int,
        supplement: str,
        next_week_plan: str,
        risks: str,
    ) -> WeeklyReport:
        report = await self.get(owner_id, report_id)
        next_content_json = _replace_weekly_free_text(
            report.content_json,
            supplement=supplement,
            next_week_plan=next_week_plan,
            risks=risks,
        )
        updated = await self._reports.save_content(
            report_id=report_id,
            owner_id=owner_id,
            expected_version=expected_version,
            content_json=next_content_json,
            updated_at=self._clock(),
        )
        if not updated:
            await self._session.rollback()
            raise WeeklyReportVersionConflictError()
        await self._session.commit()
        return await self.get(owner_id, report_id)

    async def regenerate(
        self,
        owner_id: str,
        report_id: str,
        *,
        expected_version: int,
        confirm_overwrite: bool,
    ) -> WeeklyReport:
        if not confirm_overwrite:
            raise WeeklyRegenerateNotConfirmedError()
        report = await self.get(owner_id, report_id)
        week_end = week_end_for(report.week_start)
        archived = await self._daily_reports.list_owned_archived_by_range(
            owner_id, date_from=report.week_start, date_to=week_end
        )
        now = self._clock()
        content_json = _serialize_weekly_content_v2(build_weekly_content(archived), archived)
        updated = await self._reports.replace_on_regenerate(
            report_id=report_id,
            owner_id=owner_id,
            expected_version=expected_version,
            week_end=week_end,
            generated_content_json=content_json,
            content_json=content_json,
            generated_at=now,
        )
        if not updated:
            await self._session.rollback()
            raise WeeklyReportVersionConflictError()
        await self._reports.replace_sources(report_id, _sources_for(archived, now))
        await self._session.commit()
        return await self.get(owner_id, report_id)


def _each_day(week_start: date, week_end: date) -> list[date]:
    days = []
    current = week_start
    while current <= week_end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _sources_for(reports: list[DailyReport], included_at: datetime) -> list[WeeklySource]:
    return [
        WeeklySource(
            daily_report_id=r.day_id,
            work_date=r.work_date,
            included_at=included_at,
        )
        for r in reports
    ]
