from datetime import datetime

from sqlalchemy import delete, exists, func, insert, literal, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DailyReportDay,
    ExportJob,
    ReportTemplate,
    TemplateVersion,
    User,
    UserSettings,
    WeeklyReport,
)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def any_exists(self) -> bool:
        result = await self._session.execute(select(func.count()).select_from(User))
        return result.scalar_one() > 0

    async def get_by_username_normalized(self, username_normalized: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.username_normalized == username_normalized)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)

    async def list_page(self, *, page: int, page_size: int) -> tuple[list[User], int]:
        total_result = await self._session.execute(select(func.count()).select_from(User))
        items_result = await self._session.execute(
            select(User)
            .order_by(User.created_at.desc(), User.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(items_result.scalars()), total_result.scalar_one()

    async def add(self, user: User) -> None:
        self._session.add(user)
        await self._session.flush()

    async def update_account(
        self,
        user_id: str,
        *,
        display_name: str | None,
        role: str | None,
        is_active: bool | None,
        updated_at: datetime,
    ) -> bool:
        values: dict[str, object] = {"updated_at": updated_at}
        if display_name is not None:
            values["display_name"] = display_name
        if role is not None:
            values["role"] = role
        if is_active is not None:
            values["is_active"] = is_active
        if role is not None or is_active is not None:
            values["token_version"] = User.token_version + 1

        statement = update(User).where(User.id == user_id)
        if role == "user" or is_active is False:
            another_active_admin_exists = exists(
                select(User.id).where(
                    User.id != user_id,
                    User.role == "admin",
                    User.is_active.is_(True),
                )
            )
            statement = statement.where(
                or_(
                    User.role != "admin",
                    User.is_active.is_(False),
                    another_active_admin_exists,
                )
            )

        result = await self._session.execute(statement.values(**values))
        return bool(result.rowcount == 1)

    async def update_password(
        self,
        user_id: str,
        *,
        password_hash: str,
        password_changed_at: datetime,
        must_change_password: bool,
    ) -> bool:
        result = await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                password_hash=password_hash,
                password_changed_at=password_changed_at,
                updated_at=password_changed_at,
                token_version=User.token_version + 1,
                must_change_password=must_change_password,
            )
        )
        return bool(result.rowcount == 1)

    async def create_first_user_if_empty(self, user: User) -> bool:
        """Insert `user` iff the `users` table is currently empty, atomically.

        A plain "check row count, then insert" is racy: two concurrent
        bootstrap requests can both observe zero rows before either writes.
        Folding the check into the insert itself as `INSERT ... SELECT ...
        WHERE NOT EXISTS (...)` closes the gap for free: SQLite only ever
        lets one connection hold the write lock needed to execute this
        statement, so a second concurrent caller either blocks (up to
        `busy_timeout`) until the first commits — and then correctly sees
        the table as non-empty and inserts zero rows — or, if it runs
        first, wins outright. Two concurrent bootstrap attempts can never
        both succeed.
        """
        stmt = insert(User).from_select(
            [
                "id",
                "username",
                "username_normalized",
                "display_name",
                "password_hash",
                "role",
                "must_change_password",
                "password_changed_at",
            ],
            select(
                literal(user.id),
                literal(user.username),
                literal(user.username_normalized),
                literal(user.display_name),
                literal(user.password_hash),
                literal(user.role),
                literal(user.must_change_password),
                literal(user.password_changed_at),
            ).where(~select(User.id).exists()),
        )
        result = await self._session.execute(stmt)
        return bool(result.rowcount == 1)

    async def has_business_records(self, user_id: str) -> bool:
        """Checks the three business tables `database.md` §8.4 names.

        `daily_reports` is deliberately not queried directly: every entry
        belongs to a `daily_report_days` row for the same owner, so the day
        container count already covers it transitively. Default resources
        every account gets at creation time (`user_settings`,
        `report_templates`/`template_versions`) are intentionally excluded —
        they are scaffolding, not the user's own business data, and would
        otherwise make every account permanently undeletable.
        """
        result = await self._session.execute(
            select(
                exists(select(DailyReportDay.id).where(DailyReportDay.user_id == user_id))
                | exists(select(WeeklyReport.id).where(WeeklyReport.user_id == user_id))
                | exists(select(ExportJob.id).where(ExportJob.user_id == user_id))
            )
        )
        return bool(result.scalar_one())

    async def has_business_records_bulk(self, user_ids: list[str]) -> set[str]:
        """Bulk form of `has_business_records`, for annotating a user list.

        Three grouped `IN (...)` queries (one per business table) instead of
        one `EXISTS` per user avoids an N+1 query pattern for `GET /users`.
        """
        if not user_ids:
            return set()
        day_owners = await self._session.execute(
            select(DailyReportDay.user_id).where(DailyReportDay.user_id.in_(user_ids)).distinct()
        )
        weekly_owners = await self._session.execute(
            select(WeeklyReport.user_id).where(WeeklyReport.user_id.in_(user_ids)).distinct()
        )
        export_owners = await self._session.execute(
            select(ExportJob.user_id).where(ExportJob.user_id.in_(user_ids)).distinct()
        )
        return (
            {row[0] for row in day_owners}
            | {row[0] for row in weekly_owners}
            | {row[0] for row in export_owners}
        )

    async def count_active_admins(self) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == "admin", User.is_active.is_(True))
        )
        return result.scalar_one()

    async def delete_if_no_business_records(self, user_id: str) -> bool:
        """Physically removes a user and their default scaffolding.

        Conditioned on no other active admin being required (mirrors
        `update_account`'s last-active-admin guard) so a concurrent
        deletion/demotion of the only other admin cannot leave the system
        without one. The caller must already have verified
        `has_business_records` is `False` inside the same transaction;
        `daily_report_days`/`weekly_reports`/`export_jobs` all reference
        `users.id` with `ON DELETE RESTRICT`, so a business record created
        concurrently after that check would make the final `DELETE FROM
        users` fail loudly (`IntegrityError`) rather than silently succeed.
        """
        another_active_admin_exists = exists(
            select(User.id).where(
                User.id != user_id,
                User.role == "admin",
                User.is_active.is_(True),
            )
        )
        await self._session.execute(delete(UserSettings).where(UserSettings.user_id == user_id))
        await self._session.execute(
            delete(TemplateVersion).where(
                TemplateVersion.template_id.in_(
                    select(ReportTemplate.id).where(ReportTemplate.user_id == user_id)
                )
            )
        )
        await self._session.execute(delete(ReportTemplate).where(ReportTemplate.user_id == user_id))
        result = await self._session.execute(
            delete(User).where(
                User.id == user_id,
                or_(User.role != "admin", another_active_admin_exists),
            )
        )
        return bool(result.rowcount == 1)
