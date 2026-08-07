import json
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.core.ulid import generate_ulid
from app.models import DailyReportDay, WeeklyReport
from app.repositories.daily_report import DailyReportRepository
from app.repositories.daily_report_day import DailyReportDayRepository
from app.repositories.weekly_report import WeeklyReportRepository, WeeklySource
from app.schemas.daily_report import DailyStatus
from app.schemas.weekly_report import (
    WeeklyAvailabilityData,
    WeeklyAvailabilityDay,
    WeeklyContent,
    WeeklyDay,
    WeeklyDayEntry,
    WeeklyDayField,
)
from app.services.daily_report_day import parse_day_archive_snapshot

WEEK_LENGTH = timedelta(days=6)


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


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def parse_weekly_content(content_json: str) -> WeeklyContent:
    """Parses the `schema_version=2` day/entries JSON (`database.md` §8.1).

    BE-10A's migration unconditionally upgrades every pre-existing row to
    this shape before the application ever serves traffic, so there is no
    remaining V1 (flat, single-source) shape to fall back to — the earlier
    compatibility branch this function had is gone as of `BE-10C`.
    """
    raw = json.loads(content_json)
    if (
        not isinstance(raw, dict)
        or raw.get("schema_version") != 2
        or not isinstance(raw.get("days"), list)
    ):
        raise RuntimeError("stored weekly content has an unsupported schema version")

    days: list[WeeklyDay] = []
    for day in raw["days"]:
        if (
            not isinstance(day, dict)
            or not isinstance(day.get("entries"), list)
            or not isinstance(day.get("daily_report_day_id"), str)
        ):
            raise RuntimeError("stored weekly content contains an invalid day")
        entries = day["entries"]
        if day.get("source_count") != len(entries):
            raise RuntimeError("stored weekly content source count does not match entries")
        parsed_entries: list[WeeklyDayEntry] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise RuntimeError("stored weekly content contains an invalid entry")
            parsed_entries.append(
                WeeklyDayEntry(
                    daily_report_id=entry.get("daily_report_id"),
                    submitted_at=entry.get("submitted_at"),
                    fields=entry.get("fields", []),
                )
            )
        days.append(
            WeeklyDay(
                work_date=day.get("work_date"),
                daily_report_day_id=day["daily_report_day_id"],
                entries=parsed_entries,
            )
        )
    return WeeklyContent(
        days=days,
        supplement=raw.get("supplement", ""),
        next_week_plan=raw.get("next_week_plan", ""),
        risks=raw.get("risks", ""),
    )


