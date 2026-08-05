from datetime import date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyReport


class DailyReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, report: DailyReport) -> None:
        self._session.add(report)
        await self._session.flush()

    async def get_for_owner(self, report_id: str, owner_id: str) -> DailyReport | None:
        result = await self._session.execute(
            select(DailyReport).where(
                DailyReport.id == report_id,
                DailyReport.user_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_work_date(self, owner_id: str, work_date: date) -> DailyReport | None:
        result = await self._session.execute(
            select(DailyReport).where(
                DailyReport.user_id == owner_id,
                DailyReport.work_date == work_date,
            )
        )
        return result.scalar_one_or_none()

    async def list_page(
        self,
        owner_id: str,
        *,
        date_from: date | None,
        date_to: date | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[DailyReport], int]:
        filters = [DailyReport.user_id == owner_id]
        if date_from is not None:
            filters.append(DailyReport.work_date >= date_from)
        if date_to is not None:
            filters.append(DailyReport.work_date <= date_to)
        if status is not None:
            filters.append(DailyReport.status == status)
        total_result = await self._session.execute(
            select(func.count()).select_from(DailyReport).where(*filters)
        )
        items_result = await self._session.execute(
            select(DailyReport)
            .where(*filters)
            .order_by(DailyReport.work_date.desc(), DailyReport.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(items_result.scalars()), total_result.scalar_one()

    async def save_draft(
        self,
        *,
        report_id: str,
        owner_id: str,
        expected_version: int,
        content_json: str,
        updated_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            update(DailyReport)
            .where(
                DailyReport.id == report_id,
                DailyReport.user_id == owner_id,
                DailyReport.status == "draft",
                DailyReport.version == expected_version,
            )
            .values(
                content_json=content_json,
                version=DailyReport.version + 1,
                updated_at=updated_at,
            )
        )
        return bool(result.rowcount == 1)

    async def submit_draft(
        self,
        *,
        report_id: str,
        owner_id: str,
        expected_version: int,
        submitted_at: datetime,
        auto_archive: bool,
    ) -> bool:
        values: dict[str, object] = {
            "status": "archived" if auto_archive else "submitted",
            "submitted_at": submitted_at,
            "updated_at": submitted_at,
            "version": DailyReport.version + 1,
        }
        if auto_archive:
            values["archived_at"] = submitted_at
        result = await self._session.execute(
            update(DailyReport)
            .where(
                DailyReport.id == report_id,
                DailyReport.user_id == owner_id,
                DailyReport.status == "draft",
                DailyReport.version == expected_version,
            )
            .values(**values)
        )
        return bool(result.rowcount == 1)

    async def archive_submitted(
        self,
        *,
        report_id: str,
        owner_id: str,
        expected_version: int,
        archived_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            update(DailyReport)
            .where(
                DailyReport.id == report_id,
                DailyReport.user_id == owner_id,
                DailyReport.status == "submitted",
                DailyReport.version == expected_version,
            )
            .values(
                status="archived",
                archived_at=archived_at,
                updated_at=archived_at,
                version=DailyReport.version + 1,
            )
        )
        return bool(result.rowcount == 1)
