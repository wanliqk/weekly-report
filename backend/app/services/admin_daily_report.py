import json
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.core.ulid import generate_ulid
from app.models import AdminAuditEvent, User
from app.repositories.admin_audit import AdminAuditRepository
from app.repositories.daily_report import AdminSubmittedEntry, DailyReportRepository

_REVOCATION_ACTION = "daily_submission_revoked"


class AdminDailyReportNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="待归档日报条目不存在")


class AdminDailyReportVersionConflictError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40904, http_status=409, message="日报已被更新。请重新加载。")


class AdminDailyReportService:
    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._reports = DailyReportRepository(session)
        self._audit = AdminAuditRepository(session)

    async def list_submitted(
        self, *, page: int, page_size: int
    ) -> tuple[list[AdminSubmittedEntry], int]:
        return await self._reports.list_submitted_awaiting_archive(page=page, page_size=page_size)

    async def revoke_submission(
        self,
        admin: User,
        report_id: str,
        *,
        expected_version: int,
        reason: str,
    ) -> AdminSubmittedEntry:
        target = await self._reports.get_submitted_metadata(report_id)
        if target is None:
            raise AdminDailyReportNotFoundError()

        now = self._clock()
        updated = await self._reports.revoke_submission(
            report_id=report_id,
            expected_version=expected_version,
            revoked_at=now,
        )
        if not updated:
            await self._session.rollback()
            current = await self._reports.get_submitted_metadata(report_id)
            if current is None:
                raise AdminDailyReportNotFoundError()
            raise AdminDailyReportVersionConflictError()

        await self._audit.add(
            AdminAuditEvent(
                id=generate_ulid(),
                action=_REVOCATION_ACTION,
                actor_user_id=admin.id,
                actor_username_snapshot=admin.username,
                target_type="daily_report",
                target_id=report_id,
                target_owner_id=target.owner_id,
                reason=reason,
                metadata_json=json.dumps(
                    {"work_date": target.work_date.isoformat()},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                created_at=now,
            )
        )
        await self._session.commit()
        return AdminSubmittedEntry(
            id=target.id,
            version=expected_version + 1,
            submitted_at=None,
            work_date=target.work_date,
            owner_id=target.owner_id,
            owner_username=target.owner_username,
            owner_display_name=target.owner_display_name,
        )

    async def list_audit_events(
        self,
        *,
        action: str | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AdminAuditEvent], int]:
        return await self._audit.list_page(
            action=action,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