def _serialize_weekly_content(content: WeeklyContent) -> str:
    return json.dumps(
        {
            "schema_version": 2,
            "days": [
                {
                    "work_date": day.work_date.isoformat(),
                    "daily_report_day_id": day.daily_report_day_id,
                    "source_count": len(day.entries),
                    "entries": [
                        {
                            "daily_report_id": entry.daily_report_id,
                            "submitted_at": _utc_iso(entry.submitted_at),
                            "fields": [field.model_dump(mode="json") for field in entry.fields],
                        }
                        for entry in day.entries
                    ],
                }
                for day in content.days
            ],
            "supplement": content.supplement,
            "next_week_plan": content.next_week_plan,
            "risks": content.risks,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _serialize_source_snapshot(days: list[DailyReportDay]) -> str:
    snapshot_days: list[dict[str, object]] = []
    for day in days:
        snapshot = parse_day_archive_snapshot(day.archive_snapshot_json or "")
        snapshot_days.append(
            {
                "work_date": day.work_date.isoformat(),
                "daily_report_day_id": day.id,
                "source_count": len(snapshot.entries),
                "entries": [
                    {
                        "daily_report_id": entry.daily_report_id,
                        "submitted_at": _utc_iso(entry.submitted_at),
                    }
                    for entry in snapshot.entries
                ],
            }
        )
    return json.dumps(
        {"schema_version": 2, "days": snapshot_days},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _replace_weekly_free_text(
    content_json: str, *, supplement: str, next_week_plan: str, risks: str
) -> str:
    current = parse_weekly_content(content_json)
    return _serialize_weekly_content(
        current.model_copy(
            update={
                "supplement": supplement,
                "next_week_plan": next_week_plan,
                "risks": risks,
            }
        )
    )


def build_weekly_content(
    days: list[DailyReportDay],
    *,
    supplement: str = "",
    next_week_plan: str = "",
    risks: str = "",
) -> WeeklyContent:
    """Pure function: folds each archived day's official snapshot into a week.

    Reads only each day's own `archive_snapshot_json` (never the current
    template), so later template changes cannot alter a week already
    generated. Only fields still `enabled` in each entry's own snapshot are
    carried over, matching how the daily UI itself only showed those fields
    at archive time.
    """
    weekly_days: list[WeeklyDay] = []
    for day in days:
        snapshot = parse_day_archive_snapshot(day.archive_snapshot_json or "")
        entries: list[WeeklyDayEntry] = []
        for entry in snapshot.entries:
            enabled = sorted(
                (field for field in entry.template_snapshot if field.enabled),
                key=lambda field: field.sort_order,
            )
            entries.append(
                WeeklyDayEntry(
                    daily_report_id=entry.daily_report_id,
                    submitted_at=entry.submitted_at,
                    fields=[
                        WeeklyDayField(
                            field_key=field.field_key,
                            label=field.label,
                            value=entry.content.get(field.field_key),
                        )
                        for field in enabled
                    ],
                )
            )
        weekly_days.append(
            WeeklyDay(work_date=day.work_date, daily_report_day_id=day.id, entries=entries)
        )
    return WeeklyContent(
        days=weekly_days, supplement=supplement, next_week_plan=next_week_plan, risks=risks
    )


class WeeklyReportService:
    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._reports = WeeklyReportRepository(session)
        self._daily_reports = DailyReportRepository(session)
        self._days = DailyReportDayRepository(session)

    async def availability(self, owner_id: str, week_start: date) -> WeeklyAvailabilityData:
        week_end = week_end_for(week_start)
        days = await self._days.list_in_range(owner_id, date_from=week_start, date_to=week_end)
        by_date = {day.work_date: day for day in days}

        availability_days: list[WeeklyAvailabilityDay] = []
        archived_count = 0
        non_archived_dates: list[date] = []
        for current in _each_day(week_start, week_end):
            day = by_date.get(current)
            status: DailyStatus | None = None
            if day is not None:
                if day.status == "archived":
                    status = "archived"
                    archived_count += 1
                else:
                    entries = await self._daily_reports.list_by_day(day.id)
                    if any(entry.status == "draft" for entry in entries):
                        status = "draft"
                    elif any(entry.status == "submitted" for entry in entries):
                        status = "submitted"
                    if status is not None:
                        non_archived_dates.append(current)
            availability_days.append(WeeklyAvailabilityDay(work_date=current, status=status))

        existing = await self._reports.get_by_owner_week(owner_id, week_start)
        return WeeklyAvailabilityData(
            week_start=week_start,
            week_end=week_end,
            days=availability_days,
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
        archived_days = await self._days.list_archived_in_range(
            owner_id, date_from=week_start, date_to=week_end
        )
        now = self._clock()
        content_json = _serialize_weekly_content(build_weekly_content(archived_days))
        report = WeeklyReport(
            id=generate_ulid(),
            user_id=owner_id,
            week_start=week_start,
            week_end=week_end,
            generated_content_json=content_json,
            content_json=content_json,
            source_snapshot_json=_serialize_source_snapshot(archived_days),
            generated_at=now,
            version=1,
        )
        try:
            await self._reports.add(report)
            await self._reports.replace_sources(report.id, _sources_for(archived_days, now))
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
        archived_days = await self._days.list_archived_in_range(
            owner_id, date_from=report.week_start, date_to=week_end
        )
        now = self._clock()
        content_json = _serialize_weekly_content(build_weekly_content(archived_days))
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
        await self._reports.replace_sources(report_id, _sources_for(archived_days, now))
        await self._session.commit()
        return await self.get(owner_id, report_id)


def _each_day(week_start: date, week_end: date) -> list[date]:
    days = []
    current = week_start
    while current <= week_end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _sources_for(days: list[DailyReportDay], included_at: datetime) -> list[WeeklySource]:
    return [
        WeeklySource(
            daily_report_day_id=day.id,
            work_date=day.work_date,
            included_at=included_at,
        )
        for day in days
    ]
