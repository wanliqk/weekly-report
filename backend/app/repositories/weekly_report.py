from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WeeklyReport, WeeklyReportSource


@dataclass(frozen=True)
class WeeklySource:
    daily_report_day_id: str
    work_date: date
    included_at: datetime


class WeeklyReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, report: WeeklyReport) -> None:
        self._session.add(report)
        await self._session.flush()

    async def get_for_owner(self, report_id: str, owner_id: str) -> WeeklyReport | None:
        result = await self._session.execute(
            select(WeeklyReport).where(
                WeeklyReport.id == report_id,
                WeeklyReport.user_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_owner_week(self, owner_id: str, week_start: date) -> WeeklyReport | None:
        result = await self._session.execute(
            select(WeeklyReport).where(
                WeeklyReport.user_id == owner_id,
                WeeklyReport.week_start == week_start,
            )
        )
        return result.scalar_one_or_none()

    async def count_by_week_start_range(
        self, owner_id: str, *, date_from: date, date_to: date
    ) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(WeeklyReport)
            .where(
                WeeklyReport.user_id == owner_id,
                WeeklyReport.week_start >= date_from,
                WeeklyReport.week_start <= date_to,
            )
        )
        return result.scalar_one()

    async def list_page(
        self,
        owner_id: str,
        *,
        week_from: date | None,
        week_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[WeeklyReport], int]:
        filters = [WeeklyReport.user_id == owner_id]
        if week_from is not None:
            filters.append(WeeklyReport.week_start >= week_from)
        if week_to is not None:
            filters.append(WeeklyReport.week_start <= week_to)
        total_result = await self._session.execute(
            select(func.count()).select_from(WeeklyReport).where(*filters)
        )
        items_result = await self._session.execute(
            select(WeeklyReport)
            .where(*filters)
            .order_by(WeeklyReport.week_start.desc(), WeeklyReport.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(items_result.scalars()), total_result.scalar_one()

    async def save_content(
        self,
        *,
        report_id: str,
        owner_id: str,
        expected_version: int,
        content_json: str,
        updated_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            update(WeeklyReport)
            .where(
                WeeklyReport.id == report_id,
                WeeklyReport.user_id == owner_id,
                WeeklyReport.version == expected_version,
            )
            .values(
                content_json=content_json,
                version=WeeklyReport.version + 1,
                updated_at=updated_at,
            )
        )
        return bool(result.rowcount == 1)

    async def replace_on_regenerate(
        self,
        *,
        report_id: str,
        owner_id: str,
        expected_version: int,
        week_end: date,
        generated_content_json: str,
        content_json: str,
        generated_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            update(WeeklyReport)
            .where(
                WeeklyReport.id == report_id,
                WeeklyReport.user_id == owner_id,
                WeeklyReport.version == expected_version,
            )
            .values(
                week_end=week_end,
                generated_content_json=generated_content_json,
                content_json=content_json,
                generated_at=generated_at,
                updated_at=generated_at,
                version=WeeklyReport.version + 1,
            )
        )
        return bool(result.rowcount == 1)

    async def replace_sources(self, weekly_report_id: str, sources: list[WeeklySource]) -> None:
        await self._session.execute(
            delete(WeeklyReportSource).where(
                WeeklyReportSource.weekly_report_id == weekly_report_id
            )
        )
        for source in sources:
            self._session.add(
                WeeklyReportSource(
                    weekly_report_id=weekly_report_id,
                    daily_report_day_id=source.daily_report_day_id,
                    work_date=source.work_date,
                    included_at=source.included_at,
                )
            )
        await self._session.flush()
