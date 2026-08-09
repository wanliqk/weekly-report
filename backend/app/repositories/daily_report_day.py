from datetime import date, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyReportDay


class DailyReportDayRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, day: DailyReportDay) -> None:
        self._session.add(day)
        await self._session.flush()

    async def get_for_owner_by_date(self, owner_id: str, work_date: date) -> DailyReportDay | None:
        result = await self._session.execute(
            select(DailyReportDay).where(
                DailyReportDay.user_id == owner_id,
                DailyReportDay.work_date == work_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_owner_by_id(self, owner_id: str, day_id: str) -> DailyReportDay | None:
        """Added for WECOM-06's preview endpoint, whose request body carries
        `daily_report_day_id` directly (`docs/方案设计.md` §5.2) rather than a
        `work_date` path segment."""
        result = await self._session.execute(
            select(DailyReportDay).where(
                DailyReportDay.id == day_id,
                DailyReportDay.user_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_in_range(
        self, owner_id: str, *, date_from: date, date_to: date
    ) -> list[DailyReportDay]:
        result = await self._session.execute(
            select(DailyReportDay)
            .where(
                DailyReportDay.user_id == owner_id,
                DailyReportDay.work_date >= date_from,
                DailyReportDay.work_date <= date_to,
            )
            .order_by(DailyReportDay.work_date.asc())
        )
        return list(result.scalars())

    async def list_archived_in_range(
        self, owner_id: str, *, date_from: date | None = None, date_to: date | None = None
    ) -> list[DailyReportDay]:
        filters = [DailyReportDay.user_id == owner_id, DailyReportDay.status == "archived"]
        if date_from is not None:
            filters.append(DailyReportDay.work_date >= date_from)
        if date_to is not None:
            filters.append(DailyReportDay.work_date <= date_to)
        result = await self._session.execute(
            select(DailyReportDay).where(*filters).order_by(DailyReportDay.work_date.asc())
        )
        return list(result.scalars())

    async def list_archived_work_dates_on_or_before(
        self, owner_id: str, *, on_or_before: date
    ) -> list[date]:
        """Every archived date up to and including `on_or_before`, newest first.

        Feeds the streak calculation (`StatisticsService`), which walks
        backward day by day until it finds a gap; unbounded on purpose since
        a personal daily-report history is small even after years of use.
        """
        result = await self._session.execute(
            select(DailyReportDay.work_date)
            .where(
                DailyReportDay.user_id == owner_id,
                DailyReportDay.status == "archived",
                DailyReportDay.work_date <= on_or_before,
            )
            .order_by(DailyReportDay.work_date.desc())
        )
        return [row[0] for row in result.all()]

    async def get_by_ids_for_owner_archived(
        self, owner_id: str, day_ids: list[str]
    ) -> list[DailyReportDay]:
        result = await self._session.execute(
            select(DailyReportDay)
            .where(
                DailyReportDay.user_id == owner_id,
                DailyReportDay.status == "archived",
                DailyReportDay.id.in_(day_ids),
            )
            .order_by(DailyReportDay.work_date.asc())
        )
        return list(result.scalars())

    async def touch_open_for_write(self, *, day_id: str, owner_id: str, now: datetime) -> bool:
        """Reserves the SQLite write lock and re-verifies the day is still open.

        Must run as the first write statement in the caller's transaction and
        before any read of the day's entries: SQLite only allows one writer
        transaction at a time, so this statement blocks (up to
        `busy_timeout`) any concurrent create/save/delete/submit/archive on
        the same day until the caller commits or rolls back, closing the race
        window described in `database.md` §8.2 (ADR-016). Returns `False`
        when the day was archived (or vanished) since it was last read.
        """
        result = await self._session.execute(
            update(DailyReportDay)
            .where(
                DailyReportDay.id == day_id,
                DailyReportDay.user_id == owner_id,
                DailyReportDay.status == "open",
            )
            .values(updated_at=now)
        )
        return bool(result.rowcount == 1)

    async def finalize_archive(
        self,
        *,
        day_id: str,
        owner_id: str,
        archive_snapshot_json: str,
        source_count: int,
        archived_by: str,
        archived_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            update(DailyReportDay)
            .where(
                DailyReportDay.id == day_id,
                DailyReportDay.user_id == owner_id,
                DailyReportDay.status == "open",
            )
            .values(
                status="archived",
                archive_snapshot_json=archive_snapshot_json,
                source_count=source_count,
                archived_by=archived_by,
                archived_at=archived_at,
                updated_at=archived_at,
                version=DailyReportDay.version + 1,
            )
        )
        return bool(result.rowcount == 1)

    async def delete_if_empty_open(self, *, day_id: str, owner_id: str) -> bool:
        """Removes an open day container that no longer has any entries.

        Only ever called by the draft-deletion flow after it has confirmed
        (within the same transaction, holding SQLite's write lock) that zero
        entries reference this day; see `database.md` §8.4.
        """
        result = await self._session.execute(
            delete(DailyReportDay).where(
                DailyReportDay.id == day_id,
                DailyReportDay.user_id == owner_id,
                DailyReportDay.status == "open",
            )
        )
        return bool(result.rowcount == 1)
