from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import delete, exists, func, insert, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyReport, DailyReportDay, User


class DailyReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, report: DailyReport) -> None:
        self._session.add(report)
        await self._session.flush()

    async def get_for_owner(self, report_id: str, owner_id: str) -> DailyReport | None:
        result = await self._session.execute(
            select(DailyReport)
            .join(DailyReportDay, DailyReport.day_id == DailyReportDay.id)
            .where(
                DailyReport.id == report_id,
                DailyReportDay.user_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_client_request_id(self, client_request_id: str) -> DailyReport | None:
        result = await self._session.execute(
            select(DailyReport).where(DailyReport.client_request_id == client_request_id)
        )
        return result.scalar_one_or_none()

    async def list_by_day(self, day_id: str) -> list[DailyReport]:
        result = await self._session.execute(
            select(DailyReport)
            .where(DailyReport.day_id == day_id)
            .order_by(DailyReport.submitted_at.asc(), DailyReport.id.asc())
        )
        return list(result.scalars())

    async def count_submitted_or_archived_in_range(
        self, owner_id: str, *, date_from: date, date_to: date
    ) -> int:
        """`daily_report_count` (`docs/方案设计.md` §8.6): submitted + archived

        source entries whose work date falls in the month, drafts excluded;
        a day's own aggregated official record is never counted again since
        it isn't a `daily_reports` row.
        """
        result = await self._session.execute(
            select(func.count())
            .select_from(DailyReport)
            .join(DailyReportDay, DailyReport.day_id == DailyReportDay.id)
            .where(
                DailyReportDay.user_id == owner_id,
                DailyReportDay.work_date >= date_from,
                DailyReportDay.work_date <= date_to,
                DailyReport.status.in_(("submitted", "archived")),
            )
        )
        return result.scalar_one()

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
        filters = [DailyReportDay.user_id == owner_id]
        if date_from is not None:
            filters.append(DailyReportDay.work_date >= date_from)
        if date_to is not None:
            filters.append(DailyReportDay.work_date <= date_to)
        if status is not None:
            filters.append(DailyReport.status == status)
        total_result = await self._session.execute(
            select(func.count())
            .select_from(DailyReport)
            .join(DailyReportDay, DailyReport.day_id == DailyReportDay.id)
            .where(*filters)
        )
        items_result = await self._session.execute(
            select(DailyReport)
            .join(DailyReportDay, DailyReport.day_id == DailyReportDay.id)
            .where(*filters)
            .order_by(DailyReportDay.work_date.desc(), DailyReport.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(items_result.scalars()), total_result.scalar_one()

    async def insert_entry_if_day_open(self, report: DailyReport) -> bool:
        """Inserts a new draft entry iff its day is still open, atomically.

        Mirrors `UserRepository.create_first_user_if_empty`: folding the
        "is the day still open" check into the INSERT itself (rather than
        SELECT-then-INSERT) closes the race window against a concurrent
        day-archive that `database.md` §8.2 requires — the day-archive flow
        acquires SQLite's single writer lock before this statement can run,
        so whichever transaction reaches its write first determines the
        winner; the loser observes `rowcount == 0` and must re-derive the
        day's current state (see `DailyReportService.create`).
        """
        stmt = insert(DailyReport).from_select(
            [
                "id",
                "day_id",
                "client_request_id",
                "status",
                "template_version_id",
                "template_snapshot_json",
                "content_json",
                "version",
            ],
            select(
                literal(report.id),
                literal(report.day_id),
                literal(report.client_request_id),
                literal(report.status),
                literal(report.template_version_id),
                literal(report.template_snapshot_json),
                literal(report.content_json),
                literal(report.version),
            ).where(
                exists(
                    select(DailyReportDay.id).where(
                        DailyReportDay.id == report.day_id,
                        DailyReportDay.status == "open",
                    )
                )
            ),
        )
        result = await self._session.execute(stmt)
        return bool(result.rowcount == 1)

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
                DailyReport.day_id.in_(
                    select(DailyReportDay.id).where(DailyReportDay.user_id == owner_id)
                ),
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

    async def delete_draft(
        self,
        *,
        report_id: str,
        owner_id: str,
        expected_version: int,
    ) -> bool:
        result = await self._session.execute(
            delete(DailyReport).where(
                DailyReport.id == report_id,
                DailyReport.day_id.in_(
                    select(DailyReportDay.id).where(DailyReportDay.user_id == owner_id)
                ),
                DailyReport.status == "draft",
                DailyReport.version == expected_version,
            )
        )
        return bool(result.rowcount == 1)

    async def count_by_day(self, day_id: str) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(DailyReport).where(DailyReport.day_id == day_id)
        )
        return result.scalar_one()

    async def submit_draft(
        self,
        *,
        report_id: str,
        owner_id: str,
        expected_version: int,
        submitted_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            update(DailyReport)
            .where(
                DailyReport.id == report_id,
                DailyReport.day_id.in_(
                    select(DailyReportDay.id).where(DailyReportDay.user_id == owner_id)
                ),
                DailyReport.status == "draft",
                DailyReport.version == expected_version,
            )
            .values(
                status="submitted",
                submitted_at=submitted_at,
                updated_at=submitted_at,
                version=DailyReport.version + 1,
            )
        )
        return bool(result.rowcount == 1)

    async def archive_entries(self, *, day_id: str, archived_at: datetime) -> int:
        result = await self._session.execute(
            update(DailyReport)
            .where(DailyReport.day_id == day_id, DailyReport.status == "submitted")
            .values(
                status="archived",
                archived_at=archived_at,
                updated_at=archived_at,
                version=DailyReport.version + 1,
            )
        )
        return int(result.rowcount)

    async def revoke_submission(
        self,
        *,
        report_id: str,
        expected_version: int,
        revoked_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            update(DailyReport)
            .where(
                DailyReport.id == report_id,
                DailyReport.status == "submitted",
                DailyReport.version == expected_version,
                DailyReport.day_id.in_(
                    select(DailyReportDay.id).where(DailyReportDay.status == "open")
                ),
            )
            .values(
                status="draft",
                submitted_at=None,
                updated_at=revoked_at,
                version=DailyReport.version + 1,
            )
        )
        return bool(result.rowcount == 1)

    async def list_submitted_awaiting_archive(
        self, *, page: int, page_size: int
    ) -> tuple[list["AdminSubmittedEntry"], int]:
        filters = (DailyReport.status == "submitted", DailyReportDay.status == "open")
        total_result = await self._session.execute(
            select(func.count())
            .select_from(DailyReport)
            .join(DailyReportDay, DailyReport.day_id == DailyReportDay.id)
            .where(*filters)
        )
        items_result = await self._session.execute(
            select(
                DailyReport.id,
                DailyReport.version,
                DailyReport.submitted_at,
                DailyReportDay.work_date,
                DailyReportDay.user_id,
                User.username,
                User.display_name,
            )
            .join(DailyReportDay, DailyReport.day_id == DailyReportDay.id)
            .join(User, User.id == DailyReportDay.user_id)
            .where(*filters)
            .order_by(DailyReport.submitted_at.asc(), DailyReport.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [
            AdminSubmittedEntry(
                id=row.id,
                version=row.version,
                submitted_at=row.submitted_at,
                work_date=row.work_date,
                owner_id=row.user_id,
                owner_username=row.username,
                owner_display_name=row.display_name,
            )
            for row in items_result.all()
        ]
        return items, total_result.scalar_one()

    async def get_submitted_metadata(self, report_id: str) -> "AdminSubmittedEntry | None":
        result = await self._session.execute(
            select(
                DailyReport.id,
                DailyReport.version,
                DailyReport.submitted_at,
                DailyReportDay.work_date,
                DailyReportDay.user_id,
                User.username,
                User.display_name,
            )
            .join(DailyReportDay, DailyReport.day_id == DailyReportDay.id)
            .join(User, User.id == DailyReportDay.user_id)
            .where(DailyReport.id == report_id, DailyReport.status == "submitted")
        )
        row = result.first()
        if row is None:
            return None
        return AdminSubmittedEntry(
            id=row.id,
            version=row.version,
            submitted_at=row.submitted_at,
            work_date=row.work_date,
            owner_id=row.user_id,
            owner_username=row.username,
            owner_display_name=row.display_name,
        )


@dataclass(frozen=True)
class AdminSubmittedEntry:
    """Minimal, whitelisted metadata for admin revocation (ADR-017).

    Deliberately excludes `content_json`/`template_snapshot_json`: the
    admin-facing query selects individual columns rather than full ORM
    entities so the body of a submitted entry can never reach an admin
    response, matching `architecture.md` §13.2 ("管理员查询 SQL 不选择正文列").
    """

    id: str
    version: int
    submitted_at: datetime | None
    work_date: date
    owner_id: str
    owner_username: str
    owner_display_name: str
